import time
import sqlite3 
import functools

# Cache dictionary to store query results
query_cache = {}

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

def cache_query(func):
    """
    Decorator that caches query results based on the SQL query string.
    Subsequent calls with the same query string will return the cached result
    instead of executing the query again.
    """
    @functools.wraps(func)
    def wrapper(conn, *args, **kwargs):
        # Extract the query string
        query = kwargs.get('query') if kwargs.get('query') else args[0] if args else None
        
        if not query:
            # If no query is provided, just call the original function
            return func(conn, *args, **kwargs)
        
        # Check if this query is in the cache
        if query in query_cache:
            print(f"Using cached result for query: {query}")
            return query_cache[query]
        
        # Otherwise, execute the function and cache the result
        print(f"Executing and caching query: {query}")
        result = func(conn, *args, **kwargs)
        query_cache[query] = result
        return result
    
    return wrapper

@with_db_connection
@cache_query
def fetch_users_with_cache(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

# First call will cache the result
users = fetch_users_with_cache(query="SELECT * FROM users")

# Second call will use the cached result
users_again = fetch_users_with_cache(query="SELECT * FROM users")
