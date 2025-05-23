import sqlite3
import os

class DatabaseConnection:
    """
    A custom class-based context manager for handling database connections.
    Automatically opens connection on enter and closes on exit.
    """
    
    def __init__(self, database_path):
        """
        Initialize the context manager with database path.
        
        Args:
            database_path (str): Path to the database file
        """
        self.database_path = database_path
        self.connection = None
        self.cursor = None
    
    def __enter__(self):
        """
        Enter the context manager - establish database connection.
        
        Returns:
            sqlite3.Cursor: Database cursor for executing queries
        """
        try:
            print(f"Opening database connection to: {self.database_path}")
            self.connection = sqlite3.connect(self.database_path)
            self.cursor = self.connection.cursor()
            print("Database connection established successfully")
            return self.cursor
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
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
    
    # Insert sample data
    sample_users = [
        ('John Doe', 'john.doe@example.com', 30),
        ('Jane Smith', 'jane.smith@example.com', 25),
        ('Bob Johnson', 'bob.johnson@example.com', 35),
        ('Alice Brown', 'alice.brown@example.com', 28)
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
    Demonstrate the DatabaseConnection context manager usage.
    """
    db_path = "sample_database.db"
    
    # Setup sample database
    setup_sample_database(db_path)
    
    print("\n" + "="*50)
    print("Using DatabaseConnection Context Manager")
    print("="*50)
    
    # Use the context manager to query the database
    try:
        with DatabaseConnection(db_path) as cursor:
            print("\nExecuting query: SELECT * FROM users")
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
            
            print("\nQuery results:")
            print("-" * 40)
            print(f"{'ID':<5} {'Name':<15} {'Email':<25} {'Age':<5}")
            print("-" * 40)
            
            for row in results:
                print(f"{row[0]:<5} {row[1]:<15} {row[2]:<25} {row[3]:<5}")
            
            print(f"\nTotal users found: {len(results)}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    print("\n" + "="*50)
    print("Context manager demonstration completed")
    print("="*50)
    
    # Clean up - remove sample database
    try:
        os.remove(db_path)
        print(f"Sample database {db_path} removed")
    except OSError:
        pass


if __name__ == "__main__":
    main()
