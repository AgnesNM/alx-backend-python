#!/usr/bin/env python3
import utils

import unittest
from parameterized import parameterized

from utils import access_nested_map
from unittest.mock import Mock 

from unittest.mock import patch
from utils import memoize

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

class TestGetJson(unittest.TestCase):
    """Test cases for the get_json function."""
    
    @parameterized.expand([
        ("http://example.com", {"payload": True}),
        ("http://holberton.io", {"payload": False}),
    ])
    @patch('utils.requests.get')
    def test_get_json(self, test_url, test_payload, mock_get):
        """Test that utils.get_json returns the expected result.
        
        Parameters
        ----------
        test_url : str
            The URL to test with
        test_payload : dict
            The expected payload to be returned
        mock_get : Mock
            The mocked requests.get method
        """
        # Create a mock response object
        mock_response = Mock()
        mock_response.json.return_value = test_payload        
        
        # Configure the mock to return our mock response
        mock_get.return_value = mock_response
        
        # Call the function under test
        result = utils.get_json(test_url)
        
        # Assert that requests.get was called exactly once with the test_url
        mock_get.assert_called_once_with(test_url)
        
        # Assert that the result equals the expected test_payload
        self.assertEqual(result, test_payload)

class TestMemoize(unittest.TestCase):
    """Test cases for the memoize decorator."""
    
    def test_memoize(self):
        """Test that memoize caches results and only calls the method once."""
        
        class TestClass:
            def a_method(self):
                return 42
            
            @memoize
            def a_property(self):
                return self.a_method()
        
        # Create an instance of TestClass
        test_instance = TestClass()
        
        # Mock the a_method to track how many times it's called
        with patch.object(test_instance, 'a_method', return_value=42) as mock_method:
            # Call a_property twice
            result1 = test_instance.a_property
            result2 = test_instance.a_property
            
            # Assert that both calls return the correct result
            self.assertEqual(result1, 42)
            self.assertEqual(result2, 42)
            
            # Assert that a_method was called exactly once (memoization working)
            mock_method.assert_called_once()

if __name__ == "__main__":
    unittest.main()
