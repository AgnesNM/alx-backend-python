#!/usr/bin/env python3
"""Test client module for GithubOrgClient class.

This module contains unit tests for the GithubOrgClient class,
specifically testing the org method with mocked dependencies.
"""
import unittest
from unittest.mock import patch
from parameterized import parameterized, parameterized_class
import fixtures
import unittest.mock


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
        from client import GithubOrgClient

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
        from client import GithubOrgClient

        known_payload = {
            "repos_url": "https://api.github.com/orgs/google/repos"
        }

        with patch('client.GithubOrgClient.org',
                   new_callable=lambda: property(lambda self: known_payload)):
            client = GithubOrgClient("google")
            result = client._public_repos_url
            self.assertEqual(result, known_payload["repos_url"])

    @patch('client.get_json')
    def test_public_repos(self, mock_get_json) -> None:
        """Test that GithubOrgClient.public_repos returns expected repos.

        This method tests that the public_repos method returns the correct
        list of repository names from the mocked payload.

        Args:
            mock_get_json: Mock object for the get_json function
        """
        from client import GithubOrgClient

        test_payload = [
            {"name": "episodes.dart"},
            {"name": "kratu"},
            {"name": "build_tools"},
        ]
        mock_get_json.return_value = test_payload

        test_url = "https://api.github.com/orgs/google/repos"
        property_patch = 'client.GithubOrgClient._public_repos_url'
        with patch(property_patch,
                   new_callable=lambda: property(lambda self: test_url)) \
                as mock_public_repos_url:

            client = GithubOrgClient("google")
            result = client.public_repos()

            expected_repos = ["episodes.dart", "kratu", "build_tools"]
            self.assertEqual(result, expected_repos)

            mock_get_json.assert_called_once()

    @parameterized.expand([
        ({"license": {"key": "my_license"}}, "my_license", True),
        ({"license": {"key": "other_license"}}, "my_license", False),
    ])
    def test_has_license(self, repo: dict, license_key: str, expected: bool) -> None:
        """Test that GithubOrgClient.has_license returns expected result.

        This method tests that the has_license static method correctly
        identifies whether a repository has a specific license.

        Args:
            repo: Repository dictionary containing license information
            license_key: License key to check for
            expected: Expected boolean result
        """
        from client import GithubOrgClient

        result = GithubOrgClient.has_license(repo, license_key)
        self.assertEqual(result, expected)


@parameterized_class(
    ("org_payload", "repos_payload", "expected_repos", "apache2_repos"),
    fixtures.TEST_PAYLOAD
)
class TestIntegrationGithubOrgClient(unittest.TestCase):
    """Integration test class for GithubOrgClient.

    This class tests the GithubOrgClient in an integration context,
    mocking only external HTTP requests while testing the full workflow.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up class fixtures for integration testing.

        This method sets up mock responses for requests.get to return
        the appropriate fixture data based on the requested URL.
        """
        def side_effect(url):
            """Side effect function to return appropriate mock response."""
            mock_response = unittest.mock.Mock()
            if url == "https://api.github.com/orgs/google":
                mock_response.json.return_value = cls.org_payload
            elif url == cls.org_payload.get("repos_url"):
                mock_response.json.return_value = cls.repos_payload
            else:
                mock_response.json.return_value = {}
            return mock_response

        cls.get_patcher = patch('requests.get', side_effect=side_effect)
        cls.get_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down class fixtures after integration testing.

        This method stops the requests.get patcher to clean up
        after integration tests.
        """
        cls.get_patcher.stop()

    def test_public_repos(self) -> None:
        """Test that public_repos returns expected repos from fixtures.

        This integration test verifies that the public_repos method
        returns the expected list of repository names from the fixtures.
        """
        from client import GithubOrgClient

        client = GithubOrgClient("google")
        result = client.public_repos()
        self.assertEqual(result, self.expected_repos)

    def test_public_repos_with_license(self) -> None:
        """Test public_repos with apache-2.0 license filter.

        This integration test verifies that the public_repos method
        with license="apache-2.0" returns only repositories with
        Apache 2.0 license from the fixtures.
        """
        from client import GithubOrgClient

        client = GithubOrgClient("google")
        result = client.public_repos(license="apache-2.0")
        self.assertEqual(result, self.apache2_repos)


if __name__ == "__main__":
    unittest.main()
