import sqlite3
import os

class ExecuteQuery:
    """
    A reusable class-based context manager that handles database connection
    and query execution with parameters.
    """
    
    def __init__(self, database_path, query, parameters=None):
        """
        Initialize the context manager with database path, query, and parameters.
        
        Args:
            database_path (str): Path to the database file
            query (str): SQL query to execute
            parameters (tuple/list): Parameters for the query (optional)
        """
        self.database_path = database_path
        self.query = query
        self.parameters = parameters or ()
        self.connection = None
        self.cursor = None
        self.results = None
    
    def __enter__(self):
        """
        Enter the context manager - establish connection and execute query.
        
        Returns:
            list: Query results
        """
        try:
            print(f"Opening database connection to: {self.database_path}")
            self.connection = sqlite3.connect(self.database_path)
            self.cursor = self.connection.cursor()
            print("Database connection established successfully")
            
            # Execute the query with parameters
            print(f"Executing query: {self.query}")
            if self.parameters:
                print(f"With parameters: {self.parameters}")
                self.cursor.execute(self.query, self.parameters)
            else:
                self.cursor.execute(self.query)
            
            # Fetch results for SELECT queries
            if self.query.strip().upper().startswith('SELECT'):
                self.results = self.cursor.fetchall()
                print(f"Query executed successfully, {len(self.results)} rows returned")
            else:
                # For non-SELECT queries, return affected row count
                self.results = self.cursor.rowcount
                print(f"Query executed successfully, {self.results} rows affected")
            
            return self.results
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise
        except Exception as e:
            print(f"Error executing query: {e}")
            raise
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager - clean up database connection.
        
        Args:
            exc_type: Exception type (if any)
            exc_value: Exception value (if any)
            traceback: Exception traceback (if any)
        """
        if self.cursor:
            self.cursor.close()
            print("Database cursor closed")
        
        if self.connection:
            if exc_type is None:
                # No exception occurred, commit any pending transactions
                self.connection.commit()
                print("Database transaction committed")
            else:
                # Exception occurred, rollback any pending transactions
                self.connection.rollback()
                print(f"Database transaction rolled back due to: {exc_value}")
            
            self.connection.close()
            print("Database connection closed")
        
        # Return False to propagate any exceptions that occurred
        return False


def setup_sample_database(db_path):
    """
    Create a sample database with users table for demonstration.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER
        )
    ''')
    
    # Insert sample data with varied ages
    sample_users = [
        ('John Doe', 'john.doe@example.com', 30),
        ('Jane Smith', 'jane.smith@example.com', 25),
        ('Bob Johnson', 'bob.johnson@example.com', 35),
        ('Alice Brown', 'alice.brown@example.com', 28),
        ('Charlie Wilson', 'charlie.wilson@example.com', 22),
        ('Diana Miller', 'diana.miller@example.com', 40),
        ('Eve Davis', 'eve.davis@example.com', 26),
        ('Frank Garcia', 'frank.garcia@example.com', 33)
    ]
    
    cursor.executemany(
        'INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)',
        sample_users
    )
    
    conn.commit()
    conn.close()
    print(f"Sample database created at: {db_path}")


def main():
    """
    Demonstrate the ExecuteQuery context manager usage.
    """
    db_path = "sample_database.db"
    
    # Setup sample database
    setup_sample_database(db_path)
    
    print("\n" + "="*60)
    print("Using ExecuteQuery Context Manager")
    print("="*60)
    
    # Example 1: Query users with age > 25
    print("\nExample 1: SELECT * FROM users WHERE age > ?")
    print("-" * 50)
    
    try:
        with ExecuteQuery(db_path, "SELECT * FROM users WHERE age > ?", (25,)) as results:
            print("\nQuery results:")
            print("-" * 50)
            print(f"{'ID':<5} {'Name':<15} {'Email':<25} {'Age':<5}")
            print("-" * 50)
            
            for row in results:
                print(f"{row[0]:<5} {row[1]:<15} {row[2]:<25} {row[3]:<5}")
            
            print(f"\nUsers with age > 25: {len(results)}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    # Example 2: Different query - users with specific age
    print("\n" + "="*60)
    print("Additional Example: SELECT * FROM users WHERE age = ?")
    print("-" * 50)
    
    try:
        with ExecuteQuery(db_path, "SELECT * FROM users WHERE age = ?", (30,)) as results:
            print("\nQuery results:")
            print("-" * 40)
            print(f"{'ID':<5} {'Name':<15} {'Email':<25} {'Age':<5}")
            print("-" * 40)
            
            for row in results:
                print(f"{row[0]:<5} {row[1]:<15} {row[2]:<25} {row[3]:<5}")
            
            print(f"\nUsers with age = 30: {len(results)}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    # Example 3: Query without parameters
    print("\n" + "="*60)
    print("Example with no parameters: SELECT COUNT(*) FROM users")
    print("-" * 50)
    
    try:
        with ExecuteQuery(db_path, "SELECT COUNT(*) FROM users") as results:
            print(f"\nTotal number of users: {results[0][0]}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    print("\n" + "="*60)
    print("ExecuteQuery context manager demonstration completed")
    print("="*60)
    
    # Clean up - remove sample database
    try:
        os.remove(db_path)
        print(f"Sample database {db_path} removed")
    except OSError:
        pass


if __name__ == "__main__":
    main()
