#!/usr/bin/env python3
"""
Module that provides a generator function to stream user data
from a database one row at a time.
"""
import sqlite3


def stream_users():
    """
    Generator function that connects to a database and yields
    rows from the user_data table one by one.
    
    Returns:
        generator: Yields one row at a time from the user_data table
    """
    # Establish a connection to the database
    conn = sqlite3.connect('user_database.db')
    
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    
    # Execute a SELECT query on the user_data table
    cursor.execute('SELECT * FROM user_data')
    
    # Fetch and yield one row at a time
    for row in cursor:
        yield row
    
    # Close the connection when done
    cursor.close()
    conn.close()
