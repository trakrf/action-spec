"""Tests for spec-applier Lambda handler (Phase 3.3.3)"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "shared"))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "lambda", "functions", "spec-applier"
    ),
)

from handler import lambda_handler
from spec_parser.change_detector import ChangeWarning, Severity


@patch("handler.add_pr_labels")
@patch("handler.create_pull_request")
@patch("handler.commit_file_change")
@patch("handler.create_branch")
@patch("handler.check_destructive_changes")
@patch("handler.fetch_spec_file")
@patch("handler.parse_spec")
def test_handler_creates_pr_successfully(
    mock_parse, mock_fetch, mock_check, mock_branch, mock_commit, mock_pr, mock_labels
):
    """Test complete PR creation flow end-to-end"""
    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = []  # No warnings
    mock_branch.return_value = "abc123"
    mock_commit.return_value = "def456"
    mock_pr.return_value = {
        "number": 42,
        "url": "https://github.com/test/repo/pull/42",
        "api_url": "https://api.github.com/repos/test/repo/pulls/42",
    }

    # Test event
    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "spec_path": "specs/test.yml",
                "new_spec_yaml": "new: spec",
                "commit_message": "Test update",
            }
        )
    }

    # Execute
    response = lambda_handler(event, {})

    # Verify
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True
    assert body["pr_number"] == 42
    assert "pull/42" in body["pr_url"]
    assert body["branch_name"].startswith("action-spec-update-")
    assert body["warnings"] == []


@patch("handler.add_pr_labels")
@patch("handler.create_pull_request")
@patch("handler.commit_file_change")
@patch("handler.create_branch")
@patch("handler.check_destructive_changes")
@patch("handler.fetch_spec_file")
@patch("handler.parse_spec")
def test_handler_includes_warnings_in_response(
    mock_parse, mock_fetch, mock_check, mock_branch, mock_commit, mock_pr, mock_labels
):
    """Test warnings from change_detector appear in response"""
    # Setup mocks with warnings
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = [
        ChangeWarning(Severity.WARNING, "⚠️ Test warning", "spec.test")
    ]
    mock_branch.return_value = "abc123"
    mock_commit.return_value = "def456"
    mock_pr.return_value = {
        "number": 1,
        "url": "http://test",
        "api_url": "http://api",
    }

    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "spec_path": "specs/test.yml",
                "new_spec_yaml": "new: spec",
            }
        )
    }

    response = lambda_handler(event, {})

    # Verify warnings in response
    body = json.loads(response["body"])
    assert len(body["warnings"]) == 1
    assert body["warnings"][0]["severity"] == "warning"
    assert "Test warning" in body["warnings"][0]["message"]


@patch("handler.parse_spec")
def test_handler_validates_new_spec(mock_parse):
    """Test invalid spec rejected before PR creation"""
    from spec_parser.exceptions import ValidationError

    # Setup mock to raise validation error
    mock_parse.side_effect = ValidationError("Invalid spec")

    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "spec_path": "specs/test.yml",
                "new_spec_yaml": "invalid: yaml",
            }
        )
    }

    response = lambda_handler(event, {})

    # Verify error response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    assert "Validation failed" in body["error"]


@patch("handler.create_branch")
@patch("handler.check_destructive_changes")
@patch("handler.fetch_spec_file")
@patch("handler.parse_spec")
def test_handler_handles_branch_exists_error(
    mock_parse, mock_fetch, mock_check, mock_branch
):
    """Test graceful handling when branch already exists (retry with random suffix)"""
    from github_client import BranchExistsError

    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = []

    # First call raises BranchExistsError, second succeeds
    mock_branch.side_effect = [BranchExistsError("exists"), "abc123"]

    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "spec_path": "specs/test.yml",
                "new_spec_yaml": "new: spec",
            }
        )
    }

    with patch("handler.commit_file_change"), patch(
        "handler.create_pull_request"
    ) as mock_pr, patch("handler.add_pr_labels"):

        mock_pr.return_value = {
            "number": 1,
            "url": "http://test",
            "api_url": "http://api",
        }

        response = lambda_handler(event, {})

        # Verify retry logic worked
        assert response["statusCode"] == 200
        assert mock_branch.call_count == 2  # Called twice


@patch("handler.create_branch")
@patch("handler.check_destructive_changes")
@patch("handler.fetch_spec_file")
@patch("handler.parse_spec")
def test_handler_handles_github_api_failure(
    mock_parse, mock_fetch, mock_check, mock_branch
):
    """Test error handling for GitHub API failures"""
    from github_client import GitHubError

    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = []
    mock_branch.side_effect = GitHubError("API error")

    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "spec_path": "specs/test.yml",
                "new_spec_yaml": "new: spec",
            }
        )
    }

    response = lambda_handler(event, {})

    # Verify error response
    assert response["statusCode"] == 502
    body = json.loads(response["body"])
    assert body["success"] is False
    assert "GitHub API error" in body["error"]


@patch("handler.add_pr_labels")
@patch("handler.create_pull_request")
@patch("handler.commit_file_change")
@patch("handler.create_branch")
@patch("handler.check_destructive_changes")
@patch("handler.fetch_spec_file")
@patch("handler.parse_spec")
def test_handler_handles_label_addition_failure(
    mock_parse, mock_fetch, mock_check, mock_branch, mock_commit, mock_pr, mock_labels
):
    """Test that label addition failure doesn't fail the entire request"""
    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = []
    mock_branch.return_value = "abc123"
    mock_commit.return_value = "def456"
    mock_pr.return_value = {
        "number": 1,
        "url": "http://test",
        "api_url": "http://api",
    }
    # Label addition fails
    mock_labels.side_effect = Exception("Label API error")

    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "spec_path": "specs/test.yml",
                "new_spec_yaml": "new: spec",
            }
        )
    }

    response = lambda_handler(event, {})

    # Verify request still succeeds despite label failure
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True


@patch("handler.parse_spec")
def test_handler_handles_missing_required_field(mock_parse):
    """Test error handling for missing required field in request"""
    # Setup mock
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}

    # Missing 'spec_path' field
    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "new_spec_yaml": "new: spec",
            }
        )
    }

    response = lambda_handler(event, {})

    # Verify error response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    assert "Missing required field" in body["error"]


@patch("handler.fetch_spec_file")
@patch("handler.parse_spec")
def test_handler_handles_spec_file_not_found(mock_parse, mock_fetch):
    """Test error handling when old spec file doesn't exist in repo"""
    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.side_effect = FileNotFoundError("File not found in repo")

    event = {
        "body": json.dumps(
            {
                "repo": "test/repo",
                "spec_path": "specs/missing.yml",
                "new_spec_yaml": "new: spec",
            }
        )
    }

    response = lambda_handler(event, {})

    # Verify error response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["success"] is False
    assert "Spec file not found" in body["error"]
    assert "missing.yml" in body["details"]
