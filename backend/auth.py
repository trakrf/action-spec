"""
GitHub OAuth authentication endpoints.

Provides:
- GET /auth/login - Initiate OAuth flow
- GET /auth/callback - Handle OAuth callback
- POST /auth/logout - Clear authentication
- GET /api/auth/user - Get current user info
"""

from flask import (
    Blueprint,
    request,
    redirect,
    abort,
    make_response,
    jsonify,
    session,
)
import os
import secrets
import requests
import logging
from urllib.parse import urlencode

from github_helpers import validate_github_token

logger = logging.getLogger(__name__)

# Create auth blueprint
auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route("/auth/login")
def login():
    """
    GET /auth/login

    Initiate GitHub OAuth flow by redirecting to GitHub authorization page.

    Returns:
        302: Redirect to GitHub OAuth authorization
    """
    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    # Build GitHub OAuth URL
    client_id = os.environ.get("GITHUB_OAUTH_CLIENT_ID")
    if not client_id:
        logger.error("GITHUB_OAUTH_CLIENT_ID not configured")
        abort(500, "OAuth not configured. Please contact administrator.")

    params = {
        "client_id": client_id,
        "redirect_uri": f"{request.host_url.rstrip('/')}/auth/callback",
        "scope": "repo workflow",
        "state": state,
    }

    github_auth_url = "https://github.com/login/oauth/authorize"
    redirect_url = f"{github_auth_url}?{urlencode(params)}"

    logger.info("Initiating OAuth flow, redirect to GitHub")
    return redirect(redirect_url)


@auth_blueprint.route("/auth/callback")
def callback():
    """
    GET /auth/callback

    Handle OAuth callback from GitHub. Exchange authorization code for access token
    and set HttpOnly cookie.

    Query Parameters:
        code: Authorization code from GitHub
        state: CSRF protection state parameter

    Returns:
        302: Redirect to app root with cookie set
        400: If state invalid or code missing
    """
    # Validate state (CSRF protection)
    state = request.args.get("state")
    expected_state = session.get("oauth_state")

    if not state or state != expected_state:
        logger.warning("OAuth callback with invalid state parameter")
        abort(400, "Invalid state parameter. Please try logging in again.")

    # Clear state from session (one-time use)
    session.pop("oauth_state", None)

    # Get authorization code
    code = request.args.get("code")
    if not code:
        logger.warning("OAuth callback missing authorization code")
        abort(400, "No authorization code provided")

    # Exchange code for access token
    client_id = os.environ.get("GITHUB_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("GitHub OAuth credentials not configured")
        abort(500, "OAuth not configured. Please contact administrator.")

    token_url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": f"{request.host_url.rstrip('/')}/auth/callback",
    }

    try:
        response = requests.post(
            token_url, data=data, headers={"Accept": "application/json"}
        )
        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            error = token_data.get("error", "unknown")
            error_desc = token_data.get("error_description", "No access token returned")
            logger.error(f"Failed to get access token: {error} - {error_desc}")
            abort(400, f"Failed to authenticate with GitHub: {error_desc}")

    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        abort(500, "Failed to complete authentication. Please try again.")

    # Validate token with GitHub API
    user_data = validate_github_token(access_token)
    if not user_data:
        logger.error("Token validation failed after successful exchange")
        abort(400, "Invalid token received from GitHub")

    logger.info(f"User {user_data['login']} authenticated successfully")

    # Set HttpOnly cookie and redirect to app root
    response = make_response(redirect("/"))
    response.set_cookie(
        "github_token",
        value=access_token,
        max_age=2592000,  # 30 days
        secure=True,  # HTTPS only (set to False for local dev if needed)
        httponly=True,  # Not accessible to JavaScript
        samesite="Lax",  # CSRF protection
    )

    return response


@auth_blueprint.route("/auth/logout", methods=["POST"])
def logout():
    """
    POST /auth/logout

    Clear authentication cookie.

    Returns:
        200: {"success": true}
    """
    logger.info("User logged out")
    response = make_response(jsonify({"success": True}))
    response.set_cookie("github_token", "", max_age=0)
    return response


@auth_blueprint.route("/api/auth/user")
def get_user():
    """
    GET /api/auth/user

    Return current authenticated user info from GitHub.

    Returns:
        200: {"login": str, "name": str, "avatar_url": str}
        401: {"error": str} if not authenticated or token invalid
    """
    token = request.cookies.get("github_token")

    if not token:
        return jsonify({"error": "Not authenticated"}), 401

    # Validate token with GitHub
    user_data = validate_github_token(token)

    if not user_data:
        # Token invalid/revoked, clear cookie
        logger.warning("Invalid token detected in /api/auth/user, clearing cookie")
        resp = make_response(jsonify({"error": "Token invalid or expired"}), 401)
        resp.set_cookie("github_token", "", max_age=0)
        return resp

    return jsonify(
        {
            "login": user_data["login"],
            "name": user_data.get("name"),
            "avatar_url": user_data["avatar_url"],
        }
    )
