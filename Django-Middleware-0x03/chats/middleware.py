import logging
from datetime import datetime, timedelta
from django.http import HttpResponseForbidden
from collections import defaultdict, deque

# Configure logger to write to file
logger = logging.getLogger('request_logger')
logger.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler('user_requests.log')
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)

# Add handler to logger (avoid duplicate handlers)
if not logger.handlers:
    logger.addHandler(file_handler)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get user (handle anonymous users)
        user = request.user if request.user.is_authenticated else 'Anonymous'
        
        # Log the request information
        log_message = f"{datetime.now()} - User: {user} - Path: {request.path}"
        logger.info(log_message)
        
        # Process the request
        response = self.get_response(request)
        
        return response


class RestrictAccessByTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for messaging/chat URLs
        if self.is_messaging_request(request):
            current_hour = datetime.now().hour
            
            # Allow access only between 6 AM (6) and 9 PM (21)
            # Deny access between 9 PM and 6 AM (22, 23, 0, 1, 2, 3, 4, 5)
            if current_hour >= 22 or current_hour < 6:
                return HttpResponseForbidden(
                    """
                    <html>
                    <head><title>Access Restricted</title></head>
                    <body>
                        <h1>403 Forbidden</h1>
                        <p>Messaging is only available between 6:00 AM and 9:00 PM.</p>
                        <p>Current time: {}</p>
                        <p>Please try again during allowed hours.</p>
                    </body>
                    </html>
                    """.format(datetime.now().strftime("%I:%M %p"))
                )
        
        # Process the request normally if it's allowed
        response = self.get_response(request)
        return response
    
    def is_messaging_request(self, request):
        """
        Check if the request is for messaging/chat functionality.
        Customize these paths based on your app's URL structure.
        """
        messaging_paths = [
            '/messages/',
            '/chat/',
            '/messaging/',
            '/inbox/',
            '/conversations/',
        ]
        
        # Check if the request path starts with any messaging paths
        for path in messaging_paths:
            if request.path.startswith(path):
                return True
        
        return False


class RolepermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for admin/moderator-only actions
        if self.requires_admin_access(request):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return HttpResponseForbidden(
                    """
                    <html>
                    <head><title>Authentication Required</title></head>
                    <body>
                        <h1>403 Forbidden - Authentication Required</h1>
                        <p>You must be logged in to access this resource.</p>
                        <p>Please <a href="/login/">login</a> to continue.</p>
                    </body>
                    </html>
                    """
                )
            
            # Check if user has admin or moderator role
            if not self.has_required_role(request.user):
                return HttpResponseForbidden(
                    """
                    <html>
                    <head><title>Insufficient Permissions</title></head>
                    <body>
                        <h1>403 Forbidden - Insufficient Permissions</h1>
                        <p>You do not have permission to access this resource.</p>
                        <p>Only administrators and moderators can perform this action.</p>
                        <p>Current user: {}</p>
                        <p>Required role: Admin or Moderator</p>
                    </body>
                    </html>
                    """.format(request.user.username)
                )
        
        # Process the request normally if allowed
        response = self.get_response(request)
        return response
    
    def requires_admin_access(self, request):
        """
        Define which paths require admin/moderator access.
        Customize these paths based on your application's admin actions.
        """
        admin_paths = [
            '/admin/',
            '/dashboard/',
            '/manage/',
            '/moderate/',
            '/users/ban/',
            '/users/delete/',
            '/properties/approve/',
            '/properties/reject/',
            '/reports/',
            '/analytics/',
        ]
        
        # Check if the request path starts with any admin paths
        for path in admin_paths:
            if request.path.startswith(path):
                return True
        
        return False
    
    def has_required_role(self, user):
        """
        Check if the user has admin or moderator role.
        This method supports multiple ways of checking user roles.
        """
        # Method 1: Check if user is Django superuser (built-in admin)
        if user.is_superuser:
            return True
        
        # Method 2: Check if user is Django staff (can access admin interface)
        if user.is_staff:
            return True
        
        # Method 3: Check using Django groups (recommended approach)
        if user.groups.filter(name__in=['admin', 'administrator', 'moderator']).exists():
            return True
        
        # Method 4: Check using custom user model fields (if you have them)
        # Uncomment and modify based on your user model
        # if hasattr(user, 'role'):
        #     if user.role in ['admin', 'moderator']:
        #         return True
        
        # Method 5: Check using user permissions
        if user.has_perm('auth.change_user') or user.has_perm('auth.delete_user'):
            return True
        
        return False


class OffensiveLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Dictionary to store message timestamps for each IP address
        # Using deque to efficiently manage time-based sliding window
        self.ip_message_times = defaultdict(deque)
        self.rate_limit = 5  # Maximum messages per time window
        self.time_window = timedelta(minutes=1)  # 1 minute time window

    def __call__(self, request):
        # Check if this is a POST request to messaging endpoints (sending a message)
        if request.method == 'POST' and self.is_messaging_request(request):
            client_ip = self.get_client_ip(request)
            current_time = datetime.now()
            
            # Clean old timestamps outside the time window
            self.clean_old_timestamps(client_ip, current_time)
            
            # Check if user has exceeded the rate limit
            if len(self.ip_message_times[client_ip]) >= self.rate_limit:
                return HttpResponseForbidden(
                    """
                    <html>
                    <head><title>Rate Limit Exceeded</title></head>
                    <body>
                        <h1>403 Forbidden - Rate Limit Exceeded</h1>
                        <p>You have exceeded the message limit of {} messages per minute.</p>
                        <p>Please wait before sending another message.</p>
                        <p>Time remaining: {} seconds</p>
                    </body>
                    </html>
                    """.format(
                        self.rate_limit,
                        self.get_time_remaining(client_ip, current_time)
                    )
                )
            
            # Add current timestamp to the user's message history
            self.ip_message_times[client_ip].append(current_time)
        
        # Process the request normally
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """
        Get the client's IP address from the request.
        Handles cases where the request might be behind a proxy.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def clean_old_timestamps(self, ip, current_time):
        """
        Remove timestamps that are outside the current time window.
        """
        cutoff_time = current_time - self.time_window
        
        # Remove old timestamps from the left side of the deque
        while (self.ip_message_times[ip] and 
               self.ip_message_times[ip][0] < cutoff_time):
            self.ip_message_times[ip].popleft()
    
    def get_time_remaining(self, ip, current_time):
        """
        Calculate how much time the user needs to wait before sending another message.
        """
        if not self.ip_message_times[ip]:
            return 0
        
        oldest_message_time = self.ip_message_times[ip][0]
        time_when_allowed = oldest_message_time + self.time_window
        remaining_seconds = (time_when_allowed - current_time).total_seconds()
        
        return max(0, int(remaining_seconds))
    
    def is_messaging_request(self, request):
        """
        Check if the request is for messaging/chat functionality.
        """
        messaging_paths = [
            '/messages/',
            '/chat/',
            '/messaging/',
            '/inbox/',
            '/conversations/',
        ]
        
        # Check if the request path starts with any messaging paths
        for path in messaging_paths:
            if request.path.startswith(path):
                return True
        
        return False


class RolepermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for admin/moderator-only actions
        if self.requires_admin_access(request):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return HttpResponseForbidden(
                    """
                    <html>
                    <head><title>Authentication Required</title></head>
                    <body>
                        <h1>403 Forbidden - Authentication Required</h1>
                        <p>You must be logged in to access this resource.</p>
                        <p>Please <a href="/login/">login</a> to continue.</p>
                    </body>
                    </html>
                    """
                )
            
            # Check if user has admin or moderator role
            if not self.has_required_role(request.user):
                return HttpResponseForbidden(
                    """
                    <html>
                    <head><title>Insufficient Permissions</title></head>
                    <body>
                        <h1>403 Forbidden - Insufficient Permissions</h1>
                        <p>You do not have permission to access this resource.</p>
                        <p>Only administrators and moderators can perform this action.</p>
                        <p>Current user: {}</p>
                        <p>Required role: Admin or Moderator</p>
                    </body>
                    </html>
                    """.format(request.user.username)
                )
        
        # Process the request normally if allowed
        response = self.get_response(request)
        return response
    
    def requires_admin_access(self, request):
        """
        Define which paths require admin/moderator access.
        Customize these paths based on your application's admin actions.
        """
        admin_paths = [
            '/admin/',
            '/dashboard/',
            '/manage/',
            '/moderate/',
            '/users/ban/',
            '/users/delete/',
            '/properties/approve/',
            '/properties/reject/',
            '/reports/',
            '/analytics/',
        ]
        
        # Check if the request path starts with any admin paths
        for path in admin_paths:
            if request.path.startswith(path):
                return True
        
        return False
    
    def has_required_role(self, user):
        """
        Check if the user has admin or moderator role.
        This method supports multiple ways of checking user roles.
        """
        # Method 1: Check if user is Django superuser (built-in admin)
        if user.is_superuser:
            return True
        
        # Method 2: Check if user is Django staff (can access admin interface)
        if user.is_staff:
            return True
        
        # Method 3: Check using Django groups (recommended approach)
        if user.groups.filter(name__in=['admin', 'administrator', 'moderator']).exists():
            return True
        
        # Method 4: Check using custom user model fields (if you have them)
        # Uncomment and modify based on your user model
        # if hasattr(user, 'role'):
        #     if user.role in ['admin', 'moderator']:
        #         return True
        
        # Method 5: Check using user permissions
        if user.has_perm('auth.change_user') or user.has_perm('auth.delete_user'):
            return True
        
        return False
