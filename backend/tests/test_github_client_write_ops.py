"""
Unit tests for GitHub client write operations (Phase 3.3.2).
Tests create_branch, commit_file_change, create_pull_request, add_pr_labels.
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add shared modules to path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "lambda", "shared"),
)

from github_client import (
    BranchExistsError,
    BranchNotFoundError,
    PullRequestExistsError,
    PullRequestNotFoundError,
    add_pr_labels,
    commit_file_change,
    create_branch,
    create_pull_request,
)


@patch("github_client.get_github_client")
def test_create_branch_success(mock_get_client):
    """Test branch creation with valid base_ref"""
    # Setup mock
    mock_repo = Mock()
    mock_base_ref = Mock()
    mock_base_ref.object.sha = "abc123"
    mock_repo.get_git_ref.return_value = mock_base_ref

    mock_new_ref = Mock()
    mock_new_ref.object.sha = "def456"
    mock_repo.create_git_ref.return_value = mock_new_ref

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    # Test
    sha = create_branch("trakrf/action-spec", "feature-test", "main")

    # Verify
    assert sha == "def456"
    mock_repo.get_git_ref.assert_called_once_with("heads/main")
    mock_repo.create_git_ref.assert_called_once_with(
        "refs/heads/feature-test", "abc123"
    )


@patch("github_client.get_github_client")
def test_create_branch_already_exists(mock_get_client):
    """Test BranchExistsError when branch exists"""
    from github import GithubException

    mock_repo = Mock()
    mock_base_ref = Mock()
    mock_base_ref.object.sha = "abc123"
    mock_repo.get_git_ref.return_value = mock_base_ref
    mock_repo.create_git_ref.side_effect = GithubException(
        422, {"message": "Reference already exists"}, {}
    )

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    with pytest.raises(BranchExistsError):
        create_branch("trakrf/action-spec", "feature-exists", "main")


@patch("github_client.get_github_client")
def test_commit_file_change_update(mock_get_client):
    """Test file update (file exists)"""
    mock_file = Mock()
    mock_file.sha = "file123"

    mock_commit = Mock()
    mock_commit.sha = "commit456"

    mock_repo = Mock()
    mock_repo.get_contents.return_value = mock_file
    mock_repo.update_file.return_value = {"commit": mock_commit}

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    sha = commit_file_change(
        "trakrf/action-spec", "feature-test", "spec.yml", "content", "Update spec"
    )

    assert sha == "commit456"
    mock_repo.update_file.assert_called_once()


@patch("github_client.get_github_client")
def test_commit_file_change_create(mock_get_client):
    """Test file creation (file doesn't exist)"""
    from github import UnknownObjectException

    mock_commit = Mock()
    mock_commit.sha = "commit789"

    mock_repo = Mock()
    mock_repo.get_contents.side_effect = UnknownObjectException(404, {}, {})
    mock_repo.create_file.return_value = {"commit": mock_commit}

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    sha = commit_file_change(
        "trakrf/action-spec", "feature-test", "new-spec.yml", "content", "Create spec"
    )

    assert sha == "commit789"
    mock_repo.create_file.assert_called_once()


@patch("github_client.get_github_client")
def test_create_pull_request_success(mock_get_client):
    """Test PR creation returns URL and number"""
    mock_pr = Mock()
    mock_pr.number = 42
    mock_pr.html_url = "https://github.com/trakrf/action-spec/pull/42"
    mock_pr.url = "https://api.github.com/repos/trakrf/action-spec/pulls/42"

    mock_repo = Mock()
    mock_repo.create_pull.return_value = mock_pr

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    result = create_pull_request(
        "trakrf/action-spec", "Test PR", "Test body", "feature-test"
    )

    assert result["number"] == 42
    assert "pull/42" in result["url"]
    assert "api.github.com" in result["api_url"]


@patch("github_client.get_github_client")
def test_create_pull_request_already_exists(mock_get_client):
    """Test PullRequestExistsError for duplicate PR"""
    from github import GithubException

    mock_repo = Mock()
    mock_repo.create_pull.side_effect = GithubException(
        422, {"message": "A pull request already exists"}, {}
    )

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    with pytest.raises(PullRequestExistsError):
        create_pull_request("trakrf/action-spec", "Test", "Body", "feature-dup")


@patch("github_client.get_github_client")
def test_add_pr_labels_success(mock_get_client):
    """Test labels added to PR"""
    mock_label1 = Mock()
    mock_label1.name = "automated"

    mock_issue = Mock()

    mock_repo = Mock()
    mock_repo.get_issue.return_value = mock_issue
    mock_repo.get_labels.return_value = [mock_label1]

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    add_pr_labels("trakrf/action-spec", 42, ["automated", "infrastructure-change"])

    mock_issue.add_to_labels.assert_called_once_with(
        "automated", "infrastructure-change"
    )


@patch("github_client.get_github_client")
def test_add_pr_labels_creates_missing(mock_get_client):
    """Test labels created if they don't exist"""
    mock_issue = Mock()

    mock_repo = Mock()
    mock_repo.get_issue.return_value = mock_issue
    mock_repo.get_labels.return_value = []  # No existing labels

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    add_pr_labels("trakrf/action-spec", 42, ["new-label"])

    # Verify label was created
    mock_repo.create_label.assert_called_once_with("new-label", "e4e669")
    mock_issue.add_to_labels.assert_called_once()
