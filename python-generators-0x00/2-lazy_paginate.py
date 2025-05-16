def paginate_users(page_size, offset):
    """
    Simulates fetching a page of users from a database.
    
    Args:
        page_size (int): Number of users to fetch per page
        offset (int): Starting position for fetching users
        
    Returns:
        list: A list of user records for the requested page
    """
    # This is a simulation - in a real app, you would query a database here
    # For example: SELECT * FROM users LIMIT page_size OFFSET offset
    
    # Simulating a database with 100 users
    all_users = [{"id": i, "name": f"User {i}"} for i in range(1, 101)]
    
    # Calculate the slice of users to return
    start_idx = offset
    end_idx = min(offset + page_size, len(all_users))
    
    # Return empty list if we've gone past the end
    if start_idx >= len(all_users):
        return []
    
    return all_users[start_idx:end_idx]


def lazy_paginate(page_size):
    """
    A generator function that lazily loads pages of users.
    Only fetches the next page when needed.
    
    Args:
        page_size (int): Number of users to fetch per page
        
    Yields:
        dict: User records one at a time
    """
    offset = 0
    
    while True:
        # Fetch the current page of results
        current_page = paginate_users(page_size, offset)
        
        # If the page is empty, we've reached the end
        if not current_page:
            break
        
        # Yield each user record individually
        for user in current_page:
            yield user
        
        # Update offset for the next page
        offset += page_size
