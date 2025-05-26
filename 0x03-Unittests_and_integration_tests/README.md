# Unit Tests and Integration Tests

This project contains unit tests for utility functions used in a GitHub organization client application.

## Project Structure

```
0x03-Unittests_and_integration_tests/
├── utils.py           # Utility functions module
├── test_utils.py      # Unit tests for utility functions
└── README.md          # This file
```

## Files Description

### `utils.py`
Contains generic utility functions for the GitHub org client:

- **`access_nested_map(nested_map, path)`**: Navigates through nested dictionaries using a sequence of keys
- **`get_json(url)`**: Fetches JSON data from a remote URL
- **`memoize(fn)`**: Decorator that caches method results as properties

### `test_utils.py`
Contains unit tests for the utility functions using Python's `unittest` framework and `parameterized` library for data-driven tests.

## Test Coverage

### TestAccessNestedMap
Tests the `access_nested_map` function with various nested dictionary scenarios:

- Simple nested access: `{"a": 1}` with path `("a",)` → returns `1`
- Partial nested access: `{"a": {"b": 2}}` with path `("a",)` → returns `{"b": 2}`
- Deep nested access: `{"a": {"b": 2}}` with path `("a", "b")` → returns `2`

## Requirements

- Python 3.x
- `requests` library
- `parameterized` library for test parameterization

## Installation

Install required dependencies:

```bash
pip install requests parameterized
```

## Running Tests

Run all tests:
```bash
python -m unittest test_utils.py
```

Run specific test class:
```bash
python -m unittest test_utils.TestAccessNestedMap
```

Run with verbose output:
```bash
python -m unittest test_utils.py -v
```

## Test Implementation Details

The tests use the `@parameterized.expand` decorator to run the same test logic with different input data. This approach:

- Reduces code duplication
- Makes it easy to add new test cases
- Provides clear test output for each parameter set
- Follows DRY (Don't Repeat Yourself) principles

## Example Usage

```python
from utils import access_nested_map

# Simple nested map access
nested_data = {"user": {"profile": {"name": "John Doe"}}}
name = access_nested_map(nested_data, ["user", "profile", "name"])
print(name)  # Output: John Doe
```

## Repository Information

- **GitHub repository**: `alx-backend-python`
- **Directory**: `0x03-Unittests_and_integration_tests`
- **File**: `test_utils.py`

## Learning Objectives

This project demonstrates:
- Writing unit tests with Python's `unittest` framework
- Using parameterized tests for data-driven testing
- Testing utility functions with various input scenarios
- Following Python testing best practices
- Understanding nested data structure manipulation
