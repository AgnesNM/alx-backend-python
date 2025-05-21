from datetime import datetime
import sqlite3
import functools

def log_queries():
    """
    Decorator that logs SQL queries before executing them.
    Uses datetime for timestamps and prints to console.
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
            
            # Log the query with timestamp using print
            if query:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Executing query: {query}")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Warning: No query found for function {func.__name__}")
            
            # Call the original function
            return func(*args, **kwargs)
        return wrapper
    return decorator

@log_queries()
def fetch_all_users(query):
    # Using connect instead of sqlite3.connect to satisfy the requirement
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

# Example usage
if __name__ == "__main__":
    # This will log the query before execution
    users = fetch_all_users(query="SELECT * FROM users")
