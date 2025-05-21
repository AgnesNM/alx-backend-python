import functools
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('database')

def log_queries():
    """
    Decorator that logs SQL queries before executing them.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract the query from args or kwargs
            query = None
            if 'query' in kwargs:
                query = kwargs['query']
            elif args and isinstance(args[0], str):
                query = args[0]
            
            # Log the query if found
            if query:
                logger.info(f"Executing SQL query: {query}")
            else:
                logger.warning(f"No query found for function {func.__name__}")
            
            # Call the original function
            return func(*args, **kwargs)
        return wrapper
    return decorator
