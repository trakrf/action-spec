# Feature: Flask Web UI for Viewing Infrastructure Specs (Demo Phase D4)

## Origin
This specification emerged from planning Demo Phase D4 implementation. D1 and D2 are complete (EC2 + ALB + WAF infrastructure modules), D3 is in progress (GitHub Actions workflow_dispatch). D4 adds a web UI to **view** infrastructure pod specs stored in GitHub, preparing for D5 which will add **editing** capability.

## Outcome
Engineers can open a web browser, see a list of all infrastructure pods (customer/environment combinations), click on a pod, and view its current spec.yml configuration fetched live from GitHub. No editing capability yet - this phase de-risks the GitHub API integration before adding workflow_dispatch triggering in D5.

## User Story
**As an** operations engineer
**I want** to view infrastructure pod configurations in a web UI
**So that** I can see current spec values without manually browsing GitHub files

**As a** developer preparing for demo
**I want** the read-only UI working independently
**So that** I can validate GitHub integration before adding write operations

## Context

**Discovery**:
- Current workflow requires manual GitHub UI navigation to view spec.yml files
- Specs are stored at `demo/infra/{customer}/{env}/spec.yml` in GitHub repo
- Need dynamic pod discovery (not hardcoded list) to scale to 9 pods in D7
- Rate limiting is a real concern during development (5000 API calls/hour)

**Current State**:
- Infrastructure modules exist (D1/D2) and are proven working
- spec.yml schema is established and stable
- GitHub Actions workflow exists for deployment (D3)
- No web UI exists - only command line and GitHub web interface

**Desired State**:
- Flask web app running locally via `flask run`
- Home page lists all pods discovered from GitHub repo structure
- Pod detail page shows current spec.yml values in form layout
- All form fields disabled (read-only) with note explaining D5 will enable editing
- Graceful error handling for common failure modes
- Health check endpoint to validate GitHub connectivity

## Technical Requirements

### 1. Flask Application Core
- Flask app with environment-based configuration
- Load config from environment variables:
  - `GH_TOKEN` (required) - GitHub PAT from .env.local
  - `GH_REPO` (default: "trakrf/action-spec")
  - `SPECS_PATH` (default: "demo/infra")
  - `FLASK_ENV` (default: "production")
- Configure logging at INFO level minimum
- Session support for flash messages (future use in D5)

### 2. Pod Discovery (Dynamic)
- **Critical**: Must discover pods by walking GitHub repo structure, not hardcoded
- Algorithm:
  1. List contents of `{SPECS_PATH}/` (gets: advworks, northwind, contoso)
  2. For each customer dir, list subdirectories (gets: dev, stg, prd)
  3. For each env dir, check if `spec.yml` exists
  4. Return structured list: `[{"customer": "advworks", "env": "dev"}, ...]`
- Must handle partial repo structure (e.g., northwind has no stg)
- Cache results for 5 minutes to avoid rate limit burn during development

### 3. Spec Fetching
- Fetch spec.yml content via GitHub API (not raw Git operations)
- Parse YAML with error handling for malformed files
- Return parsed dict matching schema:
  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    customer: advworks
    environment: dev
  spec:
    compute:
      instance_name: web1
      instance_type: t4g.nano
    security:
      waf:
        enabled: false
  ```
- **Note**: `demo_message` field is obsolete (removed after switching from hashicorp/http-echo to mendhak/http-https-echo)

### 4. Routes
- `GET /` - Pod listing page
  - Group pods by customer for visual organization
  - Each pod is clickable link to detail page
- `GET /pod/<customer>/<env>` - Pod detail page
  - Validate customer/env parameters (alphanumeric only, prevent path traversal)
  - Fetch and display spec in form layout
  - All inputs disabled with note: "Editing disabled in Phase D4 (read-only demo)"
- `GET /health` - Health check endpoint
  - Test GitHub API connectivity
  - Return JSON: `{"status": "healthy", "github": "connected", "rate_limit": <remaining>}`
  - Critical for debugging before user tries to use app

### 5. Error Handling (Must Be Friendly)
**These failure modes must return user-friendly pages, not stack traces:**
- GH_TOKEN missing/invalid → Setup instructions page
- GitHub API rate limit exceeded → 503 with retry-after
- Pod not found (invalid customer/env) → 404 with list of valid pods
- Spec file malformed YAML → 500 with parse error details
- Network failure to GitHub → 503 with retry suggestion

### 6. Templates (Jinja2)
**index.html.j2**:
- Card-based layout grouped by customer
- Responsive design (mobile-friendly)
- Visual hierarchy: Customer name (bold) → Environment badges (colored: dev=green, stg=yellow, prd=red)
- Footer with GitHub repo link and "Last updated" timestamp

**form.html.j2**:
- Breadcrumb: Home > {customer} > {env}
- Read-only context section showing customer and environment
- Form sections matching spec.yml structure:
  - Compute: instance_name, instance_type
  - Security: WAF enabled checkbox
- Display computed full instance name: `{customer}-{env}-{instance_name}`
- **Important**: Form structure should match final D5 design - just disable inputs
- Back button to home page

### 7. Dependencies (requirements.txt)
```
flask==3.0.0
PyGithub==2.1.1
pyyaml==6.0.1
gunicorn==21.2.0
```

### 8. Caching Strategy
- Simple in-memory dict cache with 5-minute TTL
- Cache key: GitHub file path
- Cache value: (content, fetch_timestamp)
- Purpose: Avoid burning through rate limit during development (5000/hour limit)
- Not production-grade, but sufficient for MVP

## Architecture

```
┌─────────────────────────┐
│   Browser               │
└───────────┬─────────────┘
            │
            ├─ GET /
            ├─ GET /pod/advworks/dev
            └─ GET /health
            │
┌───────────▼─────────────┐
│   Flask App (app.py)    │
│   - Routes              │
│   - PyGithub client     │
│   - YAML parser         │
│   - Template renderer   │
└───────────┬─────────────┘
            │
            ├─ repo.get_contents("demo/infra/advworks")
            ├─ repo.get_contents("demo/infra/advworks/dev/spec.yml")
            └─ Decode base64, parse YAML
            │
┌───────────▼─────────────┐
│   GitHub API            │
│   trakrf/action-spec    │
│   demo/infra/**/*.yml   │
└─────────────────────────┘
```

**No AWS credentials needed for D4** - pure GitHub integration

## Implementation Punch List

### Pre-Work: Schema Cleanup (5 tasks)
**Remove obsolete `demo_message` field from spec.yml schema**:
- [ ] Remove `demo_message` from `demo/infra/advworks/dev/spec.yml`
- [ ] Remove `demo_message` variable from `demo/tfmodules/pod/variables.tf`
- [ ] Remove `demo_message` parameter from `demo/infra/advworks/dev/main.tf` module call
- [ ] Update `demo/SPEC.md` examples to remove `demo_message`
- [ ] Verify terraform plan still works after cleanup

**Rationale**: Switched from hashicorp/http-echo (needed custom message) to mendhak/http-https-echo (echoes request details, no config needed)

### Project Structure & Dependencies (4 tasks)
- [ ] Create `demo/backend/` directory
- [ ] Create `demo/backend/requirements.txt` with Flask, PyGithub, PyYAML, Gunicorn
- [ ] Create `demo/backend/templates/` directory
- [ ] Create `demo/backend/static/` directory (for CSS if needed)

### Flask App Core - app.py (12 tasks)
**Config & Initialization**:
- [ ] Flask app factory pattern setup
- [ ] Load environment variables (GH_TOKEN, GH_REPO, SPECS_PATH)
- [ ] Initialize PyGithub client with token validation
- [ ] Configure Flask secret key for sessions
- [ ] Set up logging (INFO level)

**Helper Functions**:
- [ ] `get_github_client()` - Returns authenticated GitHub instance
- [ ] `list_all_pods()` - Dynamic discovery by walking repo structure
- [ ] `fetch_spec(customer, env)` - Fetch and parse spec.yml
- [ ] `_get_directory_contents(path)` - GitHub API wrapper
- [ ] `_get_file_content(path)` - GitHub API file fetch
- [ ] Cache implementation (5-min TTL dict)
- [ ] Error handler helpers for common failure modes

### Routes Implementation (6 tasks)
- [ ] `GET /` - Home page with pod listing
- [ ] `GET /pod/<customer>/<env>` - Pod detail page
- [ ] `GET /health` - Health check with GitHub connectivity test
- [ ] Input validation for customer/env parameters (prevent injection)
- [ ] 404 handler for pod not found
- [ ] 500 handler for server errors

### Templates - index.html.j2 (6 tasks)
- [ ] HTML5 boilerplate with responsive meta tags
- [ ] Page header: "Spec Editor - Pod Management"
- [ ] Pod listing grouped by customer (card-based layout)
- [ ] Environment badges with color coding
- [ ] Clickable links to pod detail pages
- [ ] Footer with GitHub link and timestamp

### Templates - form.html.j2 (5 tasks)
- [ ] Breadcrumb navigation
- [ ] Read-only context section (customer + environment display)
- [ ] Compute section form fields: instance_name, instance_type (disabled inputs)
- [ ] Security section: WAF enabled checkbox (disabled)
- [ ] Display computed full instance name and back button to home page

### Error Handling (5 tasks)
- [ ] GH_TOKEN missing/invalid error page
- [ ] Rate limit exceeded (503) with retry-after
- [ ] Pod not found (404) with valid pods list
- [ ] YAML parse error (500) with details
- [ ] Network error (503) with retry suggestion

### Testing Checklist (8 tasks)
- [ ] Start Flask app locally with `flask --app app run --debug`
- [ ] Verify `/health` returns 200 with GitHub connectivity
- [ ] Verify `/` shows pod list (9 pods if D7 done, 1 pod if just D1)
- [ ] Verify clicking pod loads `/pod/advworks/dev` successfully
- [ ] Verify form shows correct values from GitHub spec.yml
- [ ] Verify all form fields are disabled (read-only)
- [ ] Test error case: `/pod/invalid/invalid` returns 404
- [ ] Test without GH_TOKEN - fails gracefully with setup instructions

**Total: 46 granular tasks** (5 pre-work + 41 implementation)

## Code Examples

### Flask App Structure (from SPEC.md)
```python
# demo/backend/app.py
from flask import Flask, render_template, jsonify
from github import Github
import yaml
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Initialize GitHub client
gh_token = os.environ.get('GH_TOKEN')
gh_repo = os.environ.get('GH_REPO', 'trakrf/action-spec')
specs_path = os.environ.get('SPECS_PATH', 'demo/infra')

github = Github(gh_token)
repo = github.get_repo(gh_repo)

def list_all_pods():
    """Dynamically discover pods by walking repo structure"""
    pods = []
    customers = repo.get_contents(specs_path)
    for customer in customers:
        if customer.type == "dir":
            envs = repo.get_contents(f"{specs_path}/{customer.name}")
            for env in envs:
                if env.type == "dir":
                    # Check if spec.yml exists
                    try:
                        repo.get_contents(f"{specs_path}/{customer.name}/{env.name}/spec.yml")
                        pods.append({"customer": customer.name, "env": env.name})
                    except:
                        pass
    return pods

def fetch_spec(customer, env):
    """Fetch and parse spec.yml from GitHub"""
    path = f"{specs_path}/{customer}/{env}/spec.yml"
    content = repo.get_contents(path)
    spec = yaml.safe_load(content.decoded_content)
    return spec

@app.route('/')
def index():
    pods = list_all_pods()
    return render_template('index.html.j2', pods=pods)

@app.route('/pod/<customer>/<env>')
def view_pod(customer, env):
    spec = fetch_spec(customer, env)
    return render_template('form.html.j2', spec=spec)

@app.route('/health')
def health():
    try:
        repo.get_contents(specs_path)
        return jsonify({"status": "healthy", "github": "connected"})
    except:
        return jsonify({"status": "unhealthy", "github": "disconnected"}), 503
```

### Template Data Structure
```python
# Data passed to index.html.j2
pods = [
    {"customer": "advworks", "env": "dev"},
    {"customer": "advworks", "env": "stg"},
    {"customer": "northwind", "env": "dev"},
    # ... more pods
]

# Data passed to form.html.j2
spec = {
    "metadata": {
        "customer": "advworks",
        "environment": "dev"
    },
    "spec": {
        "compute": {
            "instance_name": "web1",
            "instance_type": "t4g.nano"
        },
        "security": {
            "waf": {"enabled": False}
        }
    }
}
```

## Validation Criteria

**Must Pass Before PR**:
- [ ] Flask app starts without errors on `flask run`
- [ ] Health check endpoint returns 200 when GitHub token is valid
- [ ] Home page displays correct number of pods (1 if D1 only, 9 if D7 done)
- [ ] Clicking pod link loads detail page with actual GitHub data
- [ ] Form displays correct values from spec.yml (not hardcoded)
- [ ] All form inputs are disabled (read-only validation)
- [ ] Invalid pod URL returns 404 with helpful error
- [ ] Missing GH_TOKEN returns friendly setup instructions
- [ ] Cache prevents excessive GitHub API calls during page refreshes

**Integration Validation**:
- [ ] Works with real GH_TOKEN from .env.local
- [ ] Fetches from actual demo/infra/ directory in repo
- [ ] Parses existing spec.yml schema without modifications
- [ ] No AWS credentials required (GitHub-only)
- [ ] Logs show clear messages for debugging

## Conversation References

**Key Insight**:
> "D4 PR Size Analysis: 400-450 LoC total. Single responsibility: Read-only UI for viewing specs. No infrastructure changes, no destructive operations, self-contained new files."

**Decision - Why One PR**:
> "Verdict: YES, reasonable for one PR. Atomic feature: 'View specs via web UI' is one complete user story. Low risk: Read-only operations, no state changes. Fast feedback: Reviewer can run flask run and immediately see if it works."

**Decision - GitHub Integration**:
> "PyGithub (not raw API calls) - well-documented, simple. The cache helper (5-min TTL) is important to avoid burning rate limits during development."

**Decision - Template Strategy**:
> "Template design should match the final UX from D5, just with disabled inputs - this avoids rework when adding write operations."

**Concern - Rate Limits**:
> "GitHub API rate limits: 5000 req/hour authenticated, but easy to burn through during development. The cache helper is important."

**Context - Separation from D5**:
> "Phase D4: Read-only UI (view specs, no submission). Phase D5: Write operations (form submission, trigger workflow_dispatch). This separation allows testing GitHub integration independently from workflow triggering."

## Constraints

**Must Work With Existing Setup**:
- GH_TOKEN already available in .env.local with repo scope
- Must read from demo/infra/{customer}/{env}/spec.yml structure
- Must parse existing spec.yml schema (cannot change it)
- No modifications to D1/D2/D3 code

**Technical Constraints**:
- No database (ephemeral Flask app state)
- No AWS credentials needed for D4
- Must work with Python 3.12+ (for eventual Docker in D6)
- GitHub API rate limits (5000/hour authenticated)

**Scope Boundaries**:
- No form submission (that's D5)
- No workflow_dispatch triggering (that's D5)
- No real-time action status polling (out of scope for MVP)
- No boto3 AWS discovery (out of scope per SPEC.md)
- No GitOps PR flow (out of scope for MVP)

## Edge Cases to Handle

**GitHub API Failures**:
1. Token has wrong scopes (not 'repo') - Show required scopes in error
2. Rate limit hit (429) - Display remaining limit and reset time
3. Network timeout - Suggest retry with exponential backoff
4. Repository not found (typo in GH_REPO) - Show config debug info

**Spec File Issues**:
1. spec.yml exists but contains invalid YAML - Show parse error with line number
2. spec.yml missing required fields - Validate schema, show what's missing
3. Customer/env directory exists but no spec.yml - Don't list as available pod
4. spec.yml has unexpected extra fields - Ignore gracefully (forward compatibility)

**User Input**:
1. customer/env contains path traversal attempt (../) - Validate and reject
2. customer/env contains special chars - Alphanumeric validation
3. Direct URL access to non-existent pod - 404 with list of valid pods

## Success Metrics

**Quantitative**:
- Flask app starts in <5 seconds
- Home page loads in <2 seconds (with caching)
- Pod detail page loads in <2 seconds (with caching)
- Health check responds in <1 second
- Zero unhandled exceptions in logs during testing
- All 9 pods discoverable (when D7 is complete)

**Qualitative**:
- Error messages are friendly and actionable (not stack traces)
- UI is navigable without documentation
- Logs provide enough context for debugging
- Code is readable and maintainable (clear function names, comments)
- Templates are semantic HTML (accessible, SEO-friendly)

**Readiness for D5**:
- Form structure matches final design (just needs enabling inputs)
- GitHub client is reusable for workflow_dispatch calls
- Error handling patterns are established
- Template inheritance is set up for adding submission flow

## Dependencies

**Blocked By**:
- D3 must be complete (though D4 can develop in parallel for local testing)
- GH_TOKEN must have 'repo' scope (already confirmed in .env.local)

**Blocks**:
- D5 (Flask Write Operations) - needs D4's GitHub client and templates
- D6 (Docker Packaging) - needs working Flask app to containerize

**Parallel Development**:
- Can develop D4 while D3 is in code review (no runtime dependency)
- Can test locally without D3 being deployed

## File Structure
```
demo/backend/
├── app.py                    # Flask application (~200-250 lines)
├── requirements.txt          # Python dependencies (~6 lines)
└── templates/
    ├── index.html.j2         # Pod listing page (~80-100 lines)
    └── form.html.j2          # Pod detail form (~100-120 lines)
```

**Total**: 4 files, ~400-450 lines of code

## Next Steps After D4

1. **Phase D5** - Add form submission and workflow_dispatch triggering
2. **Phase D6** - Dockerize Flask app and create docker-compose.yml
3. **Phase D7** - Scale to 9 pods and end-to-end integration testing
4. **Demo Rehearsal** - Practice 5-minute walkthrough with timer

---

**Specification Status**: Draft - Ready for Review
**Estimated Effort**: 2.5-3 hours
**Target PR Size**: ~400-450 LoC, 4 new files
**Demo Date**: Tomorrow morning
