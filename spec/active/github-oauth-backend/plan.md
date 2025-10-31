# Implementation Plan: GitHub OAuth Backend - Authentication API
Generated: 2025-10-31
Specification: spec.md

## Understanding

This is Phase 1 of 3-phase GitHub OAuth implementation. The goal is to build complete backend OAuth infrastructure that enables user-based GitHub authentication. All existing GitHub API operations will be migrated to use user tokens (with GH_TOKEN fallback during transition).

**Key architectural decisions:**
- OAuth flows use `requests` library (PyGithub doesn't support OAuth)
- GitHub API operations use `PyGithub` with per-request instances
- User tokens stored in HttpOnly cookies (XSS protection)
- Stateless backend (no Redis/database for sessions)
- All existing operations migrate to user tokens with GH_TOKEN fallback
- CSRF protection via session-stored state parameter

**Phases context:**
- Phase 1 (this): Complete backend OAuth + migrate all operations
- Phase 2: Frontend UI (login button, user menu)
- Phase 3: Infrastructure (Secrets Manager, deployment, remove GH_TOKEN)

## Relevant Files

**Reference Patterns** (existing code to follow):

- `backend/app.py` (lines 268-270) - Blueprint registration pattern
- `backend/api/__init__.py` (lines 11-14) - Blueprint creation pattern
- `backend/api/routes.py` (lines 16-35) - API endpoint structure
- `backend/api/helpers.py` (lines 10-25) - JSON response helpers
- `backend/tests/test_api.py` (lines 19-24) - Test fixture pattern
- `backend/tests/test_api.py` (lines 30-56) - Mock GitHub API pattern
- `backend/app.py` (lines 48-63) - PyGithub initialization and error handling

**Files to Create:**

- `backend/auth.py` - OAuth endpoints (/auth/login, /auth/callback, /auth/logout, /api/auth/user)
- `backend/github_helpers.py` - Token management, GitHub API wrappers, access control
- `backend/tests/test_auth.py` - OAuth endpoint tests (unit + integration)
- `backend/tests/test_github_helpers.py` - Helper function tests

**Files to Modify:**

- `backend/app.py` (lines ~28, ~48-63, ~268-270) - SECRET_KEY config, GH_TOKEN warning, auth blueprint registration, migrate operations in fetch_spec(), list_all_pods(), /deploy, /health
- `backend/api/routes.py` (lines ~28, ~78) - Migrate list_pods() and get_pod() to use user tokens
- `backend/api/helpers.py` (lines ~75-106) - Migrate create_pod_deployment() to accept user token
- `.env.local.example` - Add GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET, FLASK_SECRET_KEY

## Architecture Impact

- **Subsystems affected**: Authentication (new), API endpoints (existing), GitHub integration (existing)
- **New dependencies**: None (requests and flask already installed)
- **Breaking changes**: None during Phase 1 (GH_TOKEN fallback preserves existing behavior)

## Task Breakdown

### Task 1: Update Environment Configuration
**File**: `.env.local.example`
**Action**: MODIFY
**Pattern**: Follow existing .env.local.example format

**Implementation:**
Add these variables:
```bash
# GitHub OAuth (Phase 1 - for local development)
GITHUB_OAUTH_CLIENT_ID=your_client_id_here
GITHUB_OAUTH_CLIENT_SECRET=your_client_secret_here

# Flask Session Secret (Phase 1 - generate with: python -c "import secrets; print(secrets.token_hex(32))")
FLASK_SECRET_KEY=your_secret_key_here
```

**Validation:**
- File syntax valid
- Comments explain how to obtain values
- Run: `just backend lint`

---

### Task 2: Create GitHub Helpers Module
**File**: `backend/github_helpers.py`
**Action**: CREATE
**Pattern**: Follow api/helpers.py structure for helper functions

**Implementation:**
```python
"""
GitHub API helper functions for user token management.

Provides:
- Token extraction from cookies
- GitHub API call wrapper with user tokens
- Access control for repositories
- PyGithub instance management
"""

from flask import request, abort
from github import Github, GithubException
import requests
import os
import logging

logger = logging.getLogger(__name__)


def get_github_token_or_fallback():
    """
    Get user's GitHub token from cookie, fallback to GH_TOKEN.

    Returns:
        tuple: (token, is_service_account)
            - token: GitHub access token (user or service account)
            - is_service_account: True if using GH_TOKEN fallback
    """
    user_token = request.cookies.get('github_token')
    if user_token:
        logger.debug("Using user token from cookie")
        return (user_token, False)

    # Fallback to service account
    service_token = os.environ.get('GH_TOKEN')
    if service_token:
        logger.debug("Using service account token (GH_TOKEN fallback)")
        return (service_token, True)

    # No token available
    abort(401, "Not authenticated. Please log in with GitHub.")


def get_user_token_required():
    """
    Get user's GitHub token from cookie (no fallback).

    Use this for operations that MUST use user context.

    Returns:
        str: GitHub access token

    Raises:
        401: If no user token in cookie
    """
    token = request.cookies.get('github_token')
    if not token:
        abort(401, "Not authenticated. Please log in with GitHub.")
    return token


def get_github_client(require_user=False):
    """
    Get PyGithub client authenticated with user token or fallback.

    Args:
        require_user: If True, only use user tokens (no fallback)

    Returns:
        Github: Authenticated PyGithub client
    """
    if require_user:
        token = get_user_token_required()
        return Github(token)
    else:
        token, is_service = get_github_token_or_fallback()
        return Github(token)


def github_api_call(endpoint, method='GET', **kwargs):
    """
    Make GitHub REST API call with user's token.

    Uses requests library for direct API access.
    For operations not covered by PyGithub or when you need raw responses.

    Args:
        endpoint: API endpoint path (e.g., '/user', '/repos/owner/repo')
        method: HTTP method (GET, POST, PUT, DELETE)
        **kwargs: Additional arguments passed to requests.request()

    Returns:
        requests.Response: Response object

    Raises:
        401: If token invalid or missing
    """
    token, is_service = get_github_token_or_fallback()

    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'token {token}'
    headers['Accept'] = 'application/vnd.github.v3+json'

    url = f'https://api.github.com{endpoint}'
    response = requests.request(method, url, headers=headers, **kwargs)

    if response.status_code == 401:
        logger.warning(f"GitHub token invalid/expired for endpoint: {endpoint}")
        abort(401, "GitHub token invalid or expired. Please log in again.")

    return response


def check_repo_access(github_client, owner, repo):
    """
    Verify user has access to repository.

    Args:
        github_client: Authenticated PyGithub client
        owner: Repository owner (username or org)
        repo: Repository name

    Returns:
        Repository: PyGithub Repository object if accessible

    Raises:
        403: If user lacks access
        404: If repo doesn't exist or user can't see it
    """
    try:
        repo_obj = github_client.get_repo(f"{owner}/{repo}")

        # For private repos in trakrf org, verify org membership
        if owner == 'trakrf' and repo_obj.private:
            user = github_client.get_user()
            try:
                # Check if user is org member
                org = github_client.get_organization('trakrf')
                org.get_membership(user.login)
            except GithubException as e:
                if e.status == 404:
                    logger.warning(f"User {user.login} not in trakrf org, denied access to {owner}/{repo}")
                    abort(403, "Access denied: Must be trakrf organization member for private repositories")
                raise

        return repo_obj

    except GithubException as e:
        if e.status == 404:
            logger.warning(f"Repository not found or access denied: {owner}/{repo}")
            abort(404, f"Repository not found: {owner}/{repo}")
        logger.error(f"GitHub API error checking repo access: {e}")
        abort(500, "Failed to verify repository access")


def validate_github_token(token):
    """
    Validate GitHub token by calling /user endpoint.

    Args:
        token: GitHub access token to validate

    Returns:
        dict: User data if valid, None if invalid
    """
    try:
        response = requests.get(
            'https://api.github.com/user',
            headers={'Authorization': f'token {token}'}
        )

        if response.status_code == 200:
            return response.json()
        return None

    except Exception as e:
        logger.error(f"Error validating GitHub token: {e}")
        return None
```

**Validation:**
- Syntax valid: `just backend lint`
- No type errors: `python -m mypy backend/github_helpers.py` (if mypy configured)

---

### Task 3: Create Auth Module with OAuth Endpoints
**File**: `backend/auth.py`
**Action**: CREATE
**Pattern**: Follow api/routes.py blueprint pattern (lines 1-17)

**Implementation:**
```python
"""
GitHub OAuth authentication endpoints.

Provides:
- GET /auth/login - Initiate OAuth flow
- GET /auth/callback - Handle OAuth callback
- POST /auth/logout - Clear authentication
- GET /api/auth/user - Get current user info
"""

from flask import Blueprint, request, redirect, abort, make_response, jsonify, session
import os
import secrets
import requests
import logging
from urllib.parse import urlencode

from github_helpers import validate_github_token

logger = logging.getLogger(__name__)

# Create auth blueprint
auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route('/auth/login')
def login():
    """
    GET /auth/login

    Initiate GitHub OAuth flow by redirecting to GitHub authorization page.

    Returns:
        302: Redirect to GitHub OAuth authorization
    """
    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    # Build GitHub OAuth URL
    client_id = os.environ.get('GITHUB_OAUTH_CLIENT_ID')
    if not client_id:
        logger.error("GITHUB_OAUTH_CLIENT_ID not configured")
        abort(500, "OAuth not configured. Please contact administrator.")

    params = {
        'client_id': client_id,
        'redirect_uri': f"{request.host_url.rstrip('/')}/auth/callback",
        'scope': 'repo workflow',
        'state': state
    }

    github_auth_url = 'https://github.com/login/oauth/authorize'
    redirect_url = f"{github_auth_url}?{urlencode(params)}"

    logger.info(f"Initiating OAuth flow, redirect to GitHub")
    return redirect(redirect_url)


@auth_blueprint.route('/auth/callback')
def callback():
    """
    GET /auth/callback

    Handle OAuth callback from GitHub. Exchange authorization code for access token
    and set HttpOnly cookie.

    Query Parameters:
        code: Authorization code from GitHub
        state: CSRF protection state parameter

    Returns:
        302: Redirect to app root with cookie set
        400: If state invalid or code missing
    """
    # Validate state (CSRF protection)
    state = request.args.get('state')
    expected_state = session.get('oauth_state')

    if not state or state != expected_state:
        logger.warning("OAuth callback with invalid state parameter")
        abort(400, "Invalid state parameter. Please try logging in again.")

    # Clear state from session (one-time use)
    session.pop('oauth_state', None)

    # Get authorization code
    code = request.args.get('code')
    if not code:
        logger.warning("OAuth callback missing authorization code")
        abort(400, "No authorization code provided")

    # Exchange code for access token
    client_id = os.environ.get('GITHUB_OAUTH_CLIENT_ID')
    client_secret = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET')

    if not client_id or not client_secret:
        logger.error("GitHub OAuth credentials not configured")
        abort(500, "OAuth not configured. Please contact administrator.")

    token_url = 'https://github.com/login/oauth/access_token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': f"{request.host_url.rstrip('/')}/auth/callback"
    }

    try:
        response = requests.post(
            token_url,
            data=data,
            headers={'Accept': 'application/json'}
        )
        token_data = response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            error = token_data.get('error', 'unknown')
            error_desc = token_data.get('error_description', 'No access token returned')
            logger.error(f"Failed to get access token: {error} - {error_desc}")
            abort(400, f"Failed to authenticate with GitHub: {error_desc}")

    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        abort(500, "Failed to complete authentication. Please try again.")

    # Validate token with GitHub API
    user_data = validate_github_token(access_token)
    if not user_data:
        logger.error("Token validation failed after successful exchange")
        abort(400, "Invalid token received from GitHub")

    logger.info(f"User {user_data['login']} authenticated successfully")

    # Set HttpOnly cookie and redirect to app root
    response = make_response(redirect('/'))
    response.set_cookie(
        'github_token',
        value=access_token,
        max_age=2592000,  # 30 days
        secure=True,       # HTTPS only (set to False for local dev if needed)
        httponly=True,     # Not accessible to JavaScript
        samesite='Lax'     # CSRF protection
    )

    return response


@auth_blueprint.route('/auth/logout', methods=['POST'])
def logout():
    """
    POST /auth/logout

    Clear authentication cookie.

    Returns:
        200: {"success": true}
    """
    logger.info("User logged out")
    response = make_response(jsonify({'success': True}))
    response.set_cookie('github_token', '', max_age=0)
    return response


@auth_blueprint.route('/api/auth/user')
def get_user():
    """
    GET /api/auth/user

    Return current authenticated user info from GitHub.

    Returns:
        200: {"login": str, "name": str, "avatar_url": str}
        401: {"error": str} if not authenticated or token invalid
    """
    token = request.cookies.get('github_token')

    if not token:
        return jsonify({'error': 'Not authenticated'}), 401

    # Validate token with GitHub
    user_data = validate_github_token(token)

    if not user_data:
        # Token invalid/revoked, clear cookie
        logger.warning("Invalid token detected in /api/auth/user, clearing cookie")
        resp = make_response(jsonify({'error': 'Token invalid or expired'}), 401)
        resp.set_cookie('github_token', '', max_age=0)
        return resp

    return jsonify({
        'login': user_data['login'],
        'name': user_data.get('name'),
        'avatar_url': user_data['avatar_url']
    })
```

**Validation:**
- Syntax valid: `just backend lint`
- Blueprint properly structured

---

### Task 4: Update App Configuration
**File**: `backend/app.py`
**Action**: MODIFY
**Pattern**: Reference existing blueprint registration (lines 268-270)

**Implementation:**

**Change 1: Update SECRET_KEY configuration (line ~28)**

Replace:
```python
app.config["SECRET_KEY"] = os.urandom(24)
```

With:
```python
# Flask secret key for sessions (CSRF protection during OAuth)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
if not os.environ.get("FLASK_SECRET_KEY"):
    logger.warning("FLASK_SECRET_KEY not set - using random key (sessions will not persist across restarts)")
```

**Change 2: Make GH_TOKEN optional (lines ~36-40)**

Replace:
```python
# Fail fast if GH_TOKEN missing
if not GH_TOKEN:
    logger.error("GH_TOKEN environment variable is required")
    logger.error("Set GH_TOKEN in your environment or .env.local file")
    sys.exit(1)
```

With:
```python
# GH_TOKEN is now optional (fallback for operations without user context)
if not GH_TOKEN:
    logger.warning("GH_TOKEN not set - application will require user authentication for all GitHub operations")
    logger.warning("For local development, set GH_TOKEN in .env.local, or log in via /auth/login")
```

**Change 3: Update GitHub client initialization (lines ~48-63)**

Replace:
```python
# Initialize GitHub client (fail fast on auth errors)
try:
    github = Github(GH_TOKEN)
    repo = github.get_repo(GH_REPO)
    # Test connectivity
    repo.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)
    logger.info(
        f"✓ Successfully connected to GitHub repo: {GH_REPO} (branch: {WORKFLOW_BRANCH})"
    )
except BadCredentialsException:
    logger.error("GitHub authentication failed: Invalid or expired token")
    logger.error("Check that GH_TOKEN has 'repo' scope")
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to initialize GitHub client: {e}")
    logger.error(f"Repository: {GH_REPO}, Path: {SPECS_PATH}")
    sys.exit(1)
```

With:
```python
# Initialize GitHub client (with GH_TOKEN if available, for startup checks)
github = None
repo = None

if GH_TOKEN:
    try:
        github = Github(GH_TOKEN)
        repo = github.get_repo(GH_REPO)
        # Test connectivity
        repo.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)
        logger.info(
            f"✓ Successfully connected to GitHub repo: {GH_REPO} (branch: {WORKFLOW_BRANCH}) using GH_TOKEN"
        )
    except BadCredentialsException:
        logger.error("GitHub authentication failed: Invalid or expired GH_TOKEN")
        logger.error("Check that GH_TOKEN has 'repo' scope")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        logger.error(f"Repository: {GH_REPO}, Path: {SPECS_PATH}")
        sys.exit(1)
else:
    logger.info("Starting without GH_TOKEN - user authentication required for GitHub operations")
```

**Change 4: Register auth blueprint (after line ~270)**

Add after `app.register_blueprint(api_blueprint)`:
```python
# Register auth blueprint
from auth import auth_blueprint
app.register_blueprint(auth_blueprint)
```

**Validation:**
- Syntax valid: `just backend lint`
- App starts without GH_TOKEN: `python backend/app.py` (should warn but not crash)

---

### Task 5: Migrate App.py Operations to Use User Tokens
**File**: `backend/app.py`
**Action**: MODIFY
**Pattern**: Use github_helpers functions for token management

**Implementation:**

Import github_helpers at top of file (after line ~18):
```python
from github_helpers import get_github_client, check_repo_access
```

**Change 1: Update fetch_spec() function (lines ~177-208)**

Replace:
```python
def fetch_spec(customer, env):
    """
    Fetch and parse spec.yml from GitHub for a specific pod.
    """
    path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"

    try:
        logger.info(f"Fetching spec: {path}")
        content = repo.get_contents(path, ref=WORKFLOW_BRANCH)
        spec_yaml = content.decoded_content.decode("utf-8")
        spec = yaml.safe_load(spec_yaml)
        logger.info(f"✓ Successfully parsed spec for {customer}/{env}")
        return spec
```

With:
```python
def fetch_spec(customer, env):
    """
    Fetch and parse spec.yml from GitHub for a specific pod.
    Uses user token from cookie, falls back to GH_TOKEN if available.
    """
    path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"

    try:
        logger.info(f"Fetching spec: {path}")

        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)

        content = repo_obj.get_contents(path, ref=WORKFLOW_BRANCH)
        spec_yaml = content.decoded_content.decode("utf-8")
        spec = yaml.safe_load(spec_yaml)
        logger.info(f"✓ Successfully parsed spec for {customer}/{env}")
        return spec
```

**Change 2: Update list_all_pods() function (lines ~210-264)**

Replace repo calls with github_client calls:
```python
def list_all_pods():
    """
    Dynamically discover pods by walking GitHub repo structure.
    Uses user token from cookie, falls back to GH_TOKEN if available.
    """
    cache_key = f"pods:{SPECS_PATH}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    logger.info(f"Discovering pods in {SPECS_PATH}...")
    pods = []

    try:
        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)

        customers = repo_obj.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)

        for customer in customers:
            if customer.type != "dir":
                continue

            try:
                envs = repo_obj.get_contents(
                    f"{SPECS_PATH}/{customer.name}", ref=WORKFLOW_BRANCH
                )
                for env in envs:
                    if env.type != "dir":
                        continue

                    # Check if spec.yml exists
                    try:
                        repo_obj.get_contents(
                            f"{SPECS_PATH}/{customer.name}/{env.name}/spec.yml",
                            ref=WORKFLOW_BRANCH,
                        )
                        pods.append({"customer": customer.name, "env": env.name})
                        logger.debug(f"  Found pod: {customer.name}/{env.name}")
                    except:
                        # spec.yml doesn't exist in this env, skip
                        pass
            except Exception as e:
                logger.warning(f"Error listing envs for {customer.name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error discovering pods: {e}")
        raise

    # Sort: customer alphabetically, then env in lifecycle order
    env_order = {"dev": 0, "stg": 1, "prd": 2}
    pods.sort(key=lambda p: (p["customer"], env_order.get(p["env"], 99)))

    logger.info(f"✓ Discovered {len(pods)} pods")
    set_cached(cache_key, pods)
    return pods
```

**Change 3: Update /deploy endpoint (lines ~354-597)**

Replace repo calls with github_client calls. At the start of the try block (line ~362), add:
```python
        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)
```

Then replace all instances of `repo.` with `repo_obj.` within the /deploy function (lines ~404-518).

**Change 4: Update /health endpoint (lines ~600-656)**

Replace:
```python
@app.route("/health")
def health():
    """Health check: validate GitHub connectivity and show rate limit"""
    try:
        # Test connectivity
        repo.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)

        # Get rate limit info
        rate_limit = github.get_rate_limit()
```

With:
```python
@app.route("/health")
def health():
    """Health check: validate GitHub connectivity and show rate limit"""
    try:
        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)

        # Test connectivity
        repo_obj.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)

        # Get rate limit info
        rate_limit = github_client.get_rate_limit()
```

And replace subsequent `repo.` and `github.` references with `repo_obj.` and `github_client.` in the /health function.

**Validation:**
- Syntax valid: `just backend lint`
- App still works with GH_TOKEN: Start app, check /health returns 200

---

### Task 6: Migrate API Routes to Use User Tokens
**File**: `backend/api/routes.py`
**Action**: MODIFY
**Pattern**: Import and use github_helpers

**Implementation:**

Add import at top (after line ~13):
```python
from github_helpers import get_github_client
```

**Change 1: Update get_pods() (lines ~16-35)**

Replace `main_app.list_all_pods()` call to pass request context. Actually, list_all_pods already uses request context via get_github_client, so this should work as-is. No changes needed.

**Change 2: Update get_pod() (lines ~54-89)**

Same - fetch_spec already uses request context via get_github_client. No changes needed.

**Change 3: Update create_or_update_pod() (lines ~92-186)**

Replace the call to `create_pod_deployment` (line ~170) to pass github_client:
```python
    # Create deployment (branch + PR)
    try:
        # Get authenticated GitHub client
        github_client = get_github_client(require_user=False)

        result = create_pod_deployment(
            github_client,
            main_app.GH_REPO,
            main_app.SPECS_PATH,
            customer,
            env,
            spec_content,
            commit_message,
        )
        return json_success(result)
```

**Validation:**
- Syntax valid: `just backend lint`
- API endpoints accessible

---

### Task 7: Migrate API Helpers to Accept GitHub Client
**File**: `backend/api/helpers.py`
**Action**: MODIFY
**Pattern**: Change function signature to accept github_client

**Implementation:**

Replace `create_pod_deployment` function (lines ~42-108):
```python
def create_pod_deployment(
    github_client, repo_name, specs_path, customer, env, spec_content, commit_message=None
):
    """
    Create GitHub branch, commit spec file, and open PR.

    Args:
        github_client: Authenticated PyGithub client (user token or service account)
        repo_name: Repository name (e.g., 'trakrf/action-spec')
        specs_path: Base path for specs (e.g., 'infra')
        customer: Customer name (validated)
        env: Environment name (validated)
        spec_content: YAML content as string
        commit_message: Optional commit message (default: "Deploy {customer}/{env}")

    Returns:
        dict: {
            'branch': branch_name,
            'pr_url': pr.html_url,
            'pr_number': pr.number
        }

    Raises:
        GithubException: On GitHub API errors
    """
    timestamp = int(time.time())
    branch_name = f"deploy-{customer}-{env}-{timestamp}"
    spec_path = f"{specs_path}/{customer}/{env}/spec.yml"

    if not commit_message:
        commit_message = f"Deploy {customer}/{env}"

    # Get repository object
    repo = github_client.get_repo(repo_name)

    # 1. Create branch from main
    base = repo.get_branch("main")
    base_sha = base.commit.sha
    repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)

    # 2. Check if file exists (update vs create)
    try:
        existing_file = repo.get_contents(spec_path, ref="main")
        repo.update_file(
            path=spec_path,
            message=commit_message,
            content=spec_content,
            sha=existing_file.sha,
            branch=branch_name,
        )
    except GithubException as e:
        if e.status == 404:
            # File doesn't exist, create it
            repo.create_file(
                path=spec_path,
                message=commit_message,
                content=spec_content,
                branch=branch_name,
            )
        else:
            raise

    # 3. Create pull request
    pr_title = f"Deploy: {customer}/{env}"
    pr_body = f"Automated deployment for {customer}/{env}\n\nBranch: `{branch_name}`"

    pr = repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base="main")

    return {"branch": branch_name, "pr_url": pr.html_url, "pr_number": pr.number}
```

**Validation:**
- Syntax valid: `just backend lint`
- Function signature updated

---

### Task 8: Write OAuth Endpoint Tests
**File**: `backend/tests/test_auth.py`
**Action**: CREATE
**Pattern**: Follow test_api.py structure (lines 19-56)

**Implementation:**
```python
"""
Unit and integration tests for OAuth authentication endpoints.

Tests:
- GET /auth/login - OAuth initiation
- GET /auth/callback - OAuth callback handling
- POST /auth/logout - Session termination
- GET /api/auth/user - User info retrieval
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app


@pytest.fixture
def client():
    """Flask test client with session support."""
    app.app.config["TESTING"] = True
    app.app.config["SECRET_KEY"] = "test-secret-key"
    with app.app.test_client() as client:
        yield client


class TestOAuthLogin:
    """Tests for GET /auth/login"""

    @patch.dict(os.environ, {"GITHUB_OAUTH_CLIENT_ID": "test_client_id"})
    def test_login_redirects_to_github(self, client):
        """Should redirect to GitHub OAuth with correct parameters"""
        response = client.get('/auth/login', follow_redirects=False)

        assert response.status_code == 302
        assert 'github.com/login/oauth/authorize' in response.location
        assert 'client_id=test_client_id' in response.location
        assert 'scope=repo+workflow' in response.location
        assert 'state=' in response.location

    @patch.dict(os.environ, {"GITHUB_OAUTH_CLIENT_ID": ""})
    def test_login_fails_without_client_id(self, client):
        """Should return 500 if GITHUB_OAUTH_CLIENT_ID not configured"""
        response = client.get('/auth/login')

        assert response.status_code == 500

    def test_login_sets_oauth_state_in_session(self, client):
        """Should store CSRF state in session"""
        with patch.dict(os.environ, {"GITHUB_OAUTH_CLIENT_ID": "test_client_id"}):
            with client.session_transaction() as sess:
                # Session should be empty before login
                assert 'oauth_state' not in sess

            client.get('/auth/login')

            with client.session_transaction() as sess:
                # Session should contain state after login redirect
                assert 'oauth_state' in sess
                assert len(sess['oauth_state']) > 20  # Random token


class TestOAuthCallback:
    """Tests for GET /auth/callback"""

    @patch('auth.validate_github_token')
    @patch('auth.requests.post')
    @patch.dict(os.environ, {
        "GITHUB_OAUTH_CLIENT_ID": "test_client_id",
        "GITHUB_OAUTH_CLIENT_SECRET": "test_client_secret"
    })
    def test_callback_success(self, mock_post, mock_validate, client):
        """Should exchange code for token and set cookie"""
        # Mock token exchange
        mock_post.return_value.json.return_value = {
            'access_token': 'test_access_token'
        }

        # Mock token validation
        mock_validate.return_value = {
            'login': 'testuser',
            'name': 'Test User'
        }

        # Set up session state
        with client.session_transaction() as sess:
            sess['oauth_state'] = 'test_state'

        response = client.get('/auth/callback?code=test_code&state=test_state', follow_redirects=False)

        assert response.status_code == 302
        assert response.location == '/'
        assert 'github_token=test_access_token' in response.headers.get('Set-Cookie', '')
        assert 'HttpOnly' in response.headers.get('Set-Cookie', '')

    def test_callback_invalid_state(self, client):
        """Should return 400 for invalid CSRF state"""
        with client.session_transaction() as sess:
            sess['oauth_state'] = 'valid_state'

        response = client.get('/auth/callback?code=test_code&state=invalid_state')

        assert response.status_code == 400

    def test_callback_missing_code(self, client):
        """Should return 400 if authorization code missing"""
        with client.session_transaction() as sess:
            sess['oauth_state'] = 'test_state'

        response = client.get('/auth/callback?state=test_state')

        assert response.status_code == 400

    @patch('auth.requests.post')
    @patch.dict(os.environ, {
        "GITHUB_OAUTH_CLIENT_ID": "test_client_id",
        "GITHUB_OAUTH_CLIENT_SECRET": "test_client_secret"
    })
    def test_callback_token_exchange_failure(self, mock_post, client):
        """Should return 400 if token exchange fails"""
        mock_post.return_value.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Code expired'
        }

        with client.session_transaction() as sess:
            sess['oauth_state'] = 'test_state'

        response = client.get('/auth/callback?code=expired_code&state=test_state')

        assert response.status_code == 400

    @patch('auth.validate_github_token')
    @patch('auth.requests.post')
    @patch.dict(os.environ, {
        "GITHUB_OAUTH_CLIENT_ID": "test_client_id",
        "GITHUB_OAUTH_CLIENT_SECRET": "test_client_secret"
    })
    def test_callback_invalid_token(self, mock_post, mock_validate, client):
        """Should return 400 if token validation fails"""
        mock_post.return_value.json.return_value = {
            'access_token': 'invalid_token'
        }
        mock_validate.return_value = None  # Validation fails

        with client.session_transaction() as sess:
            sess['oauth_state'] = 'test_state'

        response = client.get('/auth/callback?code=test_code&state=test_state')

        assert response.status_code == 400


class TestLogout:
    """Tests for POST /auth/logout"""

    def test_logout_clears_cookie(self, client):
        """Should clear github_token cookie"""
        response = client.post('/auth/logout')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Check cookie is cleared (max_age=0)
        set_cookie = response.headers.get('Set-Cookie', '')
        assert 'github_token=' in set_cookie
        assert 'Max-Age=0' in set_cookie


class TestGetUser:
    """Tests for GET /api/auth/user"""

    @patch('auth.validate_github_token')
    def test_get_user_success(self, mock_validate, client):
        """Should return user info for valid token"""
        mock_validate.return_value = {
            'login': 'testuser',
            'name': 'Test User',
            'avatar_url': 'https://github.com/avatar.png'
        }

        client.set_cookie('github_token', 'valid_token')
        response = client.get('/api/auth/user')

        assert response.status_code == 200
        data = response.get_json()
        assert data['login'] == 'testuser'
        assert data['name'] == 'Test User'
        assert data['avatar_url'] == 'https://github.com/avatar.png'

    def test_get_user_not_authenticated(self, client):
        """Should return 401 if no token in cookie"""
        response = client.get('/api/auth/user')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    @patch('auth.validate_github_token')
    def test_get_user_invalid_token(self, mock_validate, client):
        """Should return 401 and clear cookie for invalid token"""
        mock_validate.return_value = None  # Token invalid

        client.set_cookie('github_token', 'invalid_token')
        response = client.get('/api/auth/user')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

        # Cookie should be cleared
        set_cookie = response.headers.get('Set-Cookie', '')
        assert 'Max-Age=0' in set_cookie
```

**Validation:**
- Syntax valid: `just backend lint`
- Tests run: `just backend test`
- All tests pass

---

### Task 9: Write GitHub Helpers Tests
**File**: `backend/tests/test_github_helpers.py`
**Action**: CREATE
**Pattern**: Follow test_api.py mock patterns

**Implementation:**
```python
"""
Unit tests for GitHub helper functions.

Tests:
- Token extraction and fallback
- GitHub API call wrapper
- Access control logic
- Token validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from github import GithubException
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from github_helpers import (
    get_github_token_or_fallback,
    get_user_token_required,
    get_github_client,
    github_api_call,
    check_repo_access,
    validate_github_token
)


@pytest.fixture
def app():
    """Flask app for request context."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


class TestTokenExtraction:
    """Tests for token extraction functions"""

    def test_get_token_from_cookie(self, app):
        """Should extract token from cookie"""
        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie('github_token', 'user_token_123')
                with client:
                    client.get('/')
                    token, is_service = get_github_token_or_fallback()
                    assert token == 'user_token_123'
                    assert is_service is False

    @patch.dict(os.environ, {"GH_TOKEN": "service_token_456"})
    def test_fallback_to_gh_token(self, app):
        """Should fallback to GH_TOKEN if no cookie"""
        with app.test_request_context():
            token, is_service = get_github_token_or_fallback()
            assert token == 'service_token_456'
            assert is_service is True

    @patch.dict(os.environ, {"GH_TOKEN": ""})
    def test_no_token_available_aborts(self, app):
        """Should abort 401 if no token available"""
        with app.test_request_context():
            with pytest.raises(Exception):  # Flask abort raises werkzeug exception
                get_github_token_or_fallback()

    def test_get_user_token_required_success(self, app):
        """Should return user token from cookie"""
        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie('github_token', 'user_token_123')
                with client:
                    client.get('/')
                    token = get_user_token_required()
                    assert token == 'user_token_123'

    def test_get_user_token_required_no_cookie(self, app):
        """Should abort 401 if no cookie (no fallback)"""
        with app.test_request_context():
            with pytest.raises(Exception):
                get_user_token_required()


class TestGithubClient:
    """Tests for get_github_client function"""

    @patch('github_helpers.Github')
    def test_get_client_with_user_token(self, mock_github, app):
        """Should create client with user token"""
        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie('github_token', 'user_token')
                with client:
                    client.get('/')
                    get_github_client(require_user=False)
                    mock_github.assert_called_with('user_token')

    @patch('github_helpers.Github')
    @patch.dict(os.environ, {"GH_TOKEN": "service_token"})
    def test_get_client_with_fallback(self, mock_github, app):
        """Should create client with GH_TOKEN fallback"""
        with app.test_request_context():
            get_github_client(require_user=False)
            mock_github.assert_called_with('service_token')

    @patch('github_helpers.Github')
    def test_get_client_require_user(self, mock_github, app):
        """Should only accept user token when require_user=True"""
        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie('github_token', 'user_token')
                with client:
                    client.get('/')
                    get_github_client(require_user=True)
                    mock_github.assert_called_with('user_token')


class TestGithubApiCall:
    """Tests for github_api_call wrapper"""

    @patch('github_helpers.requests.request')
    def test_api_call_success(self, mock_request, app):
        """Should make API call with user token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie('github_token', 'user_token')
                with client:
                    client.get('/')
                    response = github_api_call('/user')

                    assert response.status_code == 200
                    mock_request.assert_called_once()
                    call_kwargs = mock_request.call_args[1]
                    assert call_kwargs['headers']['Authorization'] == 'token user_token'

    @patch('github_helpers.requests.request')
    def test_api_call_401_aborts(self, mock_request, app):
        """Should abort on 401 response"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        with app.test_request_context():
            with app.test_client() as client:
                client.set_cookie('github_token', 'invalid_token')
                with client:
                    client.get('/')
                    with pytest.raises(Exception):
                        github_api_call('/user')


class TestCheckRepoAccess:
    """Tests for check_repo_access function"""

    @patch('github_helpers.Github')
    def test_public_repo_access(self, mock_github, app):
        """Should allow access to public repo"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_repo.private = False
        mock_client.get_repo.return_value = mock_repo

        with app.test_request_context():
            result = check_repo_access(mock_client, 'octocat', 'Hello-World')
            assert result == mock_repo

    @patch('github_helpers.Github')
    def test_private_trakrf_repo_member(self, mock_github, app):
        """Should allow trakrf member to access private trakrf repo"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_repo.private = True
        mock_client.get_repo.return_value = mock_repo

        mock_user = Mock()
        mock_user.login = 'member_user'
        mock_client.get_user.return_value = mock_user

        mock_org = Mock()
        mock_org.get_membership.return_value = Mock()  # Member found
        mock_client.get_organization.return_value = mock_org

        with app.test_request_context():
            result = check_repo_access(mock_client, 'trakrf', 'private-repo')
            assert result == mock_repo

    @patch('github_helpers.Github')
    def test_private_trakrf_repo_non_member(self, mock_github, app):
        """Should deny non-member access to private trakrf repo"""
        mock_client = Mock()
        mock_repo = Mock()
        mock_repo.private = True
        mock_client.get_repo.return_value = mock_repo

        mock_user = Mock()
        mock_user.login = 'external_user'
        mock_client.get_user.return_value = mock_user

        mock_org = Mock()
        mock_org.get_membership.side_effect = GithubException(404, "Not Found", None)
        mock_client.get_organization.return_value = mock_org

        with app.test_request_context():
            with pytest.raises(Exception):  # Should abort 403
                check_repo_access(mock_client, 'trakrf', 'private-repo')

    @patch('github_helpers.Github')
    def test_repo_not_found(self, mock_github, app):
        """Should abort 404 if repo doesn't exist"""
        mock_client = Mock()
        mock_client.get_repo.side_effect = GithubException(404, "Not Found", None)

        with app.test_request_context():
            with pytest.raises(Exception):  # Should abort 404
                check_repo_access(mock_client, 'nonexistent', 'repo')


class TestValidateToken:
    """Tests for validate_github_token function"""

    @patch('github_helpers.requests.get')
    def test_valid_token(self, mock_get):
        """Should return user data for valid token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'login': 'testuser',
            'name': 'Test User'
        }
        mock_get.return_value = mock_response

        result = validate_github_token('valid_token')
        assert result['login'] == 'testuser'

    @patch('github_helpers.requests.get')
    def test_invalid_token(self, mock_get):
        """Should return None for invalid token"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = validate_github_token('invalid_token')
        assert result is None

    @patch('github_helpers.requests.get')
    def test_network_error(self, mock_get):
        """Should return None on network error"""
        mock_get.side_effect = Exception("Network error")

        result = validate_github_token('any_token')
        assert result is None
```

**Validation:**
- Syntax valid: `just backend lint`
- Tests run: `just backend test`
- All tests pass

---

### Task 10: Update Existing Tests for Token Changes
**File**: `backend/tests/test_api.py`
**Action**: MODIFY
**Pattern**: Mock github_helpers functions

**Implementation:**

Add imports at top:
```python
from unittest.mock import Mock, patch, MagicMock
```

Update fixtures to mock github client:
```python
@pytest.fixture
def mock_github_client():
    """Mock GitHub client for tests."""
    with patch('github_helpers.get_github_client') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client
```

Update tests that call GitHub API to use mock_github_client fixture:
- TestGetPods: Add `mock_github_client` parameter
- TestGetPod: Add `mock_github_client` parameter
- TestCreatePod: Add `mock_github_client` parameter

Example for test_get_pods_success:
```python
    @patch("app.list_all_pods")
    def test_get_pods_success(self, mock_list_pods, mock_github_client, client):
        """Should return list of pods from list_all_pods()"""
        mock_list_pods.return_value = [
            {"customer": "acme", "env": "dev"},
            {"customer": "acme", "env": "prod"},
        ]

        response = client.get("/api/pods")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
```

**Validation:**
- Tests run: `just backend test`
- All existing tests still pass

---

### Task 11: Manual OAuth Flow Testing
**File**: N/A (manual testing)
**Action**: MANUAL TEST
**Pattern**: Follow spec validation criteria (lines 369-397)

**Testing Steps:**

1. **Set up local OAuth app:**
   - Register OAuth app at https://github.com/settings/developers
   - Set callback URL: `http://localhost:5000/auth/callback`
   - Copy Client ID and Secret to `.env.local`
   - Generate FLASK_SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`

2. **Test OAuth login flow:**
   ```bash
   # Start app
   python backend/app.py
   ```
   - Visit `http://localhost:5000/auth/login`
   - Should redirect to GitHub authorization page
   - Authorize the app
   - Should redirect back to `http://localhost:5000/`
   - Check browser DevTools → Application → Cookies
   - Verify `github_token` cookie exists with HttpOnly flag

3. **Test user info endpoint:**
   ```bash
   curl -v http://localhost:5000/api/auth/user --cookie "github_token=YOUR_TOKEN"
   ```
   - Should return JSON with login, name, avatar_url
   - Status 200

4. **Test logout:**
   ```bash
   curl -X POST http://localhost:5000/auth/logout --cookie "github_token=YOUR_TOKEN"
   ```
   - Should return `{"success": true}`
   - Cookie should be cleared

5. **Test access control:**
   - Try accessing public repo (should work)
   - Try accessing private trakrf repo as non-member (should 403)
   - Try accessing private trakrf repo as member (should work)

6. **Test fallback behavior:**
   - Clear cookie in browser
   - Try accessing `/api/pods` (should work with GH_TOKEN fallback)
   - Remove GH_TOKEN from .env.local, restart app
   - Try accessing `/api/pods` without cookie (should 401)

**Validation:**
- All manual tests pass
- OAuth flow completes successfully
- Cookies have correct security flags
- Access control works as expected

---

### Task 12: Run Full Validation Suite
**File**: N/A (validation commands)
**Action**: RUN VALIDATION
**Pattern**: Use commands from spec/stack.md

**Validation Commands:**

```bash
# Lint (syntax and style)
just backend lint

# Type check (if configured)
# python -m mypy backend/

# Unit tests
just backend test

# Build
just backend build
```

**Success Criteria:**
- ✅ Lint: No errors
- ✅ Tests: All passing (20+ tests)
- ✅ Build: Successful

**If any validation fails:**
1. Read error output carefully
2. Fix the specific issue
3. Re-run validation
4. Repeat until all pass

---

## Risk Assessment

**Risk: OAuth credentials not configured**
- **Mitigation**: Clear error messages, documentation in .env.local.example

**Risk: Cookie security in local dev (HTTPS requirement)**
- **Mitigation**: Set `secure=False` for local dev, `secure=True` for production

**Risk: Session invalidation on app restart**
- **Mitigation**: Use persistent FLASK_SECRET_KEY from environment

**Risk: Breaking existing functionality during migration**
- **Mitigation**: GH_TOKEN fallback preserves existing behavior, comprehensive tests

**Risk: PyGithub + requests mixing causing confusion**
- **Mitigation**: Clear separation (OAuth=requests, API=PyGithub), well-documented

## Integration Points

**Flask Application:**
- New auth blueprint registered alongside api blueprint
- Session configuration updated for CSRF state
- Environment variables added for OAuth and secret key

**GitHub API:**
- All operations migrated to use per-request authenticated clients
- Fallback mechanism during transition period
- Access control enforced on repository operations

**Testing:**
- New test files for auth and helpers
- Existing tests updated to mock new dependencies
- Manual OAuth flow validation

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are GATES that block progress.

After EVERY task:
- Gate 1: Syntax & Style → `just backend lint`
- Gate 2: Type Safety → (optional: mypy)
- Gate 3: Unit Tests → `just backend test`

**Enforcement:**
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

**After each task:**
1. Run `just backend lint` (must pass)
2. Run `just backend test` (must pass)

**After Task 11 (manual testing):**
- Complete all manual OAuth flow tests
- Document any issues found

**Final validation:**
- Run `just backend lint` (full codebase)
- Run `just backend test` (full test suite)
- Run `just backend build` (verify app starts)
- Manual OAuth flow test (end-to-end verification)

## Plan Quality Assessment

**Complexity Score**: 6/10 (MEDIUM-HIGH - at threshold but acceptable)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors:**
✅ Clear requirements from detailed spec with code examples
✅ Similar Flask patterns found in codebase (api/routes.py, api/helpers.py)
✅ All clarifying questions answered with clear direction
✅ Existing test patterns to follow (test_api.py)
✅ Well-defined phases (1 of 3) with clear scope boundaries
⚠️ OAuth flow is new pattern (but spec provides complete examples)
⚠️ Mixing requests + PyGithub requires careful separation

**Assessment**: High confidence in successful implementation. Spec provides comprehensive code examples, codebase has established patterns to follow, and clear answers to all ambiguities. Main complexity is migrating all operations to use user tokens, but GH_TOKEN fallback reduces risk.

**Estimated one-pass success probability**: 85%

**Reasoning**: Detailed spec with working code examples significantly reduces uncertainty. Clear codebase patterns and comprehensive test coverage provide validation gates. Main risks are integration issues between OAuth (requests) and GitHub API (PyGithub), but clear separation and fallback mechanism mitigate this. 12 well-defined tasks with specific validation criteria enable incremental progress. The 15% risk accounts for potential edge cases in token handling and access control logic.
