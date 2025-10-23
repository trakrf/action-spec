# Implementation Plan: Flask Foundation & Pod Listing (Demo Phase D4A)
Generated: 2025-01-23
Specification: spec.md

## Understanding

Phase D4A establishes the Flask web application foundation and GitHub API integration for viewing infrastructure pod specifications. This is phase 1 of a 2-phase split (D4A foundation, D4B detail view) to manage context limits and improve implementation quality.

**Key Design Decisions from Clarifying Questions:**
1. **Terraform validation**: Run `tofu plan` once after all cleanup changes (not after each file)
2. **CSS approach**: Use Tailwind CDN (least work, user familiar with it)
3. **Caching**: Simple dict with manual timestamp checks (most reliable, no dependencies)
4. **Error handling**: Fail fast at startup if GH_TOKEN invalid (no confusing runtime errors)
5. **Sorting**: Alphabetical by customer, then lifecycle order (dev → stg → prd) within each customer

**Core Requirements:**
- Remove obsolete `demo_message` field from spec.yml schema (pre-work)
- Flask app with GitHub API integration via PyGithub
- Dynamic pod discovery by walking repo structure
- Home page listing pods grouped by customer
- Health check endpoint for GitHub connectivity validation
- 5-minute caching to prevent rate limit issues

**Success Criteria:**
- Flask starts without errors
- Health check returns 200 with GitHub status
- Home page shows list of pods (1+ depending on repo state)
- Pods grouped by customer, sorted correctly
- Cache prevents excessive API calls

## Relevant Files

**Reference Patterns** (existing code to follow):
- `backend/lambda/shared/github_client.py` (lines 1-100) - PyGithub usage, exception handling, logging patterns
- `backend/lambda/functions/spec-parser/handler.py` (lines 1-80) - Structured responses, error handling, time tracking
- `demo/infra/advworks/dev/spec.yml` (lines 1-14) - Current schema with demo_message to remove

**Files to Create**:
- `demo/backend/app.py` - Flask application (~200 lines)
- `demo/backend/requirements.txt` - Python dependencies (4 lines)
- `demo/backend/templates/index.html.j2` - Pod listing page (~80-100 lines)

**Files to Modify** (Pre-work):
- `demo/infra/advworks/dev/spec.yml` (line 10) - Remove demo_message
- `demo/tfmodules/pod/variables.tf` - Remove demo_message variable definition
- `demo/infra/advworks/dev/main.tf` - Remove demo_message parameter from module call
- `demo/SPEC.md` - Update examples to remove demo_message references

## Architecture Impact

- **Subsystems affected**: New Flask web app (separate from existing Lambda backend)
- **New dependencies**: Flask, PyGithub, PyYAML, Gunicorn (all mature, well-documented)
- **Breaking changes**: None (additive only, pre-work is schema cleanup)
- **Integration points**: Reads from existing demo/infra/ directory structure via GitHub API

## Task Breakdown

### Task 1: Remove demo_message from spec.yml
**File**: `demo/infra/advworks/dev/spec.yml`
**Action**: MODIFY (remove line 10)
**Pattern**: Simple line deletion

**Implementation**:
Remove line 10:
```yaml
    demo_message: Hello from AdventureWorks Development
```

**Validation**:
- Visual inspection (line should be gone)
- File still valid YAML

---

### Task 2: Remove demo_message variable from pod module
**File**: `demo/tfmodules/pod/variables.tf`
**Action**: MODIFY (remove variable block)
**Pattern**: Find and remove entire variable declaration

**Implementation**:
Search for and remove:
```hcl
variable "demo_message" {
  description = "..."
  type        = string
  ...
}
```

**Validation**:
- Grep confirms no more demo_message in file:
  ```bash
  grep demo_message demo/tfmodules/pod/variables.tf
  # Should return nothing
  ```

---

### Task 3: Remove demo_message parameter from module call
**File**: `demo/infra/advworks/dev/main.tf`
**Action**: MODIFY (remove parameter line)
**Pattern**: Remove parameter from module block

**Implementation**:
Remove line from module "pod" block:
```hcl
  demo_message  = local.spec.spec.compute.demo_message
```

**Validation**:
- Module call should not reference demo_message

---

### Task 4: Update SPEC.md examples
**File**: `demo/SPEC.md`
**Action**: MODIFY (remove demo_message from YAML examples)
**Pattern**: Find all YAML spec examples and remove demo_message lines

**Implementation**:
Search for spec.yml examples and remove demo_message field from compute section.

**Validation**:
- Grep confirms no demo_message in examples:
  ```bash
  grep demo_message demo/SPEC.md
  # Should return only narrative text, not YAML examples
  ```

---

### Task 5: Verify Terraform still works
**File**: `demo/infra/advworks/dev/`
**Action**: TEST
**Pattern**: Run tofu plan to validate changes

**Implementation**:
```bash
cd demo/infra/advworks/dev
tofu plan
```

**Expected Output**:
- Plan should succeed without errors
- Should show EC2 user_data change (removing demo_message usage)
- No resource destruction

**Validation**:
- Exit code 0 (success)
- Plan output looks reasonable

---

### Task 6: Create demo/backend directory structure
**Files**: Create directories
**Action**: CREATE
**Pattern**: mkdir -p for nested directories

**Implementation**:
```bash
mkdir -p demo/backend/templates
mkdir -p demo/backend/static
```

**Validation**:
```bash
ls -la demo/backend/
# Should show: templates/, static/ directories
```

---

### Task 7: Create requirements.txt
**File**: `demo/backend/requirements.txt`
**Action**: CREATE
**Pattern**: Standard Python requirements file

**Implementation**:
```
flask==3.0.0
PyGithub==2.1.1
pyyaml==6.0.1
gunicorn==21.2.0
```

**Validation**:
- File exists with 4 lines
- All packages have pinned versions

---

### Task 8: Create Flask app skeleton with config
**File**: `demo/backend/app.py`
**Action**: CREATE (part 1: imports, config, logging)
**Pattern**: Follow backend/lambda/shared/github_client.py logging pattern

**Implementation**:
```python
"""
Spec Editor Flask App - Demo Phase D4A
Read-only UI for viewing infrastructure pod specifications.
"""

from flask import Flask, render_template, jsonify, abort
from github import Github
from github.GithubException import BadCredentialsException, RateLimitExceededException
import yaml
import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Configuration from environment
GH_TOKEN = os.environ.get('GH_TOKEN')
GH_REPO = os.environ.get('GH_REPO', 'trakrf/action-spec')
SPECS_PATH = os.environ.get('SPECS_PATH', 'demo/infra')

# Fail fast if GH_TOKEN missing
if not GH_TOKEN:
    logger.error("GH_TOKEN environment variable is required")
    logger.error("Set GH_TOKEN in your environment or .env.local file")
    sys.exit(1)

logger.info(f"Initializing Spec Editor")
logger.info(f"GitHub Repo: {GH_REPO}")
logger.info(f"Specs Path: {SPECS_PATH}")
```

**Validation**:
- Python syntax check: `python3 -m py_compile demo/backend/app.py`
- Import works without errors

---

### Task 9: Initialize GitHub client with error handling
**File**: `demo/backend/app.py`
**Action**: APPEND (GitHub client initialization)
**Pattern**: Follow backend/lambda/shared/github_client.py exception handling

**Implementation**:
```python
# Initialize GitHub client (fail fast on auth errors)
try:
    github = Github(GH_TOKEN)
    repo = github.get_repo(GH_REPO)
    # Test connectivity
    repo.get_contents(SPECS_PATH)
    logger.info(f"✓ Successfully connected to GitHub repo: {GH_REPO}")
except BadCredentialsException:
    logger.error("GitHub authentication failed: Invalid or expired token")
    logger.error("Check that GH_TOKEN has 'repo' scope")
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to initialize GitHub client: {e}")
    logger.error(f"Repository: {GH_REPO}, Path: {SPECS_PATH}")
    sys.exit(1)
```

**Validation**:
- App refuses to start if GH_TOKEN invalid
- Clear error messages logged

---

### Task 10: Implement caching helper
**File**: `demo/backend/app.py`
**Action**: APPEND (cache functions)
**Pattern**: Simple dict with TTL (user decision: most reliable)

**Implementation**:
```python
# Simple cache with 5-minute TTL
_cache = {}
CACHE_TTL = 300  # 5 minutes in seconds

def get_cached(key):
    """Get cached value if not expired"""
    if key in _cache:
        content, timestamp = _cache[key]
        age = time.time() - timestamp
        if age < CACHE_TTL:
            logger.debug(f"Cache hit: {key} (age: {age:.1f}s)")
            return content
        else:
            logger.debug(f"Cache expired: {key} (age: {age:.1f}s)")
            del _cache[key]
    return None

def set_cached(key, content):
    """Store value in cache with current timestamp"""
    _cache[key] = (content, time.time())
    logger.debug(f"Cached: {key}")
```

**Validation**:
- Python syntax valid
- get_cached returns None for missing keys
- get_cached returns None for expired keys

---

### Task 11: Implement pod discovery function
**File**: `demo/backend/app.py`
**Action**: APPEND (list_all_pods function)
**Pattern**: Walk GitHub directory structure, check for spec.yml

**Implementation**:
```python
def list_all_pods():
    """
    Dynamically discover pods by walking GitHub repo structure.
    Returns list of {"customer": str, "env": str} dicts.
    Sorted: alphabetically by customer, lifecycle order by env (dev, stg, prd).
    """
    cache_key = f"pods:{SPECS_PATH}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    logger.info(f"Discovering pods in {SPECS_PATH}...")
    pods = []

    try:
        customers = repo.get_contents(SPECS_PATH)

        for customer in customers:
            if customer.type != "dir":
                continue

            try:
                envs = repo.get_contents(f"{SPECS_PATH}/{customer.name}")
                for env in envs:
                    if env.type != "dir":
                        continue

                    # Check if spec.yml exists
                    try:
                        repo.get_contents(f"{SPECS_PATH}/{customer.name}/{env.name}/spec.yml")
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

**Validation**:
- Returns list of dicts with customer and env keys
- Sorted correctly (customer alpha, env lifecycle)
- Cached for 5 minutes

---

### Task 12: Implement home page route
**File**: `demo/backend/app.py`
**Action**: APPEND (home route)
**Pattern**: Flask route with error handling

**Implementation**:
```python
@app.route('/')
def index():
    """Home page: list all pods grouped by customer"""
    try:
        pods = list_all_pods()

        # Group by customer for template
        customers = {}
        for pod in pods:
            cust = pod["customer"]
            if cust not in customers:
                customers[cust] = []
            customers[cust].append(pod["env"])

        return render_template('index.html.j2',
                               pods=pods,
                               customers=customers)

    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        abort(500)
```

**Validation**:
- Route registered at `/`
- Calls list_all_pods()
- Renders index.html.j2

---

### Task 13: Implement health check route
**File**: `demo/backend/app.py`
**Action**: APPEND (health route)
**Pattern**: JSON response with GitHub connectivity test

**Implementation**:
```python
@app.route('/health')
def health():
    """Health check: validate GitHub connectivity and show rate limit"""
    try:
        # Test connectivity
        repo.get_contents(SPECS_PATH)

        # Get rate limit info
        rate_limit = github.get_rate_limit()
        remaining = rate_limit.core.remaining
        limit = rate_limit.core.limit
        reset_timestamp = rate_limit.core.reset.timestamp()

        return jsonify({
            "status": "healthy",
            "github": "connected",
            "repo": GH_REPO,
            "rate_limit": {
                "remaining": remaining,
                "limit": limit,
                "reset_at": int(reset_timestamp)
            }
        })

    except RateLimitExceededException as e:
        reset_time = github.get_rate_limit().core.reset
        return jsonify({
            "status": "unhealthy",
            "error": "Rate limit exceeded",
            "reset_at": int(reset_time.timestamp())
        }), 503

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503
```

**Validation**:
- Returns 200 with JSON when healthy
- Returns 503 with error details when unhealthy
- Shows rate limit information

---

### Task 14: Add Flask app entry point
**File**: `demo/backend/app.py`
**Action**: APPEND (main block)
**Pattern**: Standard Flask if __name__ == '__main__'

**Implementation**:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Validation**:
- Can run with: `python demo/backend/app.py`
- Dev server starts on port 5000

---

### Task 15: Create HTML5 boilerplate for index template
**File**: `demo/backend/templates/index.html.j2`
**Action**: CREATE (HTML structure)
**Pattern**: Semantic HTML5 with Tailwind CDN

**Implementation**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spec Editor - Pod Management</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Header will go here -->
    </div>
</body>
</html>
```

**Validation**:
- Valid HTML5 (DOCTYPE, meta tags, title)
- Tailwind CDN loaded
- Responsive container

---

### Task 16: Add page header and description
**File**: `demo/backend/templates/index.html.j2`
**Action**: MODIFY (add header inside container div)
**Pattern**: Tailwind utility classes for typography

**Implementation**:
Insert inside container div:
```html
        <header class="mb-8">
            <h1 class="text-4xl font-bold text-gray-900 mb-2">
                Spec Editor - Pod Management
            </h1>
            <p class="text-lg text-gray-600">
                View and manage infrastructure pod configurations
            </p>
        </header>
```

**Validation**:
- Header is large and bold
- Description is readable

---

### Task 17: Add pod listing grouped by customer
**File**: `demo/backend/templates/index.html.j2`
**Action**: MODIFY (add main content section)
**Pattern**: Tailwind card-based layout with customer grouping

**Implementation**:
Insert after header:
```html
        <main>
            {% for customer, envs in customers.items() %}
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-2xl font-semibold text-gray-800 mb-4 capitalize">
                    {{ customer }}
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {% for env in envs %}
                    <a href="/pod/{{ customer }}/{{ env }}"
                       class="block p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:shadow-lg transition-all">
                        <div class="flex items-center justify-between">
                            <span class="text-lg font-medium text-gray-700">
                                {{ customer }} / {{ env }}
                            </span>
                            {% if env == 'dev' %}
                            <span class="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                                dev
                            </span>
                            {% elif env == 'stg' %}
                            <span class="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full">
                                stg
                            </span>
                            {% elif env == 'prd' %}
                            <span class="px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full">
                                prd
                            </span>
                            {% else %}
                            <span class="px-3 py-1 bg-gray-100 text-gray-800 text-sm font-medium rounded-full">
                                {{ env }}
                            </span>
                            {% endif %}
                        </div>
                    </a>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}

            {% if customers|length == 0 %}
            <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <p class="text-yellow-700">
                    No pods found in {{ '{{ SPECS_PATH }}' }}. Check your repository structure.
                </p>
            </div>
            {% endif %}
        </main>
```

**Validation**:
- Pods grouped by customer
- Environment badges color-coded (dev=green, stg=yellow, prd=red)
- Cards are clickable links
- Responsive grid layout

---

### Task 18: Add footer with GitHub link
**File**: `demo/backend/templates/index.html.j2`
**Action**: MODIFY (add footer after main)
**Pattern**: Simple footer with metadata

**Implementation**:
Insert after main closing tag:
```html
        <footer class="mt-12 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
            <p>
                Spec Editor -
                <a href="https://github.com/trakrf/action-spec"
                   class="text-blue-600 hover:underline">
                    trakrf/action-spec
                </a>
            </p>
            <p class="mt-2">
                Last updated: {{ '{{ now().strftime("%Y-%m-%d %H:%M:%S") }}' }}
            </p>
        </footer>
```

**Validation**:
- Footer displays at bottom
- GitHub link works
- Timestamp shows current time

---

### Task 19: Test Flask app starts
**File**: Run from project root
**Action**: TEST
**Pattern**: Start Flask development server

**Implementation**:
```bash
# Load GH_TOKEN from .env.local
source .env.local

# Start Flask
cd demo/backend
flask --app app run --debug
```

**Expected Output**:
- Logs show GitHub connection successful
- Server starts on http://127.0.0.1:5000
- No errors in startup sequence

**Validation**:
- Process runs without crashing
- Can Ctrl+C to stop

---

### Task 20: Test health check endpoint
**File**: N/A (HTTP request)
**Action**: TEST
**Pattern**: curl or browser request

**Implementation**:
```bash
curl http://localhost:5000/health
```

**Expected Output**:
```json
{
  "status": "healthy",
  "github": "connected",
  "repo": "trakrf/action-spec",
  "rate_limit": {
    "remaining": 4999,
    "limit": 5000,
    "reset_at": 1737677823
  }
}
```

**Validation**:
- Returns 200 status
- JSON is valid
- Shows rate limit info

---

### Task 21: Test home page displays pods
**File**: N/A (HTTP request)
**Action**: TEST
**Pattern**: Open browser to http://localhost:5000

**Implementation**:
1. Open browser to http://localhost:5000
2. Visual inspection of page

**Expected Output**:
- Page renders without errors
- Shows "Spec Editor - Pod Management" header
- Shows at least 1 pod (advworks/dev)
- Pods are grouped by customer
- Environment badges are color-coded
- Cards are clickable

**Validation**:
- No JavaScript console errors
- No broken images/links
- Responsive layout works

---

### Task 22: Test cache prevents excessive API calls
**File**: Check Flask logs
**Action**: TEST
**Pattern**: Refresh page multiple times, check logs for cache hits

**Implementation**:
1. Refresh home page 3 times rapidly
2. Check Flask logs for "Cache hit" messages

**Expected Behavior**:
- First load: "Discovering pods..." (cache miss)
- Subsequent loads: "Cache hit: pods:demo/infra" (cache hit)
- No repeated GitHub API calls

**Validation**:
- Logs show cache working
- Page loads faster on subsequent requests

---

## Risk Assessment

**Risk**: GH_TOKEN has wrong scopes (not 'repo')
  **Mitigation**: Fail fast at startup with clear error message. Document required scopes in error output.

**Risk**: GitHub API rate limit exhausted during development
  **Mitigation**: 5-minute cache implemented. Health check shows remaining quota. User can monitor.

**Risk**: Pod discovery fails if repo structure changes
  **Mitigation**: Graceful error handling in list_all_pods(). Empty result shows friendly message.

**Risk**: Flask port 5000 already in use
  **Mitigation**: Document in error that user can kill existing process or change port.

## Integration Points

- **GitHub API**: Read-only access to demo/infra/ directory structure
- **Environment variables**: GH_TOKEN, GH_REPO, SPECS_PATH from .env.local
- **Terraform files**: Pre-work modifies spec.yml schema (safe, no runtime dependency)

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are GATES, not suggestions. Must pass before proceeding.

### Python Validation (No traditional stack.md commands for Flask demo)

Since this is a Flask demo app (not part of the Python Lambda backend), the stack.md validation commands don't directly apply. Instead:

**After creating app.py**:
```bash
# Syntax check
python3 -m py_compile demo/backend/app.py

# Run locally to validate
source .env.local
cd demo/backend
flask --app app run --debug
# Should start without errors
```

**After creating index.html.j2**:
```bash
# Visit http://localhost:5000
# Should render without errors
# Check browser console for errors
```

**Manual Testing Checklist**:
- [ ] Flask starts without errors
- [ ] Health check returns 200
- [ ] Home page renders
- [ ] Pods are listed and grouped correctly
- [ ] Cache works (check logs)
- [ ] Environment badges are correct colors

**If any gate fails**:
1. Fix the issue immediately
2. Re-run validation
3. Loop until pass
4. After 3 failed attempts → Ask for help

## Validation Sequence

**After each task group**:
1. **Tasks 1-5 (Pre-work)**: Run `tofu plan` in demo/infra/advworks/dev
2. **Tasks 6-14 (Flask app)**: Run `python3 -m py_compile demo/backend/app.py`
3. **Tasks 15-18 (Template)**: Start Flask and visit home page
4. **Tasks 19-22 (Testing)**: Full manual test checklist

**Final validation before shipping**:
```bash
# Start Flask
source .env.local
cd demo/backend
flask --app app run --debug

# In another terminal:
curl http://localhost:5000/health
# Should return 200 with JSON

# In browser:
open http://localhost:5000
# Should show pod listing

# Check logs for cache working
# Refresh page, should see "Cache hit" in logs
```

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM)
- Pre-work: 5 simple file modifications
- Flask app: New subsystem but clear pattern
- Template: Single page with Tailwind CDN
- Total: 22 well-defined tasks

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ PyGithub already used in project (backend/lambda/shared/github_client.py)
- ✅ Simple caching strategy (dict with TTL)
- ✅ All clarifying questions answered
- ✅ User familiar with Tailwind
- ✅ Fail-fast error handling reduces debugging complexity
- ⚠️ New subsystem (Flask) but mature, well-documented framework

**Assessment**: High confidence in implementation success. Flask and PyGithub are mature, well-documented libraries. Pre-work is straightforward. Main risk is GitHub API integration, but pattern exists in codebase and user clarifications addressed key decisions.

**Estimated one-pass success probability**: 85%

**Reasoning**: Straightforward tasks with clear patterns. Only uncertainty is template styling (Tailwind unfamiliar to AI), but CDN approach minimizes this risk. Cache implementation is simple dict (very reliable). Error handling is fail-fast (reduces runtime surprises).
