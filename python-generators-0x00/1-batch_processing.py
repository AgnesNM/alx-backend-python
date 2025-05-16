import sqlite3

def stream_users_in_batches(batch_size):
    """
    Generator function that fetches users from database in batches.
    
    Args:
        batch_size (int): Number of users to fetch in each batch
        
    Yields:
        list: A batch of user records
    """
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()
    
    # Get total count of users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # Calculate number of batches
    offset = 0
    
    while offset < total_users:
        cursor.execute(
            "SELECT * FROM users LIMIT ? OFFSET ?", 
            (batch_size, offset)
        )
        batch = cursor.fetchall()
        
        if not batch:
            break
            
        yield batch
        offset += batch_size
    
    cursor.close()
    connection.close()

def batch_processing(batch_size):
    """
    Processes batches of users, filtering for users over age 25.
    
    Args:
        batch_size (int): Size of each batch to process
        
    Yields:
        list: Filtered batch containing only users over 25
    """
    for batch in stream_users_in_batches(batch_size):
        # Assuming age is at index 2 in the user record
        filtered_batch = [user for user in batch if user[2] > 25]
        
        if filtered_batch:
            yield filtered_batch

# Example usage
def main():
    # Process users in batches of 100
    for filtered_batch in batch_processing(100):
        print(f"Processing batch with {len(filtered_batch)} users over 25")
        # Process the filtered batch here
        # For example: insert_into_target_table(filtered_batch)

if __name__ == "__main__":
    main()
