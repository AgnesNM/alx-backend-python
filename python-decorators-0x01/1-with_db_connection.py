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
