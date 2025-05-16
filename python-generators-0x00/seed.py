import mysql.connector
import uuid
import csv
import os
from mysql.connector import Error

def connect_db():
    """Connects to the MySQL database server"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='password'  # Replace with your MySQL password
        )
        if connection.is_connected():
            print("Successfully connected to MySQL server")
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def create_database(connection):
    """Creates the database ALX_prodev if it does not exist"""
    try:
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS ALX_prodev")
        print("Database ALX_prodev created or already exists")
    except Error as e:
        print(f"Error while creating database: {e}")

def connect_to_prodev():
    """Connects to the ALX_prodev database in MySQL"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='password',  # Replace with your MySQL password
            database='ALX_prodev'
        )
        if connection.is_connected():
            print("Successfully connected to ALX_prodev database")
            return connection
    except Error as e:
        print(f"Error while connecting to ALX_prodev: {e}")
        return None

def create_table(connection):
    """Creates a table user_data if it does not exist with the required fields"""
    try:
        cursor = connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            user_id CHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            age DECIMAL(5,2) NOT NULL,
            INDEX (user_id)
        )
        """)
        print("Table user_data created or already exists")
    except Error as e:
        print(f"Error while creating table: {e}")

def insert_data(connection, data):
    """Inserts data in the database if it does not exist"""
    try:
        cursor = connection.cursor()
        
        # Check if record exists with this user_id
        check_query = "SELECT COUNT(*) FROM user_data WHERE user_id = %s"
        insert_query = """
        INSERT INTO user_data (user_id, name, email, age)
        VALUES (%s, %s, %s, %s)
        """
        
        for record in data:
            # If user_id is not provided, generate one
            if not record[0]:
                record[0] = str(uuid.uuid4())
                
            # Check if record exists
            cursor.execute(check_query, (record[0],))
            count = cursor.fetchone()[0]
            
            if count == 0:
                cursor.execute(insert_query, tuple(record))
                print(f"Inserted record for {record[1]}")
            else:
                print(f"Record with user_id {record[0]} already exists, skipping")
        
        connection.commit()
        print("Data insertion completed")
    except Error as e:
        print(f"Error while inserting data: {e}")

def load_csv_data(file_path):
    """Load data from CSV file"""
    data = []
    try:
        with open(file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            headers = next(csv_reader)  # Skip header row
            
            for row in csv_reader:
                # If no user_id provided, it will be generated in insert_data function
                if len(row) < 4:
                    row = [''] + row  # Add empty user_id if not provided
                data.append(row)
                
        return data
    except FileNotFoundError:
        print(f"CSV file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading CSV data: {e}")
        return []

def row_generator(connection, table_name="user_data", batch_size=100):
    """
    A generator function that streams rows from a database table one by one
    
    Args:
        connection: MySQL database connection
        table_name: Name of the table to stream from
        batch_size: Number of rows to fetch at once (for efficiency)
        
    Yields:
        One row at a time as a dictionary
    """
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get total number of rows for progress tracking
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        total_rows = cursor.fetchone()['count']
        print(f"Total rows to stream: {total_rows}")
        
        # Stream in batches for efficiency, but yield one by one
        offset = 0
        while True:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
            batch = cursor.fetchall()
            
            if not batch:  # No more rows
                break
                
            # Yield rows one by one
            for row in batch:
                yield row
                
            offset += len(batch)
            print(f"Progress: {min(offset, total_rows)}/{total_rows} rows processed")
            
    except Error as e:
        print(f"Error in row generator: {e}")
        raise StopIteration

def demonstrate_generator(connection):
    """Demonstrates the row generator functionality"""
    print("\nDemonstrating row generator:")
    try:
        # Use the generator to stream rows one by one
        for i, row in enumerate(row_generator(connection)):
            print(f"Row {i+1}: {row}")
            
            # Optional: add a limit for demonstration
            if i >= 9:  # Show only first 10 rows
                print("... more rows available ...")
                break
                
    except Exception as e:
        print(f"Error during generator demonstration: {e}")

def main():
    # Connect to MySQL server
    connection = connect_db()
    if connection:
        # Create database
        create_database(connection)
        connection.close()
        
        # Connect to the ALX_prodev database
        db_connection = connect_to_prodev()
        if db_connection:
            # Create table
            create_table(db_connection)
            
            # Check if CSV file exists
            csv_file = 'user_data.csv'
            if os.path.exists(csv_file):
                # Load and insert data
                data = load_csv_data(csv_file)
                if data:
                    insert_data(db_connection, data)
                    
                    # Demonstrate the row generator
                    demonstrate_generator(db_connection)
            else:
                print(f"CSV file '{csv_file}' not found. Please provide a CSV file with user data.")
            
            # Close the connection
            if db_connection.is_connected():
                db_connection.close()
                print("MySQL connection closed")
    
if __name__ == "__main__":
    main()
