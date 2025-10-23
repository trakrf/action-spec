# Implementation Plan: Phase 3.3.2 - GitHub Client Write Operations & Code Reorganization
Generated: 2025-10-23
Specification: spec.md

## Understanding

This phase establishes the foundation for GitHub PR creation by:
1. **Reorganizing shared code**: Moving `parser.py`, `change_detector.py`, `exceptions.py` from `functions/spec-parser/` to `shared/spec_parser/` so they can be imported by multiple Lambda functions (spec-parser and spec-applier)
2. **Extending GitHub client**: Adding 4 write operations (create_branch, commit_file_change, create_pull_request, add_pr_labels) and 5 new exception types
3. **Adding security config**: ALLOWED_REPOS parameter to SAM template for repository whitelist
4. **Comprehensive testing**: 8 unit tests with mocked PyGithub, plus optional integration tests

**Critical Path**: Code reorganization MUST be done first and validated before any other work. If imports break, everything downstream fails.

## Relevant Files

**Reference Patterns** (existing code to follow):
- `backend/lambda/shared/github_client.py` (lines 81-145) - `get_github_client()` pattern with @lru_cache, SSM auth
- `backend/lambda/shared/github_client.py` (lines 186-279) - `fetch_spec_file()` retry logic pattern
- `backend/lambda/shared/github_client.py` (lines 30-78) - Exception class hierarchy pattern
- `backend/tests/test_github_client.py` (lines 32-80) - Test fixture patterns (mock_ssm, mock_github, set_env_vars)
- `backend/lambda/functions/spec-parser/handler.py` (lines 12-14) - sys.path setup pattern for imports

**Files to Create**:
- `backend/lambda/shared/spec_parser/__init__.py` - Empty init file to make spec_parser a package
- `backend/tests/test_github_client_write_ops.py` - Unit tests for new GitHub write operations (8 tests)
- `scripts/test-github-write-integration.sh` - Optional integration test script (manual execution)

**Files to Move** (reorganization):
- `backend/lambda/functions/spec-parser/parser.py` → `backend/lambda/shared/spec_parser/parser.py`
- `backend/lambda/functions/spec-parser/change_detector.py` → `backend/lambda/shared/spec_parser/change_detector.py`
- `backend/lambda/functions/spec-parser/exceptions.py` → `backend/lambda/shared/spec_parser/exceptions.py`

**Files to Modify**:
- `backend/lambda/shared/github_client.py` (lines ~280+) - Add 4 new functions, 5 exception classes (~200 lines)
- `backend/lambda/functions/spec-parser/handler.py` (line 37) - Change `from parser import SpecParser` to `from spec_parser.parser import SpecParser`
- `template.yaml` (lines 10-16) - Add ALLOWED_REPOS to Globals.Function.Environment.Variables
- `template.yaml` (lines 36-49) - Add AllowedRepos parameter after GithubTokenParamName

## Architecture Impact

- **Subsystems affected**:
  - Backend Lambda functions (github_client, spec-parser)
  - AWS SAM infrastructure (template.yaml)
  - Testing framework (pytest)

- **New dependencies**: None (PyGithub already installed in Phase 3.3.1)

- **Breaking changes**:
  - spec-parser handler imports change (but transparent to API consumers)
  - ALLOWED_REPOS must be set in SAM deployment (but has safe default)

## Task Breakdown

### Task 1: Code Reorganization - Create spec_parser Package
**Files**:
- CREATE: `backend/lambda/shared/spec_parser/__init__.py`
- CREATE: `backend/lambda/shared/spec_parser/` directory

**Action**: CREATE directory and package init

**Implementation**:
```bash
# Create package directory
mkdir -p backend/lambda/shared/spec_parser/

# Create empty __init__.py to make it a Python package
touch backend/lambda/shared/spec_parser/__init__.py
```

**Validation**:
```bash
# Verify directory exists
ls -la backend/lambda/shared/spec_parser/

# Expected: __init__.py exists (0 bytes is fine)
```

---

### Task 2: Code Reorganization - Move parser.py
**Files**:
- MOVE: `backend/lambda/functions/spec-parser/parser.py` → `backend/lambda/shared/spec_parser/parser.py`

**Action**: MOVE file

**Pattern**: Follow existing shared module pattern (github_client.py, security_wrapper.py in shared/)

**Implementation**:
```bash
# Move file (preserves git history)
git mv backend/lambda/functions/spec-parser/parser.py backend/lambda/shared/spec_parser/parser.py
```

**Validation**:
```bash
# Verify file exists in new location
ls -la backend/lambda/shared/spec_parser/parser.py

# Verify file removed from old location
! ls backend/lambda/functions/spec-parser/parser.py
```

---

### Task 3: Code Reorganization - Move change_detector.py
**Files**:
- MOVE: `backend/lambda/functions/spec-parser/change_detector.py` → `backend/lambda/shared/spec_parser/change_detector.py`

**Action**: MOVE file

**Implementation**:
```bash
git mv backend/lambda/functions/spec-parser/change_detector.py backend/lambda/shared/spec_parser/change_detector.py
```

**Validation**:
```bash
ls -la backend/lambda/shared/spec_parser/change_detector.py
! ls backend/lambda/functions/spec-parser/change_detector.py
```

---

### Task 4: Code Reorganization - Move exceptions.py
**Files**:
- MOVE: `backend/lambda/functions/spec-parser/exceptions.py` → `backend/lambda/shared/spec_parser/exceptions.py`

**Action**: MOVE file

**Implementation**:
```bash
git mv backend/lambda/functions/spec-parser/exceptions.py backend/lambda/shared/spec_parser/exceptions.py
```

**Validation**:
```bash
ls -la backend/lambda/shared/spec_parser/exceptions.py
! ls backend/lambda/functions/spec-parser/exceptions.py
```

---

### Task 5: Update spec-parser Handler Imports
**File**: `backend/lambda/functions/spec-parser/handler.py`

**Action**: MODIFY imports (line 37)

**Pattern**: Reference handler.py lines 12-14 for sys.path pattern

**Implementation**:
```python
# OLD (line 37):
from parser import SpecParser

# NEW:
from spec_parser.parser import SpecParser
```

**Validation**:
```bash
# Syntax check
cd backend
python3 -m py_compile lambda/functions/spec-parser/handler.py

# Run spec-parser tests to verify reorganization didn't break anything
pytest tests/test_parser.py -v
pytest tests/test_change_detector.py -v

# Spot-check: Try importing in Python REPL
cd backend
python3 -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'lambda', 'shared'))
from spec_parser.parser import SpecParser
from spec_parser.change_detector import check_destructive_changes
from spec_parser.exceptions import ParseError
print('✅ Imports successful')
"
```

**CRITICAL VALIDATION GATE**: All existing tests must pass before proceeding.

---

### Task 6: Add BranchExistsError Exception
**File**: `backend/lambda/shared/github_client.py`

**Action**: MODIFY (add after FileNotFoundError class, around line 78)

**Pattern**: Follow existing exception pattern from lines 30-78

**Implementation**:
```python
# Add after FileNotFoundError class (line ~78)

class BranchExistsError(GitHubError):
    """Branch already exists in repository"""
    pass
```

**Validation**:
```bash
cd backend
python3 -m py_compile lambda/shared/github_client.py
```

---

### Task 7: Add Remaining GitHub Exception Types
**File**: `backend/lambda/shared/github_client.py`

**Action**: MODIFY (add after BranchExistsError)

**Implementation**:
```python
# Add after BranchExistsError

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

**Validation**:
```bash
cd backend
python3 -m py_compile lambda/shared/github_client.py
black --check lambda/shared/github_client.py
```

---

### Task 8: Implement create_branch Function
**File**: `backend/lambda/shared/github_client.py`

**Action**: MODIFY (add after fetch_spec_file function, around line 279)

**Pattern**: Follow fetch_spec_file retry pattern (lines 186-279)

**Implementation**:
```python
# Add after fetch_spec_file function (line ~280)

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
        logger.info(f"Created branch {branch_name} in {repo_name} (SHA: {new_ref.object.sha})")
        return new_ref.object.sha
    except GithubException as e:
        if "Reference already exists" in str(e):
            raise BranchExistsError(f"Branch '{branch_name}' already exists in {repo_name}")
        raise GitHubError(f"Failed to create branch: {e}")
```

**Validation**:
```bash
cd backend
python3 -m py_compile lambda/shared/github_client.py
black --check lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

---

### Task 9: Implement commit_file_change Function
**File**: `backend/lambda/shared/github_client.py`

**Action**: MODIFY (add after create_branch)

**Pattern**: Similar to create_branch with error handling

**Implementation**:
```python
# Add after create_branch

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
        logger.info(f"Updated {file_path} in {repo_name} on {branch_name}")
        return result['commit'].sha
    except UnknownObjectException:
        # File doesn't exist, create it
        result = repo.create_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            branch=branch_name
        )
        logger.info(f"Created {file_path} in {repo_name} on {branch_name}")
        return result['commit'].sha
```

**Validation**:
```bash
cd backend
python3 -m py_compile lambda/shared/github_client.py
black --check lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

---

### Task 10: Implement create_pull_request Function
**File**: `backend/lambda/shared/github_client.py`

**Action**: MODIFY (add after commit_file_change)

**Implementation**:
```python
# Add after commit_file_change

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
            title=title,
            body=body,
            head=head_branch,
            base=base_branch
        )
        logger.info(f"Created PR #{pr.number} in {repo_name}: {pr.html_url}")
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
```

**Validation**:
```bash
cd backend
python3 -m py_compile lambda/shared/github_client.py
black --check lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

---

### Task 11: Implement add_pr_labels Function
**File**: `backend/lambda/shared/github_client.py`

**Action**: MODIFY (add after create_pull_request)

**Implementation**:
```python
# Add after create_pull_request

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
```

**Validation**:
```bash
cd backend
python3 -m py_compile lambda/shared/github_client.py
black --check lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

---

### Task 12: Add ALLOWED_REPOS to SAM Template Globals
**File**: `template.yaml`

**Action**: MODIFY (lines 10-16 in Globals.Function.Environment.Variables)

**Implementation**:
```yaml
# Modify Globals.Function.Environment.Variables (around line 10-16)
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
        ALLOWED_REPOS: !Ref AllowedRepos  # ADD THIS LINE
    Layers:
      - !Ref SharedDependenciesLayer
```

**Validation**:
```bash
# Validate YAML syntax
sam validate --template template.yaml
```

---

### Task 13: Add AllowedRepos Parameter to SAM Template
**File**: `template.yaml`

**Action**: MODIFY (add after GithubTokenParamName parameter, around line 49)

**Implementation**:
```yaml
# Add after GithubTokenParamName parameter (around line 46-49)
Parameters:
  Environment:
    Type: String
    Default: demo
    AllowedValues:
      - local
      - demo
      - prod
    Description: Deployment environment

  GithubTokenParamName:
    Type: String
    Default: /actionspec/github-token
    Description: SSM Parameter name for GitHub PAT

  AllowedRepos:  # ADD THIS PARAMETER
    Type: String
    Default: "trakrf/action-spec"
    Description: Comma-separated list of allowed repositories (e.g., "owner/repo1,owner/repo2")
```

**Validation**:
```bash
sam validate --template template.yaml
```

---

### Task 14: Create Unit Tests for GitHub Write Operations
**File**: `backend/tests/test_github_client_write_ops.py`

**Action**: CREATE

**Pattern**: Follow test_github_client.py patterns (lines 32-80 for fixtures)

**Implementation**:
See spec.md section 4 for complete test implementations. Create file with:
- test_create_branch_success
- test_create_branch_already_exists
- test_commit_file_change_update
- test_commit_file_change_create
- test_create_pull_request_success
- test_create_pull_request_already_exists
- test_add_pr_labels_success
- test_add_pr_labels_creates_missing

**Validation**:
```bash
cd backend
pytest tests/test_github_client_write_ops.py -v --cov=lambda.shared.github_client --cov-report=term-missing

# Expected: 8/8 tests pass, coverage > 85% for new functions
```

---

### Task 15: Run Full Validation Suite
**Files**: All modified files

**Action**: VALIDATE all changes

**Validation Gates** (from spec/stack.md):
```bash
cd backend

# Gate 1: Formatting
black --check lambda/ tests/

# Gate 2: Type checking
mypy lambda/ --ignore-missing-imports

# Gate 3: All tests
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=80

# Gate 4: SAM template
sam validate --template ../template.yaml
```

**Success Criteria**:
- ✅ All tests pass (existing + 8 new)
- ✅ Coverage > 85% for github_client.py
- ✅ Black formatting clean
- ✅ Mypy types clean
- ✅ SAM template valid

---

### Task 16: Create Optional Integration Test Script
**File**: `scripts/test-github-write-integration.sh`

**Action**: CREATE (optional, for manual execution)

**Implementation**:
```bash
#!/bin/bash
# Optional integration test for GitHub write operations
# Requires: GITHUB_TOKEN environment variable

set -e

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not set. Skipping integration tests."
    exit 0
fi

echo "🧪 Running GitHub write operations integration tests..."

# Test 1: Create branch
python3 -c "
import os
import sys
sys.path.insert(0, 'backend/lambda/shared')
os.environ['GITHUB_TOKEN_SSM_PARAM'] = '/test/token'
os.environ['ALLOWED_REPOS'] = 'trakrf/action-spec'

# Mock SSM to return GITHUB_TOKEN env var
import boto3
from unittest.mock import MagicMock, patch

with patch('github_client.boto3.client') as mock_client:
    mock_ssm = MagicMock()
    mock_client.return_value = mock_ssm
    mock_ssm.get_parameter.return_value = {
        'Parameter': {'Value': os.environ['GITHUB_TOKEN']}
    }

    from github_client import create_branch, BranchExistsError

    try:
        sha = create_branch('trakrf/action-spec', 'test-integration-branch', 'main')
        print(f'✅ Branch created: {sha}')
    except BranchExistsError:
        print('✅ Branch already exists (expected for re-runs)')
"

echo "✅ Integration tests complete"
echo "⚠️  Note: Clean up test branches manually"
```

**Validation**:
```bash
chmod +x scripts/test-github-write-integration.sh

# Only run if GITHUB_TOKEN is set
if [ -n "$GITHUB_TOKEN" ]; then
    ./scripts/test-github-write-integration.sh
fi
```

## Risk Assessment

- **Risk**: Code reorganization breaks existing spec-parser tests
  **Mitigation**: Validate tests pass after Task 5 before proceeding. Have rollback plan (git revert).

- **Risk**: GitHub API mocking doesn't match real behavior
  **Mitigation**: Optional integration tests (Task 16) validate against real API. Review PyGithub docs.

- **Risk**: SAM template syntax error prevents deployment
  **Mitigation**: Run `sam validate` after every template change (Tasks 12-13).

- **Risk**: Missing error scenarios in write operations
  **Mitigation**: Study fetch_spec_file error handling pattern (lines 186-279). Test all exception types.

- **Risk**: Import path issues in Lambda runtime
  **Mitigation**: Follow exact sys.path pattern from handler.py (lines 12-14). Test locally with same structure.

## Integration Points

- **spec_parser package**: Will be imported by spec-applier in Phase 3.3.3
- **GitHub write operations**: Will be used by spec-applier handler in Phase 3.3.3
- **ALLOWED_REPOS**: Required for production security, prevents unauthorized repo access

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are GATES that block progress, not suggestions.

After EVERY code change, run validation commands from `spec/stack.md`:

**Gate 1: Syntax & Style (Formatting)**
```bash
cd backend
black --check lambda/ tests/
```

**Gate 2: Type Safety**
```bash
cd backend
mypy lambda/ --ignore-missing-imports
```

**Gate 3: Unit Tests**
```bash
cd backend
pytest tests/ -v --cov=lambda --cov-report=term-missing
```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts on same issue → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

**After Code Reorganization (Tasks 1-5)**:
```bash
cd backend
pytest tests/test_parser.py tests/test_change_detector.py -v
# MUST PASS before continuing
```

**After Each GitHub Function (Tasks 8-11)**:
```bash
cd backend
python3 -m py_compile lambda/shared/github_client.py
black --check lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

**After SAM Template Changes (Tasks 12-13)**:
```bash
sam validate --template template.yaml
```

**Final Validation (Task 15)**:
```bash
cd backend
black --check lambda/ tests/
mypy lambda/ --ignore-missing-imports
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=80
sam validate --template ../template.yaml
```

## Plan Quality Assessment

**Complexity Score**: 7/10 (MEDIUM-HIGH)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ Similar patterns found in codebase (github_client.py Phase 3.3.1)
- ✅ All clarifying questions answered
- ✅ Existing test patterns to follow (test_github_client.py)
- ✅ PyGithub documentation available
- ⚠️ Code reorganization is first-time - must validate carefully
- ⚠️ GitHub write operations not previously implemented - new territory

**Assessment**: High confidence due to clear spec and existing patterns, but code reorganization adds risk. Mitigation: strict validation gates after reorganization.

**Estimated one-pass success probability**: 75%

**Reasoning**: The foundation (Phase 3.3.1) provides strong patterns to follow. Code reorganization is the highest risk area - if tests pass after Task 5, remaining work is straightforward PyGithub calls following existing patterns. Test coverage requirement (>85%) ensures quality.
