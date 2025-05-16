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
    cursor = db_connection.cursor()
    
    offset = 0
    while True:
        # Fetch one batch from user_data table
        cursor.execute(
            "SELECT * FROM user_data ORDER BY id LIMIT %s OFFSET %s",
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

#############################

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
    cursor = db_connection.cursor()
    
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

def batch_processing(batch_size=100):
    """
    Process users in batches and yield those over the age of 25.
    
    Args:
        batch_size (int): The number of users to fetch and process in each batch
        
    Yields:
        dict: Each user over the age of 25
    """
    # Use the stream_users_in_batches function
    for batch in stream_users_in_batches(batch_size):
        filtered_count = 0
        
        # Process each user in the current batch
        for user in batch:
            # Yield users over 25 directly instead of collecting in a list
            if user['age'] > 25:
                yield user
                filtered_count += 1
                
        # Print progress information
        print(f"Processed batch of {len(batch)} users. "
              f"Found {filtered_count} users over 25 in this batch.")
