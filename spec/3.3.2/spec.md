# Phase 3.3.2: GitHub Client Write Operations & Code Reorganization

## Origin
This specification is Part 1 of the Spec Applier & PR Creation feature (split from original 3.3.2). This phase establishes the **foundation** for GitHub write operations and reorganizes shared modules for cross-Lambda consumption.

## Outcome
GitHub client can create branches, commit files, and create pull requests. Spec parsing modules are reorganized into shared/ directory for consumption by multiple Lambda functions.

**What will change:**
- Move `parser.py`, `change_detector.py`, `exceptions.py` to `shared/spec_parser/`
- Update `spec-parser` handler imports
- Extend `github_client.py` with 4 new functions (branch, commit, PR, labels)
- Add 5 new exception types
- Add `ALLOWED_REPOS` to SAM template
- Comprehensive unit tests for write operations

## User Story
As a **developer implementing PR automation**
I want **reusable GitHub write operations and shared spec parsing modules**
So that **multiple Lambdas can create PRs and validate specs**

## Context

**Discovery**: Phase 3.3.1 provides read-only GitHub access. Phase 3.2a/3.2b provide spec parsing and change detection. Now we need to:
1. Make parsing modules accessible to multiple Lambdas (can't import across function directories)
2. Add GitHub write operations to create PRs

**Current State**:
- `parser.py`, `change_detector.py`, `exceptions.py` in `functions/spec-parser/` (not accessible to spec-applier)
- `github_client.py` only reads from GitHub (no write operations)
- SAM template missing `ALLOWED_REPOS` environment variable
- No PR creation capability

**Desired State**:
- Shared modules in `shared/spec_parser/` (accessible via Lambda layer)
- GitHub client can create branches, commit files, create PRs, add labels
- All existing spec-parser tests still pass
- New tests cover write operations
- SAM template includes `ALLOWED_REPOS`

**Why This Matters**:
- **Code Reuse**: spec-applier needs parser and change_detector (can't import from another function)
- **Foundation**: GitHub write ops are prerequisite for Phase 3.3.3
- **Security**: Repository whitelist (ALLOWED_REPOS) prevents unauthorized access

## Technical Requirements

### 1. Code Reorganization (CRITICAL FIRST STEP)

**Move spec-parser modules to shared/**:
```bash
mkdir -p backend/lambda/shared/spec_parser/
mv backend/lambda/functions/spec-parser/parser.py backend/lambda/shared/spec_parser/
mv backend/lambda/functions/spec-parser/change_detector.py backend/lambda/shared/spec_parser/
mv backend/lambda/functions/spec-parser/exceptions.py backend/lambda/shared/spec_parser/
touch backend/lambda/shared/spec_parser/__init__.py
```

**Updated Directory Structure**:
```
backend/lambda/
├── shared/                          # Shared via Lambda Layer
│   ├── github_client.py
│   ├── security_wrapper.py
│   └── spec_parser/                 # NEW: Shared spec parsing logic
│       ├── __init__.py              # NEW
│       ├── parser.py                # MOVED from functions/spec-parser/
│       ├── change_detector.py       # MOVED from functions/spec-parser/
│       └── exceptions.py            # MOVED from functions/spec-parser/
├── functions/
│   ├── spec-parser/
│   │   ├── handler.py               # UPDATE: imports from spec_parser package
│   │   ├── requirements.txt
│   │   └── schema/
│   └── spec-applier/
│       └── handler.py               # Future: will import from spec_parser
```

**Update spec-parser handler imports** (`backend/lambda/functions/spec-parser/handler.py`):
```python
# OLD (before reorganization):
from parser import parse_spec
from exceptions import ParseError, ValidationError, SecurityError

# NEW (after reorganization):
from spec_parser.parser import parse_spec
from spec_parser.exceptions import ParseError, ValidationError, SecurityError
```

**Why This Must Be First**:
- spec-applier (Phase 3.3.3) will need these modules
- Lambda functions can't import from each other's directories
- Must verify tests still pass before building on top

### 2. Extend GitHub Client Module (`backend/lambda/shared/github_client.py`)

Add these functions to existing module from Phase 3.3.1:

```python
def create_branch(repo_name: str, branch_name: str, base_ref: str = 'main') -> str:
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

    Implementation:
        1. Validate repo_name format and whitelist
        2. Get authenticated GitHub client
        3. Get repository object
        4. Get SHA of base_ref (e.g., main branch HEAD)
        5. Create git reference: refs/heads/{branch_name}
        6. Return SHA

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
        raise RepositoryNotFoundError(repo_name, f"Base branch '{base_ref}' not found")

    # Create new branch
    try:
        new_ref = repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
        return new_ref.object.sha
    except GithubException as e:
        if "Reference already exists" in str(e):
            raise BranchExistsError(f"Branch '{branch_name}' already exists in {repo_name}")
        raise GitHubError(f"Failed to create branch: {e}")


def commit_file_change(
    repo_name: str,
    branch_name: str,
    file_path: str,
    new_content: str,
    commit_message: str
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

    Implementation:
        1. Validate repo and get client
        2. Get file's current SHA (required for update)
        3. Update file content with commit message
        4. Return commit SHA

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
        file = repo.get_contents(file_path, ref=branch_name)
        result = repo.update_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            sha=file.sha,
            branch=branch_name
        )
        return result['commit'].sha
    except UnknownObjectException:
        # File doesn't exist, create it
        result = repo.create_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            branch=branch_name
        )
        return result['commit'].sha


def create_pull_request(
    repo_name: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = 'main'
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

    Implementation:
        1. Validate repo and get client
        2. Create PR using PyGithub
        3. Extract number and URLs
        4. Return dict

    Example:
        pr = create_pull_request(
            "trakrf/action-spec",
            "Update WAF settings",
            "## Changes\n- Enabled WAF",
            "feature-123"
        )
        # pr = {"number": 10, "url": "https://...", "api_url": "https://api..."}
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
            title=title,
            body=body,
            head=head_branch,
            base=base_branch
        )
        return {
            'number': pr.number,
            'url': pr.html_url,
            'api_url': pr.url
        }
    except GithubException as e:
        if "A pull request already exists" in str(e):
            raise PullRequestExistsError(f"PR already exists for branch '{head_branch}'")
        if "404" in str(e) or "not found" in str(e).lower():
            raise BranchNotFoundError(f"Branch '{head_branch}' not found in {repo_name}")
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

    Implementation:
        1. Validate repo and get client
        2. Get PR as issue (labels work on issues)
        3. For each label, create if doesn't exist
        4. Add all labels to PR

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

    # Add labels to PR
    issue.add_to_labels(*labels)
```

**New Exception Types** (add to github_client.py):
```python
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
```

### 3. SAM Template Updates (`template.yaml`)

**Add ALLOWED_REPOS to Globals**:
```yaml
Globals:
  Function:
    Runtime: python3.11
    Timeout: 30
    MemorySize: 256
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment
        SPECS_BUCKET: !Ref SpecsBucket
        GITHUB_TOKEN_SSM_PARAM: !Ref GithubTokenParamName
        ALLOWED_REPOS: !Ref AllowedRepos  # NEW: Add this line
    Layers:
      - !Ref SharedDependenciesLayer
```

**Add AllowedRepos parameter**:
```yaml
Parameters:
  # ... existing parameters ...

  AllowedRepos:  # NEW: Add this parameter
    Type: String
    Default: "trakrf/action-spec"
    Description: Comma-separated list of allowed repositories (e.g., "owner/repo1,owner/repo2")
```

### 4. Testing Requirements

**Unit Tests** (`backend/tests/test_github_client_write_ops.py`):

```python
"""Tests for GitHub client write operations (Phase 3.3.2)"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.lambda.shared.github_client import (
    create_branch,
    commit_file_change,
    create_pull_request,
    add_pr_labels,
    BranchExistsError,
    BranchNotFoundError,
    PullRequestExistsError,
    PullRequestNotFoundError,
)


@patch('backend.lambda.shared.github_client.get_github_client')
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
    mock_repo.create_git_ref.assert_called_once_with("refs/heads/feature-test", "abc123")


@patch('backend.lambda.shared.github_client.get_github_client')
def test_create_branch_already_exists(mock_get_client):
    """Test BranchExistsError when branch exists"""
    from github import GithubException

    mock_repo = Mock()
    mock_repo.create_git_ref.side_effect = GithubException(
        422, {"message": "Reference already exists"}, {}
    )

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    with pytest.raises(BranchExistsError):
        create_branch("trakrf/action-spec", "feature-exists", "main")


@patch('backend.lambda.shared.github_client.get_github_client')
def test_commit_file_change_update(mock_get_client):
    """Test file update (file exists)"""
    mock_file = Mock()
    mock_file.sha = "file123"

    mock_commit = Mock()
    mock_commit.sha = "commit456"

    mock_repo = Mock()
    mock_repo.get_contents.return_value = mock_file
    mock_repo.update_file.return_value = {'commit': mock_commit}

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    sha = commit_file_change(
        "trakrf/action-spec",
        "feature-test",
        "spec.yml",
        "content",
        "Update spec"
    )

    assert sha == "commit456"
    mock_repo.update_file.assert_called_once()


@patch('backend.lambda.shared.github_client.get_github_client')
def test_commit_file_change_create(mock_get_client):
    """Test file creation (file doesn't exist)"""
    from github import UnknownObjectException

    mock_commit = Mock()
    mock_commit.sha = "commit789"

    mock_repo = Mock()
    mock_repo.get_contents.side_effect = UnknownObjectException(404, {}, {})
    mock_repo.create_file.return_value = {'commit': mock_commit}

    mock_client = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_get_client.return_value = mock_client

    sha = commit_file_change(
        "trakrf/action-spec",
        "feature-test",
        "new-spec.yml",
        "content",
        "Create spec"
    )

    assert sha == "commit789"
    mock_repo.create_file.assert_called_once()


@patch('backend.lambda.shared.github_client.get_github_client')
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
        "trakrf/action-spec",
        "Test PR",
        "Test body",
        "feature-test"
    )

    assert result['number'] == 42
    assert "pull/42" in result['url']
    assert "api.github.com" in result['api_url']


@patch('backend.lambda.shared.github_client.get_github_client')
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


@patch('backend.lambda.shared.github_client.get_github_client')
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

    mock_issue.add_to_labels.assert_called_once_with("automated", "infrastructure-change")


@patch('backend.lambda.shared.github_client.get_github_client')
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
```

## Validation Criteria

### Prerequisites (Before Implementation):
- [ ] Read Phase 3.3.1 github_client.py to understand existing patterns
- [ ] Read Phase 3.2a/3.2b test patterns for mocking strategy

### Immediate (Measured at PR Merge):
- [ ] **Code reorganization complete** - parser.py, change_detector.py, exceptions.py moved to shared/spec_parser/
- [ ] **spec-parser handler updated** - imports from spec_parser package
- [ ] **All existing spec-parser tests still pass** - verify reorganization didn't break anything
- [ ] **4 GitHub write functions implemented** - create_branch, commit_file_change, create_pull_request, add_pr_labels
- [ ] **5 new exception types added** - BranchExistsError, PullRequestExistsError, etc.
- [ ] **ALLOWED_REPOS in SAM template** - parameter and environment variable
- [ ] **8 unit tests pass** - test_github_client_write_ops.py
- [ ] **Test coverage > 85%** - for new github_client functions
- [ ] **Black formatting clean** - cd backend && black --check lambda/
- [ ] **Mypy types clean** - cd backend && mypy lambda/ --ignore-missing-imports

## Success Metrics

**Technical:**
- All existing tests still pass after reorganization
- New GitHub write operations covered by unit tests
- No breaking changes to spec-parser functionality

**Foundation:**
- Phase 3.3.3 can import from spec_parser package
- Phase 3.3.3 can use GitHub write operations

## Dependencies
- **Requires**: Phase 3.3.1 (github_client.py foundation, PyGithub installed)
- **Requires**: Phase 3.2a (parser.py exists)
- **Requires**: Phase 3.2b (change_detector.py exists)
- **Blocks**: Phase 3.3.3 (spec-applier needs these functions)

## Edge Cases to Handle

1. **Branch Already Exists**:
   - Detection: GithubException with "Reference already exists"
   - Response: Raise BranchExistsError

2. **File Doesn't Exist (commit_file_change)**:
   - Detection: UnknownObjectException when getting file
   - Response: Create file instead of update

3. **PR Already Exists**:
   - Detection: GithubException with "pull request already exists"
   - Response: Raise PullRequestExistsError

4. **Label Doesn't Exist**:
   - Detection: Check repo.get_labels()
   - Response: Create label with default color

## Implementation Notes

### Why Code Reorganization First?
- Lambda functions can't import from each other's directories
- Must be in shared/ to be accessible via Lambda layer
- Verify tests pass before building dependent code

### Why Add ALLOWED_REPOS Now?
- github_client.py already uses it (logs warning if missing)
- Phase 3.3.1 should have had it (fixing technical debt)
- Required for production security

### Testing Strategy
- Mock PyGithub objects (repo, issue, pr)
- Test success paths and error paths
- Verify exception types raised correctly
