#!/usr/bin/env python3
"""Test client for GithubOrgClient
"""
import unittest
from unittest.mock import patch
from parameterized import parameterized
from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Test class for GithubOrgClient"""

    @patch('client.get_json')
    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    def test_org(self, mock_get_json, org_name):
        """Test that GithubOrgClient.org returns the correct value"""
        expected_org_data = {
            "login": org_name,
            "id": 12345,
            "url": "https://api.github.com/orgs/{}".format(org_name)
        }
        mock_get_json.return_value = expected_org_data
        
        client = GithubOrgClient(org_name)
        result = client.org
        
        expected_url = "https://api.github.com/orgs/{}".format(org_name)
        mock_get_json.assert_called_once_with(expected_url)
        self.assertEqual(result, expected_org_data)


if __name__ == "__main__":
    unittest.main()
