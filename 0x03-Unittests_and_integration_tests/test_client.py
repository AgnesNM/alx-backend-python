#!/usr/bin/env python3
"""Test client module for GithubOrgClient class.

This module contains unit tests for the GithubOrgClient class,
specifically testing the org method with mocked dependencies.
"""
import unittest
from unittest.mock import patch
from parameterized import parameterized
from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Test class for GithubOrgClient functionality.

    This class contains test methods to verify the correct behavior
    of the GithubOrgClient class methods.
    """

    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch('client.get_json')
    def test_org(self, org_name: str, mock_get_json) -> None:
        """Test that GithubOrgClient.org returns the correct value.

        This method tests that the org property of GithubOrgClient
        returns the expected organization data and calls get_json
        with the correct URL.

        Args:
            org_name: Name of the organization to test
            mock_get_json: Mock object for the get_json function
        """
        expected_org_data = {"login": org_name, "id": 12345}
        mock_get_json.return_value = expected_org_data

        client = GithubOrgClient(org_name)
        result = client.org
        
        self.assertEqual(result, expected_org_data)

    def test_public_repos_url(self) -> None:
        """Test that GithubOrgClient._public_repos_url returns expected URL.

        This method tests that the _public_repos_url property returns
        the correct repos_url from the mocked org payload.
        """
        known_payload = {
            "repos_url": "https://api.github.com/orgs/google/repos"
        }
        
        with patch('client.GithubOrgClient.org', 
                   new_callable=lambda: property(lambda self: known_payload)):
            client = GithubOrgClient("google")
            result = client._public_repos_url
            self.assertEqual(result, known_payload["repos_url"])


if __name__ == "__main__":
    unittest.main()

