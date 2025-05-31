#!/usr/bin/env python3
"""Test client for GithubOrgClient
"""
import unittest
from unittest.mock import patch
from parameterized import parameterized
from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Test class for GithubOrgClient"""

    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch('utils.get_json')
    def test_org(self, mock_get_json, org_name):
        """Test that GithubOrgClient.org returns the correct value"""
        # Create a mock return value for get_json
        expected_org_data = {"login": org_name, "id": 12345, "url": f"https://api.github.com/orgs/{org_name}"}
        mock_get_json.return_value = expected_org_data
        
        # Create GithubOrgClient instance
        client = GithubOrgClient(org_name)
        
        # Access the org property
        result = client.org
        
        # Assert that get_json was called once with the expected URL
        expected_url = f"https://api.github.com/orgs/{org_name}"
        mock_get_json.assert_called_once_with(expected_url)
        
        # Assert that the result is what we expected
        self.assertEqual(result, expected_org_data)


if __name__ == "__main__":
    unittest.main()