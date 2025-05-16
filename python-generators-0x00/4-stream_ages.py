def stream_user_ages():
    """
    Generator function that streams user ages one by one from the database.
    This avoids loading the entire dataset into memory.
    
    Yields:
        int: Age of each user, one at a time
    """
    # Simulate database connection setup
    # In a real application: conn = database.connect(...)
    
    # We'll use batched fetching under the hood for efficiency
    # This is an implementation detail hidden from the caller
    offset = 0
    batch_size = 100  # Process in small batches for efficiency
    
    while True:
        # Construct SQL query to get a batch of user records
        # Note: We're NOT using SQL's AVG function as required
        query = f"SELECT age FROM users LIMIT {batch_size} OFFSET {offset}"
        
        # For simulation purposes only - in a real app you'd execute the query
        print(f"Executing: {query}")
        
        # Simulate fetching a batch of results
        # In a real app: results = cursor.execute(query).fetchall()
        
        # Create simulated data - would be your actual query results
        # Assume we have 1000 users total
        all_ages = [20 + (i % 60) for i in range(1, 1001)]  # Ages between 20-79
        
        start_idx = offset
        end_idx = min(offset + batch_size, len(all_ages))
        
        # Check if we've processed all records
        if start_idx >= len(all_ages):
            break
            
        # Get the current batch of ages
        current_batch = all_ages[start_idx:end_idx]
        
        # Yield each age individually from this batch
        for age in current_batch:
            yield age
            
        # Move to the next batch
        offset += batch_size


def calculate_average_age():
    """
    Calculates the average age of all users without loading the entire
    dataset into memory by using the stream_user_ages generator.
    
    Returns:
        float: The average age of all users
    """
    total_age = 0
    count = 0
    
    # Process one age at a time from the generator
    for age in stream_user_ages():
        total_age += age
        count += 1
    
    # Avoid division by zero
    if count == 0:
        return 0
        
    # Calculate and return the average
    return total_age / count


# Main execution
if __name__ == "__main__":
    average_age = calculate_average_age()
    print(f"Average age of users: {average_age:.2f}")
