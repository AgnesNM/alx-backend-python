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

class TestGetJson(unittest.TestCase):
    """Test class for utils.get_json function."""
    
    def test_get_json(self):
        """Test that utils.get_json returns the expected result."""
        # Test case 1: http://example.com with {"payload": True}
        test_url = "http://example.com"
        test_payload = {"payload": True}
        
        with patch('utils.requests.get') as mock_get:
            # Configure the mock to return a Mock object with a json method
            mock_response = Mock()
            mock_response.json.return_value = test_payload
            mock_get.return_value = mock_response
            
            # Call the function under test
            result = utils.get_json(test_url)
            
            # Assert that requests.get was called exactly once with the test_url
            mock_get.assert_called_once_with(test_url)
            
            # Assert that the result equals the expected test_payload
            self.assertEqual(result, test_payload)
        
        # Test case 2: http://holberton.io with {"payload": False}
        test_url = "http://holberton.io"
        test_payload = {"payload": False}
        
        with patch('utils.requests.get') as mock_get:
            # Configure the mock to return a Mock object with a json method
            mock_response = Mock()
            mock_response.json.return_value = test_payload
            mock_get.return_value = mock_response
            
            # Call the function under test
            result = utils.get_json(test_url)
            
            # Assert that requests.get was called exactly once with the test_url
            mock_get.assert_called_once_with(test_url)
            
            # Assert that the result equals the expected test_payload
            self.assertEqual(result, test_payload)





if __name__ == "__main__":
    unittest.main()
