"""
Unit tests for github_client module.
Tests authentication, file fetching, error handling, and retry logic.
"""

import os
import sys
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "shared"))

from github_client import (
    get_github_client,
    fetch_spec_file,
    AuthenticationError,
    RateLimitError,
    RepositoryNotFoundError,
    FileNotFoundError,
    GitHubError,
    _validate_repository_whitelist,
)


# Fixtures


@pytest.fixture
def mock_ssm():
    """Mock boto3 SSM client."""
    with patch("github_client.boto3.client") as mock_client:
        mock_ssm = MagicMock()
        mock_client.return_value = mock_ssm

        # Default: return valid token
        mock_ssm.get_parameter.return_value = {
            "Parameter": {"Value": "ghp_test_token_1234567890"}
        }

        yield mock_ssm


@pytest.fixture
def mock_github():
    """Mock PyGithub Github client."""
    with patch("github_client.Github") as mock_github_class:
        mock_client = MagicMock()
        mock_github_class.return_value = mock_client

        # Default: valid rate limit
        mock_rate_limit = MagicMock()
        mock_rate_limit.core.remaining = 5000
        mock_rate_limit.core.limit = 5000
        mock_client.get_rate_limit.return_value = mock_rate_limit

        yield mock_client


@pytest.fixture(autouse=True)
def set_env_vars():
    """Set required environment variables for tests."""
    os.environ["GITHUB_TOKEN_SSM_PARAM"] = "/actionspec/github-token"
    os.environ["ALLOWED_REPOS"] = "trakrf/action-spec,trakrf/demo-repo"

    yield

    # Cleanup
    if "GITHUB_TOKEN_SSM_PARAM" in os.environ:
        del os.environ["GITHUB_TOKEN_SSM_PARAM"]
    if "ALLOWED_REPOS" in os.environ:
        del os.environ["ALLOWED_REPOS"]


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear @lru_cache between tests."""
    get_github_client.cache_clear()
    yield
    get_github_client.cache_clear()


# Tests: get_github_client()


def test_get_github_client_success(mock_ssm, mock_github):
    """Test successful client creation with valid token."""
    client = get_github_client()

    assert client is not None
    mock_ssm.get_parameter.assert_called_once_with(
        Name="/actionspec/github-token", WithDecryption=True
    )


def test_get_github_client_caches_instance(mock_ssm, mock_github):
    """Test @lru_cache caches client instance."""
    client1 = get_github_client()
    client2 = get_github_client()

    assert client1 is client2  # Same instance
    # SSM called only once due to cache
    assert mock_ssm.get_parameter.call_count == 1


def test_get_github_client_missing_env_var(mock_ssm, mock_github):
    """Test error when GITHUB_TOKEN_SSM_PARAM not set."""
    del os.environ["GITHUB_TOKEN_SSM_PARAM"]

    with pytest.raises(AuthenticationError) as exc_info:
        get_github_client()

    assert "environment variable not set" in str(exc_info.value)


def test_get_github_client_ssm_parameter_not_found(mock_ssm, mock_github):
    """Test error when SSM parameter doesn't exist."""
    from botocore.exceptions import ClientError

    mock_ssm.get_parameter.side_effect = ClientError(
        {"Error": {"Code": "ParameterNotFound", "Message": "Parameter not found"}},
        "GetParameter",
    )

    with pytest.raises(AuthenticationError) as exc_info:
        get_github_client()

    assert "not found" in str(exc_info.value)
    assert "/actionspec/github-token" in str(exc_info.value)


def test_get_github_client_invalid_token(mock_ssm, mock_github):
    """Test AuthenticationError for invalid GitHub token."""
    from github.GithubException import BadCredentialsException

    mock_github.get_rate_limit.side_effect = BadCredentialsException(
        401, {"message": "Bad credentials"}
    )

    with pytest.raises(AuthenticationError) as exc_info:
        get_github_client()

    assert "Invalid or expired" in str(exc_info.value)


# Tests: _validate_repository_whitelist()


def test_validate_repository_whitelist_success():
    """Test successful whitelist validation."""
    # Should not raise
    _validate_repository_whitelist("trakrf/action-spec")


def test_validate_repository_whitelist_invalid_format():
    """Test error for malformed repository name."""
    with pytest.raises(ValueError) as exc_info:
        _validate_repository_whitelist("invalid-repo-name")

    assert "Invalid repository format" in str(exc_info.value)
    assert "owner/repo" in str(exc_info.value)


def test_validate_repository_whitelist_not_allowed():
    """Test error for repository not in whitelist."""
    with pytest.raises(RepositoryNotFoundError) as exc_info:
        _validate_repository_whitelist("attacker/malicious-repo")

    assert "attacker/malicious-repo" in str(exc_info.value)


# Tests: fetch_spec_file()


def test_fetch_spec_file_success(mock_ssm, mock_github):
    """Test successful file fetch."""
    # Mock repository and file
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_file = MagicMock()
    mock_file.decoded_content = b"apiVersion: actionspec/v1\nkind: StaticSite"
    mock_repo.get_contents.return_value = mock_file

    content = fetch_spec_file("trakrf/action-spec", "specs/examples/minimal.yml")

    assert "apiVersion: actionspec/v1" in content
    mock_repo.get_contents.assert_called_once_with(
        "specs/examples/minimal.yml", ref="main"
    )


def test_fetch_spec_file_with_custom_ref(mock_ssm, mock_github):
    """Test file fetch with custom branch ref."""
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_file = MagicMock()
    mock_file.decoded_content = b"test content"
    mock_repo.get_contents.return_value = mock_file

    content = fetch_spec_file("trakrf/action-spec", "test.yml", ref="feature/test")

    mock_repo.get_contents.assert_called_once_with("test.yml", ref="feature/test")


def test_fetch_spec_file_not_in_whitelist(mock_ssm, mock_github):
    """Test error when repository not in whitelist."""
    with pytest.raises(RepositoryNotFoundError):
        fetch_spec_file("unauthorized/repo", "test.yml")


def test_fetch_spec_file_directory_traversal(mock_ssm, mock_github):
    """Test error for directory traversal attempt."""
    with pytest.raises(ValueError) as exc_info:
        fetch_spec_file("trakrf/action-spec", "../../../etc/passwd")

    assert "directory traversal" in str(exc_info.value).lower()


def test_fetch_spec_file_repository_not_found(mock_ssm, mock_github):
    """Test error when repository doesn't exist."""
    from github import UnknownObjectException

    mock_github.get_repo.side_effect = UnknownObjectException(
        404, {"message": "Not Found"}
    )

    with pytest.raises(RepositoryNotFoundError) as exc_info:
        fetch_spec_file("trakrf/action-spec", "test.yml")

    assert "trakrf/action-spec" in str(exc_info.value)


def test_fetch_spec_file_file_not_found(mock_ssm, mock_github):
    """Test error when file doesn't exist."""
    from github import UnknownObjectException

    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_repo.get_contents.side_effect = UnknownObjectException(
        404, {"message": "Not Found"}
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        fetch_spec_file("trakrf/action-spec", "missing.yml")

    assert "missing.yml" in str(exc_info.value)
    assert "trakrf/action-spec" in str(exc_info.value)


def test_fetch_spec_file_rate_limit_retry_success(mock_ssm, mock_github):
    """Test exponential backoff succeeds on retry 2."""
    from github import RateLimitExceededException

    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_file = MagicMock()
    mock_file.decoded_content = b"success after retry"

    # Fail twice, succeed third time
    mock_repo.get_contents.side_effect = [
        RateLimitExceededException(403, {"message": "Rate limit"}),
        RateLimitExceededException(403, {"message": "Rate limit"}),
        mock_file,
    ]

    with patch("github_client.time.sleep") as mock_sleep:
        content = fetch_spec_file("trakrf/action-spec", "test.yml")

    assert "success after retry" in content
    # Verify exponential backoff: 1s, 2s
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0][0][0] == 1  # First retry: 1s
    assert mock_sleep.call_args_list[1][0][0] == 2  # Second retry: 2s


def test_fetch_spec_file_rate_limit_exhausted(mock_ssm, mock_github):
    """Test RateLimitError after max retries."""
    from github import RateLimitExceededException

    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    # Always fail with rate limit
    mock_repo.get_contents.side_effect = RateLimitExceededException(
        403, {"message": "Rate limit"}
    )

    # Mock rate limit reset time
    mock_rate_limit = MagicMock()
    mock_rate_limit.core.reset.timestamp.return_value = time.time() + 300  # 5 minutes
    mock_github.get_rate_limit.return_value = mock_rate_limit

    with patch("github_client.time.sleep"):
        with pytest.raises(RateLimitError) as exc_info:
            fetch_spec_file("trakrf/action-spec", "test.yml")

    assert exc_info.value.retry_after > 0
    assert "Exhausted" in str(exc_info.value)


def test_fetch_spec_file_is_directory(mock_ssm, mock_github):
    """Test error when path is a directory, not a file."""
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    # Return list (directory) instead of file
    mock_repo.get_contents.return_value = [MagicMock(), MagicMock()]

    with pytest.raises(FileNotFoundError):
        fetch_spec_file("trakrf/action-spec", "specs/")
