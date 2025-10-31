"""
Unit and integration tests for OAuth authentication endpoints.

Tests:
- GET /auth/login - OAuth initiation
- GET /auth/callback - OAuth callback handling
- POST /auth/logout - Session termination
- GET /api/auth/user - User info retrieval
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app


@pytest.fixture
def client():
    """Flask test client with session support."""
    app.app.config["TESTING"] = True
    app.app.config["SECRET_KEY"] = "test-secret-key"
    with app.app.test_client() as client:
        yield client


class TestOAuthLogin:
    """Tests for GET /auth/login"""

    @patch.dict(os.environ, {"GITHUB_OAUTH_CLIENT_ID": "test_client_id"})
    def test_login_redirects_to_github(self, client):
        """Should redirect to GitHub OAuth with correct parameters"""
        response = client.get("/auth/login", follow_redirects=False)

        assert response.status_code == 302
        assert "github.com/login/oauth/authorize" in response.location
        assert "client_id=test_client_id" in response.location
        assert "scope=repo+workflow" in response.location
        assert "state=" in response.location

    @patch.dict(os.environ, {"GITHUB_OAUTH_CLIENT_ID": ""})
    def test_login_fails_without_client_id(self, client):
        """Should return 500 if GITHUB_OAUTH_CLIENT_ID not configured"""
        response = client.get("/auth/login")

        assert response.status_code == 500

    def test_login_sets_oauth_state_in_session(self, client):
        """Should store CSRF state in session"""
        with patch.dict(os.environ, {"GITHUB_OAUTH_CLIENT_ID": "test_client_id"}):
            with client.session_transaction() as sess:
                # Session should be empty before login
                assert "oauth_state" not in sess

            client.get("/auth/login")

            with client.session_transaction() as sess:
                # Session should contain state after login redirect
                assert "oauth_state" in sess
                assert len(sess["oauth_state"]) > 20  # Random token


class TestOAuthCallback:
    """Tests for GET /auth/callback"""

    @patch("auth.validate_github_token")
    @patch("auth.requests.post")
    @patch.dict(
        os.environ,
        {
            "GITHUB_OAUTH_CLIENT_ID": "test_client_id",
            "GITHUB_OAUTH_CLIENT_SECRET": "test_client_secret",
        },
    )
    def test_callback_success(self, mock_post, mock_validate, client):
        """Should exchange code for token and set cookie"""
        # Mock token exchange
        mock_post.return_value.json.return_value = {"access_token": "test_access_token"}

        # Mock token validation
        mock_validate.return_value = {"login": "testuser", "name": "Test User"}

        # Set up session state
        with client.session_transaction() as sess:
            sess["oauth_state"] = "test_state"

        response = client.get(
            "/auth/callback?code=test_code&state=test_state", follow_redirects=False
        )

        assert response.status_code == 302
        assert response.location == "/"
        assert "github_token=test_access_token" in response.headers.get(
            "Set-Cookie", ""
        )
        assert "HttpOnly" in response.headers.get("Set-Cookie", "")

    def test_callback_invalid_state(self, client):
        """Should return 400 for invalid CSRF state"""
        with client.session_transaction() as sess:
            sess["oauth_state"] = "valid_state"

        response = client.get("/auth/callback?code=test_code&state=invalid_state")

        assert response.status_code == 400

    def test_callback_missing_code(self, client):
        """Should return 400 if authorization code missing"""
        with client.session_transaction() as sess:
            sess["oauth_state"] = "test_state"

        response = client.get("/auth/callback?state=test_state")

        assert response.status_code == 400

    @patch("auth.requests.post")
    @patch.dict(
        os.environ,
        {
            "GITHUB_OAUTH_CLIENT_ID": "test_client_id",
            "GITHUB_OAUTH_CLIENT_SECRET": "test_client_secret",
        },
    )
    def test_callback_token_exchange_failure(self, mock_post, client):
        """Should return 400 if token exchange fails"""
        mock_post.return_value.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Code expired",
        }

        with client.session_transaction() as sess:
            sess["oauth_state"] = "test_state"

        response = client.get("/auth/callback?code=expired_code&state=test_state")

        assert response.status_code == 400

    @patch("auth.validate_github_token")
    @patch("auth.requests.post")
    @patch.dict(
        os.environ,
        {
            "GITHUB_OAUTH_CLIENT_ID": "test_client_id",
            "GITHUB_OAUTH_CLIENT_SECRET": "test_client_secret",
        },
    )
    def test_callback_invalid_token(self, mock_post, mock_validate, client):
        """Should return 400 if token validation fails"""
        mock_post.return_value.json.return_value = {"access_token": "invalid_token"}
        mock_validate.return_value = None  # Validation fails

        with client.session_transaction() as sess:
            sess["oauth_state"] = "test_state"

        response = client.get("/auth/callback?code=test_code&state=test_state")

        assert response.status_code == 400


class TestLogout:
    """Tests for POST /auth/logout"""

    def test_logout_clears_cookie(self, client):
        """Should clear github_token cookie"""
        response = client.post("/auth/logout")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Check cookie is cleared (max_age=0)
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "github_token=" in set_cookie
        assert "Max-Age=0" in set_cookie


class TestGetUser:
    """Tests for GET /api/auth/user"""

    @patch("auth.validate_github_token")
    def test_get_user_success(self, mock_validate, client):
        """Should return user info for valid token"""
        mock_validate.return_value = {
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://github.com/avatar.png",
        }

        client.set_cookie("github_token", "valid_token")
        response = client.get("/api/auth/user")

        assert response.status_code == 200
        data = response.get_json()
        assert data["login"] == "testuser"
        assert data["name"] == "Test User"
        assert data["avatar_url"] == "https://github.com/avatar.png"

    def test_get_user_not_authenticated(self, client):
        """Should return 401 if no token in cookie"""
        response = client.get("/api/auth/user")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    @patch("auth.validate_github_token")
    def test_get_user_invalid_token(self, mock_validate, client):
        """Should return 401 and clear cookie for invalid token"""
        mock_validate.return_value = None  # Token invalid

        client.set_cookie("github_token", "invalid_token")
        response = client.get("/api/auth/user")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

        # Cookie should be cleared
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "Max-Age=0" in set_cookie
