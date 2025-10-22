"""
GitHub client for ActionSpec Lambda functions.
Handles authentication, file fetching, and error handling.
"""

from functools import lru_cache
from typing import Optional
import os
import time
import logging

import boto3
from botocore.exceptions import ClientError
from github import (
    Github,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)
from github.GithubException import BadCredentialsException

logger = logging.getLogger()

# Configuration constants
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
BACKOFF_MULTIPLIER = 2


class GitHubError(Exception):
    """Base exception for GitHub client errors."""

    pass


class AuthenticationError(GitHubError):
    """GitHub authentication failed (invalid/expired token)."""

    def __init__(self, message: str, token_param: Optional[str] = None):
        self.message = message
        self.token_param = token_param
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.token_param:
            return f"GitHub authentication failed: {self.message} (SSM parameter: {self.token_param})"
        return f"GitHub authentication failed: {self.message}"


class RateLimitError(GitHubError):
    """GitHub API rate limit exceeded."""

    def __init__(self, message: str, retry_after: int):
        self.message = message
        self.retry_after = retry_after  # Seconds until rate limit resets
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        return f"GitHub rate limit exceeded: {self.message} (retry after {self.retry_after}s)"


class RepositoryNotFoundError(GitHubError):
    """Repository doesn't exist or token lacks access."""

    def __init__(self, repo_name: str):
        self.repo_name = repo_name
        super().__init__(f"Repository not found or inaccessible: {repo_name}")


class FileNotFoundError(GitHubError):
    """File doesn't exist at specified path."""

    def __init__(self, repo_name: str, file_path: str, ref: str):
        self.repo_name = repo_name
        self.file_path = file_path
        self.ref = ref
        super().__init__(f"File not found: {file_path} in {repo_name} (ref: {ref})")


@lru_cache(maxsize=1)
def get_github_client() -> Github:
    """
    Retrieve GitHub PAT from SSM Parameter Store and create authenticated client.

    Returns:
        Github: Authenticated PyGithub client instance

    Raises:
        AuthenticationError: If token is invalid or SSM parameter missing

    Implementation Notes:
    - Uses @lru_cache to cache client instance (reduces SSM calls)
    - Retrieves token from GITHUB_TOKEN_SSM_PARAM environment variable
    - Validates token by checking rate_limit (confirms auth works)
    """
    # Get SSM parameter name from environment
    param_name = os.environ.get("GITHUB_TOKEN_SSM_PARAM")
    if not param_name:
        raise AuthenticationError(
            "GITHUB_TOKEN_SSM_PARAM environment variable not set", token_param=None
        )

    # Retrieve token from SSM Parameter Store
    try:
        ssm = boto3.client("ssm")
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        token = response["Parameter"]["Value"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            raise AuthenticationError(
                f"SSM parameter not found: {param_name}", token_param=param_name
            )
        logger.error(f"Failed to retrieve GitHub token from SSM: {e}")
        raise AuthenticationError(
            f"Failed to retrieve token from SSM: {type(e).__name__}",
            token_param=param_name,
        )
    except Exception as e:
        logger.error(f"Failed to retrieve GitHub token from SSM: {e}")
        raise AuthenticationError(
            f"Failed to retrieve token from SSM: {type(e).__name__}",
            token_param=param_name,
        )

    # Create GitHub client
    try:
        client = Github(token)

        # Validate token by checking rate limit (lightweight API call)
        rate_limit = client.get_rate_limit()
        logger.info(
            f"GitHub client authenticated successfully "
            f"(rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit})"  # type: ignore[attr-defined]
        )

        return client

    except BadCredentialsException:
        raise AuthenticationError(
            "Invalid or expired GitHub token", token_param=param_name
        )
    except Exception as e:
        logger.error(f"Failed to create GitHub client: {e}")
        raise AuthenticationError(
            f"Failed to create GitHub client: {type(e).__name__}",
            token_param=param_name,
        )


def _validate_repository_whitelist(repo_name: str) -> None:
    """
    Validate repository is in ALLOWED_REPOS whitelist.

    Args:
        repo_name: Repository in format "owner/repo"

    Raises:
        ValueError: If repo_name format is invalid
        RepositoryNotFoundError: If repository not in whitelist
    """
    # Validate format
    if "/" not in repo_name:
        raise ValueError(
            f"Invalid repository format: '{repo_name}'. "
            f"Expected format: 'owner/repo' (e.g., 'trakrf/action-spec')"
        )

    # Get whitelist from environment
    allowed_repos_str = os.environ.get("ALLOWED_REPOS", "")
    if not allowed_repos_str:
        logger.warning("ALLOWED_REPOS not set - all repositories allowed (insecure!)")
        return

    allowed_repos = [repo.strip() for repo in allowed_repos_str.split(",")]

    if repo_name not in allowed_repos:
        logger.warning(
            f"Repository not in whitelist: {repo_name} "
            f"(allowed: {', '.join(allowed_repos)})"
        )
        raise RepositoryNotFoundError(repo_name)

    logger.debug(f"Repository whitelist check passed: {repo_name}")


def fetch_spec_file(repo_name: str, file_path: str, ref: str = "main") -> str:
    """
    Fetch ActionSpec YAML file content from GitHub repository.

    Args:
        repo_name: Repository in format "owner/repo" (e.g., "trakrf/action-spec")
        file_path: Path to spec file (e.g., "specs/examples/secure-web-waf.spec.yml")
        ref: Git ref (branch/tag/commit, default: 'main')

    Returns:
        str: Decoded file content (UTF-8)

    Raises:
        FileNotFoundError: If file doesn't exist at path
        RepositoryNotFoundError: If repository not in whitelist or doesn't exist
        RateLimitError: If GitHub rate limit exceeded after retries
        ValueError: If repo_name format is invalid

    Implementation Notes:
    - Validates repository whitelist before API call
    - Uses PyGithub repo.get_contents() API
    - Decodes base64 content automatically
    - Implements exponential backoff for rate limits (3 retries: 1s, 2s, 4s)
    """
    # Validate repository whitelist
    _validate_repository_whitelist(repo_name)

    # Sanitize file_path to prevent directory traversal
    if "../" in file_path or ".\\" in file_path:
        raise ValueError(
            f"Invalid file path (directory traversal detected): {file_path}"
        )

    # Get authenticated client
    client = get_github_client()

    # Fetch file with retry logic
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Get repository
            try:
                repo = client.get_repo(repo_name)
            except UnknownObjectException:
                raise RepositoryNotFoundError(repo_name)

            # Get file contents
            try:
                file_content = repo.get_contents(file_path, ref=ref)
            except UnknownObjectException:
                raise FileNotFoundError(repo_name, file_path, ref)

            # Decode content (PyGithub returns base64-encoded)
            if hasattr(file_content, "decoded_content"):
                content = file_content.decoded_content.decode("utf-8")
            else:
                # Handle case where file_content is a list (directory)
                raise FileNotFoundError(repo_name, file_path, ref)

            logger.info(
                f"Successfully fetched file: {file_path} from {repo_name} "
                f"(ref: {ref}, size: {len(content)} bytes)"
            )

            return content

        except RateLimitExceededException as e:
            # Check if we have retries left
            if attempt < MAX_RETRIES:
                backoff = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER**attempt)
                logger.warning(
                    f"Rate limit exceeded, retrying in {backoff}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(backoff)
            else:
                # Get retry_after from rate limit
                rate_limit = client.get_rate_limit()
                reset_timestamp = rate_limit.core.reset.timestamp()  # type: ignore[attr-defined]
                retry_after = int(reset_timestamp - time.time())

                raise RateLimitError(
                    f"Exhausted {MAX_RETRIES} retries", retry_after=max(retry_after, 0)
                )

        except (FileNotFoundError, RepositoryNotFoundError, ValueError):
            # Don't retry these errors
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching file: {e}")
            raise GitHubError(f"Failed to fetch file: {type(e).__name__}: {str(e)}")

    # Should never reach here
    raise GitHubError("Unexpected error in fetch_spec_file retry loop")
