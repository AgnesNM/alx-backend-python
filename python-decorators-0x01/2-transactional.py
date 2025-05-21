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

def transactional(func):
    """
    Decorator that wraps a database operation inside a transaction.
    Automatically commits changes if the function executes successfully,
    or rolls back if an error occurs.
    """
    @functools.wraps(func)
    def wrapper(conn, *args, **kwargs):
        try:
            # Execute the function
            result = func(conn, *args, **kwargs)
            # If successful, commit the transaction
            conn.commit()
            return result
        except Exception as e:
            # If an error occurs, roll back the transaction
            conn.rollback()
            # Re-raise the exception to maintain the error information
            raise e
    return wrapper

@with_db_connection
@transactional
def update_user_email(conn, user_id, new_email):
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))

# Update user's email with automatic transaction handling
update_user_email(user_id=1, new_email='Crawford_Cartwright@hotmail.com')
