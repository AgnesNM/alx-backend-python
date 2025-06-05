import logging
from datetime import datetime

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
