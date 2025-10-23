# Feature: Flask Foundation & Pod Listing (Demo Phase D4A)

## Origin
This is Phase 1 of the D4 spec split. D4 was split into D4A (foundation) and D4B (detail view) to manage context limits and improve implementation quality. This phase establishes the Flask app infrastructure and GitHub API integration, proving the core connectivity works before building the detail view in D4B.

## Outcome
A working Flask web application that:
- Lists all infrastructure pods discovered from GitHub
- Provides a health check endpoint to validate GitHub connectivity
- Has proper error handling for GitHub authentication issues
- Serves as the foundation for D4B's detail view implementation

**Shippable**: Yes - provides immediate value for verifying GitHub integration works.

## User Story
**As a** developer building the spec-editor demo
**I want** to validate that GitHub API integration works
**So that** I have confidence before building the detail view

**As an** operations engineer
**I want** to see a list of all available pods
**So that** I can navigate to any pod configuration

## Context

**Discovery**:
- Need to prove GitHub API connectivity works before building complex UI
- Pod discovery algorithm must be dynamic (not hardcoded)
- Rate limiting is a concern - need caching from the start
- Split from original D4 spec to manage context and improve quality

**Current State**:
- D1, D2, D3 complete (EC2 + ALB + WAF + GitHub Actions)
- spec.yml schema has obsolete `demo_message` field that needs cleanup
- No Flask app exists yet
- GH_TOKEN available in .env.local

**Desired State**:
- Flask app running locally via `flask run`
- Home page (`/`) shows list of pods grouped by customer
- Health check endpoint (`/health`) validates GitHub connectivity
- Graceful error when GH_TOKEN is missing/invalid
- Foundation ready for D4B to add detail view

## Technical Requirements

### 1. Pre-Work: Schema Cleanup
**Remove obsolete `demo_message` field before starting Flask work**:
- Remove from `demo/infra/advworks/dev/spec.yml`
- Remove variable from `demo/tfmodules/pod/variables.tf`
- Remove parameter from `demo/infra/advworks/dev/main.tf`
- Update examples in `demo/SPEC.md`
- Verify `terraform plan` still works

**Rationale**: Switched from hashicorp/http-echo (needed message) to mendhak/http-https-echo (echoes request details, no config needed)

### 2. Flask Application Core
- Flask app with environment-based configuration
- Load config from environment variables:
  - `GH_TOKEN` (required) - GitHub PAT from .env.local
  - `GH_REPO` (default: "trakrf/action-spec")
  - `SPECS_PATH` (default: "demo/infra")
  - `FLASK_ENV` (default: "production")
- Configure logging at INFO level minimum
- Session support for flash messages (future use in D5)
- Flask secret key from os.urandom(24)

### 3. GitHub Client Integration
- Initialize PyGithub client with token validation
- Implement caching helper:
  - Simple in-memory dict: `{path: (content, timestamp)}`
  - 5-minute TTL
  - Purpose: Avoid rate limit burn during development
- Error handling for authentication failures

### 4. Pod Discovery (Dynamic)
- **Critical**: Must discover pods by walking GitHub repo structure
- Algorithm:
  1. List contents of `{SPECS_PATH}/` (gets: advworks, northwind, contoso)
  2. For each customer dir, list subdirectories (gets: dev, stg, prd)
  3. For each env dir, check if `spec.yml` exists
  4. Return structured list: `[{"customer": "advworks", "env": "dev"}, ...]`
- Must handle partial repo structure (e.g., northwind might not have stg)
- Cache the pod list for 5 minutes

### 5. Routes (D4A Scope)
**`GET /` - Pod listing page**:
- Call `list_all_pods()` helper
- Group pods by customer for display
- Render `index.html.j2` template
- Handle GitHub API errors gracefully

**`GET /health` - Health check endpoint**:
- Test GitHub API connectivity (try fetching SPECS_PATH)
- Return JSON: `{"status": "healthy", "github": "connected", "rate_limit": <remaining>}`
- Return 503 if GitHub unreachable
- Critical for debugging before user tries app

**Note**: Pod detail route (`/pod/<customer>/<env>`) is D4B scope.

### 6. Templates (D4A Scope)
**index.html.j2 only** (form.html.j2 is D4B):
- HTML5 boilerplate with responsive meta tags
- Page header: "Spec Editor - Pod Management"
- Pod listing grouped by customer (card-based layout)
- Environment badges with color coding:
  - dev = green
  - stg = yellow
  - prd = red
- Clickable links to pod detail pages (will work after D4B)
- Footer with GitHub repo link and timestamp
- Minimal inline CSS for layout

### 7. Error Handling (D4A Scope)
**Handle these failure modes gracefully**:
- GH_TOKEN missing/invalid → Show setup instructions page
- GitHub API network error → 503 with retry suggestion
- Pod discovery fails → Show error with troubleshooting steps

**Note**: Full error suite (404 for invalid pods, YAML parse errors) is D4B scope.

### 8. Dependencies
**requirements.txt**:
```
flask==3.0.0
PyGithub==2.1.1
pyyaml==6.0.1
gunicorn==21.2.0
```

## Architecture

```
┌─────────────────────────┐
│   Browser               │
└───────────┬─────────────┘
            │
            ├─ GET /         (shows pod list)
            └─ GET /health   (validates GitHub)
            │
┌───────────▼─────────────┐
│   Flask App (app.py)    │
│   D4A Scope:            │
│   - Pod discovery       │
│   - GitHub client       │
│   - Home page route     │
│   - Health check        │
│   - Cache helper        │
└───────────┬─────────────┘
            │
            ├─ repo.get_contents("demo/infra/advworks")
            ├─ repo.get_contents("demo/infra/northwind")
            └─ Cache results for 5 minutes
            │
┌───────────▼─────────────┐
│   GitHub API            │
│   trakrf/action-spec    │
│   demo/infra/**         │
└─────────────────────────┘
```

**No AWS credentials needed** - pure GitHub integration

## Implementation Punch List

### Pre-Work: Schema Cleanup (5 tasks)
- [ ] Remove `demo_message` from `demo/infra/advworks/dev/spec.yml`
- [ ] Remove `demo_message` variable from `demo/tfmodules/pod/variables.tf`
- [ ] Remove `demo_message` parameter from `demo/infra/advworks/dev/main.tf`
- [ ] Update `demo/SPEC.md` examples to remove `demo_message`
- [ ] Verify `terraform plan` still works after cleanup

### Project Structure (4 tasks)
- [ ] Create `demo/backend/` directory
- [ ] Create `demo/backend/requirements.txt`
- [ ] Create `demo/backend/templates/` directory
- [ ] Create `demo/backend/static/` directory (for future CSS)

### Flask App Core (8 tasks)
- [ ] Flask app initialization with config loading
- [ ] Load environment variables (GH_TOKEN, GH_REPO, SPECS_PATH)
- [ ] Initialize PyGithub client with token validation
- [ ] Configure Flask secret key and logging (INFO level)
- [ ] Implement cache helper (dict with 5-min TTL)
- [ ] Create `get_github_client()` helper function
- [ ] Create `_get_directory_contents(path)` GitHub API wrapper
- [ ] Error handling for missing/invalid GH_TOKEN

### Pod Discovery (4 tasks)
- [ ] Implement `list_all_pods()` function
- [ ] Walk GitHub repo structure (customers → environments)
- [ ] Check for spec.yml existence in each env directory
- [ ] Cache pod list results for 5 minutes

### Routes (2 tasks)
- [ ] `GET /` - Home page with pod listing
- [ ] `GET /health` - Health check with GitHub connectivity test

### Template (6 tasks)
- [ ] Create `templates/index.html.j2`
- [ ] HTML5 boilerplate with responsive design
- [ ] Page header and description
- [ ] Pod cards grouped by customer
- [ ] Environment badges (color-coded)
- [ ] Footer with GitHub link and timestamp

### Testing (3 tasks)
- [ ] Start Flask: `flask --app demo/backend/app run --debug`
- [ ] Verify `/health` returns 200 with GitHub status
- [ ] Verify `/` shows pod list (1+ pods depending on repo state)

**Total: 32 tasks** (5 pre-work + 27 implementation)

## Code Example

```python
# demo/backend/app.py (D4A skeleton)
from flask import Flask, render_template, jsonify
from github import Github
import os
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Config
GH_TOKEN = os.environ.get('GH_TOKEN')
GH_REPO = os.environ.get('GH_REPO', 'trakrf/action-spec')
SPECS_PATH = os.environ.get('SPECS_PATH', 'demo/infra')

# Cache (simple dict with TTL)
_cache = {}
CACHE_TTL = 300  # 5 minutes

def get_cached(key):
    if key in _cache:
        content, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return content
    return None

def set_cached(key, content):
    _cache[key] = (content, time.time())

# GitHub client
github = None
repo = None

try:
    github = Github(GH_TOKEN)
    repo = github.get_repo(GH_REPO)
except Exception as e:
    app.logger.error(f"Failed to initialize GitHub client: {e}")

def list_all_pods():
    """Dynamically discover pods from GitHub repo structure"""
    cache_key = f"pods:{SPECS_PATH}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    pods = []
    customers = repo.get_contents(SPECS_PATH)
    for customer in customers:
        if customer.type == "dir":
            envs = repo.get_contents(f"{SPECS_PATH}/{customer.name}")
            for env in envs:
                if env.type == "dir":
                    try:
                        repo.get_contents(f"{SPECS_PATH}/{customer.name}/{env.name}/spec.yml")
                        pods.append({"customer": customer.name, "env": env.name})
                    except:
                        pass

    set_cached(cache_key, pods)
    return pods

@app.route('/')
def index():
    if not repo:
        return "Error: GitHub client not initialized. Check GH_TOKEN.", 500

    try:
        pods = list_all_pods()
        return render_template('index.html.j2', pods=pods)
    except Exception as e:
        app.logger.error(f"Failed to list pods: {e}")
        return f"Error fetching pods: {e}", 500

@app.route('/health')
def health():
    if not repo:
        return jsonify({"status": "unhealthy", "error": "GitHub client not initialized"}), 503

    try:
        repo.get_contents(SPECS_PATH)
        rate_limit = github.get_rate_limit()
        return jsonify({
            "status": "healthy",
            "github": "connected",
            "rate_limit": rate_limit.core.remaining
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503
```

## Validation Criteria

**Must Pass Before Shipping D4A**:
- [ ] Flask app starts without errors
- [ ] Health check returns 200 when GH_TOKEN is valid
- [ ] Health check returns 503 when GH_TOKEN is missing
- [ ] Home page displays list of pods (1+ pods)
- [ ] Pods are grouped by customer in UI
- [ ] Clicking a pod link shows URL (even if 404 - D4B will handle)
- [ ] Cache prevents excessive API calls (verify in logs)
- [ ] No unhandled exceptions in Flask logs

**Integration Validation**:
- [ ] Uses real GH_TOKEN from .env.local
- [ ] Fetches from actual demo/infra/ directory
- [ ] Discovers pods dynamically (not hardcoded)
- [ ] Logs show clear messages for debugging

## Success Metrics

**Quantitative**:
- Flask starts in <5 seconds
- Health check responds in <1 second
- Home page loads in <2 seconds (with caching)
- Pod discovery happens in <3 seconds (first load)

**Qualitative**:
- Error messages are friendly (not stack traces)
- UI shows pods clearly grouped by customer
- Health check provides useful debugging info
- Code is readable with clear function names

## Dependencies

**Blocked By**:
- D3 must be complete (merged)
- GH_TOKEN in .env.local with repo scope

**Blocks**:
- D4B (Pod Detail View) - needs this foundation

**Enables**:
- D4B can focus purely on detail view without GitHub client concerns
- Validates GitHub API approach before building complex UI

## Constraints

**Must Work With**:
- Existing demo/infra/ directory structure
- GH_TOKEN from .env.local
- Python 3.12+
- No AWS credentials needed

**Scope Boundaries (Deferred to D4B)**:
- No pod detail view route
- No form.html.j2 template
- No form submission capability
- No spec.yml YAML parsing (beyond existence check)
- No 404 handling for invalid pods
- No YAML parse error handling

## Next Steps After D4A

1. **Ship D4A** - Get PR merged
2. **Run /cleanup** - Prepare for D4B
3. **Phase D4B** - Build pod detail view on this foundation
4. **Phase D5** - Add form submission + workflow_dispatch
5. **Phase D6** - Docker packaging

---

**Specification Status**: Ready for Planning
**Estimated Effort**: 1.5-2 hours
**Target PR Size**: ~200 LoC, 2 new files (app.py, index.html.j2)
**Complexity**: 5/10 (Medium - New subsystem but clear patterns)
