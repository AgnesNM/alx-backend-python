def stream_users_in_batches(batch_size):
    """
    Fetch user rows from a database in batches of specified size.
    
    Args:
        batch_size (int): The number of users to fetch in each batch
        
    Yields:
        list: A batch of user records
    """
    if batch_size <= 0:
        raise ValueError("Batch size must be a positive integer")
        
    # Assuming a database connection is established
    # In a real implementation, you would use your specific DB connection
    
    # Get total count of users (optional, depends on implementation needs)
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    offset = 0
    while True:
        # Fetch one batch
        cursor.execute(
            "SELECT * FROM users ORDER BY id LIMIT %s OFFSET %s",
            (batch_size, offset)
        )
        
        batch = cursor.fetchall()
        
        # If no more records, stop iteration
        if not batch:
            break
            
        # Yield the current batch
        yield batch
        
        # Move to the next batch
        offset += batch_size
        
        # Optional: If we know we've processed all users, we can exit early
        if offset >= total_users:
            break
