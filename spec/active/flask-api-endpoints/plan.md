# Implementation Plan: Flask REST API Endpoints

Generated: 2025-10-30
Specification: spec.md

## Understanding

This feature adds REST API endpoints to the existing Flask application to enable frontend decoupling. The app currently uses Jinja templates and needs JSON endpoints that expose the same data without breaking existing functionality.

**Key Requirements**:
- 4 API endpoints: GET /api/pods, GET /api/pod/<customer>/<env>, POST /api/pod, GET /api/health
- Reuse ALL existing functions (list_all_pods, fetch_spec, deployment logic)
- No CORS needed (single-origin deployment: Flask serves both API and frontend via gunicorn)
- Backward compatibility: All existing Jinja routes must continue working
- Internal devops tooling: Prioritize simplicity and debuggability over abstraction

**Design Decisions from Clarification**:
1. Organized structure: Separate API module (not inline in app.py)
2. No CORS: Single container deployment eliminates cross-origin concerns
3. Extract shared deployment logic into helper function
4. Minimal pod listing format: Just wrap existing list_all_pods()
5. Inline error handling with simple json_error() helper
6. Unit tests only with mocked GitHub calls
7. Check and fix existing /health endpoint to ensure JSON response

## Relevant Files

**Reference Patterns** (existing code to follow):

- `backend/app.py` (lines 205-254) - `list_all_pods()` function to wrap in API
- `backend/app.py` (lines 173-203) - `fetch_spec()` function to wrap in API
- `backend/app.py` (lines 356-560) - `/deploy` endpoint showing branch→file→PR workflow
- `backend/app.py` (lines 562-612) - `/health` endpoint to modify for proper JSON
- `backend/app.py` (lines 82-137) - Validation functions to reuse
- `backend/app.py` (lines 139-171) - `generate_spec_yaml()` to use in POST

**Files to Create**:

- `backend/api/__init__.py` - API module initialization
- `backend/api/routes.py` - All API endpoint handlers (pods, pod detail, pod create/update)
- `backend/api/helpers.py` - Shared helper functions (json_error, extract_deployment_logic)
- `backend/tests/test_api.py` - Unit tests for all API endpoints with mocked GitHub

**Files to Modify**:

- `backend/app.py` (after line 43) - Register API routes with Flask app
- `backend/app.py` (lines 562-612) - Ensure /health returns proper JSON (may already be correct)
- `backend/app.py` (lines 356-560) - Extract shared deployment logic into helper function

## Architecture Impact

- **Subsystems affected**: Backend API only
- **New dependencies**: None (all required packages already installed)
- **Breaking changes**: None (additive only)
- **Code organization**: New `backend/api/` module for clean separation

## Task Breakdown

### Task 1: Create API helpers module
**File**: `backend/api/helpers.py`
**Action**: CREATE

**Implementation**:
```python
"""
Shared helper functions for API endpoints.
"""
from flask import jsonify


def json_error(message, status_code, details=None):
    """
    Return consistent JSON error response.

    Args:
        message: Human-readable error message
        status_code: HTTP status code (400, 404, 500, etc.)
        details: Optional dict with additional error context

    Returns:
        tuple: (jsonify response, status_code)
    """
    response = {'error': message}
    if details:
        response['details'] = details
    return jsonify(response), status_code


def json_success(data, status_code=200):
    """
    Return consistent JSON success response.

    Args:
        data: Dict or list to return as JSON
        status_code: HTTP status code (default 200)

    Returns:
        tuple: (jsonify response, status_code)
    """
    return jsonify(data), status_code
```

**Validation**:
- Lint: `cd backend && black --check api/`
- No typecheck needed (no type hints required for Python)
- No tests yet (helpers tested via API endpoint tests)

### Task 2: Extract deployment logic into helper
**File**: `backend/api/helpers.py`
**Action**: MODIFY (append)

**Pattern**: Reference `backend/app.py` lines 392-520 (deployment workflow in /deploy endpoint)

**Implementation**:
Extract the branch→file→PR creation logic from `/deploy` endpoint:

```python
def create_pod_deployment(repo, customer, env, spec_content, commit_message=None):
    """
    Create GitHub branch, commit spec file, and open PR.

    Extracted from /deploy endpoint to be reusable by API.

    Args:
        repo: PyGithub Repository object
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
    import time
    from github import GithubException
    from app import SPECS_PATH

    timestamp = int(time.time())
    branch_name = f"deploy-{customer}-{env}-{timestamp}"
    spec_path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"

    if not commit_message:
        commit_message = f"Deploy {customer}/{env}"

    # 1. Create branch from main
    base = repo.get_branch('main')
    base_sha = base.commit.sha
    repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)

    # 2. Check if file exists (update vs create)
    try:
        existing_file = repo.get_contents(spec_path, ref='main')
        repo.update_file(
            path=spec_path,
            message=commit_message,
            content=spec_content,
            sha=existing_file.sha,
            branch=branch_name
        )
    except GithubException as e:
        if e.status == 404:
            # File doesn't exist, create it
            repo.create_file(
                path=spec_path,
                message=commit_message,
                content=spec_content,
                branch=branch_name
            )
        else:
            raise

    # 3. Create pull request
    pr_title = f"Deploy: {customer}/{env}"
    pr_body = f"Automated deployment for {customer}/{env}\n\nBranch: `{branch_name}`"

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base='main'
    )

    return {
        'branch': branch_name,
        'pr_url': pr.html_url,
        'pr_number': pr.number
    }
```

**Validation**:
- Lint: `cd backend && black --check api/`
- No tests yet (tested via API endpoint tests)

### Task 3: Create API module initialization
**File**: `backend/api/__init__.py`
**Action**: CREATE

**Implementation**:
```python
"""
REST API module for Flask application.

Provides JSON endpoints for:
- Pod listing (GET /api/pods)
- Pod details (GET /api/pod/<customer>/<env>)
- Pod creation/update (POST /api/pod)
- Health check (GET /api/health already exists in main app)
"""

from flask import Blueprint

# Create API blueprint
api_blueprint = Blueprint('api', __name__, url_prefix='/api')

# Import routes to register with blueprint
from . import routes

__all__ = ['api_blueprint']
```

**Validation**:
- Lint: `cd backend && black --check api/`
- Import test: `python -c "from backend.api import api_blueprint; print('OK')"`

### Task 4: Create API routes module
**File**: `backend/api/routes.py`
**Action**: CREATE

**Pattern**: Reference `backend/app.py` lines 205-254 (list_all_pods), 173-203 (fetch_spec), 139-171 (generate_spec_yaml)

**Implementation**:
```python
"""
API route handlers.
"""
from flask import request
from github import GithubException

from . import api_blueprint
from .helpers import json_error, json_success, create_pod_deployment

# Import existing functions from main app
from app import (
    list_all_pods,
    fetch_spec,
    generate_spec_yaml,
    validate_path_component,
    validate_instance_name,
    g_github,
    repo
)


@api_blueprint.route('/pods', methods=['GET'])
def get_pods():
    """
    GET /api/pods

    List all pods discovered from GitHub repository structure.

    Returns:
        200: [{"customer": "foo", "env": "dev"}, ...]
        500: {"error": "message"}
    """
    try:
        pods = list_all_pods()
        return json_success(pods)
    except GithubException as e:
        return json_error(
            'Failed to fetch pod list from GitHub',
            500,
            {'github_error': str(e)}
        )
    except Exception as e:
        return json_error(
            'Unexpected error fetching pods',
            500,
            {'details': str(e)}
        )


@api_blueprint.route('/pod/<customer>/<env>', methods=['GET'])
def get_pod(customer, env):
    """
    GET /api/pod/<customer>/<env>

    Fetch spec.yml for a specific pod.

    Args:
        customer: Customer name
        env: Environment name (dev, stg, prd)

    Returns:
        200: {parsed YAML structure}
        404: {"error": "Pod not found"}
        500: {"error": "message"}
    """
    # Validate path components
    customer_err = validate_path_component(customer, 'customer')
    if customer_err:
        return json_error(customer_err, 400)

    env_err = validate_path_component(env, 'environment')
    if env_err:
        return json_error(env_err, 400)

    try:
        spec = fetch_spec(customer, env)
        if spec is None:
            return json_error(
                f'Pod not found: {customer}/{env}',
                404
            )
        return json_success(spec)
    except GithubException as e:
        if e.status == 404:
            return json_error(
                f'Pod not found: {customer}/{env}',
                404
            )
        return json_error(
            'Failed to fetch pod from GitHub',
            500,
            {'github_error': str(e)}
        )
    except Exception as e:
        return json_error(
            'Unexpected error fetching pod',
            500,
            {'details': str(e)}
        )


@api_blueprint.route('/pod', methods=['POST'])
def create_or_update_pod():
    """
    POST /api/pod

    Create or update a pod specification.

    Request body:
        {
            "customer": "string",
            "env": "string",
            "spec": {
                "instance_name": "string",
                "waf_enabled": boolean
            },
            "commit_message": "string (optional)"
        }

    Returns:
        200: {
            "branch": "deploy-customer-env-timestamp",
            "pr_url": "https://github.com/.../pull/123",
            "pr_number": 123
        }
        400: {"error": "Validation error", "details": {...}}
        500: {"error": "GitHub API error"}
    """
    # Parse JSON body
    try:
        data = request.get_json()
        if not data:
            return json_error('Request body must be JSON', 400)
    except Exception as e:
        return json_error('Invalid JSON in request body', 400, {'details': str(e)})

    # Extract and validate required fields
    customer = data.get('customer')
    env = data.get('env')
    spec = data.get('spec', {})
    commit_message = data.get('commit_message')

    if not customer:
        return json_error('Missing required field: customer', 400)
    if not env:
        return json_error('Missing required field: env', 400)
    if not spec:
        return json_error('Missing required field: spec', 400)

    # Validate path components
    customer_err = validate_path_component(customer, 'customer')
    if customer_err:
        return json_error(customer_err, 400)

    env_err = validate_path_component(env, 'environment')
    if env_err:
        return json_error(env_err, 400)

    # Extract spec fields
    instance_name = spec.get('instance_name')
    waf_enabled = spec.get('waf_enabled', False)

    if not instance_name:
        return json_error('Missing required spec field: instance_name', 400)

    # Validate instance name
    instance_err = validate_instance_name(instance_name)
    if instance_err:
        return json_error(instance_err, 400)

    # Generate YAML content
    try:
        spec_content = generate_spec_yaml(customer, env, instance_name, waf_enabled)
    except Exception as e:
        return json_error(
            'Failed to generate spec YAML',
            500,
            {'details': str(e)}
        )

    # Create deployment (branch + PR)
    try:
        result = create_pod_deployment(
            repo,
            customer,
            env,
            spec_content,
            commit_message
        )
        return json_success(result)
    except GithubException as e:
        return json_error(
            'Failed to create GitHub deployment',
            500,
            {'github_error': str(e)}
        )
    except Exception as e:
        return json_error(
            'Unexpected error creating deployment',
            500,
            {'details': str(e)}
        )
```

**Validation**:
- Lint: `cd backend && black --check api/`
- Import test: `python -c "from backend.api.routes import get_pods; print('OK')"`

### Task 5: Register API blueprint in main app
**File**: `backend/app.py`
**Action**: MODIFY

**Pattern**: Flask blueprint registration (standard pattern)

After line 43 (after `WORKFLOW_BRANCH = ...`), add:

```python
# Register API blueprint
from api import api_blueprint
app.register_blueprint(api_blueprint)
```

**Validation**:
- Lint: `cd backend && black --check app.py`
- Flask app starts without errors: `cd backend && python app.py` (check for startup errors, Ctrl+C to stop)

### Task 6: Verify /health endpoint returns JSON
**File**: `backend/app.py`
**Action**: VERIFY (potentially modify lines 562-612)

**Check existing /health endpoint** (lines 562-612) to ensure it returns proper JSON format.

Current endpoint already returns JSON via `jsonify()` on line 606, so this likely needs no changes.

**Verification**:
- Read lines 562-612
- Confirm response uses `jsonify()` and includes `status`, `github`, `repo`, etc.
- If already correct: No changes needed
- If returns HTML: Convert to JSON response matching spec format

**Expected format**:
```python
return jsonify({
    'status': 'ok',
    'github_connected': True
}), 200
```

**Validation**:
- Lint: `cd backend && black --check app.py`
- Manual test: `curl http://localhost:5000/health` (check JSON response)

### Task 7: Create unit tests for API endpoints
**File**: `backend/tests/test_api.py`
**Action**: CREATE

**Pattern**: Use Flask test client and unittest.mock for GitHub API

**Implementation**:
```python
"""
Unit tests for API endpoints.

Tests all /api/* routes with mocked GitHub API calls.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from github import GithubException

from app import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestGetPods:
    """Tests for GET /api/pods"""

    @patch('app.list_all_pods')
    def test_get_pods_success(self, mock_list_pods, client):
        """Should return list of pods from list_all_pods()"""
        mock_list_pods.return_value = [
            {'customer': 'acme', 'env': 'dev'},
            {'customer': 'acme', 'env': 'prod'},
        ]

        response = client.get('/api/pods')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]['customer'] == 'acme'
        assert data[0]['env'] == 'dev'

    @patch('app.list_all_pods')
    def test_get_pods_github_error(self, mock_list_pods, client):
        """Should return 500 on GitHub API error"""
        mock_list_pods.side_effect = GithubException(500, 'API error')

        response = client.get('/api/pods')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'GitHub' in data['error']


class TestGetPod:
    """Tests for GET /api/pod/<customer>/<env>"""

    @patch('app.fetch_spec')
    def test_get_pod_success(self, mock_fetch, client):
        """Should return parsed spec for valid pod"""
        mock_fetch.return_value = {
            'metadata': {'customer': 'acme', 'environment': 'dev'},
            'spec': {'compute': {'instance_name': 'acme-dev-web'}}
        }

        response = client.get('/api/pod/acme/dev')

        assert response.status_code == 200
        data = response.get_json()
        assert data['metadata']['customer'] == 'acme'
        assert 'spec' in data

    @patch('app.fetch_spec')
    def test_get_pod_not_found(self, mock_fetch, client):
        """Should return 404 for non-existent pod"""
        mock_fetch.return_value = None

        response = client.get('/api/pod/nonexistent/dev')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_pod_invalid_customer(self, client):
        """Should return 400 for invalid customer name"""
        response = client.get('/api/pod/INVALID!/dev')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestCreatePod:
    """Tests for POST /api/pod"""

    @patch('api.helpers.create_pod_deployment')
    @patch('app.generate_spec_yaml')
    def test_create_pod_success(self, mock_generate, mock_deploy, client):
        """Should create branch and PR for valid pod"""
        mock_generate.return_value = 'metadata:\n  customer: acme\n'
        mock_deploy.return_value = {
            'branch': 'deploy-acme-dev-123456',
            'pr_url': 'https://github.com/test/repo/pull/1',
            'pr_number': 1
        }

        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev',
            'spec': {
                'instance_name': 'acme-dev-web',
                'waf_enabled': True
            }
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'branch' in data
        assert 'pr_url' in data
        assert data['pr_number'] == 1

    def test_create_pod_missing_customer(self, client):
        """Should return 400 if customer missing"""
        response = client.post('/api/pod', json={
            'env': 'dev',
            'spec': {'instance_name': 'test'}
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'customer' in data['error'].lower()

    def test_create_pod_invalid_json(self, client):
        """Should return 400 for invalid JSON"""
        response = client.post(
            '/api/pod',
            data='not json',
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    @patch('api.helpers.create_pod_deployment')
    @patch('app.generate_spec_yaml')
    def test_create_pod_github_error(self, mock_generate, mock_deploy, client):
        """Should return 500 on GitHub API error"""
        mock_generate.return_value = 'metadata:\n  customer: acme\n'
        mock_deploy.side_effect = GithubException(500, 'API error')

        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev',
            'spec': {'instance_name': 'acme-dev-web'}
        })

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
```

**Validation**:
- Lint: `cd backend && black --check tests/`
- Run tests: `cd backend && pytest tests/test_api.py -v`
- Coverage: `cd backend && pytest tests/test_api.py -v --cov=api --cov-report=term-missing`

### Task 8: Manual API testing
**Action**: Manual verification with curl

**Test each endpoint**:

```bash
# 1. Start Flask app
cd backend && python app.py

# In another terminal:

# 2. Test GET /api/pods
curl http://localhost:5000/api/pods

# 3. Test GET /api/pod/<customer>/<env>
curl http://localhost:5000/api/pod/acme/dev

# 4. Test POST /api/pod (requires valid GitHub token)
curl -X POST http://localhost:5000/api/pod \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "testcust",
    "env": "dev",
    "spec": {
      "instance_name": "testcust-dev-web",
      "waf_enabled": false
    }
  }'

# 5. Test GET /health (verify JSON format)
curl http://localhost:5000/health
```

**Expected results**:
- All endpoints return valid JSON
- Error responses have consistent format
- Status codes match spec (200, 400, 404, 500)

**Validation**: Manual verification checklist completed

### Task 9: Verify backward compatibility
**Action**: Test existing Jinja routes still work

**Test existing routes**:
```bash
# Start Flask app
cd backend && python app.py

# In browser or curl:
# 1. Home page (pod listing)
curl http://localhost:5000/

# 2. Pod detail page
curl http://localhost:5000/pod/acme/dev

# 3. New pod form
curl http://localhost:5000/pod/new

# 4. Health check
curl http://localhost:5000/health
```

**Validation**: All existing routes return HTML (not broken by API addition)

### Task 10: Update log and create summary
**Action**: Document completion in log.md

**Create final summary** showing:
- All tasks completed
- Validation results
- Manual testing results
- Backward compatibility verified

**Validation**: Log.md exists with complete session summary

## Risk Assessment

### Risk: Import errors in api/routes.py
**Mitigation**:
- Import functions from app.py carefully (may need to adjust imports if circular dependency)
- Test imports immediately after creating files
- Use `from app import ...` not `import app` to avoid circular issues

### Risk: GitHub API failures in tests
**Mitigation**:
- Use unittest.mock.patch for all GitHub API calls
- Mock at the function level (list_all_pods, fetch_spec) not PyGithub level
- Provide realistic mock return values matching actual API responses

### Risk: Existing /deploy route breaks after extraction
**Mitigation**:
- Extract deployment logic carefully, keeping /deploy working
- /deploy endpoint should call the new helper function
- Test /deploy manually after extraction to ensure it still works

### Risk: YAML parsing errors not handled properly
**Mitigation**:
- Reuse existing error handling from fetch_spec()
- Wrap generate_spec_yaml() calls in try/except
- Return 500 with details on YAML errors

## Integration Points

**API module integrates with**:
- `app.py`: Main Flask app (blueprint registration)
- Existing functions: list_all_pods(), fetch_spec(), generate_spec_yaml(), validators
- GitHub API: via PyGithub through existing repo object
- Templates: No changes (API and templates coexist)

**No changes to**:
- Templates (backend/templates/)
- Static files
- Environment variables
- Dependencies (requirements.txt)

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY code change, use commands from `spec/stack.md`:

### Gate 1: Lint & Format
```bash
cd backend
black --check api/ tests/
```
If fails: `black api/ tests/` to auto-fix

### Gate 2: Type Safety
Not applicable (Python without type hints)

### Gate 3: Unit Tests
```bash
cd backend
pytest tests/test_api.py -v --cov=api --cov-report=term-missing
```
Must pass with reasonable coverage (>70%)

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

**After each task**:
1. Lint: `cd backend && black --check <modified_files>`
2. Import test: Try importing modified modules
3. Unit tests: `cd backend && pytest tests/test_api.py -v` (once tests exist)

**Final validation** (before shipping):
1. Lint: `cd backend && black --check lambda/ tests/`
2. Full test suite: `cd backend && pytest tests/ -v --cov=lambda --cov-report=term-missing`
3. Manual API testing with curl (all 4 endpoints)
4. Backward compatibility check (all existing routes work)

## Plan Quality Assessment

**Complexity Score**: 2/10 (LOW)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ All functions to reuse are identified with line numbers
- ✅ Existing Flask app structure is simple and well-organized
- ✅ Similar route patterns found at app.py:256-612
- ✅ All clarifying questions answered
- ✅ Test patterns straightforward (Flask test client + mocking)
- ✅ No new dependencies required
- ✅ No breaking changes (additive only)

**Assessment**: High confidence implementation. All existing code is identified and simple to wrap in API endpoints. No architectural complexity or unknown patterns.

**Estimated one-pass success probability**: 90%

**Reasoning**: Straightforward wrapping of existing functions with JSON responses. Main risks are minor import issues and ensuring backward compatibility, both easily validated. Internal tooling context reduces edge case concerns.
