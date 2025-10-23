# Implementation Plan: Pod Detail View & Complete Error Handling (Demo Phase D4B)
Generated: 2025-10-23
Specification: spec.md

## Understanding

This phase builds directly on D4A's Flask foundation to add:
1. **Pod detail view** - Display spec.yml configuration in a read-only web form
2. **Comprehensive error handling** - Graceful degradation for all failure modes
3. **Input validation** - Security against path traversal and injection attacks
4. **User-friendly recovery** - Error pages with navigation back to valid options

**Key Architectural Decision**: Keep it simple. Single error template, no caching for specs (D4A cache handles pod listing), Tailwind CDN for consistency, manual testing to ship fast.

**Design Philosophy**:
- Follow D4A patterns exactly (GitHub client, logger, route structure)
- Prioritize working demo over perfect code
- Focus on user recovery from errors (show valid options)
- Tech debt full test coverage for later

## Relevant Files

**Reference Patterns** (existing code to follow):
- `demo/backend/app.py` (lines 79-128) - Pod discovery pattern with GitHub API
- `demo/backend/app.py` (lines 130-150) - Route pattern with error handling
- `demo/backend/app.py` (lines 61-77) - Cache helper functions (reference only, not using for specs)
- `demo/backend/templates/index.html.j2` (lines 1-82) - Tailwind structure, environment badges
- `demo/backend/templates/index.html.j2` (lines 34-50) - Environment badge coloring logic

**Files to Create**:
- `demo/backend/templates/form.html.j2` - Pod detail form (read-only inputs, breadcrumb navigation)
- `demo/backend/templates/error.html.j2` - Universal error page (adapts to 404/500/503)

**Files to Modify**:
- `demo/backend/app.py` (add ~80 lines) - New functions and routes:
  - `validate_path_component()` helper (lines ~195-210)
  - `fetch_spec()` function (lines ~212-235)
  - `/pod/<customer>/<env>` route (lines ~237-270)
  - Error handlers for 404, 500, 503 (lines ~272-295)
  - Template context processor for env badges (lines ~297-305)

## Architecture Impact
- **Subsystems affected**: Flask backend (demo only, not production Lambda)
- **New dependencies**: None (PyYAML already in requirements.txt)
- **Breaking changes**: None (purely additive)
- **Validation approach**: Manual testing via `just dev` (no pytest for demo)

## Task Breakdown

### Task 1: Add Input Validation Helper
**File**: `demo/backend/app.py`
**Action**: CREATE (new function)
**Pattern**: Security-first validation following OWASP guidelines

**Implementation**:
```python
# Add after line 77 (after set_cached function)

import re

def validate_path_component(value, param_name):
    """
    Validate URL path components to prevent path traversal and injection.

    Args:
        value: The path component to validate (customer or env)
        param_name: Name for error messages ("customer" or "environment")

    Returns:
        str: The validated value

    Raises:
        ValueError: If validation fails
    """
    if not value or len(value) > 50:
        raise ValueError(f"{param_name} must be 1-50 characters")

    # Alphanumeric, hyphen, underscore only
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValueError(f"{param_name} contains invalid characters (use a-z, A-Z, 0-9, -, _ only)")

    # Prevent path traversal
    if '..' in value or '/' in value or '\\' in value:
        logger.warning(f"Path traversal attempt detected: {param_name}={value}")
        raise ValueError(f"{param_name} contains path traversal attempt")

    return value
```

**Validation**: Visual inspection (function added, no syntax errors)

---

### Task 2: Add Spec Fetching Function
**File**: `demo/backend/app.py`
**Action**: CREATE (new function)
**Pattern**: Follow D4A's `list_all_pods()` pattern (lines 79-128)

**Implementation**:
```python
# Add after validate_path_component function

def fetch_spec(customer, env):
    """
    Fetch and parse spec.yml from GitHub for a specific pod.

    Args:
        customer: Customer name (validated)
        env: Environment name (validated)

    Returns:
        dict: Parsed spec.yml content

    Raises:
        Exception: If spec not found or YAML parse fails
    """
    path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"

    try:
        logger.info(f"Fetching spec: {path}")
        content = repo.get_contents(path)
        spec_yaml = content.decoded_content.decode('utf-8')
        spec = yaml.safe_load(spec_yaml)
        logger.info(f"✓ Successfully parsed spec for {customer}/{env}")
        return spec

    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in {path}: {e}")
        raise ValueError(f"Invalid YAML in spec.yml: {e}")

    except Exception as e:
        logger.error(f"Failed to fetch spec {path}: {e}")
        raise
```

**Validation**: Visual inspection (function added, follows D4A patterns)

---

### Task 3: Add Pod Detail Route
**File**: `demo/backend/app.py`
**Action**: CREATE (new route)
**Pattern**: Follow D4A's `index()` route pattern (lines 130-150)

**Implementation**:
```python
# Add after index() route (around line 150)

@app.route('/pod/<customer>/<env>')
def view_pod(customer, env):
    """Pod detail page: show spec.yml configuration in read-only form"""
    try:
        # Validate input parameters
        customer = validate_path_component(customer, "customer")
        env = validate_path_component(env, "environment")

        # Fetch and parse spec
        spec = fetch_spec(customer, env)

        # Render form with spec data
        return render_template('form.html.j2',
                               customer=customer,
                               env=env,
                               spec=spec)

    except ValueError as e:
        # Validation error - show error page with details
        logger.warning(f"Validation error for /pod/{customer}/{env}: {e}")
        return render_template('error.html.j2',
                               error_type="validation",
                               error_title="Invalid Request",
                               error_message=str(e),
                               show_pods=True,
                               pods=list_all_pods()), 400

    except Exception as e:
        # Spec not found or other error
        logger.error(f"Error viewing pod {customer}/{env}: {e}")
        return render_template('error.html.j2',
                               error_type="not_found",
                               error_title="Pod Not Found",
                               error_message=f"Could not find spec for {customer}/{env}",
                               show_pods=True,
                               pods=list_all_pods()), 404
```

**Validation**: Visual inspection (route added, error handling comprehensive)

---

### Task 4: Add Flask Error Handlers
**File**: `demo/backend/app.py`
**Action**: CREATE (new error handlers)
**Pattern**: Standard Flask error handler pattern

**Implementation**:
```python
# Add after view_pod() route

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors globally"""
    return render_template('error.html.j2',
                           error_type="not_found",
                           error_title="Page Not Found",
                           error_message="The page you're looking for doesn't exist",
                           show_pods=True,
                           pods=list_all_pods()), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors globally"""
    logger.error(f"Internal server error: {error}")
    return render_template('error.html.j2',
                           error_type="server_error",
                           error_title="Internal Server Error",
                           error_message="Something went wrong. Please try again later.",
                           show_pods=False,
                           pods=[]), 500

@app.errorhandler(503)
def service_unavailable_error(error):
    """Handle 503 errors (GitHub API issues)"""
    return render_template('error.html.j2',
                           error_type="service_unavailable",
                           error_title="Service Unavailable",
                           error_message="GitHub API is temporarily unavailable. Please try again later.",
                           show_pods=False,
                           pods=[]), 503
```

**Validation**: Visual inspection (handlers registered, follow Flask conventions)

---

### Task 5: Add Template Context Processor
**File**: `demo/backend/app.py`
**Action**: CREATE (new context processor)
**Pattern**: Standard Flask context processor for template helpers

**Implementation**:
```python
# Add after error handlers, before if __name__ == '__main__'

@app.context_processor
def utility_processor():
    """Add utility functions to all templates"""
    def env_badge_color(env):
        """Return Tailwind color classes for environment badges"""
        colors = {
            'dev': 'green',
            'stg': 'yellow',
            'prd': 'red'
        }
        return colors.get(env, 'gray')

    return dict(env_badge_color=env_badge_color)
```

**Validation**: Visual inspection (context processor added)

---

### Task 6: Create Pod Detail Form Template
**File**: `demo/backend/templates/form.html.j2`
**Action**: CREATE
**Pattern**: Copy structure from `index.html.j2`, adapt for form display

**Implementation**:
```jinja2
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ customer }} / {{ env }} - Spec Editor</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <!-- Breadcrumb Navigation -->
        <nav class="mb-6 text-sm">
            <a href="/" class="text-blue-600 hover:underline">Home</a>
            <span class="text-gray-400 mx-2">/</span>
            <span class="text-gray-700 font-medium">{{ customer }}</span>
            <span class="text-gray-400 mx-2">/</span>
            <span class="text-gray-700 font-medium">{{ env }}</span>
        </nav>

        <!-- Header with Environment Badge -->
        <header class="mb-8">
            <div class="flex items-center justify-between mb-4">
                <h1 class="text-3xl font-bold text-gray-900 capitalize">
                    {{ customer }}
                </h1>
                {% if env == 'dev' %}
                <span class="px-4 py-2 bg-green-100 text-green-800 text-lg font-medium rounded-full">
                    {{ env }}
                </span>
                {% elif env == 'stg' %}
                <span class="px-4 py-2 bg-yellow-100 text-yellow-800 text-lg font-medium rounded-full">
                    {{ env }}
                </span>
                {% elif env == 'prd' %}
                <span class="px-4 py-2 bg-red-100 text-red-800 text-lg font-medium rounded-full">
                    {{ env }}
                </span>
                {% else %}
                <span class="px-4 py-2 bg-gray-100 text-gray-800 text-lg font-medium rounded-full">
                    {{ env }}
                </span>
                {% endif %}
            </div>

            <!-- Read-only Notice -->
            <div class="bg-blue-50 border-l-4 border-blue-400 p-4">
                <p class="text-blue-700">
                    <strong>Read-only mode:</strong> This is Phase D4B - viewing only.
                    Phase D5 will enable editing and deployment.
                </p>
            </div>
        </header>

        <!-- Pod Configuration Form (Read-only) -->
        <main>
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-xl font-semibold text-gray-800 mb-4">
                    Pod Configuration
                </h2>

                <form class="space-y-6">
                    <!-- Computed Instance Name (Display only) -->
                    <div class="bg-gray-50 p-4 rounded border border-gray-200">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Full Instance Name
                        </label>
                        <p class="text-lg font-mono text-gray-900">
                            {{ customer }}-{{ env }}-{{ spec.spec.compute.instance_name }}
                        </p>
                        <p class="text-xs text-gray-500 mt-1">
                            Format: {customer}-{environment}-{instance_name}
                        </p>
                    </div>

                    <!-- Compute Section -->
                    <div class="border-t pt-6">
                        <h3 class="text-lg font-semibold text-gray-800 mb-4">Compute</h3>

                        <div class="space-y-4">
                            <div>
                                <label for="instance_name" class="block text-sm font-medium text-gray-700 mb-2">
                                    Instance Name
                                </label>
                                <input type="text"
                                       id="instance_name"
                                       value="{{ spec.spec.compute.instance_name }}"
                                       disabled
                                       class="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-700">
                            </div>

                            <div>
                                <label for="instance_type" class="block text-sm font-medium text-gray-700 mb-2">
                                    Instance Type
                                </label>
                                <input type="text"
                                       id="instance_type"
                                       value="{{ spec.spec.compute.instance_type }}"
                                       disabled
                                       class="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-700">
                            </div>
                        </div>
                    </div>

                    <!-- Security Section -->
                    <div class="border-t pt-6">
                        <h3 class="text-lg font-semibold text-gray-800 mb-4">Security</h3>

                        <div class="flex items-center">
                            <input type="checkbox"
                                   id="waf_enabled"
                                   {% if spec.spec.security.waf.enabled %}checked{% endif %}
                                   disabled
                                   class="h-5 w-5 text-blue-600 border-gray-300 rounded">
                            <label for="waf_enabled" class="ml-3 text-sm font-medium text-gray-700">
                                Web Application Firewall (WAF) Enabled
                            </label>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div class="border-t pt-6 flex justify-between">
                        <a href="/"
                           class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                            ← Back to Pods
                        </a>

                        <button type="button"
                                disabled
                                class="px-6 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed">
                            Save Changes (Disabled in D4B)
                        </button>
                    </div>
                </form>
            </div>
        </main>

        <footer class="mt-12 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
            <p>
                Spec Editor -
                <a href="https://github.com/trakrf/action-spec"
                   class="text-blue-600 hover:underline">
                    trakrf/action-spec
                </a>
            </p>
            <p class="mt-2">
                Demo Phase D4B - Pod Detail View (Read-only)
            </p>
        </footer>
    </div>
</body>
</html>
```

**Validation**:
- Visual inspection (HTML structure valid)
- Browser test: Check form displays correctly with disabled inputs

---

### Task 7: Create Error Template
**File**: `demo/backend/templates/error.html.j2`
**Action**: CREATE
**Pattern**: Universal error page that adapts to error type

**Implementation**:
```jinja2
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ error_title }} - Spec Editor</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <header class="mb-8">
            <h1 class="text-4xl font-bold text-gray-900 mb-2">
                Spec Editor
            </h1>
        </header>

        <main>
            <!-- Error Display -->
            <div class="bg-white rounded-lg shadow-md p-8 mb-6">
                <!-- Error Icon and Title -->
                <div class="text-center mb-6">
                    {% if error_type == 'not_found' %}
                    <div class="text-6xl mb-4">🔍</div>
                    {% elif error_type == 'validation' %}
                    <div class="text-6xl mb-4">⚠️</div>
                    {% elif error_type == 'server_error' %}
                    <div class="text-6xl mb-4">💥</div>
                    {% elif error_type == 'service_unavailable' %}
                    <div class="text-6xl mb-4">🚫</div>
                    {% else %}
                    <div class="text-6xl mb-4">❌</div>
                    {% endif %}

                    <h2 class="text-3xl font-bold text-gray-900 mb-2">
                        {{ error_title }}
                    </h2>
                    <p class="text-lg text-gray-600">
                        {{ error_message }}
                    </p>
                </div>

                <!-- Valid Pods List (if available) -->
                {% if show_pods and pods|length > 0 %}
                <div class="border-t pt-6">
                    <h3 class="text-xl font-semibold text-gray-800 mb-4">
                        Available Pods
                    </h3>
                    <p class="text-gray-600 mb-4">
                        Try one of these valid pods instead:
                    </p>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {% for pod in pods %}
                        <a href="/pod/{{ pod.customer }}/{{ pod.env }}"
                           class="block p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:shadow-lg transition-all">
                            <div class="flex items-center justify-between">
                                <span class="font-medium text-gray-700">
                                    {{ pod.customer }} / {{ pod.env }}
                                </span>
                                {% if pod.env == 'dev' %}
                                <span class="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                                    dev
                                </span>
                                {% elif pod.env == 'stg' %}
                                <span class="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full">
                                    stg
                                </span>
                                {% elif pod.env == 'prd' %}
                                <span class="px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full">
                                    prd
                                </span>
                                {% else %}
                                <span class="px-3 py-1 bg-gray-100 text-gray-800 text-sm font-medium rounded-full">
                                    {{ pod.env }}
                                </span>
                                {% endif %}
                            </div>
                        </a>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}

                <!-- Navigation -->
                <div class="border-t pt-6 mt-6">
                    <a href="/"
                       class="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                        ← Back to Home
                    </a>
                </div>
            </div>
        </main>

        <footer class="mt-12 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
            <p>
                Spec Editor -
                <a href="https://github.com/trakrf/action-spec"
                   class="text-blue-600 hover:underline">
                    trakrf/action-spec
                </a>
            </p>
        </footer>
    </div>
</body>
</html>
```

**Validation**:
- Visual inspection (HTML structure valid)
- Browser test: Trigger different error types to verify display

---

### Task 8: Manual Testing
**File**: N/A (testing only)
**Action**: TEST
**Pattern**: Use `just dev` and browser/curl for validation

**Test Scenarios**:

1. **Valid pod - Happy path**:
   ```bash
   # Start Flask server
   cd demo && just dev

   # In browser: http://localhost:5000/pod/advworks/dev
   # Expected: Form displays with advworks-dev-web1, t4g.nano, WAF unchecked
   ```

2. **Invalid pod - 404**:
   ```bash
   # In browser: http://localhost:5000/pod/invalid/invalid
   # Expected: Error page with list of valid pods
   ```

3. **Path traversal - Validation error**:
   ```bash
   # In browser: http://localhost:5000/pod/../etc/passwd
   # Expected: Error page with validation message
   ```

4. **Special characters - Validation error**:
   ```bash
   # In browser: http://localhost:5000/pod/test<script>/dev
   # Expected: Error page with "invalid characters" message
   ```

5. **Home navigation**:
   ```bash
   # From any error page, click "Back to Home"
   # Expected: Returns to pod listing page
   ```

6. **Breadcrumb navigation**:
   ```bash
   # From form page, click "Home" in breadcrumb
   # Expected: Returns to pod listing page
   ```

7. **Back button from form**:
   ```bash
   # From form page, click "Back to Pods" button
   # Expected: Returns to pod listing page
   ```

**Validation**:
- ✅ All 7 test scenarios pass
- ✅ No Python exceptions in Flask logs
- ✅ Error messages are user-friendly
- ✅ Navigation works correctly

---

## Risk Assessment

**Risk: YAML parsing errors**
- **Likelihood**: Low (spec.yml files are Terraform-managed)
- **Impact**: Medium (user sees 500 error)
- **Mitigation**: Error handler shows friendly message, logging captures details

**Risk: GitHub API rate limits**
- **Likelihood**: Low (D4A cache prevents excessive calls)
- **Impact**: Medium (503 errors)
- **Mitigation**: Error template explains rate limits, suggests retry

**Risk: Path traversal attacks**
- **Likelihood**: Low (validation blocks common patterns)
- **Impact**: High (security issue)
- **Mitigation**: Comprehensive validation with logging of attempts

**Risk: Template rendering errors**
- **Likelihood**: Low (Jinja2 is stable)
- **Impact**: Medium (500 errors)
- **Mitigation**: Test all template paths, error handler catches exceptions

**Risk: Missing spec fields**
- **Likelihood**: Low (spec.yml schema is fixed)
- **Impact**: Medium (template KeyError)
- **Mitigation**: Use Jinja2 default filters if needed, test with real specs

## Integration Points

**D4A Integration**:
- Uses existing GitHub client (`repo` global)
- Uses existing logger configuration
- Uses existing cache helpers (reference only)
- Follows existing route patterns
- Matches existing template styling

**Template Integration**:
- `form.html.j2` matches `index.html.j2` structure
- `error.html.j2` matches `index.html.j2` structure
- Both use same Tailwind CDN
- Environment badges reuse D4A logic

**Route Integration**:
- `/pod/<customer>/<env>` complements `/` (home)
- Error handlers work globally for all routes
- Breadcrumb links back to `/`

## VALIDATION GATES (ADAPTED FOR DEMO)

**Note**: This is demo code, not production Lambda. Standard validation gates from `spec/stack.md` don't apply. Using demo-specific validation:

**Manual Testing Gates** (from Task 8):
- ✅ Gate 1: Happy path works (valid pod displays correctly)
- ✅ Gate 2: Error handling works (invalid pod shows error page)
- ✅ Gate 3: Security works (path traversal blocked)
- ✅ Gate 4: Navigation works (all links functional)

**Quick Validation Commands**:
```bash
# Start Flask dev server
cd demo && just dev

# Test health endpoint (should show GitHub connected)
just health

# Test home page (should list pods)
just test-home

# Manual browser testing required for pod detail view
```

**Enforcement Rules**:
- If Flask crashes on startup → Fix Python syntax errors
- If templates fail to render → Fix Jinja2 syntax
- If test scenarios fail → Fix logic errors
- After fixes → Restart Flask and re-test

## Validation Sequence

**After each code task (Tasks 1-7)**:
1. Save the file
2. Check Python syntax: `python3 -m py_compile demo/backend/app.py`
3. Visual inspection (no typos, follows patterns)

**After all code complete (Task 8)**:
1. Start Flask: `cd demo && just dev`
2. Run all 7 test scenarios
3. Check Flask logs for errors
4. Verify no exceptions
5. Test navigation thoroughly

**Final validation before shipping**:
1. Flask starts without errors
2. All 7 test scenarios pass
3. Error pages display correctly
4. Forms are read-only (inputs disabled)
5. Breadcrumb navigation works
6. Back buttons work

## Plan Quality Assessment

**Complexity Score**: 4/10 (LOW-MEDIUM)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ D4A patterns established at demo/backend/app.py (lines 1-193)
✅ Template patterns at demo/backend/templates/index.html.j2 (lines 1-82)
✅ All clarifying questions answered (single template, Tailwind, error UX, breadcrumb, no cache, manual testing)
✅ No new dependencies needed
✅ Pure additive changes (no breaking changes)
✅ Similar validation pattern already in D4A codebase
✅ Flask error handlers are standard patterns

**Assessment**: High confidence implementation. Building on solid D4A foundation with clear patterns to follow. Only risk is template syntax errors, easily caught in manual testing.

**Estimated one-pass success probability**: 85%

**Reasoning**: Straightforward additive changes to working Flask app. Clear patterns from D4A. Main uncertainties are minor (template syntax, edge case handling). Manual testing will catch any issues quickly. High confidence in successful execution.
