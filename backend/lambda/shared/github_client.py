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


class BranchExistsError(GitHubError):
    """Branch already exists in repository"""

    pass


class PullRequestExistsError(GitHubError):
    """Pull request already exists for this branch"""

    pass


class BranchNotFoundError(GitHubError):
    """Branch doesn't exist in repository"""

    pass


class PullRequestNotFoundError(GitHubError):
    """Pull request doesn't exist"""

    pass


class LabelNotFoundError(GitHubError):
    """Label doesn't exist in repository"""

    pass


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


def create_branch(repo_name: str, branch_name: str, base_ref: str = "main") -> str:
    """
    Create a new feature branch in repository.

    Args:
        repo_name: Repository in format "owner/repo"
        branch_name: New branch name (e.g., "action-spec-update-1234567890")
        base_ref: Base branch to fork from (default: 'main')

    Returns:
        str: SHA of the new branch HEAD

    Raises:
        BranchExistsError: If branch name already exists
        RepositoryNotFoundError: If base_ref doesn't exist

    Example:
        sha = create_branch("trakrf/action-spec", "feature-123", "main")
    """
    _validate_repository_whitelist(repo_name)
    client = get_github_client()

    try:
        repo = client.get_repo(repo_name)
    except UnknownObjectException:
        raise RepositoryNotFoundError(repo_name)

    # Get base branch SHA
    try:
        base_ref_obj = repo.get_git_ref(f"heads/{base_ref}")
        base_sha = base_ref_obj.object.sha
    except UnknownObjectException:
        raise RepositoryNotFoundError(repo_name)

    # Create new branch
    try:
        new_ref = repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
        logger.info(
            f"Created branch {branch_name} in {repo_name} (SHA: {new_ref.object.sha})"
        )
        return new_ref.object.sha
    except GithubException as e:
        if "Reference already exists" in str(e):
            raise BranchExistsError(
                f"Branch '{branch_name}' already exists in {repo_name}"
            )
        raise GitHubError(f"Failed to create branch: {e}")


def commit_file_change(
    repo_name: str,
    branch_name: str,
    file_path: str,
    new_content: str,
    commit_message: str,
) -> str:
    """
    Commit file change to existing branch.

    Args:
        repo_name: Repository in format "owner/repo"
        branch_name: Branch to commit to
        file_path: File path to update
        new_content: New file content (UTF-8 string)
        commit_message: Commit message

    Returns:
        str: SHA of the new commit

    Example:
        sha = commit_file_change(
            "trakrf/action-spec",
            "feature-123",
            "specs/example.yml",
            "apiVersion: v1...",
            "Update WAF settings"
        )
    """
    _validate_repository_whitelist(repo_name)
    client = get_github_client()

    try:
        repo = client.get_repo(repo_name)
    except UnknownObjectException:
        raise RepositoryNotFoundError(repo_name)

    # Get current file to get SHA (required for update)
    try:
        file_obj = repo.get_contents(file_path, ref=branch_name)
        # file_obj is ContentFile (not a list) when fetching a single file
        file_sha = file_obj.sha if not isinstance(file_obj, list) else file_obj[0].sha  # type: ignore[union-attr]
        result = repo.update_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            sha=file_sha,
            branch=branch_name,
        )
        logger.info(f"Updated {file_path} in {repo_name} on {branch_name}")
        return result["commit"].sha
    except UnknownObjectException:
        # File doesn't exist, create it
        result = repo.create_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            branch=branch_name,
        )
        logger.info(f"Created {file_path} in {repo_name} on {branch_name}")
        return result["commit"].sha


def create_pull_request(
    repo_name: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
) -> dict:
    """
    Create pull request from head branch to base branch.

    Args:
        repo_name: Repository in format "owner/repo"
        title: PR title
        body: PR description (supports Markdown)
        head_branch: Source branch (your changes)
        base_branch: Target branch (default: 'main')

    Returns:
        dict: PR details with keys:
            - number: PR number
            - url: HTML URL for PR
            - api_url: API URL for PR

    Raises:
        BranchNotFoundError: If head_branch doesn't exist
        PullRequestExistsError: If PR already exists for this branch

    Example:
        pr = create_pull_request(
            "trakrf/action-spec",
            "Update WAF settings",
            "## Changes\n- Enabled WAF",
            "feature-123"
        )
    """
    _validate_repository_whitelist(repo_name)
    client = get_github_client()

    try:
        repo = client.get_repo(repo_name)
    except UnknownObjectException:
        raise RepositoryNotFoundError(repo_name)

    # Create PR
    try:
        pr = repo.create_pull(
            title=title, body=body, head=head_branch, base=base_branch
        )
        logger.info(f"Created PR #{pr.number} in {repo_name}: {pr.html_url}")
        return {"number": pr.number, "url": pr.html_url, "api_url": pr.url}
    except GithubException as e:
        if "A pull request already exists" in str(e):
            raise PullRequestExistsError(
                f"PR already exists for branch '{head_branch}'"
            )
        if "404" in str(e) or "not found" in str(e).lower():
            raise BranchNotFoundError(
                f"Branch '{head_branch}' not found in {repo_name}"
            )
        raise GitHubError(f"Failed to create PR: {e}")


def add_pr_labels(repo_name: str, pr_number: int, labels: list[str]) -> None:
    """
    Add labels to existing pull request.

    Args:
        repo_name: Repository in format "owner/repo"
        pr_number: PR number
        labels: List of label names (e.g., ["infrastructure-change", "automated"])

    Raises:
        PullRequestNotFoundError: If PR doesn't exist

    Example:
        add_pr_labels("trakrf/action-spec", 10, ["automated", "infrastructure-change"])
    """
    _validate_repository_whitelist(repo_name)
    client = get_github_client()

    try:
        repo = client.get_repo(repo_name)
    except UnknownObjectException:
        raise RepositoryNotFoundError(repo_name)

    # Get PR as issue (labels are issue attributes)
    try:
        issue = repo.get_issue(pr_number)
    except UnknownObjectException:
        raise PullRequestNotFoundError(f"PR #{pr_number} not found in {repo_name}")

    # Create labels if they don't exist
    existing_labels = {label.name for label in repo.get_labels()}
    for label_name in labels:
        if label_name not in existing_labels:
            # Create with default gray color
            repo.create_label(label_name, "e4e669")
            logger.info(f"Created label '{label_name}' in {repo_name}")

    # Add labels to PR
    issue.add_to_labels(*labels)
    logger.info(f"Added labels {labels} to PR #{pr_number} in {repo_name}")
