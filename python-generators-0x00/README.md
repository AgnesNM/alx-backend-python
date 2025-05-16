# MySQL Database Row Generator

This project demonstrates how to set up a MySQL database and create a generator that streams rows one by one from the database. It's designed for efficient data processing, especially when working with large datasets where loading everything into memory at once would be impractical.

## Overview

The `seed.py` script performs the following operations:

1. Connects to a MySQL server
2. Creates a database called `ALX_prodev`
3. Creates a table called `user_data` with the specified fields
4. Imports sample data from a CSV file
5. Demonstrates a row generator that streams database rows one by one

## Requirements

- Python 3.6+
- MySQL server installed and running
- `mysql-connector-python` package
- A `user_data.csv` file with sample data

## Installation

1. Install the required Python package:
   ```
   pip install mysql-connector-python
   ```

2. Ensure MySQL server is running on your machine

3. Place your `user_data.csv` file in the same directory as the script (the CSV should contain columns for name, email, and age - user_id will be generated if not provided)

## Database Structure

The script creates a table with the following structure:

- `user_id` (Primary Key, UUID, Indexed)
- `name` (VARCHAR, NOT NULL)
- `email` (VARCHAR, NOT NULL)
- `age` (DECIMAL, NOT NULL)

## Script Functions

The `seed.py` script includes the following functions:

- `connect_db()`: Connects to the MySQL database server
- `create_database(connection)`: Creates the database `ALX_prodev` if it does not exist
- `connect_to_prodev()`: Connects to the ALX_prodev database in MySQL
- `create_table(connection)`: Creates a table user_data with the required fields
- `insert_data(connection, data)`: Inserts data in the database if it does not exist
- `load_csv_data(file_path)`: Loads data from a CSV file
- `row_generator(connection, table_name, batch_size)`: Streams rows from the database one by one

## How the Row Generator Works

The row generator uses a technique called "batched fetching" to efficiently stream rows:

1. Fetches rows in batches (default 100 rows at a time) to minimize database round trips
2. Yields each row individually, maintaining a streaming interface
3. Continues fetching batches until all rows have been processed
4. Reports progress as rows are fetched

This approach balances efficiency (fewer database queries) with memory usage (doesn't load everything at once).

### Generator Usage Example

```python
# Connect to the database
connection = connect_to_prodev()

# Use the generator to process rows one by one
for row in row_generator(connection, "user_data"):
    # Process each row as it comes
    print(row)
    # Do something with the row...
    process_data(row)
    
# No need to worry about memory issues with large datasets
```

## Memory Efficiency

This generator approach is particularly useful when:

- Working with large datasets that don't fit in memory
- Processing rows in a streaming fashion (e.g., for data pipelines)
- Implementing ETL (Extract, Transform, Load) processes
- Building data processing workflows where you need to process one row at a time

## Customization

You can customize the script by:

1. Changing database connection parameters (host, user, password)
2. Modifying batch size in the row generator (smaller batches use less memory, larger batches require fewer queries)
3. Adding additional processing logic within the generator loop

## Troubleshooting

- **Connection issues**: Ensure MySQL is running and credentials are correct
- **CSV format errors**: Make sure your CSV has the correct format (columns for name, email, age)
- **Permissions**: Ensure your MySQL user has rights to create databases and tables

## Future Enhancements

Possible enhancements to this script could include:

- Adding command-line arguments for configuration
- Implementing connection pooling for improved performance
- Adding support for different database engines
- Creating a more robust error handling system
- Supporting transactions for safer data operations
