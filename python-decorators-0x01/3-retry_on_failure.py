import time
import sqlite3 
import functools

def with_db_connection(func):
    """
    Decorator that automatically handles opening and closing database connections.
    Opens a SQLite connection, passes it to the decorated function, and ensures
    the connection is closed afterward, even if an exception occurs.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Open a connection to the database
        conn = sqlite3.connect('users.db')
        try:
            # Add the connection as the first argument
            result = func(conn, *args, **kwargs)
            return result
        finally:
            # Ensure the connection is closed, even if an exception occurs
            conn.close()
    return wrapper

def retry_on_failure(retries=3, delay=2):
    """
    Decorator that retries a database operation if it fails due to transient errors.
    
    Args:
        retries: Number of times to retry the operation before giving up (default: 3)
        delay: Number of seconds to wait between retries (default: 2)
    
    Returns:
        Decorator function that wraps the original function with retry logic
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None
            
            # Try the operation up to 'retries' times
            while attempts < retries + 1:  # +1 for the initial attempt
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    last_exception = e
                    
                    # If we've used all our retries, re-raise the last exception
                    if attempts > retries:
                        print(f"Operation failed after {retries} retries")
                        raise last_exception
                    
                    # Otherwise, wait and try again
                    print(f"Attempt {attempts} failed. Retrying in {delay} seconds...")
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception if last_exception else Exception("Unknown error occurred")
        return wrapper
    return decorator

@with_db_connection
@retry_on_failure(retries=3, delay=1)
def fetch_users_with_retry(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# Attempt to fetch users with automatic retry on failure
users = fetch_users_with_retry()
print(users)
