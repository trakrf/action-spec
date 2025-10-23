# Phase 3.3.3: Spec Applier Lambda & PR Description Generator

## Origin
This specification is Part 2 of the Spec Applier & PR Creation feature (split from original 3.3.2). This phase implements the **core Lambda handler** that creates GitHub PRs with destructive change warnings.

## Outcome
The spec-applier Lambda accepts updated spec YAML, validates it, runs change detection, and creates a GitHub PR with formatted warnings. This completes the backend API for frontend integration (Phase 3.4).

**What will change:**
- Replace spec-applier stub handler with full implementation
- Implement PR description generator with change warnings
- Update SAM template API endpoint path from `/api/submit` to `/spec/apply`
- Update handler function name to `lambda_handler`
- Comprehensive unit tests for handler and PR generator
- Error handling for all failure scenarios

## User Story
As a **user submitting infrastructure changes via ActionSpec**
I want **automated PR creation with clear change summaries and warnings**
So that **I can review destructive changes before they're applied**

## Context

**Discovery**: Phase 3.3.2 provides GitHub write operations and reorganized spec parsing modules. Phase 3.2b provides change detection. Now we integrate them to create PRs with warnings.

**Current State**:
- spec-applier Lambda is a stub returning hardcoded JSON
- GitHub client can create branches, commit files, create PRs (Phase 3.3.2)
- change_detector.py exists but isn't consumed by any Lambda
- No PR description template

**Desired State**:
- spec-applier accepts spec YAML and creates GitHub PR
- Runs change detection (old spec vs new spec)
- PR description includes formatted warnings from change_detector
- Labels automatically applied: `infrastructure-change`, `automated`
- Returns PR URL and warnings in response
- All error scenarios handled gracefully

**Why This Matters**:
- **User Safety**: Warns before destructive changes (WAF disable, data loss)
- **Auditability**: All changes tracked in Git via PRs
- **Integration Point**: Connects validation (3.2a), detection (3.2b), GitHub (3.3.2)
- **Frontend Ready**: Provides API for Phase 3.4 React form

## Technical Requirements

### 1. PR Description Generator

Add to spec-applier handler file (`backend/lambda/functions/spec-applier/handler.py`):

```python
def generate_pr_description(old_spec: dict, new_spec: dict, warnings: list) -> str:
    """
    Generate formatted PR description with warnings from change_detector.

    Args:
        old_spec: Previous spec dict
        new_spec: Updated spec dict
        warnings: List of ChangeWarning objects from check_destructive_changes()

    Returns:
        Markdown-formatted PR description

    Example Output:
        ## ActionSpec Update

        **Spec**: `my-webapp` (type: `APIService`)

        ### Warnings
        ⚠️ WARNING: Disabling WAF will remove security protection
        🔴 CRITICAL: Changing database engine requires data migration

        ### Review Checklist
        - [ ] Reviewed all warnings above
        - [ ] Confirmed changes are intentional
        - [ ] Tested in staging environment (if applicable)

        ---
        🤖 Automated by [ActionSpec](https://github.com/trakrf/action-spec)
    """
    from spec_parser.change_detector import Severity

    # Build warnings section from change_detector output
    if warnings:
        warnings_md = "\n".join([
            f"{_severity_emoji(w.severity)} {w.severity.value.upper()}: {w.message}"
            for w in warnings
        ])
    else:
        warnings_md = "No warnings - changes appear safe ✅"

    # Build spec summary (basic metadata)
    spec_type = new_spec.get('spec', {}).get('type', 'unknown')
    spec_name = new_spec.get('metadata', {}).get('name', 'unnamed')

    # Combine into template
    template = f"""## ActionSpec Update

**Spec**: `{spec_name}` (type: `{spec_type}`)

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


def _severity_emoji(severity) -> str:
    """Map Severity enum to emoji indicator"""
    from spec_parser.change_detector import Severity

    emoji_map = {
        Severity.INFO: 'ℹ️',
        Severity.WARNING: '⚠️',
        Severity.CRITICAL: '🔴'
    }
    return emoji_map.get(severity, '•')
```

### 2. Spec Applier Handler Implementation

Replace stub in `backend/lambda/functions/spec-applier/handler.py`:

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
      "warnings": [
        {
          "severity": "warning",
          "message": "⚠️ WARNING: Disabling WAF will remove security protection",
          "field_path": "spec.security.waf.enabled"
        }
      ]
    }

    Response (Validation Error):
    {
      "success": false,
      "error": "Validation failed",
      "details": "..."
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

        # 5. Create feature branch with timestamp for uniqueness
        timestamp = int(time.time())
        branch_name = f"action-spec-update-{timestamp}"

        try:
            branch_sha = create_branch(repo_name, branch_name, base_ref='main')
            logger.info(f"Created branch {branch_name} (SHA: {branch_sha})")
        except BranchExistsError:
            # Retry with random suffix if timestamp collision
            import random
            suffix = random.randint(1000, 9999)
            branch_name = f"action-spec-update-{timestamp}-{suffix}"
            branch_sha = create_branch(repo_name, branch_name, base_ref='main')
            logger.info(f"Created branch {branch_name} with random suffix (SHA: {branch_sha})")

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
            # This shouldn't happen with timestamp-based names, but handle gracefully
            logger.warning(f"PR already exists for branch {branch_name}")
            return {
                'statusCode': 409,
                'body': json.dumps({
                    'success': False,
                    'error': 'Pull request already exists',
                    'details': f"A PR already exists for branch '{branch_name}'"
                })
            }

        # 9. Add labels for filtering and automation
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
                        'severity': w.severity.value,  # Severity is str Enum, .value gives "warning"/"critical"/"info"
                        'message': w.message,
                        'field_path': w.field_path
                    }
                    for w in warnings
                ]
            })
        }

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


# Helper functions (defined above in section 1)
def generate_pr_description(old_spec: dict, new_spec: dict, warnings: list) -> str:
    # ... (see section 1 for full implementation)
    pass


def _severity_emoji(severity) -> str:
    # ... (see section 1 for full implementation)
    pass
```

### 3. SAM Template Updates (`template.yaml`)

**Update SpecApplierFunction**:
```yaml
SpecApplierFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub ${AWS::StackName}-spec-applier
    CodeUri: backend/lambda/functions/spec-applier/
    Handler: handler.lambda_handler  # CHANGED: Must match function name
    Description: Apply spec changes via GitHub PR (Phase 3.3.3)
    Policies:
      - S3CrudPolicy:
          BucketName: !Ref SpecsBucket
      - Statement:
          - Sid: SSMGetParameter
            Effect: Allow
            Action:
              - ssm:GetParameter
            Resource: !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter${GithubTokenParamName}
          - Sid: CloudWatchLogs
            Effect: Allow
            Action:
              - logs:CreateLogGroup
              - logs:CreateLogStream
              - logs:PutLogEvents
            Resource: !Sub arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-*
    Events:
      ApplySpecApi:  # CHANGED: Event name
        Type: Api
        Properties:
          RestApiId: !Ref ActionSpecApi
          Path: /spec/apply  # CHANGED: From /api/submit to /spec/apply
          Method: POST
          Auth:
            ApiKeyRequired: true
```

### 4. Testing Requirements

**Unit Tests** (`backend/tests/test_spec_applier.py`):

```python
"""Tests for spec-applier Lambda handler (Phase 3.3.3)"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock


@patch('backend.lambda.functions.spec_applier.handler.create_pull_request')
@patch('backend.lambda.functions.spec_applier.handler.commit_file_change')
@patch('backend.lambda.functions.spec_applier.handler.create_branch')
@patch('backend.lambda.functions.spec_applier.handler.check_destructive_changes')
@patch('backend.lambda.functions.spec_applier.handler.fetch_spec_file')
@patch('backend.lambda.functions.spec_applier.handler.parse_spec')
def test_handler_creates_pr_successfully(
    mock_parse, mock_fetch, mock_check, mock_branch, mock_commit, mock_pr
):
    """Test complete PR creation flow end-to-end"""
    from backend.lambda.functions.spec_applier.handler import lambda_handler

    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}
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


@patch('backend.lambda.functions.spec_applier.handler.check_destructive_changes')
@patch('backend.lambda.functions.spec_applier.handler.fetch_spec_file')
@patch('backend.lambda.functions.spec_applier.handler.parse_spec')
def test_handler_includes_warnings_in_response(mock_parse, mock_fetch, mock_check):
    """Test warnings from change_detector appear in response"""
    from backend.lambda.functions.spec_applier.handler import lambda_handler
    from spec_parser.change_detector import ChangeWarning, Severity

    # Setup mocks with warnings
    mock_parse.return_value = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}
    mock_fetch.return_value = "old: spec"
    mock_check.return_value = [
        ChangeWarning(Severity.WARNING, "Test warning", "spec.test")
    ]

    event = {
        'body': json.dumps({
            'repo': 'test/repo',
            'spec_path': 'specs/test.yml',
            'new_spec_yaml': 'new: spec',
        })
    }

    with patch('backend.lambda.functions.spec_applier.handler.create_branch'), \
         patch('backend.lambda.functions.spec_applier.handler.commit_file_change'), \
         patch('backend.lambda.functions.spec_applier.handler.create_pull_request') as mock_pr:

        mock_pr.return_value = {'number': 1, 'url': 'http://test', 'api_url': 'http://api'}

        response = lambda_handler(event, {})

        # Verify warnings in response
        body = json.loads(response['body'])
        assert len(body['warnings']) == 1
        assert body['warnings'][0]['severity'] == 'warning'
        assert 'Test warning' in body['warnings'][0]['message']


@patch('backend.lambda.functions.spec_applier.handler.parse_spec')
def test_handler_validates_new_spec(mock_parse):
    """Test invalid spec rejected before PR creation"""
    from backend.lambda.functions.spec_applier.handler import lambda_handler
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


@patch('backend.lambda.functions.spec_applier.handler.create_branch')
@patch('backend.lambda.functions.spec_applier.handler.check_destructive_changes')
@patch('backend.lambda.functions.spec_applier.handler.fetch_spec_file')
@patch('backend.lambda.functions.spec_applier.handler.parse_spec')
def test_handler_handles_branch_exists_error(mock_parse, mock_fetch, mock_check, mock_branch):
    """Test graceful handling when branch already exists (retry with random suffix)"""
    from backend.lambda.functions.spec_applier.handler import lambda_handler
    from github_client import BranchExistsError

    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}
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

    with patch('backend.lambda.functions.spec_applier.handler.commit_file_change'), \
         patch('backend.lambda.functions.spec_applier.handler.create_pull_request') as mock_pr:

        mock_pr.return_value = {'number': 1, 'url': 'http://test', 'api_url': 'http://api'}

        response = lambda_handler(event, {})

        # Verify retry logic worked
        assert response['statusCode'] == 200
        assert mock_branch.call_count == 2  # Called twice (first failed, second succeeded)


@patch('backend.lambda.functions.spec_applier.handler.create_branch')
@patch('backend.lambda.functions.spec_applier.handler.check_destructive_changes')
@patch('backend.lambda.functions.spec_applier.handler.fetch_spec_file')
@patch('backend.lambda.functions.spec_applier.handler.parse_spec')
def test_handler_handles_github_api_failure(mock_parse, mock_fetch, mock_check, mock_branch):
    """Test error handling for GitHub API failures"""
    from backend.lambda.functions.spec_applier.handler import lambda_handler
    from github_client import GitHubError

    # Setup mocks
    mock_parse.return_value = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}
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

**PR Description Generator Tests** (`backend/tests/test_pr_description_generator.py`):

```python
"""Tests for PR description generator (Phase 3.3.3)"""
from backend.lambda.functions.spec_applier.handler import generate_pr_description
from spec_parser.change_detector import ChangeWarning, Severity


def test_generate_pr_description_with_warnings():
    """Test PR description includes warnings from change_detector"""
    old_spec = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}
    new_spec = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}

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
    old_spec = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}
    new_spec = {"metadata": {"name": "test"}, "spec": {"type": "StaticSite"}}

    description = generate_pr_description(old_spec, new_spec, [])

    assert "No warnings - changes appear safe ✅" in description
    assert "Review Checklist" in description


def test_generate_pr_description_includes_spec_metadata():
    """Test PR description includes spec name and type"""
    old_spec = {"metadata": {"name": "my-app"}, "spec": {"type": "APIService"}}
    new_spec = {"metadata": {"name": "my-app"}, "spec": {"type": "APIService"}}

    description = generate_pr_description(old_spec, new_spec, [])

    assert "`my-app`" in description
    assert "`APIService`" in description
```

## Validation Criteria

### Prerequisites (Before Implementation):
- [ ] Phase 3.3.2 complete (GitHub write ops available, spec_parser reorganized)
- [ ] Read existing handler.py stub to understand structure
- [ ] Read Phase 3.1 test patterns for Lambda handler testing

### Immediate (Measured at PR Merge):
- [ ] **Handler implementation complete** - Full spec-applier logic replacing stub
- [ ] **PR description generator implemented** - With emoji severity indicators
- [ ] **SAM template updated** - Path changed to /spec/apply, handler name to lambda_handler
- [ ] **5 handler tests pass** - test_spec_applier.py
- [ ] **3 PR generator tests pass** - test_pr_description_generator.py
- [ ] **Test coverage > 85%** - for handler and generator functions
- [ ] **Change detector integration working** - Warnings appear in PR and response
- [ ] **Black formatting clean** - cd backend && black --check lambda/
- [ ] **Mypy types clean** - cd backend && mypy lambda/ --ignore-missing-imports
- [ ] **All validation gates pass** - lint, typecheck, test from spec/stack.md

## Success Metrics

**Technical:**
- Handler creates PRs with formatted descriptions
- Warnings from change_detector appear correctly
- All error scenarios handled gracefully
- Test coverage meets >85% threshold

**Integration:**
- Phase 3.3.4 can run manual integration tests
- API endpoint ready for Phase 3.4 frontend

## Dependencies
- **Requires**: Phase 3.3.2 (GitHub write ops, spec_parser in shared/)
- **Requires**: Phase 3.2b (change_detector.py)
- **Requires**: Phase 3.2a (parser.py)
- **Blocks**: Phase 3.3.4 (manual integration tests)
- **Blocks**: Phase 3.4 (frontend needs this API)

## Edge Cases to Handle

1. **Invalid New Spec**:
   - Detection: ValidationError from parse_spec()
   - Response: Return 400 with error details
   - **Do NOT create PR** when validation fails

2. **Old Spec Not Found**:
   - Detection: FileNotFoundError from fetch_spec_file()
   - Response: Return 404 with helpful message

3. **Branch Already Exists** (timestamp collision):
   - Detection: BranchExistsError from create_branch()
   - Response: Retry with random suffix (e.g., timestamp-1234)

4. **PR Already Exists** (shouldn't happen with timestamps):
   - Detection: PullRequestExistsError
   - Response: Return 409 Conflict with message

5. **GitHub API Failure Mid-Operation**:
   - Detection: GitHubError exceptions
   - Response: Return 502 Bad Gateway
   - **Note**: Branch may be left orphaned (user can delete manually)

6. **Label Addition Fails** (non-critical):
   - Detection: Exception in add_pr_labels()
   - Response: Log warning but don't fail request
   - PR is still created successfully

## Implementation Notes

### Why Timestamp-Based Branch Names?
- **Uniqueness**: Prevents collisions for simultaneous submissions
- **Traceability**: Easy to identify when change was submitted
- **Chronological sorting**: Branches sort by time
- **Human-readable**: Better than UUIDs

### Why Include Warnings in Response AND PR?
- **Frontend UX**: Can display warnings immediately before user even clicks PR link
- **PR Documentation**: Warnings preserved in GitHub history
- **Redundancy**: Users see warnings in both places

### Why Make Label Addition Non-Critical?
- PR creation is the primary goal
- Labels are nice-to-have for filtering
- Don't fail the entire request if label API has issues

### Error Response Format
All error responses follow consistent structure:
```json
{
  "success": false,
  "error": "Error category",
  "details": "Specific error message"
}
```
