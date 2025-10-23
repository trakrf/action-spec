# Feature: Pod Detail View & Complete Error Handling (Demo Phase D4B)

## Origin
This is Phase 2 of the D4 spec split. D4A established the Flask foundation and pod listing. D4B adds the pod detail view with form display, comprehensive error handling, and complete testing. This completes the read-only spec viewer before D5 adds write operations.

## Outcome
A complete read-only spec viewer that:
- Shows detailed pod configuration in a form layout
- Handles all error scenarios gracefully (404, 500, rate limits, YAML errors)
- Validates user input to prevent security issues
- Provides friendly error messages for troubleshooting
- Is fully tested and ready for D5 to add write operations

**Shippable**: Yes - completes the D4 feature set with full functionality.

## User Story
**As an** operations engineer
**I want** to view a pod's spec.yml configuration in a web form
**So that** I can see all current values without browsing GitHub files

**As a** developer preparing for demo
**I want** comprehensive error handling and validation
**So that** the app degrades gracefully and helps users troubleshoot issues

## Context

**Discovery**:
- D4A proved GitHub API integration works
- D4A foundation (Flask app, GitHub client, caching) is solid
- Now focus purely on detail view without GitHub connectivity concerns
- Form structure must match D5 final design (just disable inputs)

**Current State** (after D4A):
- Flask app running with pod listing
- Health check validates GitHub connectivity
- Cache prevents rate limit issues
- Basic error handling for missing GH_TOKEN

**Desired State**:
- Pod detail route (`/pod/<customer>/<env>`) displays spec in form
- Form shows: instance_name, instance_type, WAF enabled status
- All inputs disabled with note about D5 enabling editing
- Comprehensive error handling for all failure modes
- Input validation prevents path traversal and injection
- Complete testing validates all scenarios

## Technical Requirements

### 1. Spec Fetching & Parsing
- Add `fetch_spec(customer, env)` function to D4A's app.py
- Fetch spec.yml content via GitHub API
- Parse YAML with error handling for malformed files
- Cache parsed spec for 5 minutes (same pattern as D4A)
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

### 2. Pod Detail Route
**`GET /pod/<customer>/<env>`**:
- Extract customer and env from URL parameters
- Validate parameters (alphanumeric only, no special chars)
- Prevent path traversal attacks (reject `..`, `/`, `\`)
- Call `fetch_spec(customer, env)`
- Handle errors:
  - 404 if spec.yml not found (show list of valid pods)
  - 500 if YAML parse fails (show parse error details)
  - 503 if GitHub API fails (show retry suggestion)
- Render `form.html.j2` with spec data

### 3. form.html.j2 Template
**Structure**:
- Breadcrumb navigation: `Home > {customer} > {env}`
- Read-only context section:
  - Customer name (large, bold)
  - Environment badge (colored: dev=green, stg=yellow, prd=red)
- Form sections (all inputs disabled):
  - **Compute section**:
    - `instance_name` - text input, disabled
    - `instance_type` - text input, disabled
  - **Security section**:
    - `waf.enabled` - checkbox, disabled, checked if true
- Display computed full name: `{customer}-{env}-{instance_name}`
- Note: "Editing disabled in Phase D4 (read-only demo). D5 will enable editing."
- Back button linking to home page

### 4. Comprehensive Error Handling
**404 - Pod Not Found**:
- Friendly page: "Pod not found: {customer}/{env}"
- List all valid pods with links
- Suggest double-checking URL

**500 - YAML Parse Error**:
- Friendly page: "Error parsing spec.yml"
- Show file path and specific error message
- Link to raw file on GitHub for manual inspection

**503 - GitHub API Failure**:
- Rate limit exceeded: Show remaining quota and reset time
- Network error: Suggest retry and check connectivity
- Repository not found: Show config debug info (GH_REPO value)

**Custom Error Handlers**:
- Register Flask error handlers for 404, 500, 503
- All error pages use consistent template style
- Include navigation back to home page

### 5. Input Validation & Security
**Validate customer/env parameters**:
- Must be alphanumeric only (a-z, A-Z, 0-9, hyphen, underscore)
- Reject if contains: `..`, `/`, `\`, null bytes
- Reject if longer than 50 characters
- Log suspicious attempts at INFO level

**Example validation function**:
```python
import re

def validate_path_component(value, param_name):
    if not value or len(value) > 50:
        raise ValueError(f"{param_name} must be 1-50 characters")

    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValueError(f"{param_name} contains invalid characters")

    if '..' in value or '/' in value or '\\' in value:
        raise ValueError(f"{param_name} contains path traversal attempt")

    return value
```

### 6. Template Data Structure
**Data passed to form.html.j2**:
```python
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

**Template helper function**:
```python
@app.context_processor
def utility_processor():
    def env_badge_color(env):
        colors = {
            'dev': 'green',
            'stg': 'yellow',
            'prd': 'red'
        }
        return colors.get(env, 'gray')
    return dict(env_badge_color=env_badge_color)
```

## Architecture (D4B Additions)

```
┌─────────────────────────┐
│   Browser               │
└───────────┬─────────────┘
            │
            ├─ GET /                          (D4A)
            ├─ GET /health                    (D4A)
            └─ GET /pod/advworks/dev          (D4B - NEW)
            │
┌───────────▼─────────────┐
│   Flask App (app.py)    │
│   D4B Additions:        │
│   - fetch_spec()        │
│   - Pod detail route    │
│   - Input validation    │
│   - Error handlers      │
└───────────┬─────────────┘
            │
            ├─ repo.get_contents("demo/infra/advworks/dev/spec.yml")
            ├─ yaml.safe_load(content)
            └─ Cache parsed spec
            │
┌───────────▼─────────────┐
│   GitHub API            │
│   spec.yml content      │
└─────────────────────────┘
```

## Implementation Punch List

### Spec Fetching (4 tasks)
- [ ] Add `_get_file_content(path)` helper to app.py
- [ ] Implement `fetch_spec(customer, env)` function
- [ ] Parse YAML with `yaml.safe_load()`
- [ ] Cache parsed spec for 5 minutes

### Pod Detail Route (4 tasks)
- [ ] Create `validate_path_component()` helper
- [ ] Implement `GET /pod/<customer>/<env>` route
- [ ] Call validation on customer/env parameters
- [ ] Render form.html.j2 with spec data

### form.html.j2 Template (8 tasks)
- [ ] HTML5 boilerplate matching index.html.j2 style
- [ ] Breadcrumb navigation
- [ ] Read-only context section (customer + env badge)
- [ ] Compute section (instance_name, instance_type inputs - disabled)
- [ ] Security section (WAF checkbox - disabled)
- [ ] Display computed full instance name
- [ ] Note about D5 enabling editing
- [ ] Back button to home page

### Error Handlers (5 tasks)
- [ ] Create 404 error handler (pod not found)
- [ ] Create 500 error handler (YAML parse error)
- [ ] Create 503 error handler (GitHub API failure)
- [ ] Create error templates (or inline error pages)
- [ ] Test each error scenario manually

### Testing (5 tasks)
- [ ] Test valid pod: `/pod/advworks/dev` shows form
- [ ] Test invalid pod: `/pod/invalid/invalid` returns 404
- [ ] Test path traversal: `/pod/../../etc` is rejected
- [ ] Test YAML parse error (manually corrupt spec.yml temporarily)
- [ ] Test rate limit (manually exhaust API quota if possible)

**Total: 26 tasks**

## Code Examples

### Spec Fetching
```python
# Add to demo/backend/app.py

import yaml

def fetch_spec(customer, env):
    """Fetch and parse spec.yml from GitHub"""
    cache_key = f"spec:{customer}/{env}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"
    try:
        content = repo.get_contents(path)
        spec = yaml.safe_load(content.decoded_content)
        set_cached(cache_key, spec)
        return spec
    except Exception as e:
        app.logger.error(f"Failed to fetch spec {path}: {e}")
        raise
```

### Pod Detail Route
```python
@app.route('/pod/<customer>/<env>')
def view_pod(customer, env):
    if not repo:
        return "Error: GitHub client not initialized", 500

    try:
        # Validate input
        customer = validate_path_component(customer, "customer")
        env = validate_path_component(env, "environment")

        # Fetch spec
        spec = fetch_spec(customer, env)
        return render_template('form.html.j2', spec=spec)

    except ValueError as e:
        # Invalid input
        return f"Invalid input: {e}", 400

    except Exception as e:
        # Spec not found or other error
        app.logger.error(f"Error viewing pod {customer}/{env}: {e}")
        pods = list_all_pods()  # Show valid options
        return render_template('404.html',
                               customer=customer,
                               env=env,
                               pods=pods), 404
```

### Error Handlers
```python
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal error: {error}")
    return render_template('500.html', error=str(error)), 500

@app.errorhandler(503)
def service_unavailable(error):
    return render_template('503.html', error=str(error)), 503
```

## Validation Criteria

**Must Pass Before Shipping D4B**:
- [ ] Pod detail page displays correct spec values from GitHub
- [ ] All form inputs are disabled (read-only validation)
- [ ] Computed instance name displays correctly: `{customer}-{env}-{instance_name}`
- [ ] Invalid pod URL returns 404 with list of valid pods
- [ ] Path traversal attempts are rejected (400 error)
- [ ] YAML parse errors show friendly error page
- [ ] Breadcrumb navigation works (can get back to home)
- [ ] Error pages match site style and provide helpful context

**Integration Validation**:
- [ ] Works with D4A's GitHub client and caching
- [ ] Parses existing spec.yml schema correctly
- [ ] No console errors or warnings
- [ ] Logs show clear messages for each error type

## Success Metrics

**Quantitative**:
- Pod detail page loads in <2 seconds (with caching)
- YAML parsing completes in <500ms
- Zero unhandled exceptions in logs
- All error handlers return appropriate HTTP codes

**Qualitative**:
- Error messages are actionable (tell user what to do)
- Form structure is ready for D5 (just needs enabling inputs)
- Code follows D4A's patterns and conventions
- Templates use consistent styling

**Readiness for D5**:
- Form has proper structure for adding submission
- GitHub client can be extended for workflow_dispatch
- Error handling patterns established
- Input validation is production-ready

## Dependencies

**Blocked By**:
- D4A must be complete and shipped
- GH_TOKEN in .env.local with repo scope

**Blocks**:
- D5 (Flask Write Operations) - needs this complete UI
- D6 (Docker Packaging) - needs full app to containerize

**Builds On D4A**:
- Uses Flask app foundation from D4A
- Uses GitHub client and caching from D4A
- Extends index.html.j2 style to form.html.j2

## Constraints

**Must Work With**:
- D4A's Flask app structure
- D4A's GitHub client and cache
- Existing spec.yml schema (no modifications)
- Python 3.12+

**Security Requirements**:
- Prevent path traversal attacks
- Prevent XSS (Flask auto-escapes templates)
- Validate all user input
- Log suspicious activity

**Scope Boundaries (Deferred to D5)**:
- No form submission handling
- No POST routes
- No workflow_dispatch triggering
- No state management beyond caching

## Edge Cases Handled

**Spec File Issues**:
1. spec.yml missing required fields → Show parse error with schema expectations
2. spec.yml has unexpected extra fields → Ignore gracefully (forward compatibility)
3. spec.yml is empty → Show parse error
4. Customer/env dir exists but no spec.yml → Return 404 with valid pods list

**User Input**:
1. customer/env with uppercase → Accept (case-sensitive matching)
2. customer/env with hyphens/underscores → Accept (valid pattern)
3. customer/env with spaces → Reject (400 error)
4. customer/env with path traversal (../) → Reject and log (400 error)

**GitHub API**:
1. Rate limit exceeded → 503 with reset time
2. Network timeout → 503 with retry suggestion
3. 404 from GitHub → 404 with valid pods list

## Next Steps After D4B

1. **Ship D4B** - Complete read-only viewer
2. **Demo Tomorrow** - Show working pod listing + detail view
3. **Phase D5** - Add form submission + workflow_dispatch triggering
4. **Phase D6** - Docker packaging for deployment
5. **Phase D7** - Scale to 9 pods and integration testing

---

**Specification Status**: Ready for Planning
**Estimated Effort**: 1.5-2 hours
**Target PR Size**: ~200 LoC addition to D4A, 1 new file (form.html.j2)
**Complexity**: 4/10 (Low-Medium - Building on solid D4A foundation)
