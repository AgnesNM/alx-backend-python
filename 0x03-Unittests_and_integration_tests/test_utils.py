#!/usr/bin/env python3
import unittest
from parameterized import parameterized
from utils import access_nested_map

class TestAccessNestedMap(unittest.TestCase):
    """Test class for access_nested_map function"""
    
    @parameterized.expand([
        ({"a": 1}, ("a",), 1),
        ({"a": {"b": 2}}, ("a",), {"b": 2}),
        ({"a": {"b": 2}}, ("a", "b"), 2),
    ])
    def test_access_nested_map(self, nested_map, path, expected):
        """Test that access_nested_map returns the expected result"""
        
        self.assertEqual(access_nested_map(nested_map, path), expected)
    
    @parameterized.expand([
        ({}, ("a",)),
        ({"a": 1}, ("a", "b"))
    ])
    def test_access_nested_map_exception(self, nested_map, path):
        """Test that access_nested_map raises KeyError with expected message"""

        with self.assertRaises(KeyError) as context:
            access_nested_map(nested_map, path)
        
        # The exception message should be the key that caused the error
        # For empty dict {}, trying to access "a" raises KeyError('a')
        # For {"a": 1}, trying to access "b" from integer 1 raises KeyError('b')

        expected_key = path[-1]  # The last key in the path that failed
        self.assertEqual(str(context.exception), f"'{expected_key}'")

if __name__ == "__main__":
    unittest.main()
