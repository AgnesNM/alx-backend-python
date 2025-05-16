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

###################################

def batch_processing(batch_size=100):
    """
    Process users in batches and filter those over the age of 25.
    
    Args:
        batch_size (int): The number of users to fetch and process in each batch
        
    Returns:
        list: All users over the age of 25
    """
    filtered_users = []
    
    # Use the stream_users_in_batches function we defined earlier
    for batch in stream_users_in_batches(batch_size):
        # Process each user in the current batch
        for user in batch:
            # Assuming user is a dict or object with an 'age' attribute
            # Adapt this according to your actual data structure
            if user['age'] > 25:
                filtered_users.append(user)
                
        # Optional: Print progress information
        print(f"Processed batch of {len(batch)} users. "
              f"Found {len(filtered_users)} users over 25 so far.")
    
    return filtered_users
