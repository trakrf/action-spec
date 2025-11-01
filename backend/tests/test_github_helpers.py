"""
Unit tests for GitHub helper functions.

Tests:
- Token extraction and fallback
- GitHub API call wrapper
- Access control logic
- Token validation
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask
from github import GithubException
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from github_helpers import (
    get_github_token,
    get_github_client,
    github_api_call,
    check_repo_access,
    validate_github_token,
)


@pytest.fixture
def app():
    """Flask app for request context."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


class TestTokenExtraction:
    """Tests for OAuth token extraction"""

    def test_get_token_from_cookie(self, app):
        """Should extract user's OAuth token from cookie"""
        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie("github_token", "user_token_123")
                with client:
                    client.get("/")
                    token = get_github_token()
                    assert token == "user_token_123"

    def test_no_token_aborts(self, app):
        """Should abort 401 if user not authenticated"""
        with app.test_request_context():
            with pytest.raises(Exception):  # Flask abort raises werkzeug exception
                get_github_token()


class TestGithubClient:
    """Tests for OAuth-authenticated GitHub client"""

    @patch("github_helpers.Github")
    def test_get_client_with_user_token(self, mock_github, app):
        """Should create client with user's OAuth token"""
        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie("github_token", "user_token")
                with client:
                    client.get("/")
                    get_github_client()
                    mock_github.assert_called_with("user_token")

    @patch("github_helpers.Github")
    def test_get_client_no_auth_aborts(self, mock_github, app):
        """Should abort 401 if user not authenticated"""
        with app.test_request_context():
            with pytest.raises(Exception):
                get_github_client()


class TestGithubApiCall:
    """Tests for github_api_call wrapper"""

    @patch("github_helpers.requests.request")
    def test_api_call_success(self, mock_request, app):
        """Should make API call with user token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie("github_token", "user_token")
                with client:
                    client.get("/")
                    response = github_api_call("/user")

                    assert response.status_code == 200
                    mock_request.assert_called_once()
                    call_kwargs = mock_request.call_args[1]
                    assert call_kwargs["headers"]["Authorization"] == "token user_token"

    @patch("github_helpers.requests.request")
    def test_api_call_401_aborts(self, mock_request, app):
        """Should abort on 401 response"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie("github_token", "invalid_token")
                with client:
                    client.get("/")
                    with pytest.raises(Exception):
                        github_api_call("/user")


class TestCheckRepoAccess:
    """Tests for check_repo_access function"""

    def test_public_repo_access(self, app):
        """Should allow access to public repo"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_repo.private = False
        mock_client.get_repo.return_value = mock_repo

        with app.test_request_context():
            result = check_repo_access(mock_client, "octocat", "Hello-World")
            assert result == mock_repo

    def test_private_trakrf_repo_member(self, app):
        """Should allow trakrf member to access private trakrf repo"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_repo.private = True
        mock_client.get_repo.return_value = mock_repo

        mock_user = Mock()
        mock_user.login = "member_user"
        mock_client.get_user.return_value = mock_user

        mock_org = Mock()
        mock_org.get_membership.return_value = Mock()  # Member found
        mock_client.get_organization.return_value = mock_org

        with app.test_request_context():
            result = check_repo_access(mock_client, "trakrf", "private-repo")
            assert result == mock_repo

    def test_private_trakrf_repo_non_member(self, app):
        """Should deny non-member access to private trakrf repo"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_repo.private = True
        mock_client.get_repo.return_value = mock_repo

        mock_user = Mock()
        mock_user.login = "external_user"
        mock_client.get_user.return_value = mock_user

        mock_org = Mock()
        mock_org.get_membership.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )
        mock_client.get_organization.return_value = mock_org

        with app.test_request_context():
            with pytest.raises(Exception):  # Should abort 403
                check_repo_access(mock_client, "trakrf", "private-repo")

    def test_repo_not_found(self, app):
        """Should abort 404 if repo doesn't exist"""
        mock_client = Mock()
        mock_client.get_repo.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )

        with app.test_request_context():
            with pytest.raises(Exception):  # Should abort 404
                check_repo_access(mock_client, "nonexistent", "repo")


class TestValidateToken:
    """Tests for validate_github_token function"""

    @patch("github_helpers.requests.get")
    def test_valid_token(self, mock_get):
        """Should return user data for valid token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "name": "Test User"}
        mock_get.return_value = mock_response

        result = validate_github_token("valid_token")
        assert result["login"] == "testuser"

    @patch("github_helpers.requests.get")
    def test_invalid_token(self, mock_get):
        """Should return None for invalid token"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = validate_github_token("invalid_token")
        assert result is None

    @patch("github_helpers.requests.get")
    def test_network_error(self, mock_get):
        """Should return None on network error"""
        mock_get.side_effect = Exception("Network error")

        result = validate_github_token("any_token")
        assert result is None
