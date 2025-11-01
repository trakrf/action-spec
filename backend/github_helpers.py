"""
GitHub API helper functions for user token management.

Provides:
- Token extraction from cookies
- GitHub API call wrapper with user tokens
- Access control for repositories
- PyGithub instance management
"""

from flask import request, abort
from github import Github, GithubException
import requests
import os
import logging

logger = logging.getLogger(__name__)


def get_github_token():
    """
    Get user's GitHub token from cookie.

    OAuth-only authentication - all operations use user tokens.

    Returns:
        str: GitHub access token from user's OAuth session

    Raises:
        401: If no user token in cookie (user not authenticated)
    """
    token = request.cookies.get("github_token")
    if not token:
        abort(401, "Not authenticated. Please log in with GitHub.")
    return token


def get_github_client():
    """
    Get PyGithub client authenticated with user's OAuth token.

    OAuth-only authentication - all operations use user tokens.

    Returns:
        Github: Authenticated PyGithub client

    Raises:
        401: If user not authenticated
    """
    token = get_github_token()
    return Github(token)


def github_api_call(endpoint, method="GET", **kwargs):
    """
    Make GitHub REST API call with user's OAuth token.

    Uses requests library for direct API access.
    For operations not covered by PyGithub or when you need raw responses.

    Args:
        endpoint: API endpoint path (e.g., '/user', '/repos/owner/repo')
        method: HTTP method (GET, POST, PUT, DELETE)
        **kwargs: Additional arguments passed to requests.request()

    Returns:
        requests.Response: Response object

    Raises:
        401: If token invalid or missing
    """
    token = get_github_token()

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"token {token}"
    headers["Accept"] = "application/vnd.github.v3+json"

    url = f"https://api.github.com{endpoint}"
    response = requests.request(method, url, headers=headers, **kwargs)

    if response.status_code == 401:
        logger.warning(f"GitHub token invalid/expired for endpoint: {endpoint}")
        abort(401, "GitHub token invalid or expired. Please log in again.")

    return response


def check_repo_access(github_client, owner, repo):
    """
    Verify user has access to repository.

    Args:
        github_client: Authenticated PyGithub client
        owner: Repository owner (username or org)
        repo: Repository name

    Returns:
        Repository: PyGithub Repository object if accessible

    Raises:
        403: If user lacks access
        404: If repo doesn't exist or user can't see it
    """
    try:
        repo_obj = github_client.get_repo(f"{owner}/{repo}")

        # For private repos in trakrf org, verify org membership
        if owner == "trakrf" and repo_obj.private:
            user = github_client.get_user()
            try:
                # Check if user is org member
                org = github_client.get_organization("trakrf")
                org.get_membership(user.login)
            except GithubException as e:
                if e.status == 404:
                    logger.warning(
                        f"User {user.login} not in trakrf org, denied access to {owner}/{repo}"
                    )
                    abort(
                        403,
                        "Access denied: Must be trakrf organization member for private repositories",
                    )
                raise

        return repo_obj

    except GithubException as e:
        if e.status == 404:
            logger.warning(f"Repository not found or access denied: {owner}/{repo}")
            abort(404, f"Repository not found: {owner}/{repo}")
        logger.error(f"GitHub API error checking repo access: {e}")
        abort(500, "Failed to verify repository access")


def validate_github_token(token):
    """
    Validate GitHub token by calling /user endpoint.

    Args:
        token: GitHub access token to validate

    Returns:
        dict: User data if valid, None if invalid
    """
    try:
        response = requests.get(
            "https://api.github.com/user", headers={"Authorization": f"token {token}"}
        )

        if response.status_code == 200:
            return response.json()
        return None

    except Exception as e:
        logger.error(f"Error validating GitHub token: {e}")
        return None
