import logging
from datetime import datetime
from django.http import HttpResponseForbidden

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
