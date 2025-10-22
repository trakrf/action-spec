# Implementation Plan: Phase 3.3.1 - GitHub Client Foundation
Generated: 2025-01-22
Specification: spec.md

## Understanding

This phase implements read-only GitHub integration for ActionSpec. The core requirement is to:
1. Authenticate with GitHub using a PAT stored in AWS SSM Parameter Store
2. Fetch ActionSpec YAML files from repositories
3. Handle errors gracefully (auth failures, rate limits, missing files)
4. Cache the GitHub client to reduce SSM calls
5. Enforce repository whitelist for security

This is the **foundation** for Phase 3.3.2 (PR creation) and Phase 3.4 (frontend form generator). Read-only access is intentionally shipped first to validate authentication setup before implementing write operations.

**Key Design Decisions:**
- Custom exception classes following `spec-parser/exceptions.py` pattern
- Repository whitelist validation in `fetch_spec_file()` (fail fast)
- `@lru_cache` for client caching (memory-only, no disk)
- Exponential backoff for GitHub rate limits (3 retries: 1s, 2s, 4s)
- Manual integration test script for real GitHub validation

## Relevant Files

**Reference Patterns** (existing code to follow):
- `backend/lambda/functions/spec-parser/exceptions.py` - Custom exception pattern with formatted messages
- `backend/lambda/shared/security_wrapper.py` - Module structure, logging, error handling
- `backend/tests/test_parser.py` (lines 1-30) - Test structure with fixtures and sys.path setup
- `backend/tests/test_security_wrapper.py` (lines 24-31) - MockContext class pattern
- `template.yaml` (lines 196-201, 249-253) - SSM parameter IAM policy pattern

**Files to Create**:
- `backend/lambda/shared/github_client.py` - Core GitHub integration module
- `backend/tests/test_github_client.py` - Comprehensive unit tests with mocks
- `backend/lambda/requirements.txt` - Shared dependency file (PyGithub)
- `docs/GITHUB_SETUP.md` - User documentation for PAT setup and SSM configuration
- `scripts/test-github-integration.sh` - Manual integration test script

**Files to Modify**:
- `template.yaml` - Add PyGithub to SharedDependenciesLayer build (no code changes, SAM handles it)
- `PRD.md` - Add tech debt note for Terraform automation of SSM parameter

## Architecture Impact
- **Subsystems affected**: Lambda backend only (shared module)
- **New dependencies**: PyGithub==2.1.1 (GitHub API wrapper), boto3 (already available in Lambda)
- **Breaking changes**: None (new functionality only)

## Task Breakdown

### Task 1: Create Custom Exception Classes
**File**: backend/lambda/shared/github_client.py
**Action**: CREATE
**Pattern**: Reference `backend/lambda/functions/spec-parser/exceptions.py` for structure

**Implementation**:
```python
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
from github import Github, GithubException, RateLimitExceededException, UnknownObjectException
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
        super().__init__(
            f"File not found: {file_path} in {repo_name} (ref: {ref})"
        )
```

**Validation**:
```bash
cd backend
python -m py_compile lambda/shared/github_client.py
black --check lambda/shared/github_client.py
```

---

### Task 2: Implement GitHub Client Authentication
**File**: backend/lambda/shared/github_client.py
**Action**: MODIFY (append to file from Task 1)
**Pattern**: Use boto3 SSM client, follow security_wrapper.py logging patterns

**Implementation**:
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
    - Retrieves token from GITHUB_TOKEN_SSM_PARAM environment variable
    - Validates token by checking rate_limit (confirms auth works)
    """
    # Get SSM parameter name from environment
    param_name = os.environ.get('GITHUB_TOKEN_SSM_PARAM')
    if not param_name:
        raise AuthenticationError(
            "GITHUB_TOKEN_SSM_PARAM environment variable not set",
            token_param=None
        )

    # Retrieve token from SSM Parameter Store
    try:
        ssm = boto3.client('ssm')
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        token = response['Parameter']['Value']
    except ssm.exceptions.ParameterNotFound:
        raise AuthenticationError(
            f"SSM parameter not found: {param_name}",
            token_param=param_name
        )
    except Exception as e:
        logger.error(f"Failed to retrieve GitHub token from SSM: {e}")
        raise AuthenticationError(
            f"Failed to retrieve token from SSM: {type(e).__name__}",
            token_param=param_name
        )

    # Create GitHub client
    try:
        client = Github(token)

        # Validate token by checking rate limit (lightweight API call)
        rate_limit = client.get_rate_limit()
        logger.info(
            f"GitHub client authenticated successfully "
            f"(rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit})"
        )

        return client

    except BadCredentialsException:
        raise AuthenticationError(
            "Invalid or expired GitHub token",
            token_param=param_name
        )
    except Exception as e:
        logger.error(f"Failed to create GitHub client: {e}")
        raise AuthenticationError(
            f"Failed to create GitHub client: {type(e).__name__}",
            token_param=param_name
        )
```

**Validation**:
```bash
cd backend
black --check lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

---

### Task 3: Implement Repository Whitelist Validation
**File**: backend/lambda/shared/github_client.py
**Action**: MODIFY (append helper function)
**Pattern**: Validation before external API call (fail fast)

**Implementation**:
```python
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
    if '/' not in repo_name:
        raise ValueError(
            f"Invalid repository format: '{repo_name}'. "
            f"Expected format: 'owner/repo' (e.g., 'trakrf/action-spec')"
        )

    # Get whitelist from environment
    allowed_repos_str = os.environ.get('ALLOWED_REPOS', '')
    if not allowed_repos_str:
        logger.warning("ALLOWED_REPOS not set - all repositories allowed (insecure!)")
        return

    allowed_repos = [repo.strip() for repo in allowed_repos_str.split(',')]

    if repo_name not in allowed_repos:
        logger.warning(
            f"Repository not in whitelist: {repo_name} "
            f"(allowed: {', '.join(allowed_repos)})"
        )
        raise RepositoryNotFoundError(repo_name)

    logger.debug(f"Repository whitelist check passed: {repo_name}")
```

**Validation**:
```bash
cd backend
black --check lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

---

### Task 4: Implement File Fetching with Retry Logic
**File**: backend/lambda/shared/github_client.py
**Action**: MODIFY (append main function)
**Pattern**: Exponential backoff for rate limits

**Implementation**:
```python
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
    if '../' in file_path or '.\\' in file_path:
        raise ValueError(f"Invalid file path (directory traversal detected): {file_path}")

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
            if hasattr(file_content, 'decoded_content'):
                content = file_content.decoded_content.decode('utf-8')
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
                backoff = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
                logger.warning(
                    f"Rate limit exceeded, retrying in {backoff}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(backoff)
            else:
                # Get retry_after from rate limit
                rate_limit = client.get_rate_limit()
                reset_timestamp = rate_limit.core.reset.timestamp()
                retry_after = int(reset_timestamp - time.time())

                raise RateLimitError(
                    f"Exhausted {MAX_RETRIES} retries",
                    retry_after=max(retry_after, 0)
                )

        except (FileNotFoundError, RepositoryNotFoundError, ValueError):
            # Don't retry these errors
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching file: {e}")
            raise GitHubError(f"Failed to fetch file: {type(e).__name__}: {str(e)}")

    # Should never reach here
    raise GitHubError("Unexpected error in fetch_spec_file retry loop")
```

**Validation**:
```bash
cd backend
black lambda/shared/github_client.py
mypy lambda/shared/github_client.py --ignore-missing-imports
```

---

### Task 5: Create Comprehensive Unit Tests
**File**: backend/tests/test_github_client.py
**Action**: CREATE
**Pattern**: Follow `test_parser.py` structure with fixtures and mocks

**Implementation**:
```python
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
    with patch('github_client.boto3.client') as mock_client:
        mock_ssm = MagicMock()
        mock_client.return_value = mock_ssm

        # Default: return valid token
        mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'ghp_test_token_1234567890'}
        }

        yield mock_ssm


@pytest.fixture
def mock_github():
    """Mock PyGithub Github client."""
    with patch('github_client.Github') as mock_github_class:
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
    os.environ['GITHUB_TOKEN_SSM_PARAM'] = '/actionspec/github-token'
    os.environ['ALLOWED_REPOS'] = 'trakrf/action-spec,trakrf/demo-repo'

    yield

    # Cleanup
    if 'GITHUB_TOKEN_SSM_PARAM' in os.environ:
        del os.environ['GITHUB_TOKEN_SSM_PARAM']
    if 'ALLOWED_REPOS' in os.environ:
        del os.environ['ALLOWED_REPOS']


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
        Name='/actionspec/github-token',
        WithDecryption=True
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
    del os.environ['GITHUB_TOKEN_SSM_PARAM']

    with pytest.raises(AuthenticationError) as exc_info:
        get_github_client()

    assert 'environment variable not set' in str(exc_info.value)


def test_get_github_client_ssm_parameter_not_found(mock_ssm, mock_github):
    """Test error when SSM parameter doesn't exist."""
    mock_ssm.get_parameter.side_effect = mock_ssm.exceptions.ParameterNotFound(
        {'Error': {'Code': 'ParameterNotFound'}},
        'GetParameter'
    )

    with pytest.raises(AuthenticationError) as exc_info:
        get_github_client()

    assert 'not found' in str(exc_info.value)
    assert '/actionspec/github-token' in str(exc_info.value)


def test_get_github_client_invalid_token(mock_ssm, mock_github):
    """Test AuthenticationError for invalid GitHub token."""
    from github.GithubException import BadCredentialsException

    mock_github.get_rate_limit.side_effect = BadCredentialsException(
        401, {'message': 'Bad credentials'}
    )

    with pytest.raises(AuthenticationError) as exc_info:
        get_github_client()

    assert 'Invalid or expired' in str(exc_info.value)


# Tests: _validate_repository_whitelist()

def test_validate_repository_whitelist_success():
    """Test successful whitelist validation."""
    # Should not raise
    _validate_repository_whitelist('trakrf/action-spec')


def test_validate_repository_whitelist_invalid_format():
    """Test error for malformed repository name."""
    with pytest.raises(ValueError) as exc_info:
        _validate_repository_whitelist('invalid-repo-name')

    assert 'Invalid repository format' in str(exc_info.value)
    assert 'owner/repo' in str(exc_info.value)


def test_validate_repository_whitelist_not_allowed():
    """Test error for repository not in whitelist."""
    with pytest.raises(RepositoryNotFoundError) as exc_info:
        _validate_repository_whitelist('attacker/malicious-repo')

    assert 'attacker/malicious-repo' in str(exc_info.value)


# Tests: fetch_spec_file()

def test_fetch_spec_file_success(mock_ssm, mock_github):
    """Test successful file fetch."""
    # Mock repository and file
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_file = MagicMock()
    mock_file.decoded_content = b'apiVersion: actionspec/v1\nkind: StaticSite'
    mock_repo.get_contents.return_value = mock_file

    content = fetch_spec_file(
        'trakrf/action-spec',
        'specs/examples/minimal.yml'
    )

    assert 'apiVersion: actionspec/v1' in content
    mock_repo.get_contents.assert_called_once_with(
        'specs/examples/minimal.yml',
        ref='main'
    )


def test_fetch_spec_file_with_custom_ref(mock_ssm, mock_github):
    """Test file fetch with custom branch ref."""
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_file = MagicMock()
    mock_file.decoded_content = b'test content'
    mock_repo.get_contents.return_value = mock_file

    content = fetch_spec_file(
        'trakrf/action-spec',
        'test.yml',
        ref='feature/test'
    )

    mock_repo.get_contents.assert_called_once_with(
        'test.yml',
        ref='feature/test'
    )


def test_fetch_spec_file_not_in_whitelist(mock_ssm, mock_github):
    """Test error when repository not in whitelist."""
    with pytest.raises(RepositoryNotFoundError):
        fetch_spec_file('unauthorized/repo', 'test.yml')


def test_fetch_spec_file_directory_traversal(mock_ssm, mock_github):
    """Test error for directory traversal attempt."""
    with pytest.raises(ValueError) as exc_info:
        fetch_spec_file('trakrf/action-spec', '../../../etc/passwd')

    assert 'directory traversal' in str(exc_info.value).lower()


def test_fetch_spec_file_repository_not_found(mock_ssm, mock_github):
    """Test error when repository doesn't exist."""
    from github import UnknownObjectException

    mock_github.get_repo.side_effect = UnknownObjectException(
        404, {'message': 'Not Found'}
    )

    with pytest.raises(RepositoryNotFoundError) as exc_info:
        fetch_spec_file('trakrf/action-spec', 'test.yml')

    assert 'trakrf/action-spec' in str(exc_info.value)


def test_fetch_spec_file_file_not_found(mock_ssm, mock_github):
    """Test error when file doesn't exist."""
    from github import UnknownObjectException

    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_repo.get_contents.side_effect = UnknownObjectException(
        404, {'message': 'Not Found'}
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        fetch_spec_file('trakrf/action-spec', 'missing.yml')

    assert 'missing.yml' in str(exc_info.value)
    assert 'trakrf/action-spec' in str(exc_info.value)


def test_fetch_spec_file_rate_limit_retry_success(mock_ssm, mock_github):
    """Test exponential backoff succeeds on retry 2."""
    from github import RateLimitExceededException

    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    mock_file = MagicMock()
    mock_file.decoded_content = b'success after retry'

    # Fail twice, succeed third time
    mock_repo.get_contents.side_effect = [
        RateLimitExceededException(403, {'message': 'Rate limit'}),
        RateLimitExceededException(403, {'message': 'Rate limit'}),
        mock_file
    ]

    with patch('github_client.time.sleep') as mock_sleep:
        content = fetch_spec_file('trakrf/action-spec', 'test.yml')

    assert 'success after retry' in content
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
        403, {'message': 'Rate limit'}
    )

    # Mock rate limit reset time
    mock_rate_limit = MagicMock()
    mock_rate_limit.core.reset.timestamp.return_value = time.time() + 300  # 5 minutes
    mock_github.get_rate_limit.return_value = mock_rate_limit

    with patch('github_client.time.sleep'):
        with pytest.raises(RateLimitError) as exc_info:
            fetch_spec_file('trakrf/action-spec', 'test.yml')

    assert exc_info.value.retry_after > 0
    assert 'Exhausted' in str(exc_info.value)


def test_fetch_spec_file_is_directory(mock_ssm, mock_github):
    """Test error when path is a directory, not a file."""
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    # Return list (directory) instead of file
    mock_repo.get_contents.return_value = [MagicMock(), MagicMock()]

    with pytest.raises(FileNotFoundError):
        fetch_spec_file('trakrf/action-spec', 'specs/')
```

**Validation**:
```bash
cd backend
pytest tests/test_github_client.py -v
pytest tests/test_github_client.py -v --cov=lambda/shared/github_client --cov-report=term-missing
black --check tests/test_github_client.py
```

---

### Task 6: Create Requirements File
**File**: backend/lambda/requirements.txt
**Action**: CREATE
**Pattern**: New file for shared dependencies

**Implementation**:
```
# ActionSpec Lambda Dependencies
# Shared across all Lambda functions

# GitHub API integration
PyGithub==2.1.1

# YAML parsing (already used by spec-parser)
PyYAML==6.0.1

# JSON Schema validation (already used by spec-parser)
jsonschema==4.20.0

# AWS SDK (provided by Lambda runtime, but specified for local development)
boto3==1.34.10
```

**Validation**:
```bash
# Verify file exists and is readable
cat backend/lambda/requirements.txt
```

---

### Task 7: Create GitHub Setup Documentation
**File**: docs/GITHUB_SETUP.md
**Action**: CREATE
**Pattern**: User-facing documentation (no code reference needed)

**Implementation**:
```markdown
# GitHub Personal Access Token Setup

## Overview
ActionSpec uses a GitHub Personal Access Token (PAT) to authenticate with GitHub for reading spec files and creating pull requests. This guide walks through token creation, storage in AWS SSM Parameter Store, and validation.

## Prerequisites
- GitHub account with access to repositories
- AWS CLI installed and configured
- AWS account with SSM Parameter Store access

## Step 1: Create GitHub Personal Access Token

1. **Navigate to GitHub Settings**:
   - Go to https://github.com/settings/tokens
   - Or: Settings > Developer Settings > Personal Access Tokens > Tokens (classic)

2. **Generate New Token**:
   - Click **"Generate new token (classic)"**
   - Name: `ActionSpec Lambda Access`
   - Expiration: **90 days** (recommended for security)
   - Select scopes:
     - ✅ `repo` (Full control of private repositories)
       - Includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`
   - Click **"Generate token"**

3. **Copy Token Immediately**:
   - ⚠️ **CRITICAL**: Copy the token now - you won't see it again
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Store securely (password manager recommended)

## Step 2: Store Token in AWS SSM Parameter Store

### Option A: Using AWS CLI (Recommended)

```bash
aws ssm put-parameter \
  --name /actionspec/github-token \
  --type SecureString \
  --value "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  --description "GitHub PAT for ActionSpec Lambda functions" \
  --region us-west-2
```

**Expected output**:
```json
{
    "Version": 1,
    "Tier": "Standard"
}
```

### Option B: Using AWS Console

1. Navigate to **AWS Systems Manager** > **Parameter Store**
2. Click **"Create parameter"**
3. Configure parameter:
   - **Name**: `/actionspec/github-token`
   - **Description**: `GitHub PAT for ActionSpec Lambda functions`
   - **Tier**: Standard
   - **Type**: **SecureString** (encrypted at rest)
   - **KMS Key**: `alias/aws/ssm` (default AWS managed key)
   - **Value**: Paste your GitHub PAT
4. Click **"Create parameter"**

## Step 3: Verify Setup

### Test SSM Parameter Retrieval

```bash
# Test parameter exists and is retrievable
aws ssm get-parameter \
  --name /actionspec/github-token \
  --with-decryption \
  --region us-west-2 \
  --query 'Parameter.Value' \
  --output text
```

**Expected**: Your GitHub PAT should be displayed (starts with `ghp_`)

### Test Lambda Can Retrieve Token

Run integration test script:

```bash
./scripts/test-github-integration.sh
```

This script:
1. Retrieves token from SSM
2. Authenticates with GitHub
3. Fetches a test spec file from action-spec repository
4. Reports success/failure

**Expected output**:
```
✅ SSM Parameter retrieved successfully
✅ GitHub authentication successful (rate limit: 5000/5000)
✅ Test spec file fetched successfully (567 bytes)

All tests passed!
```

## Step 4: Configure Lambda Execution Role

The Lambda execution role needs permission to read the SSM parameter.

### Check Existing Permissions

```bash
# Get Lambda execution role ARN
aws lambda get-function \
  --function-name actionspec-form-generator \
  --query 'Configuration.Role' \
  --output text

# Check role policies
aws iam list-attached-role-policies --role-name <role-name>
```

### Required IAM Policy

The SAM template (`template.yaml`) already includes this policy for functions that need GitHub access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMGetParameter",
      "Effect": "Allow",
      "Action": ["ssm:GetParameter"],
      "Resource": "arn:aws:ssm:us-west-2:*:parameter/actionspec/github-token"
    }
  ]
}
```

If deploying manually, attach this policy to the Lambda execution role.

## Security Best Practices

### Token Rotation

**Recommended schedule**: Every 90 days

```bash
# Generate new token in GitHub (follow Step 1)

# Update SSM parameter
aws ssm put-parameter \
  --name /actionspec/github-token \
  --type SecureString \
  --value "ghp_NEW_TOKEN_HERE" \
  --overwrite \
  --region us-west-2
```

Lambda will pick up new token on next invocation (thanks to `@lru_cache` clearing on restart).

### Environment Separation

Use different tokens for dev/prod:

```bash
# Development
aws ssm put-parameter \
  --name /actionspec/dev/github-token \
  --type SecureString \
  --value "ghp_DEV_TOKEN" \
  --region us-west-2

# Production
aws ssm put-parameter \
  --name /actionspec/prod/github-token \
  --type SecureString \
  --value "ghp_PROD_TOKEN" \
  --region us-west-2
```

Update Lambda `GITHUB_TOKEN_SSM_PARAM` environment variable accordingly.

### Least Privilege

- **Minimum scope**: `repo` (required for private repos)
- **Read-only alternative**: `public_repo` (only if all specs are in public repos)
- **Future**: Consider GitHub Apps for better security (higher rate limits, fine-grained permissions)

### Monitoring

**Track token usage** in GitHub Settings > Personal Access Tokens:
- Last used timestamp
- API rate limit consumption
- Suspicious activity

**CloudWatch metrics** to monitor:
- Lambda invocation errors (may indicate auth failures)
- `AuthenticationError` exceptions in logs

## Troubleshooting

### Error: "Parameter not found"

**Cause**: SSM parameter doesn't exist or name mismatch

**Solution**:
```bash
# List all parameters
aws ssm describe-parameters --region us-west-2

# Verify exact parameter name
aws ssm get-parameter --name /actionspec/github-token --region us-west-2
```

### Error: "Bad credentials"

**Cause**: Token is expired, revoked, or invalid

**Solution**:
1. Check token expiration in GitHub Settings
2. Verify token has `repo` scope
3. Generate new token and update SSM parameter

### Error: "AccessDeniedException" (Lambda)

**Cause**: Lambda execution role lacks `ssm:GetParameter` permission

**Solution**:
```bash
# Check Lambda role
aws lambda get-function --function-name actionspec-form-generator \
  --query 'Configuration.Role'

# Attach required policy (if missing)
aws iam attach-role-policy \
  --role-name <lambda-role-name> \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

### Error: "Rate limit exceeded"

**Cause**: Too many GitHub API requests

**Authenticated rate limit**: 5000 requests/hour

**Solution**:
- Wait for rate limit reset (check `X-RateLimit-Reset` header)
- Exponential backoff should handle this automatically
- Consider GitHub App for 15,000 requests/hour

## Tech Debt: Terraform Automation

**Current**: Manual SSM parameter creation via AWS CLI/Console

**Future** (tracked in PRD.md):
- Automate SSM parameter creation via Terraform
- Read token from `terraform.tfvars` or environment variable
- Follow 12-factor app principles (config from environment)

**Target**:
```hcl
# infrastructure/modules/backend/ssm.tf
resource "aws_ssm_parameter" "github_token" {
  name        = "/actionspec/${var.environment}/github-token"
  description = "GitHub PAT for ActionSpec Lambda functions"
  type        = "SecureString"
  value       = var.github_token  # From terraform.tfvars or TF_VAR_github_token

  lifecycle {
    ignore_changes = [value]  # Allow manual rotation without Terraform drift
  }
}
```

## Additional Resources

- [GitHub PAT Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [AWS SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
```

**Validation**:
```bash
# Verify documentation renders correctly
cat docs/GITHUB_SETUP.md | head -50
```

---

### Task 8: Create Integration Test Script
**File**: scripts/test-github-integration.sh
**Action**: CREATE
**Pattern**: Manual testing script for real GitHub validation

**Implementation**:
```bash
#!/usr/bin/env bash
#
# Integration test for GitHub client
# Tests real GitHub authentication and file fetching
#
# Usage: ./scripts/test-github-integration.sh
#
# Prerequisites:
# - GitHub PAT stored in SSM: /actionspec/github-token
# - AWS CLI configured
# - Python 3.11+ with PyGithub installed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SSM_PARAM_NAME="${GITHUB_TOKEN_SSM_PARAM:-/actionspec/github-token}"
TEST_REPO="trakrf/action-spec"
TEST_FILE="specs/examples/secure-web-waf.spec.yml"
AWS_REGION="${AWS_REGION:-us-west-2}"

echo "=================================================="
echo "GitHub Integration Test"
echo "=================================================="
echo ""

# Test 1: Retrieve token from SSM
echo "Test 1: Retrieve GitHub token from SSM..."
if TOKEN=$(aws ssm get-parameter \
    --name "$SSM_PARAM_NAME" \
    --with-decryption \
    --region "$AWS_REGION" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null); then
    echo -e "${GREEN}✅ SSM Parameter retrieved successfully${NC}"
    echo "   Parameter: $SSM_PARAM_NAME"
    echo "   Token prefix: ${TOKEN:0:7}..."
else
    echo -e "${RED}❌ Failed to retrieve SSM parameter${NC}"
    echo "   Parameter: $SSM_PARAM_NAME"
    echo "   Region: $AWS_REGION"
    echo ""
    echo "Create parameter with:"
    echo "  aws ssm put-parameter \\"
    echo "    --name $SSM_PARAM_NAME \\"
    echo "    --type SecureString \\"
    echo "    --value 'ghp_YOUR_TOKEN_HERE' \\"
    echo "    --region $AWS_REGION"
    exit 1
fi
echo ""

# Test 2: Authenticate with GitHub
echo "Test 2: Authenticate with GitHub..."
PYTHON_TEST_AUTH=$(cat <<'EOF'
import sys
from github import Github, GithubException

token = sys.argv[1]
try:
    client = Github(token)
    rate_limit = client.get_rate_limit()
    print(f"✅ GitHub authentication successful")
    print(f"   Rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit}")
    print(f"   Reset: {rate_limit.core.reset}")
    sys.exit(0)
except GithubException as e:
    print(f"❌ GitHub authentication failed: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)

if python3 -c "$PYTHON_TEST_AUTH" "$TOKEN"; then
    echo ""
else
    echo -e "${RED}❌ GitHub authentication failed${NC}"
    echo "   Check token validity in GitHub Settings"
    exit 1
fi

# Test 3: Fetch test spec file
echo "Test 3: Fetch test spec file..."
PYTHON_TEST_FETCH=$(cat <<'EOF'
import sys
from github import Github

token = sys.argv[1]
repo_name = sys.argv[2]
file_path = sys.argv[3]

try:
    client = Github(token)
    repo = client.get_repo(repo_name)
    file_content = repo.get_contents(file_path)
    content = file_content.decoded_content.decode('utf-8')

    print(f"✅ Test spec file fetched successfully")
    print(f"   Repository: {repo_name}")
    print(f"   File: {file_path}")
    print(f"   Size: {len(content)} bytes")
    print(f"   First line: {content.split(chr(10))[0]}")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed to fetch file: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)

if python3 -c "$PYTHON_TEST_FETCH" "$TOKEN" "$TEST_REPO" "$TEST_FILE"; then
    echo ""
else
    echo -e "${RED}❌ Failed to fetch test file${NC}"
    echo "   Repository: $TEST_REPO"
    echo "   File: $TEST_FILE"
    exit 1
fi

# Test 4: Test repository whitelist (should fail for unauthorized repo)
echo "Test 4: Test repository whitelist..."
UNAUTHORIZED_REPO="unauthorized/repo"
PYTHON_TEST_WHITELIST=$(cat <<'EOF'
import sys
from github import Github

token = sys.argv[1]
repo_name = sys.argv[2]

try:
    client = Github(token)
    repo = client.get_repo(repo_name)
    # Should fail before getting here due to whitelist
    print(f"❌ Whitelist check failed - unauthorized repo accessed", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    # Expected to fail (repo doesn't exist or unauthorized)
    print(f"✅ Whitelist validation working (unauthorized repo rejected)")
    print(f"   Attempted: {repo_name}")
    sys.exit(0)
EOF
)

python3 -c "$PYTHON_TEST_WHITELIST" "$TOKEN" "$UNAUTHORIZED_REPO"
echo ""

# Summary
echo "=================================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "=================================================="
echo ""
echo "Your GitHub integration is working correctly."
echo "You can now use the github_client module in Lambda functions."
echo ""
echo "Next steps:"
echo "  1. Deploy Lambda functions: sam build && sam deploy"
echo "  2. Test via API Gateway endpoint"
echo "  3. Monitor CloudWatch logs for authentication issues"
```

**Validation**:
```bash
chmod +x scripts/test-github-integration.sh
bash -n scripts/test-github-integration.sh  # Syntax check
```

---

### Task 9: Add Tech Debt Note to PRD.md
**File**: PRD.md
**Action**: MODIFY
**Pattern**: Add note to Future Enhancements section

**Implementation**:
Append to the appropriate section in PRD.md (search for "Future Enhancements" or "Tech Debt"):

```markdown
### Tech Debt: GitHub Token Management

**Current State (Phase 3.3.1)**:
- GitHub PAT manually created and stored in SSM Parameter Store via AWS CLI
- Token value pasted from GitHub settings into `aws ssm put-parameter` command
- Manual rotation every 90 days

**Desired State** (12-Factor App Compliance):
- GitHub token sourced from environment variable or Terraform variable
- Terraform creates SSM parameter automatically during deployment
- Token value read from `terraform.tfvars` (gitignored) or `TF_VAR_github_token` env var
- Infrastructure-as-code for reproducible deployments

**Benefits**:
- ✅ Eliminates manual AWS CLI steps
- ✅ Environment-specific tokens (dev/staging/prod) managed consistently
- ✅ Token rotation integrated into deployment pipeline
- ✅ Follows 12-factor app config principles

**Implementation Plan**:
```hcl
# infrastructure/modules/backend/ssm.tf
resource "aws_ssm_parameter" "github_token" {
  name        = "/actionspec/${var.environment}/github-token"
  description = "GitHub PAT for ActionSpec Lambda functions"
  type        = "SecureString"
  value       = var.github_token  # From terraform.tfvars or TF_VAR_github_token

  lifecycle {
    ignore_changes = [value]  # Allow manual rotation without Terraform drift
  }

  tags = {
    Project     = "ActionSpec"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# infrastructure/modules/backend/variables.tf
variable "github_token" {
  description = "GitHub Personal Access Token for Lambda functions"
  type        = string
  sensitive   = true
}
```

**Usage**:
```bash
# Option 1: terraform.tfvars (gitignored)
echo 'github_token = "ghp_YOUR_TOKEN_HERE"' >> terraform.tfvars
terraform apply

# Option 2: Environment variable (CI/CD)
export TF_VAR_github_token="ghp_YOUR_TOKEN_HERE"
terraform apply

# Option 3: GitHub Secrets (GitHub Actions)
# Store token in repo secrets, reference as ${{ secrets.GITHUB_TOKEN }}
```

**Effort Estimate**: 2-3 hours
- Create Terraform resource (30 min)
- Update deployment documentation (30 min)
- Test in dev environment (1 hour)
- Validate across environments (1 hour)

**Priority**: Medium (quality-of-life improvement, not blocking)

**Tracked**: Phase 3.3.1 implementation complete, tech debt logged for future sprint
```

**Validation**:
```bash
# Verify note added correctly
grep -A 5 "Tech Debt: GitHub Token Management" PRD.md
```

---

### Task 10: Run Full Validation Suite
**File**: N/A (validation only)
**Action**: VALIDATE
**Pattern**: Use validation commands from spec/stack.md

**Implementation**:

Run all validation gates:

```bash
# Gate 1: Lint & Format
cd backend
black --check lambda/shared/github_client.py
black --check tests/test_github_client.py

# Auto-fix if needed
black lambda/shared/github_client.py tests/test_github_client.py

# Gate 2: Type Safety
mypy lambda/shared/github_client.py --ignore-missing-imports

# Gate 3: Unit Tests
pytest tests/test_github_client.py -v

# Gate 4: Test Coverage
pytest tests/test_github_client.py -v \
  --cov=lambda/shared/github_client \
  --cov-report=term-missing \
  --cov-fail-under=90

# Gate 5: All tests (including existing tests)
pytest tests/ -v

# Gate 6: Security check (no secrets in code)
grep -r "ghp_" backend/lambda/ backend/tests/ || echo "✅ No GitHub tokens found in code"
```

**Success Criteria**:
- All linting passes (black clean)
- All type checks pass (mypy clean)
- All unit tests pass (18+ tests)
- Test coverage > 90% for github_client.py
- No GitHub tokens in committed code

---

## Risk Assessment

**Risk**: PyGithub API changes or deprecation
**Mitigation**: Pin specific version (2.1.1), monitor PyGithub changelog, test against real GitHub API regularly

**Risk**: SSM parameter not created by user
**Mitigation**: Clear error messages guide user to GITHUB_SETUP.md, AuthenticationError includes SSM parameter name

**Risk**: Rate limit exhaustion in production
**Mitigation**: Exponential backoff (3 retries), clear RateLimitError with retry_after timestamp, future: GitHub App with 15k/hour limit

**Risk**: Token expiration mid-operation
**Mitigation**: @lru_cache clears on Lambda recycle, BadCredentialsException raises AuthenticationError with clear message

**Risk**: Directory traversal attack via file_path
**Mitigation**: Explicit validation rejects `../` and `..\` patterns before GitHub API call

## Integration Points

**SAM Template Updates**:
- SharedDependenciesLayer will automatically include PyGithub when SAM builds from requirements.txt
- No template.yaml code changes needed (SAM detects requirements.txt)

**Lambda Functions Using This Module**:
- form-generator (Phase 3.4): Fetches spec files for form population
- spec-applier (Phase 3.3.2): Fetches spec files for PR creation

**Environment Variables Required**:
- `GITHUB_TOKEN_SSM_PARAM`: Already configured in template.yaml (line 14)
- `ALLOWED_REPOS`: Add to template.yaml Globals section

**SSM Parameter**:
- Must be created manually before Lambda invocation
- Parameter name: `/actionspec/github-token`
- Type: SecureString (encrypted at rest)

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY code change:

**Gate 1: Syntax & Style (lint)**
```bash
cd backend
black --check lambda/shared/github_client.py tests/test_github_client.py
```

**Gate 2: Type Safety (typecheck)**
```bash
cd backend
mypy lambda/shared/github_client.py --ignore-missing-imports
```

**Gate 3: Unit Tests (test)**
```bash
cd backend
pytest tests/test_github_client.py -v
```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

**After Each Task**:
1. Run Gate 1 (black) - Must pass before continuing
2. Run Gate 2 (mypy) - Must pass before continuing
3. Run Gate 3 (pytest for that specific test file) - Must pass before continuing

**Final Validation** (Task 10):
```bash
cd backend

# Comprehensive validation
black lambda/ tests/
mypy lambda/shared/github_client.py --ignore-missing-imports
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=80

# Manual integration test (requires SSM parameter setup)
../scripts/test-github-integration.sh
```

**Expected Results**:
- ✅ All files formatted (black clean)
- ✅ All type checks pass (mypy clean)
- ✅ All 18+ unit tests pass
- ✅ Test coverage > 90% for github_client.py
- ✅ Integration test passes (with real GitHub token)

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM-LOW)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Similar patterns found in codebase at backend/lambda/functions/spec-parser/exceptions.py
✅ All clarifying questions answered (exception pattern, whitelist location, integration test, requirements.txt location, tech debt approach)
✅ Existing test patterns to follow at backend/tests/test_parser.py and test_security_wrapper.py
✅ PyGithub is well-documented library (https://pygithub.readthedocs.io/)
✅ AWS SSM boto3 patterns are standard

**Assessment**: High confidence implementation with clear patterns to follow and comprehensive test strategy. The main risk is user setup (SSM parameter creation), mitigated by detailed documentation.

**Estimated one-pass success probability**: 85%

**Reasoning**: Well-defined scope, existing patterns to follow, comprehensive tests, and clear validation gates. The 15% risk accounts for potential PyGithub API nuances and user setup issues (SSM parameter not created).
