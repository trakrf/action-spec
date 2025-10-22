# Phase 3.3.2: Spec Applier & PR Creation

## Origin
This specification implements the second sub-phase of Phase 3.3 (GitHub Integration & AWS Discovery) from PRD.md. This is the **core write operation** that enables ActionSpec to create pull requests with infrastructure changes and change warnings.

## Outcome
ActionSpec can create GitHub pull requests with updated spec files, formatted descriptions, and **destructive change warnings** from the change detection engine (Phase 3.2b). This completes the spec submission workflow and enables the React frontend (Phase 3.4).

**What will change:**
- Complete `spec-applier` Lambda implementation (replaces stub from Phase 3.1)
- Extended `github_client.py` with branch creation and PR operations
- **Integration with `change_detector.py`** from Phase 3.2b
- PR description template with change summary and warnings
- Labels and reviewers automatically added to PRs
- Comprehensive error handling for GitHub API failures

## User Story
As a **user submitting infrastructure changes via ActionSpec**
I want **automated PR creation with clear change summaries and warnings**
So that **I can review destructive changes before they're applied**

## Context

**Discovery**: Phase 3.3.1 provides read-only GitHub access. Phase 3.2b provides change detection. Now we combine them to create PRs that warn users about destructive changes (WAF disabling, compute downsizing, etc.).

**Current State**:
- spec-applier Lambda is a stub returning hardcoded JSON
- github_client.py only reads from GitHub (no write operations)
- change_detector.py exists but isn't used by any Lambda
- No PR creation capability

**Desired State**:
- spec-applier Lambda accepts updated spec YAML
- Creates feature branch: `action-spec-update-{timestamp}`
- Commits spec changes to branch
- **Runs change detection** (old spec vs new spec)
- Creates PR with formatted description including warnings
- Adds labels: `infrastructure-change`, `automated`
- Returns PR URL to caller

**Why This Matters**:
- **User Safety**: Warns before destructive changes (WAF disable, data loss)
- **Auditability**: All changes tracked in Git history
- **Review Process**: PRs enable team review before apply
- **Integration Point**: Connects validation (3.2), detection (3.2b), and GitHub (3.3.1)

## Technical Requirements

### 1. Extend GitHub Client Module (`backend/lambda/shared/github_client.py`)

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

    Implementation Notes:
    - Get SHA of base_ref (e.g., main branch HEAD)
    - Create git reference: refs/heads/{branch_name}
    - Uses PyGithub repo.get_git_ref() and repo.create_git_ref()
    """
    pass

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

    Implementation Notes:
    - Get current file SHA (required for update)
    - Uses PyGithub repo.update_file()
    - Handles both new files and updates
    """
    pass

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

    Implementation Notes:
    - Uses PyGithub repo.create_pull()
    - Returns immediately (doesn't wait for CI/CD)
    """
    pass

def add_pr_labels(repo_name: str, pr_number: int, labels: list[str]) -> None:
    """
    Add labels to existing pull request.

    Args:
        repo_name: Repository in format "owner/repo"
        pr_number: PR number
        labels: List of label names (e.g., ["infrastructure-change", "automated"])

    Raises:
        PullRequestNotFoundError: If PR doesn't exist
        LabelNotFoundError: If label doesn't exist in repository

    Implementation Notes:
    - Labels must exist in repository first
    - Creates labels if they don't exist (with default color)
    - Uses PyGithub issue.add_to_labels()
    """
    pass
```

**New Exception Types:**
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

### 2. Spec Applier Lambda Implementation (`backend/lambda/functions/spec-applier/handler.py`)

Replace stub with full implementation:

```python
from shared.github_client import (
    create_branch,
    commit_file_change,
    create_pull_request,
    add_pr_labels
)
from spec_parser.change_detector import check_destructive_changes, Severity
from spec_parser.parser import parse_spec
from shared.security_wrapper import secure_handler
import os
import json
import time

@secure_handler
def handler(event, context):
    """
    POST /spec/apply

    Request Body:
    {
      "repo": "trakrf/action-spec",
      "spec_path": "specs/examples/secure-web-waf.spec.yml",
      "new_spec_yaml": "apiVersion: actionspec/v1\n...",
      "commit_message": "Enable WAF protection"
    }

    Response:
    {
      "success": true,
      "pr_url": "https://github.com/trakrf/action-spec/pull/123",
      "pr_number": 123,
      "branch_name": "action-spec-update-1234567890",
      "warnings": [
        {
          "severity": "WARNING",
          "message": "⚠️ WARNING: Disabling WAF will remove security protection",
          "field_path": "spec.security.waf.enabled"
        }
      ]
    }
    """

    # 1. Parse request body
    body = json.loads(event['body'])
    repo_name = body['repo']
    spec_path = body['spec_path']
    new_spec_yaml = body['new_spec_yaml']
    commit_message = body.get('commit_message', 'Update ActionSpec configuration')

    # 2. Validate new spec
    new_spec = parse_spec(new_spec_yaml)

    # 3. Fetch old spec from GitHub
    old_spec_yaml = fetch_spec_file(repo_name, spec_path)
    old_spec = parse_spec(old_spec_yaml)

    # 4. Run change detection (KEY INTEGRATION!)
    warnings = check_destructive_changes(old_spec, new_spec)

    # 5. Create feature branch
    timestamp = int(time.time())
    branch_name = f"action-spec-update-{timestamp}"
    create_branch(repo_name, branch_name, base_ref='main')

    # 6. Commit changes
    commit_sha = commit_file_change(
        repo_name,
        branch_name,
        spec_path,
        new_spec_yaml,
        commit_message
    )

    # 7. Generate PR description
    pr_body = generate_pr_description(old_spec, new_spec, warnings)
    pr_title = f"ActionSpec Update: {commit_message}"

    # 8. Create pull request
    pr_info = create_pull_request(
        repo_name,
        pr_title,
        pr_body,
        head_branch=branch_name,
        base_branch='main'
    )

    # 9. Add labels
    add_pr_labels(repo_name, pr_info['number'], ['infrastructure-change', 'automated'])

    # 10. Return response
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'pr_url': pr_info['url'],
            'pr_number': pr_info['number'],
            'branch_name': branch_name,
            'warnings': [w.to_dict() for w in warnings]
        })
    }
```

### 3. PR Description Generator

```python
def generate_pr_description(old_spec: dict, new_spec: dict, warnings: list) -> str:
    """
    Generate formatted PR description with change summary and warnings.

    Returns Markdown-formatted description following template:

    ## ActionSpec Update

    ### Changes
    - **WAF Protection**: `false` → `true`
    - **Compute Size**: `small` → `medium`

    ### Warnings
    ⚠️ WARNING: Disabling WAF will remove security protection (spec.security.waf.enabled)
    🔴 CRITICAL: Changing database engine requires data migration (spec.data.engine)

    ### Review Checklist
    - [ ] Reviewed all warnings above
    - [ ] Confirmed changes are intentional
    - [ ] Tested in staging environment (if applicable)

    ---
    🤖 Automated by [ActionSpec](https://github.com/trakrf/action-spec)
    """

    # Extract changed fields
    changes = _detect_field_changes(old_spec, new_spec)

    # Build changes section
    changes_md = "\n".join([
        f"- **{change['field']}**: `{change['old']}` → `{change['new']}`"
        for change in changes
    ])

    # Build warnings section
    warnings_md = "\n".join([
        f"{_severity_emoji(w.severity)} {w.severity}: {w.message} ({w.field_path})"
        for w in warnings
    ])

    # Combine into template
    template = f"""## ActionSpec Update

### Changes
{changes_md or "No field changes detected"}

### Warnings
{warnings_md or "No warnings - changes appear safe ✅"}

### Review Checklist
- [ ] Reviewed all warnings above
- [ ] Confirmed changes are intentional
- [ ] Tested in staging environment (if applicable)

---
🤖 Automated by [ActionSpec](https://github.com/trakrf/action-spec)
"""

    return template

def _severity_emoji(severity: str) -> str:
    """Map severity to emoji indicator"""
    return {
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'CRITICAL': '🔴'
    }.get(severity, '•')

def _detect_field_changes(old_spec: dict, new_spec: dict) -> list[dict]:
    """
    Detect changed fields between old and new spec.

    Returns list of dicts with keys:
        - field: Human-readable field name (e.g., "WAF Protection")
        - old: Old value
        - new: New value
        - path: JSON path (e.g., "spec.security.waf.enabled")
    """
    changes = []

    # Check common fields
    if old_spec.get('spec', {}).get('security', {}).get('waf', {}).get('enabled') != \
       new_spec.get('spec', {}).get('security', {}).get('waf', {}).get('enabled'):
        changes.append({
            'field': 'WAF Protection',
            'old': old_spec.get('spec', {}).get('security', {}).get('waf', {}).get('enabled'),
            'new': new_spec.get('spec', {}).get('security', {}).get('waf', {}).get('enabled'),
            'path': 'spec.security.waf.enabled'
        })

    # Add more field comparisons...

    return changes
```

### 4. API Gateway Integration

Update SAM template to wire spec-applier:

```yaml
SpecApplierFunction:
  Type: AWS::Serverless::Function
  Properties:
    Handler: handler.handler
    Events:
      ApplySpec:
        Type: Api
        Properties:
          RestApiId: !Ref ActionSpecApi
          Path: /spec/apply
          Method: POST
    Environment:
      Variables:
        GITHUB_TOKEN_SSM_PARAM: !Ref GithubTokenParam
        ALLOWED_REPOS: !Ref AllowedRepos
```

### 5. Testing Requirements

**Unit Tests (pytest):**

```python
# test_spec_applier.py

def test_handler_creates_pr_successfully(mock_github, mock_ssm):
    """Test complete PR creation flow end-to-end"""
    pass

def test_handler_includes_warnings_in_pr(mock_change_detector):
    """Test warnings from change_detector appear in PR description"""
    pass

def test_handler_validates_new_spec(mock_parser):
    """Test invalid spec rejected before PR creation"""
    pass

def test_handler_handles_branch_exists_error(mock_github):
    """Test graceful handling when branch already exists (retry with new timestamp)"""
    pass

def test_handler_handles_github_api_failure(mock_github):
    """Test error handling for GitHub API failures"""
    pass

# test_github_client_write_ops.py

def test_create_branch_success(mock_github):
    """Test branch creation with valid base_ref"""
    pass

def test_create_branch_already_exists(mock_github):
    """Test BranchExistsError when branch exists"""
    pass

def test_commit_file_change_success(mock_github):
    """Test file commit to existing branch"""
    pass

def test_create_pull_request_success(mock_github):
    """Test PR creation returns URL and number"""
    pass

def test_create_pull_request_already_exists(mock_github):
    """Test PullRequestExistsError for duplicate PR"""
    pass

def test_add_pr_labels_success(mock_github):
    """Test labels added to PR"""
    pass

def test_add_pr_labels_creates_missing_labels(mock_github):
    """Test labels created if they don't exist"""
    pass

# test_pr_description_generator.py

def test_generate_pr_description_with_warnings():
    """Test PR description includes warnings from change_detector"""
    warnings = [
        ChangeWarning(Severity.WARNING, "WAF disabled", "spec.security.waf.enabled"),
        ChangeWarning(Severity.CRITICAL, "Engine changed", "spec.data.engine")
    ]
    description = generate_pr_description(old_spec, new_spec, warnings)

    assert "⚠️ WARNING: WAF disabled" in description
    assert "🔴 CRITICAL: Engine changed" in description
    pass

def test_generate_pr_description_no_warnings():
    """Test PR description when no warnings (safe changes)"""
    pass

def test_detect_field_changes_waf_toggle():
    """Test field change detection for WAF enable/disable"""
    pass
```

**Integration Tests (Manual):**
- [ ] Create real PR in test repository
- [ ] Verify PR description formatting in GitHub UI
- [ ] Verify warnings appear correctly
- [ ] Verify labels applied
- [ ] Test with multiple simultaneous requests (branch name uniqueness)

### 6. Change Detector Integration (CRITICAL!)

**Import and Use:**
```python
from spec_parser.change_detector import check_destructive_changes, Severity, ChangeWarning

# In handler function:
warnings = check_destructive_changes(old_spec, new_spec)

# warnings is List[ChangeWarning] with attributes:
# - severity: Severity enum (INFO, WARNING, CRITICAL)
# - message: str (user-facing warning)
# - field_path: str (e.g., "spec.security.waf.enabled")

# Convert to dict for JSON response:
warnings_json = [
    {
        'severity': w.severity.value,
        'message': w.message,
        'field_path': w.field_path
    }
    for w in warnings
]
```

**Why This Integration Matters:**
- Phase 3.2b built change detection but it wasn't used
- This Lambda is the **first consumer** of change_detector.py
- Proves change detection works end-to-end
- Provides user value (safety warnings)

## Validation Criteria

### Immediate (Measured at PR Merge):
- [ ] spec-applier Lambda creates real PR in action-spec repo
- [ ] PR description includes change summary
- [ ] **PR description includes warnings from change_detector** (key validation!)
- [ ] PR has labels: `infrastructure-change`, `automated`
- [ ] Branch name includes timestamp (uniqueness)
- [ ] Lambda returns PR URL in response
- [ ] Unit tests cover all error scenarios (10+ tests)
- [ ] Test coverage > 85% for spec-applier handler
- [ ] Integration with change_detector.py verified (warning test passes)

### Integration Tests (Manual Validation):
- [ ] Create PR that disables WAF → Warning appears in description
- [ ] Create PR that downsizes compute → Warning appears in description
- [ ] Create PR with safe changes → "No warnings" message appears
- [ ] Multiple simultaneous requests → Unique branch names generated

### Post-Merge (Phase 3.4 Validation):
- [ ] React frontend can submit spec → PR created successfully
- [ ] Frontend displays warnings from Lambda response
- [ ] Users can click PR URL to review changes

## Success Metrics

**Technical:**
- < 5s end-to-end latency (fetch old spec → create PR)
- 100% test pass rate
- Zero PR creation failures in first week
- Warnings appear in 100% of PRs with destructive changes

**User Experience:**
- Users understand warnings without documentation
- PR descriptions provide sufficient context for review
- Clear next steps (review checklist)

## Dependencies
- **Requires**: Phase 3.3.1 (github_client.py foundation)
- **Requires**: Phase 3.2b (change_detector.py)
- **Requires**: Phase 3.2a (parser.py for spec validation)
- **Blocks**: Phase 3.4 (frontend needs this endpoint)

## Edge Cases to Handle

1. **Branch Already Exists**:
   - Scenario: User submits twice quickly
   - Detection: BranchExistsError from create_branch()
   - Response: Retry with new timestamp (add random suffix if needed)

2. **PR Already Exists for Branch**:
   - Scenario: Manual PR created for same branch
   - Detection: PullRequestExistsError
   - Response: Return existing PR URL (don't fail)

3. **Invalid New Spec**:
   - Scenario: User submits malformed YAML
   - Detection: ValidationError from parse_spec()
   - Response: Return 400 with validation errors (don't create PR)

4. **Old Spec Not Found**:
   - Scenario: Spec file moved or renamed
   - Detection: FileNotFoundError from fetch_spec_file()
   - Response: Return 404 with helpful message

5. **GitHub API Failure Mid-Operation**:
   - Scenario: Branch created but commit fails
   - Detection: Any GitHub exception after branch creation
   - Response: Log branch name, return error, leave branch (user can delete manually)

6. **Rate Limit During PR Creation**:
   - Scenario: Multiple PRs created simultaneously
   - Detection: RateLimitError
   - Response: Retry with exponential backoff (inherited from 3.3.1)

## Implementation Notes

### Why Timestamp in Branch Name?
- Uniqueness: Prevents collisions for simultaneous submissions
- Traceability: Easy to identify when change was submitted
- Sorting: Branches sort chronologically
- No UUID: Timestamps more human-readable

### Why Include Warnings in Response?
- Frontend UX: Can display warnings immediately
- Redundancy: Users see warnings in response AND in PR
- Validation: Confirms change detection ran

### Why Labels?
- Filtering: Easy to find ActionSpec PRs
- Automation: Can trigger CI/CD based on labels
- Documentation: Self-documenting PR source

### Why Review Checklist?
- User Guidance: Clear next steps
- Safety: Encourages thoughtful review
- Best Practice: Aligns with GitHub workflow

## Future Enhancements (Post-Phase 3.3.2)

Not in scope for this phase but documented for future work:

1. **PR Reviewers Auto-Assignment**
   - Benefit: Ensures PRs get reviewed
   - Implementation: Add to create_pull_request()
   - Effort: 1-2 hours

2. **CI/CD Status Checks**
   - Benefit: Block merge until validation passes
   - Implementation: GitHub Actions workflow
   - Effort: 3-4 hours

3. **Rollback Detection**
   - Benefit: Identify spec reverts (going back to old version)
   - Implementation: Compare new spec to older commits
   - Effort: 4-6 hours

4. **Slack Notifications**
   - Benefit: Alert team when PR created
   - Implementation: SNS → Lambda → Slack webhook
   - Effort: 2-3 hours

## Conversation References

**Key Insights:**
- "Phase 3.3.2 is the core feature of Phase 3.3" - Why this is the most important sub-phase
- "Integration with change_detector.py from Phase 3.2b" - First consumer of change detection
- "PR includes change warnings from detector" - Key success criterion

**Decisions Made:**
- Timestamp-based branch names (uniqueness + human-readable)
- Warnings in both response and PR description (redundancy for UX)
- Labels automatically applied (filtering + automation)
- Review checklist in PR template (user guidance)

**Concerns Addressed:**
- Branch name collisions: Timestamp + optional random suffix
- API failures mid-operation: Graceful degradation (leave branch)
- Invalid specs: Validate before creating PR
- User safety: Warnings prominently displayed
