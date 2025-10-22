# Phase 3.3.1: GitHub Client Foundation

## Origin
This specification implements the first sub-phase of Phase 3.3 (GitHub Integration & AWS Discovery) from PRD.md. Phase 3.3 was split into three independently deliverable PRs to manage complexity. This is the foundation that enables read-only GitHub access.

## Outcome
ActionSpec can authenticate with GitHub using a PAT stored in AWS SSM Parameter Store and fetch ActionSpec YAML files from repositories. This provides the foundation for PR creation (Phase 3.3.2) and form pre-population (Phase 3.4).

**What will change:**
- New `backend/lambda/shared/github_client.py` module with GitHub authentication and file fetching
- New `docs/GITHUB_SETUP.md` documentation for PAT creation and SSM configuration
- Unit tests with mocked PyGithub responses
- Error handling for auth failures, rate limits, and missing files

## User Story
As a **developer integrating ActionSpec with GitHub**
I want **secure, cached GitHub API access**
So that **I can fetch spec files without exposing tokens or hitting rate limits**

## Context

**Discovery**: Phase 3.1 created stub Lambda functions. Phase 3.2 built validation and change detection. Now we need to connect to GitHub to read real spec files and (in 3.3.2) create PRs.

**Current State**:
- Stub Lambda functions return hardcoded JSON
- No GitHub integration exists
- SSM Parameter Store is configured but unused
- PyGithub not yet integrated

**Desired State**:
- GitHub client module handles authentication via SSM
- Can fetch spec file content from any allowed repository
- Exponential backoff handles rate limiting gracefully
- Clear error messages for auth failures and missing files
- Token cached in memory to reduce SSM calls

**Why This Matters**:
- Foundation for Phase 3.3.2 (PR creation)
- Needed by form-generator Lambda in Phase 3.4
- Read-only access is safer to ship first
- Validates GitHub token setup before write operations

## Technical Requirements

### 1. GitHub Client Module (`backend/lambda/shared/github_client.py`)

**Core Functions:**

```python
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
    - Retrieves token from SSM_PARAM_NAME environment variable
    - Validates token by checking rate_limit (confirms auth works)
    """
    pass

def fetch_spec_file(repo_name: str, file_path: str, ref: str = 'main') -> str:
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
        PermissionError: If repository is private and token lacks access
        RateLimitError: If GitHub rate limit exceeded (includes retry-after)

    Implementation Notes:
    - Uses PyGithub repo.get_contents() API
    - Decodes base64 content automatically
    - Implements exponential backoff for rate limits (see retry logic below)
    """
    pass
```

**Error Handling & Retry Logic:**

```python
class GitHubError(Exception):
    """Base exception for GitHub client errors"""
    pass

class AuthenticationError(GitHubError):
    """GitHub authentication failed (invalid/expired token)"""
    pass

class RateLimitError(GitHubError):
    """GitHub API rate limit exceeded"""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after  # Seconds until rate limit resets

class RepositoryNotFoundError(GitHubError):
    """Repository doesn't exist or token lacks access"""
    pass

class FileNotFoundError(GitHubError):
    """File doesn't exist at specified path"""
    pass
```

**Retry Logic (Exponential Backoff):**

```python
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
BACKOFF_MULTIPLIER = 2

def _retry_with_backoff(func, *args, **kwargs):
    """
    Retry function with exponential backoff on rate limit errors.

    Strategy:
    - Retry 1: Wait 1 second
    - Retry 2: Wait 2 seconds
    - Retry 3: Wait 4 seconds
    - After 3 retries: Raise RateLimitError with retry_after value

    Non-rate-limit errors: Fail immediately (no retry)
    """
    pass
```

### 2. Environment Configuration

**Lambda Environment Variables:**
- `GITHUB_TOKEN_SSM_PARAM`: SSM Parameter Store path (e.g., `/actionspec/github-token`)
- `ALLOWED_REPOS`: Comma-separated whitelist (e.g., `trakrf/action-spec,trakrf/demo-repo`)

**SSM Parameter Setup:**
- Parameter Name: `/actionspec/github-token`
- Type: `SecureString`
- KMS Key: Default AWS managed key
- Value: GitHub Personal Access Token (PAT) with `repo` scope

### 3. Security Requirements

**MUST:**
- Never log GitHub tokens (even partially)
- Validate repository is in ALLOWED_REPOS whitelist
- Sanitize file paths to prevent directory traversal
- Use SecureString type in SSM (encrypted at rest)

**MUST NOT:**
- Store tokens in Lambda environment variables (use SSM only)
- Cache tokens on disk (memory only via @lru_cache)
- Return token in error messages
- Allow access to repositories outside whitelist

### 4. Testing Requirements

**Unit Tests (pytest):**
```python
# test_github_client.py

def test_get_github_client_success(mock_ssm, mock_github):
    """Test successful client creation with valid token"""
    pass

def test_get_github_client_invalid_token(mock_ssm):
    """Test AuthenticationError raised for invalid token"""
    pass

def test_get_github_client_missing_ssm_param(mock_ssm):
    """Test error when SSM parameter doesn't exist"""
    pass

def test_fetch_spec_file_success(mock_github):
    """Test fetching valid spec file returns content"""
    pass

def test_fetch_spec_file_not_found(mock_github):
    """Test FileNotFoundError for missing file"""
    pass

def test_fetch_spec_file_rate_limit_retry(mock_github):
    """Test exponential backoff on rate limit (succeeds on retry 2)"""
    pass

def test_fetch_spec_file_rate_limit_exhausted(mock_github):
    """Test RateLimitError after max retries"""
    pass

def test_fetch_spec_file_unauthorized_repo(mock_github):
    """Test PermissionError for private repo without access"""
    pass

def test_repository_whitelist_enforcement():
    """Test requests to non-whitelisted repos are rejected"""
    pass
```

**Mocking Strategy:**
- Use `unittest.mock.patch` for boto3 SSM client
- Use `unittest.mock.MagicMock` for PyGithub objects
- Mock rate limit responses with `github.RateLimitExceededException`
- Mock file content with base64-encoded YAML

### 5. Documentation Requirements

**`docs/GITHUB_SETUP.md`:**

```markdown
# GitHub Personal Access Token Setup

## Overview
ActionSpec uses a GitHub Personal Access Token (PAT) to authenticate with GitHub for reading spec files and creating pull requests.

## Creating a PAT

1. Go to GitHub Settings > Developer Settings > Personal Access Tokens > Tokens (classic)
2. Click "Generate new token (classic)"
3. Name: "ActionSpec Lambda Access"
4. Expiration: 90 days (recommended)
5. Scopes: Select `repo` (full repository access)
6. Click "Generate token"
7. **IMPORTANT**: Copy the token immediately (you won't see it again)

## Storing Token in AWS SSM

### Using AWS CLI:
```bash
aws ssm put-parameter \
  --name /actionspec/github-token \
  --type SecureString \
  --value "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  --description "GitHub PAT for ActionSpec Lambda functions" \
  --region us-west-2
```

### Using AWS Console:
1. Navigate to AWS Systems Manager > Parameter Store
2. Click "Create parameter"
3. Name: `/actionspec/github-token`
4. Type: `SecureString`
5. KMS Key: Use default AWS managed key
6. Value: Paste your GitHub PAT
7. Click "Create parameter"

## Verifying Setup

Test Lambda can retrieve token:
```bash
aws lambda invoke \
  --function-name actionspec-spec-parser \
  --payload '{"test": "github-auth"}' \
  response.json
```

Expected: No authentication errors in CloudWatch logs

## Security Best Practices

- Rotate tokens every 90 days
- Use separate tokens for dev/prod environments
- Never commit tokens to version control
- Use minimum required scopes (repo only)
- Monitor token usage in GitHub Settings > Personal Access Tokens

## Troubleshooting

**Error: "Parameter not found"**
- Verify parameter name matches GITHUB_TOKEN_SSM_PARAM environment variable
- Check Lambda execution role has `ssm:GetParameter` permission

**Error: "Bad credentials"**
- Token may be expired or revoked
- Regenerate token and update SSM parameter

**Error: "Rate limit exceeded"**
- Authenticated rate limit: 5000 requests/hour
- Wait for rate limit reset (check X-RateLimit-Reset header)
- Consider using GitHub App for higher limits (future enhancement)
```

### 6. Lambda IAM Permissions

Add to Lambda execution role policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter"
      ],
      "Resource": [
        "arn:aws:ssm:us-west-2:*:parameter/actionspec/github-token"
      ]
    }
  ]
}
```

### 7. Dependencies

Add to `backend/lambda/requirements.txt`:
```
PyGithub==2.1.1  # GitHub API wrapper
```

## Validation Criteria

### Immediate (Measured at PR Merge):
- [ ] `get_github_client()` successfully retrieves token from SSM
- [ ] `get_github_client()` caches client instance (verify @lru_cache works)
- [ ] `fetch_spec_file()` returns content from action-spec repository
- [ ] Unit tests cover all error scenarios (8+ tests)
- [ ] Test coverage > 90% for github_client.py
- [ ] Documentation allows new developer to set up PAT
- [ ] No tokens logged in CloudWatch (manual log review)
- [ ] Repository whitelist blocks unauthorized repos

### Integration Tests (Manual Testing):
- [ ] Create real SSM parameter with test token
- [ ] Lambda can fetch real spec file from action-spec repo
- [ ] Rate limit retry works (mock rate limit in test)
- [ ] Error messages are user-friendly and don't expose tokens

### Post-Merge (Phase 3.3.2 Validation):
- [ ] form-generator Lambda can use github_client to fetch specs
- [ ] spec-applier Lambda can use github_client as foundation for PR creation

## Success Metrics

**Technical:**
- Zero authentication failures with valid token
- < 500ms response time for cached client
- < 2s response time for spec file fetch
- 100% test pass rate
- Zero security findings in code review

**User Experience:**
- Clear error messages guide token setup
- Documentation enables setup in < 10 minutes
- No manual token rotation needed within 90 days

## Dependencies
- **Requires**: Phase 3.1 (SAM template with Lambda functions)
- **Requires**: SSM Parameter Store configured
- **Blocks**: Phase 3.3.2 (PR creation needs this foundation)
- **Blocks**: Phase 3.4 (form-generator needs spec fetching)

## Edge Cases to Handle

1. **Token Expired Mid-Operation**:
   - Detection: PyGithub raises `BadCredentialsException`
   - Response: Clear cache, raise AuthenticationError with helpful message
   - User Action: Rotate token in SSM, Lambda will pick up new token on next invocation

2. **Repository Renamed/Moved**:
   - Detection: `UnknownObjectException` from PyGithub
   - Response: Raise RepositoryNotFoundError with repo name
   - User Action: Update ALLOWED_REPOS environment variable

3. **Spec File Moved**:
   - Detection: `UnknownObjectException` with 404 status
   - Response: Raise FileNotFoundError with attempted path
   - User Action: Update file_path parameter in request

4. **Rate Limit Hit During Fetch**:
   - Detection: `RateLimitExceededException` from PyGithub
   - Response: Retry with exponential backoff (3 attempts)
   - Failure: Raise RateLimitError with retry_after timestamp

5. **Network Timeout**:
   - Detection: `requests.Timeout` from underlying library
   - Response: Retry once, then fail with clear timeout error
   - User Action: Check AWS network connectivity, VPC configuration

6. **Malformed Repository Name**:
   - Detection: Missing "/" separator in repo_name
   - Response: Raise ValueError with format example
   - Prevention: Add validation before GitHub API call

## Implementation Notes

### Why @lru_cache?
- Reduces SSM API calls (cost savings: ~$0.05 per 10,000 calls)
- Improves Lambda cold start performance
- Thread-safe caching (important for concurrent invocations)
- Memory-only (cache cleared on Lambda recycle)

### Why Exponential Backoff?
- GitHub recommends exponential backoff for rate limits
- Prevents thundering herd problem
- Gives API time to recover
- Industry standard retry pattern

### Why Repository Whitelist?
- Security: Prevents unauthorized repo access
- Cost: Limits API usage to expected repos
- Compliance: Ensures only approved repos are modified
- Easy to expand: Just update environment variable

### Why Read-Only First?
- Risk Reduction: Can't accidentally modify repos
- Validation: Confirms auth setup works
- Foundation: PR creation (3.3.2) builds on this
- Incremental Delivery: Ship value sooner

## Future Enhancements (Post-Phase 3.3.1)

Not in scope for this phase but documented for future work:

1. **GitHub App Authentication** (vs PAT)
   - Benefit: Higher rate limits (15,000/hour)
   - Benefit: Better security (app permissions vs user permissions)
   - Effort: 4-6 hours (app setup, webhook handling)

2. **Caching Spec File Content** (Redis/ElastiCache)
   - Benefit: Reduce GitHub API calls
   - Benefit: Faster response times
   - Effort: 8-12 hours (infrastructure, cache invalidation logic)

3. **Multi-Repository Support**
   - Benefit: Manage specs across multiple repos
   - Effort: 2-4 hours (mostly configuration)

4. **GraphQL API Migration**
   - Benefit: More efficient queries (less data transfer)
   - Benefit: Reduced rate limit consumption
   - Effort: 6-8 hours (learning GraphQL, migration)

## Conversation References

**Key Insights:**
- "Phase 3.3 is too big for one PR" - Split decision that created this sub-phase
- "Read-only GitHub access is safer to ship first" - Risk reduction strategy
- "3.3.2 builds on 3.3.1 foundation" - Sequential dependency justification

**Decisions Made:**
- Use SSM Parameter Store for token storage (security best practice)
- Implement exponential backoff (GitHub API recommendation)
- Repository whitelist enforcement (security requirement)
- @lru_cache for client instance (performance optimization)

**Concerns Addressed:**
- Token exposure in logs: Explicit "never log tokens" requirement
- Rate limiting: Exponential backoff with 3 retries
- Error clarity: Specific exception types with helpful messages
- Testing without real credentials: Comprehensive mocking strategy
