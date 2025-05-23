import asyncio
import aiosqlite
import os
import time

async def setup_sample_database(db_path):
    """
    Create a sample database with users table for demonstration.
    """
    async with aiosqlite.connect(db_path) as conn:
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER
            )
        ''')
        
        # Insert sample data with varied ages, including users over 40
        sample_users = [
            ('John Doe', 'john.doe@example.com', 30),
            ('Jane Smith', 'jane.smith@example.com', 25),
            ('Bob Johnson', 'bob.johnson@example.com', 35),
            ('Alice Brown', 'alice.brown@example.com', 28),
            ('Charlie Wilson', 'charlie.wilson@example.com', 22),
            ('Diana Miller', 'diana.miller@example.com', 45),  # > 40
            ('Eve Davis', 'eve.davis@example.com', 26),
            ('Frank Garcia', 'frank.garcia@example.com', 33),
            ('Grace Lee', 'grace.lee@example.com', 42),        # > 40
            ('Henry Taylor', 'henry.taylor@example.com', 48),  # > 40
            ('Ivy Chen', 'ivy.chen@example.com', 29),
            ('Jack Robinson', 'jack.robinson@example.com', 51) # > 40
        ]
        
        await conn.executemany(
            'INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)',
            sample_users
        )
        
        await conn.commit()
        print(f"Sample database created at: {db_path}")


async def async_fetch_users(db_path):
    """
    Asynchronously fetch all users from the database.
    
    Args:
        db_path (str): Path to the database file
        
    Returns:
        list: All users from the database
    """
    print("🔍 Starting async_fetch_users()...")
    start_time = time.time()
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Add a small delay to simulate real-world database latency
            await asyncio.sleep(0.1)
            
            cursor = await conn.execute("SELECT * FROM users")
            results = await cursor.fetchall()
            await cursor.close()
            
            end_time = time.time()
            print(f"✅ async_fetch_users() completed in {end_time - start_time:.3f} seconds")
            print(f"   Found {len(results)} total users")
            
            return results
            
    except Exception as e:
        print(f"❌ Error in async_fetch_users(): {e}")
        raise


async def async_fetch_older_users(db_path):
    """
    Asynchronously fetch users older than 40 from the database.
    
    Args:
        db_path (str): Path to the database file
        
    Returns:
        list: Users older than 40
    """
    print("🔍 Starting async_fetch_older_users()...")
    start_time = time.time()
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Add a small delay to simulate real-world database latency
            await asyncio.sleep(0.15)
            
            cursor = await conn.execute("SELECT * FROM users WHERE age > ?", (40,))
            results = await cursor.fetchall()
            await cursor.close()
            
            end_time = time.time()
            print(f"✅ async_fetch_older_users() completed in {end_time - start_time:.3f} seconds")
            print(f"   Found {len(results)} users older than 40")
            
            return results
            
    except Exception as e:
        print(f"❌ Error in async_fetch_older_users(): {e}")
        raise


async def fetch_concurrently(db_path):
    """
    Execute both database queries concurrently using asyncio.gather().
    
    Args:
        db_path (str): Path to the database file
        
    Returns:
        tuple: Results from both queries (all_users, older_users)
    """
    print("\n" + "="*60)
    print("🚀 Starting concurrent database queries...")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # Execute both queries concurrently using asyncio.gather()
        all_users, older_users = await asyncio.gather(
            async_fetch_users(db_path),
            async_fetch_older_users(db_path)
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n🎉 Both queries completed concurrently in {total_time:.3f} seconds")
        print("="*60)
        
        return all_users, older_users
        
    except Exception as e:
        print(f"❌ Error in concurrent execution: {e}")
        raise


def display_results(all_users, older_users):
    """
    Display the results from both queries in a formatted way.
    
    Args:
        all_users (list): Results from async_fetch_users()
        older_users (list): Results from async_fetch_older_users()
    """
    print("\n" + "="*60)
    print("📊 QUERY RESULTS")
    print("="*60)
    
    # Display all users
    print(f"\n🧑‍🤝‍🧑 ALL USERS ({len(all_users)} total):")
    print("-" * 50)
    print(f"{'ID':<5} {'Name':<15} {'Email':<25} {'Age':<5}")
    print("-" * 50)
    
    for row in all_users:
        print(f"{row[0]:<5} {row[1]:<15} {row[2]:<25} {row[3]:<5}")
    
    # Display older users
    print(f"\n👴 USERS OLDER THAN 40 ({len(older_users)} total):")
    print("-" * 50)
    print(f"{'ID':<5} {'Name':<15} {'Email':<25} {'Age':<5}")
    print("-" * 50)
    
    for row in older_users:
        print(f"{row[0]:<5} {row[1]:<15} {row[2]:<25} {row[3]:<5}")
    
    print("\n" + "="*60)


async def main():
    """
    Main function to demonstrate concurrent database queries.
    """
    db_path = "async_sample_database.db"
    
    try:
        # Setup sample database
        await setup_sample_database(db_path)
        
        # Run concurrent queries
        all_users, older_users = await fetch_concurrently(db_path)
        
        # Display results
        display_results(all_users, older_users)
        
        # Demonstrate the performance benefit of concurrent execution
        print("⚡ Performance Comparison:")
        print("- Sequential execution would take ~0.25 seconds (0.1 + 0.15)")
        print("- Concurrent execution took less time due to parallel processing")
        
    except Exception as e:
        print(f"❌ An error occurred in main(): {e}")
    
    finally:
        # Clean up - remove sample database
        try:
            os.remove(db_path)
            print(f"\n🗑️  Sample database {db_path} removed")
        except OSError:
            pass


def run_concurrent_queries():
    """
    Entry point function using asyncio.run() as requested.
    """
    print("🎯 Starting Async Database Query Demo")
    print("📚 Using aiosqlite for asynchronous SQLite operations")
    print("⚡ Executing queries concurrently with asyncio.gather()")
    
    # Use asyncio.run() to execute the concurrent fetch
    asyncio.run(main())


if __name__ == "__main__":
    run_concurrent_queries()
