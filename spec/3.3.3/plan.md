# Implementation Plan: Spec Applier Lambda & PR Description Generator
Generated: 2025-10-23
Specification: spec/3.3.3/spec.md

## Understanding

This phase implements the spec-applier Lambda handler that creates GitHub PRs with formatted descriptions including destructive change warnings. It integrates:
- Phase 3.3.2 GitHub write operations (`create_branch`, `commit_file_change`, `create_pull_request`, `add_pr_labels`)
- Phase 3.2b change detection (`check_destructive_changes()`)
- Phase 3.2a spec parsing (`parse_spec()`)

The handler accepts POST requests with new spec YAML, validates it, fetches the old spec from GitHub, runs change detection, creates a feature branch, commits changes, and creates a PR with formatted warnings.

**Key Architectural Decisions:**
1. Use `kind` field (not `spec.type`) for spec metadata - matches ActionSpec schema structure
2. Single retry with random suffix on BranchExistsError (not multiple retries)
3. Test `_severity_emoji()` indirectly through `generate_pr_description()` integration

## Relevant Files

**Reference Patterns** (existing code to follow):

- `backend/lambda/functions/spec-parser/handler.py` (lines 1-87) - Lambda handler pattern with @secure_handler, JSON body parsing, error handling
- `backend/lambda/shared/github_client.py` (lines 312-526) - GitHub write operations (create_branch, commit_file_change, create_pull_request, add_pr_labels)
- `backend/lambda/shared/spec_parser/change_detector.py` (lines 35-64) - Change detection with ChangeWarning/Severity usage
- `backend/tests/test_change_detector.py` (lines 29-55) - Test pattern for warnings validation

**Files to Create:**

- `backend/tests/test_spec_applier.py` - Handler tests (5 test cases for PR creation flow, validation, errors)
- `backend/tests/test_pr_description_generator.py` - PR description generator tests (3 test cases)

**Files to Modify:**

- `backend/lambda/functions/spec-applier/handler.py` (replace lines 1-48) - Implement full handler logic with PR description generator
- `template.yaml` (lines 250, 272) - Update Description and Path (/api/submit → /spec/apply)

## Architecture Impact

- **Subsystems affected**: Lambda Backend, GitHub API Integration
- **New dependencies**: None (all dependencies from Phase 3.3.2: PyGithub, PyYAML, jsonschema, boto3)
- **Breaking changes**: API endpoint path changes from `/api/submit` to `/spec/apply` (documented in spec)

## Task Breakdown

### Task 1: Implement PR Description Generator Helper Functions
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: ADD (new functions at end of file, after lambda_handler placeholder)
**Pattern**: Reference `spec_parser/change_detector.py` lines 22-32 for Severity enum usage

**Implementation**:
```python
def _severity_emoji(severity) -> str:
    """Map Severity enum to emoji indicator"""
    from spec_parser.change_detector import Severity

    emoji_map = {
        Severity.INFO: 'ℹ️',
        Severity.WARNING: '⚠️',
        Severity.CRITICAL: '🔴'
    }
    return emoji_map.get(severity, '•')


def generate_pr_description(old_spec: dict, new_spec: dict, warnings: list) -> str:
    """
    Generate formatted PR description with warnings from change_detector.

    Args:
        old_spec: Previous spec dict
        new_spec: Updated spec dict
        warnings: List of ChangeWarning objects from check_destructive_changes()

    Returns:
        Markdown-formatted PR description
    """
    # Build warnings section
    if warnings:
        warnings_md = "\n".join([
            f"{_severity_emoji(w.severity)} {w.severity.value.upper()}: {w.message}"
            for w in warnings
        ])
    else:
        warnings_md = "No warnings - changes appear safe ✅"

    # Extract spec metadata (use 'kind' not 'spec.type')
    spec_kind = new_spec.get('kind', 'unknown')
    spec_name = new_spec.get('metadata', {}).get('name', 'unnamed')

    # Build template
    template = f"""## ActionSpec Update

**Spec**: `{spec_name}` (kind: `{spec_kind}`)

### Warnings
{warnings_md}

### Review Checklist
- [ ] Reviewed all warnings above
- [ ] Confirmed changes are intentional
- [ ] Tested in staging environment (if applicable)

---
🤖 Automated by [ActionSpec](https://github.com/trakrf/action-spec)
"""

    return template
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-applier/handler.py
mypy lambda/functions/spec-applier/ --ignore-missing-imports
```

---

### Task 2: Implement Lambda Handler - Imports and Setup
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: MODIFY (replace lines 1-48 with full implementation)
**Pattern**: Reference `spec-parser/handler.py` lines 1-19 for imports and path setup

**Implementation**:
```python
"""
Spec Applier Lambda Function
Phase 3.3.3: Create GitHub PRs with spec changes and destructive change warnings
"""

import json
import os
import sys
import time
import logging

# Add shared layer to path (matches Phase 3.1 pattern)
sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from github_client import (
    create_branch,
    commit_file_change,
    create_pull_request,
    add_pr_labels,
    fetch_spec_file,
    GitHubError,
    BranchExistsError,
    PullRequestExistsError,
)
from spec_parser.change_detector import check_destructive_changes, Severity
from spec_parser.parser import parse_spec
from spec_parser.exceptions import ValidationError, ParseError
from security_wrapper import secure_handler

logger = logging.getLogger()
logger.setLevel(logging.INFO)
```

**Validation**: Same as Task 1 (black + mypy)

---

### Task 3: Implement Lambda Handler - Request Parsing and Validation
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: MODIFY (continue handler implementation)
**Pattern**: Reference `spec-parser/handler.py` lines 40-61 for JSON body parsing

**Implementation**:
```python
@secure_handler
def lambda_handler(event, context):
    """
    POST /spec/apply

    Creates GitHub PR with spec changes and destructive change warnings.

    Request Body:
    {
      "repo": "trakrf/action-spec",
      "spec_path": "specs/examples/secure-web-waf.spec.yml",
      "new_spec_yaml": "apiVersion: actionspec/v1\n...",
      "commit_message": "Enable WAF protection"
    }

    Response (Success):
    {
      "success": true,
      "pr_url": "https://github.com/trakrf/action-spec/pull/123",
      "pr_number": 123,
      "branch_name": "action-spec-update-1234567890",
      "warnings": [...]
    }
    """
    try:
        # 1. Parse request body
        body = json.loads(event['body'])
        repo_name = body['repo']
        spec_path = body['spec_path']
        new_spec_yaml = body['new_spec_yaml']
        commit_message = body.get('commit_message', 'Update ActionSpec configuration')

        logger.info(f"Processing spec update for {repo_name}:{spec_path}")

        # 2. Validate new spec (will raise ValidationError if invalid)
        try:
            new_spec = parse_spec(new_spec_yaml)
        except (ValidationError, ParseError) as e:
            logger.warning(f"Spec validation failed: {e}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Validation failed',
                    'details': str(e)
                })
            }
```

**Validation**: Same as Task 1

---

### Task 4: Implement Lambda Handler - Old Spec Fetch and Change Detection
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: MODIFY (continue handler implementation)
**Pattern**: Reference `github_client.py` lines 216-309 for fetch_spec_file() and error handling

**Implementation**:
```python
        # 3. Fetch old spec from GitHub
        try:
            old_spec_yaml = fetch_spec_file(repo_name, spec_path)
            old_spec = parse_spec(old_spec_yaml)
        except FileNotFoundError as e:
            logger.error(f"Old spec not found: {e}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'success': False,
                    'error': 'Spec file not found',
                    'details': f"File '{spec_path}' not found in {repo_name}"
                })
            }

        # 4. Run change detection (KEY INTEGRATION with Phase 3.2b!)
        warnings = check_destructive_changes(old_spec, new_spec)
        logger.info(f"Change detection found {len(warnings)} warning(s)")
```

**Validation**: Same as Task 1

---

### Task 5: Implement Lambda Handler - Branch Creation with Retry Logic
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: MODIFY (continue handler implementation)
**Pattern**: Reference `github_client.py` lines 312-359 for create_branch() and BranchExistsError handling

**Implementation**:
```python
        # 5. Create feature branch with timestamp for uniqueness
        timestamp = int(time.time())
        branch_name = f"action-spec-update-{timestamp}"

        try:
            branch_sha = create_branch(repo_name, branch_name, base_ref='main')
            logger.info(f"Created branch {branch_name} (SHA: {branch_sha})")
        except BranchExistsError:
            # Retry ONCE with random suffix if timestamp collision
            import random
            suffix = random.randint(1000, 9999)
            branch_name = f"action-spec-update-{timestamp}-{suffix}"
            branch_sha = create_branch(repo_name, branch_name, base_ref='main')
            logger.info(f"Created branch {branch_name} with random suffix (SHA: {branch_sha})")
```

**Validation**: Same as Task 1

---

### Task 6: Implement Lambda Handler - File Commit and PR Creation
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: MODIFY (continue handler implementation)
**Pattern**: Reference `github_client.py` lines 361-483 for commit_file_change() and create_pull_request()

**Implementation**:
```python
        # 6. Commit spec changes to branch
        commit_sha = commit_file_change(
            repo_name,
            branch_name,
            spec_path,
            new_spec_yaml,
            commit_message
        )
        logger.info(f"Committed changes (SHA: {commit_sha})")

        # 7. Generate PR description with warnings
        pr_body = generate_pr_description(old_spec, new_spec, warnings)
        pr_title = f"ActionSpec Update: {commit_message}"

        # 8. Create pull request
        try:
            pr_info = create_pull_request(
                repo_name,
                pr_title,
                pr_body,
                head_branch=branch_name,
                base_branch='main'
            )
            logger.info(f"Created PR #{pr_info['number']}: {pr_info['url']}")
        except PullRequestExistsError:
            # PR already exists for this branch (edge case)
            logger.warning(f"PR already exists for branch {branch_name}")
            return {
                'statusCode': 409,
                'body': json.dumps({
                    'success': False,
                    'error': 'Pull request already exists',
                    'details': f"A PR already exists for branch '{branch_name}'"
                })
            }
```

**Validation**: Same as Task 1

---

### Task 7: Implement Lambda Handler - Label Addition and Success Response
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: MODIFY (continue handler implementation)
**Pattern**: Reference `github_client.py` lines 486-525 for add_pr_labels()

**Implementation**:
```python
        # 9. Add labels for filtering and automation (non-critical)
        try:
            add_pr_labels(repo_name, pr_info['number'], ['infrastructure-change', 'automated'])
            logger.info(f"Added labels to PR #{pr_info['number']}")
        except Exception as e:
            # Label addition is non-critical - log but don't fail
            logger.warning(f"Failed to add labels: {e}")

        # 10. Return response with PR URL and warnings
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'pr_url': pr_info['url'],
                'pr_number': pr_info['number'],
                'branch_name': branch_name,
                'warnings': [
                    {
                        'severity': w.severity.value,
                        'message': w.message,
                        'field_path': w.field_path
                    }
                    for w in warnings
                ]
            })
        }
```

**Validation**: Same as Task 1

---

### Task 8: Implement Lambda Handler - Error Handling
**File**: `backend/lambda/functions/spec-applier/handler.py`
**Action**: MODIFY (complete handler implementation)
**Pattern**: Reference `spec-parser/handler.py` lines 46-51 for error response format

**Implementation**:
```python
    except GitHubError as e:
        logger.error(f"GitHub error: {e}")
        return {
            'statusCode': 502,
            'body': json.dumps({
                'success': False,
                'error': 'GitHub API error',
                'details': str(e)
            })
        }
    except KeyError as e:
        logger.error(f"Missing required field in request: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'Missing required field',
                'details': f"Required field '{e}' not found in request body"
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            })
        }
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-applier/handler.py
mypy lambda/functions/spec-applier/ --ignore-missing-imports
```

---

### Task 9: Update SAM Template
**File**: `template.yaml`
**Action**: MODIFY (lines 250 and 272)
**Pattern**: Follow existing function definition structure

**Changes**:
1. Line 250: Change `Description: Apply spec changes via GitHub PR (Phase 3.1 stub)`
   to `Description: Apply spec changes via GitHub PR (Phase 3.3.3)`

2. Line 272: Change `Path: /api/submit` to `Path: /spec/apply`

**Validation**:
```bash
sam validate --template template.yaml
```

---

### Task 10: Create Handler Tests - Setup and Success Case
**File**: `backend/tests/test_spec_applier.py`
**Action**: CREATE
**Pattern**: Reference `test_change_detector.py` lines 1-55 for test structure and imports

**Implementation**:
```python
"""Tests for spec-applier Lambda handler (Phase 3.3.3)"""
import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "functions", "spec-applier"))

from handler import lambda_handler
from spec_parser.change_detector import ChangeWarning, Severity


@patch('handler.add_pr_labels')
@patch('handler.create_pull_request')
@patch('handler.commit_file_change')
@patch('handler.create_branch')
@patch('handler.check_destructive_changes')
@patch('handler.fetch_spec_file')
@patch('handler.parse_spec')
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
        'number': 42,
        'url': 'https://github.com/test/repo/pull/42',
        'api_url': 'https://api.github.com/repos/test/repo/pulls/42'
    }

    # Test event
    event = {
        'body': json.dumps({
            'repo': 'test/repo',
            'spec_path': 'specs/test.yml',
            'new_spec_yaml': 'new: spec',
            'commit_message': 'Test update'
        })
    }

    # Execute
    response = lambda_handler(event, {})

    # Verify
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['success'] is True
    assert body['pr_number'] == 42
    assert 'pull/42' in body['pr_url']
    assert body['branch_name'].startswith('action-spec-update-')
    assert body['warnings'] == []
```

**Validation**:
```bash
cd backend
pytest tests/test_spec_applier.py::test_handler_creates_pr_successfully -v
```

---

### Task 11: Create Handler Tests - Warnings and Validation Cases
**File**: `backend/tests/test_spec_applier.py`
**Action**: MODIFY (add more test cases)
**Pattern**: Reference `test_change_detector.py` lines 29-55 for ChangeWarning usage

**Implementation**:
```python
@patch('handler.add_pr_labels')
@patch('handler.create_pull_request')
@patch('handler.commit_file_change')
@patch('handler.create_branch')
@patch('handler.check_destructive_changes')
@patch('handler.fetch_spec_file')
@patch('handler.parse_spec')
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
    mock_pr.return_value = {'number': 1, 'url': 'http://test', 'api_url': 'http://api'}

    event = {
        'body': json.dumps({
            'repo': 'test/repo',
            'spec_path': 'specs/test.yml',
            'new_spec_yaml': 'new: spec',
        })
    }

    response = lambda_handler(event, {})

    # Verify warnings in response
    body = json.loads(response['body'])
    assert len(body['warnings']) == 1
    assert body['warnings'][0]['severity'] == 'warning'
    assert 'Test warning' in body['warnings'][0]['message']


@patch('handler.parse_spec')
def test_handler_validates_new_spec(mock_parse):
    """Test invalid spec rejected before PR creation"""
    from spec_parser.exceptions import ValidationError

    # Setup mock to raise validation error
    mock_parse.side_effect = ValidationError("Invalid spec")

    event = {
        'body': json.dumps({
            'repo': 'test/repo',
            'spec_path': 'specs/test.yml',
            'new_spec_yaml': 'invalid: yaml',
        })
    }

    response = lambda_handler(event, {})

    # Verify error response
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['success'] is False
    assert 'Validation failed' in body['error']
```

**Validation**:
```bash
cd backend
pytest tests/test_spec_applier.py -v
```

---

### Task 12: Create Handler Tests - Error Handling Cases
**File**: `backend/tests/test_spec_applier.py`
**Action**: MODIFY (add error handling tests)
**Pattern**: Follow existing test patterns

**Implementation**:
```python
@patch('handler.create_branch')
@patch('handler.check_destructive_changes')
@patch('handler.fetch_spec_file')
@patch('handler.parse_spec')
def test_handler_handles_branch_exists_error(mock_parse, mock_fetch, mock_check, mock_branch):
    """Test graceful handling when branch already exists (retry with random suffix)"""
    from github_client import BranchExistsError

    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = []

    # First call raises BranchExistsError, second succeeds
    mock_branch.side_effect = [BranchExistsError("exists"), "abc123"]

    event = {
        'body': json.dumps({
            'repo': 'test/repo',
            'spec_path': 'specs/test.yml',
            'new_spec_yaml': 'new: spec',
        })
    }

    with patch('handler.commit_file_change'), \
         patch('handler.create_pull_request') as mock_pr, \
         patch('handler.add_pr_labels'):

        mock_pr.return_value = {'number': 1, 'url': 'http://test', 'api_url': 'http://api'}

        response = lambda_handler(event, {})

        # Verify retry logic worked
        assert response['statusCode'] == 200
        assert mock_branch.call_count == 2  # Called twice


@patch('handler.create_branch')
@patch('handler.check_destructive_changes')
@patch('handler.fetch_spec_file')
@patch('handler.parse_spec')
def test_handler_handles_github_api_failure(mock_parse, mock_fetch, mock_check, mock_branch):
    """Test error handling for GitHub API failures"""
    from github_client import GitHubError

    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = []
    mock_branch.side_effect = GitHubError("API error")

    event = {
        'body': json.dumps({
            'repo': 'test/repo',
            'spec_path': 'specs/test.yml',
            'new_spec_yaml': 'new: spec',
        })
    }

    response = lambda_handler(event, {})

    # Verify error response
    assert response['statusCode'] == 502
    body = json.loads(response['body'])
    assert body['success'] is False
    assert 'GitHub API error' in body['error']
```

**Validation**:
```bash
cd backend
pytest tests/test_spec_applier.py -v --cov=lambda/functions/spec-applier --cov-report=term-missing
```

---

### Task 13: Create PR Description Generator Tests
**File**: `backend/tests/test_pr_description_generator.py`
**Action**: CREATE
**Pattern**: Reference `test_change_detector.py` for test structure

**Implementation**:
```python
"""Tests for PR description generator (Phase 3.3.3)"""
import os
import sys

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "functions", "spec-applier"))

from handler import generate_pr_description
from spec_parser.change_detector import ChangeWarning, Severity


def test_generate_pr_description_with_warnings():
    """Test PR description includes warnings from change_detector"""
    old_spec = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    new_spec = {"metadata": {"name": "test"}, "kind": "WebApplication"}

    warnings = [
        ChangeWarning(Severity.WARNING, "⚠️ WARNING: WAF disabled", "spec.security.waf.enabled"),
        ChangeWarning(Severity.CRITICAL, "🔴 CRITICAL: Engine changed", "spec.data.engine")
    ]

    description = generate_pr_description(old_spec, new_spec, warnings)

    assert "⚠️ WARNING: WAF disabled" in description
    assert "🔴 CRITICAL: Engine changed" in description
    assert "Review Checklist" in description
    assert "ActionSpec Update" in description


def test_generate_pr_description_no_warnings():
    """Test PR description when no warnings (safe changes)"""
    old_spec = {"metadata": {"name": "test"}, "kind": "StaticSite"}
    new_spec = {"metadata": {"name": "test"}, "kind": "StaticSite"}

    description = generate_pr_description(old_spec, new_spec, [])

    assert "No warnings - changes appear safe ✅" in description
    assert "Review Checklist" in description


def test_generate_pr_description_includes_spec_metadata():
    """Test PR description includes spec name and kind"""
    old_spec = {"metadata": {"name": "my-app"}, "kind": "APIService"}
    new_spec = {"metadata": {"name": "my-app"}, "kind": "APIService"}

    description = generate_pr_description(old_spec, new_spec, [])

    assert "`my-app`" in description
    assert "`APIService`" in description
```

**Validation**:
```bash
cd backend
pytest tests/test_pr_description_generator.py -v
black tests/test_pr_description_generator.py
```

---

## Risk Assessment

- **Risk**: Incorrect import paths for spec_parser modules
  **Mitigation**: Follow existing patterns from spec-parser handler (sys.path.insert), test imports in Task 2

- **Risk**: parse_spec() function signature mismatch
  **Mitigation**: Reference parser.py to confirm it's a standalone function (not SpecParser.parse_and_validate method)

- **Risk**: Missing random module import in branch retry logic
  **Mitigation**: Add `import random` inline in exception handler (Task 5)

- **Risk**: Test mocking complexity with nested patches
  **Mitigation**: Use @patch decorators in reverse order (innermost last), follow test_github_client.py patterns

## Integration Points

- **GitHub client integration**: Uses create_branch, commit_file_change, create_pull_request, add_pr_labels from Phase 3.3.2
- **Change detector integration**: Calls check_destructive_changes() from Phase 3.2b, returns ChangeWarning objects
- **Spec parser integration**: Uses parse_spec() from Phase 3.2a for validation
- **SAM template**: Updates API endpoint path to /spec/apply

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY code change:

**Gate 1: Syntax & Style**
```bash
cd backend
black --check lambda/functions/spec-applier/handler.py tests/test_spec_applier.py tests/test_pr_description_generator.py
```

**Gate 2: Type Safety**
```bash
cd backend
mypy lambda/functions/spec-applier/ --ignore-missing-imports
```

**Gate 3: Unit Tests**
```bash
cd backend
pytest tests/test_spec_applier.py tests/test_pr_description_generator.py -v
```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

After each task:
```bash
cd backend
black lambda/ tests/
mypy lambda/ --ignore-missing-imports
pytest tests/test_spec_applier.py tests/test_pr_description_generator.py -v
```

Final validation:
```bash
cd backend
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=85
sam validate --template template.yaml
```

## Plan Quality Assessment

**Complexity Score**: 5/10 (WELL-SCOPED)
**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from comprehensive spec
✅ Similar patterns found in spec-parser/handler.py (lines 1-87)
✅ GitHub write operations already implemented and tested (Phase 3.3.2)
✅ Change detector module exists and tested (Phase 3.2b)
✅ All clarifying questions answered (kind vs spec.type, retry strategy)
✅ Existing test patterns to follow at backend/tests/test_change_detector.py

**Assessment**: High confidence implementation - integrates existing tested components with clear patterns to follow. All dependencies from Phase 3.3.2/3.2b/3.2a are complete and stable.

**Estimated one-pass success probability**: 85%

**Reasoning**: Well-defined integration task with comprehensive spec, existing patterns, and tested dependencies. Main risks are minor (import paths, mock ordering) and easily fixable. The 15% uncertainty accounts for potential spec_parser import quirks and test mock complexity.
