# Implementation Plan: Pod Form Operations - Edit & Create UI (Demo Phase D5A)
Generated: 2025-10-23
Specification: spec.md

## Understanding

This phase adds write operations UI to the spec-editor Flask app. We're building dual-mode forms (edit existing pods + create new pods) with full validation, but WITHOUT triggering actual GitHub Actions workflows. Instead, we show a deployment preview. This keeps D5A testable without workflow permissions and separates UI logic from API integration (D5B will wire up workflow_dispatch).

**Key Design Decisions from Clarifying Questions**:
- Single form.html.j2 with {% if mode %} conditionals (not separate templates)
- Tailwind card with key-value pairs for deployment preview
- "Create New Pod" button in top right corner of home page
- Live JavaScript to update computed name as user types
- Error banner at top of form for validation feedback
- Explicit `from flask import request` import

**Architecture**: This is a demo Flask app, not the production Lambda backend. Manual testing via browser, no pytest/mypy validation gates.

## Relevant Files

**Reference Patterns** (existing code to follow):
- `demo/backend/app.py` (lines 80-106) - `validate_path_component()` pattern for input validation
- `demo/backend/app.py` (lines 108-138) - `fetch_spec()` pattern for GitHub API calls
- `demo/backend/app.py` (lines 213-248) - `view_pod()` route with error handling pattern
- `demo/backend/templates/form.html.j2` (lines 1-152) - Existing form structure with Tailwind
- `demo/backend/templates/error.html.j2` (lines 22-32) - Error type icon pattern
- `demo/backend/templates/index.html.j2` (lines 20-56) - Customer grouping and environment badges

**Files to Create**:
- `demo/backend/templates/success.html.j2` - Deployment preview/success page

**Files to Modify**:
- `demo/backend/app.py` (~150 LoC additions):
  - Add `request` import (line 6)
  - Add `validate_instance_name()` helper (after line 106)
  - Add `GET /pod/new` route (after line 248)
  - Add `POST /deploy` route (after new route)
  - Update `view_pod()` to pass mode=edit (line 225)
- `demo/backend/templates/form.html.j2` (~100 LoC changes):
  - Add mode parameter handling for dual modes
  - Remove disabled attributes from inputs
  - Add customer/env dropdowns for create mode
  - Add form submission to POST /deploy
  - Add live JavaScript for computed name preview
  - Update read-only notice
- `demo/backend/templates/error.html.j2` (~3 LoC addition):
  - Add conflict error icon (line 22 area)
- `demo/backend/templates/index.html.j2` (~8 LoC addition):
  - Add "Create New Pod" button in header (line 11 area)

## Architecture Impact

- **Subsystems affected**: Flask backend (routes, templates, validation)
- **New dependencies**: None (all dependencies already in requirements.txt)
- **Breaking changes**: None (purely additive - new routes and template updates)

## Task Breakdown

### Task 1: Add validate_instance_name() Helper
**File**: `demo/backend/app.py`
**Action**: CREATE (new function)
**Pattern**: Follow `validate_path_component()` at lines 80-106

**Implementation**:
```python
# Add after validate_path_component() function (after line 106)

def validate_instance_name(value):
    """
    Validate instance_name (stricter than customer/env).

    Must be:
    - Lowercase letters, numbers, hyphens only
    - 1-30 characters
    - Cannot start or end with hyphen

    Args:
        value: The instance name to validate

    Returns:
        str: The validated value

    Raises:
        ValueError: If validation fails
    """
    if not value or len(value) > 30:
        raise ValueError("instance_name must be 1-30 characters")

    if not re.match(r'^[a-z0-9-]+$', value):
        raise ValueError("instance_name must be lowercase letters, numbers, and hyphens only (no uppercase, no underscores, no spaces)")

    if value.startswith('-') or value.endswith('-'):
        raise ValueError("instance_name cannot start or end with hyphen")

    return value
```

**Validation**: Start Flask (`just dev`), function should be defined without syntax errors.

---

### Task 2: Add request Import
**File**: `demo/backend/app.py`
**Action**: MODIFY
**Pattern**: Existing Flask imports at line 6

**Implementation**:
Change line 6 from:
```python
from flask import Flask, render_template, jsonify, abort
```

To:
```python
from flask import Flask, render_template, jsonify, abort, request
```

**Validation**: Start Flask (`just dev`), no import errors.

---

### Task 3: Add GET /pod/new Route
**File**: `demo/backend/app.py`
**Action**: CREATE (new route)
**Pattern**: Follow `view_pod()` route structure at lines 213-248

**Implementation**:
```python
# Add after view_pod() route (after line 248)

@app.route('/pod/new')
def new_pod():
    """Create new pod form"""
    if not repo:
        logger.error("GitHub client not initialized")
        abort(500)

    # Empty spec structure for template
    empty_spec = {
        'metadata': {
            'customer': '',
            'environment': ''
        },
        'spec': {
            'compute': {
                'instance_name': '',
                'instance_type': 't4g.nano'
            },
            'security': {
                'waf': {
                    'enabled': False
                }
            }
        }
    }

    return render_template('form.html.j2',
                           mode='new',
                           customer='',
                           env='',
                           spec=empty_spec)
```

**Validation**: Visit `http://localhost:5000/pod/new` - should load (will error until form template updated).

---

### Task 4: Add POST /deploy Route
**File**: `demo/backend/app.py`
**Action**: CREATE (new route)
**Pattern**: Follow error handling from `view_pod()` at lines 230-248

**Implementation**:
```python
# Add after new_pod() route

@app.route('/deploy', methods=['POST'])
def deploy():
    """Handle form submission - validate and preview (D5A: no actual deployment)"""
    if not repo:
        logger.error("GitHub client not initialized")
        abort(500)

    try:
        # Extract and validate form data
        customer = validate_path_component(request.form['customer'], 'customer')
        env = validate_path_component(request.form['environment'], 'environment')
        instance_name = validate_instance_name(request.form['instance_name'])
        instance_type = request.form.get('instance_type', '').strip()
        waf_enabled = request.form.get('waf_enabled') == 'on'
        mode = request.form.get('mode', 'edit')

        # Validate instance_type not empty
        if not instance_type:
            raise ValueError("instance_type cannot be empty")

        # CRITICAL: For new pods, check if spec already exists
        if mode == 'new':
            path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"
            try:
                repo.get_contents(path)
                # File exists - reject with 409 Conflict
                logger.warning(f"Attempted to create existing pod: {customer}/{env}")
                pods = list_all_pods()
                return render_template('error.html.j2',
                    error_type="conflict",
                    error_title="Pod Already Exists",
                    error_message=f"Pod {customer}/{env} already exists. Choose a different customer/environment combination or edit the existing pod.",
                    show_pods=True,
                    pods=pods), 409
            except:
                # File doesn't exist - good to proceed
                logger.info(f"Creating new pod: {customer}/{env}")
                pass
        else:
            logger.info(f"Updating existing pod: {customer}/{env}")

        # D5A: Preview deployment inputs (no actual workflow trigger)
        deployment_inputs = {
            'customer': customer,
            'environment': env,
            'instance_name': instance_name,
            'instance_type': instance_type,
            'waf_enabled': str(waf_enabled).lower()
        }

        logger.info(f"Deployment preview: {deployment_inputs}")

        return render_template('success.html.j2',
            mode=mode,
            customer=customer,
            env=env,
            deployment_inputs=deployment_inputs,
            preview_mode=True)  # D5A flag

    except ValueError as e:
        # Validation error
        logger.warning(f"Validation error in /deploy: {e}")
        return render_template('error.html.j2',
            error_type="validation",
            error_title="Invalid Input",
            error_message=str(e),
            show_pods=True,
            pods=list_all_pods()), 400

    except KeyError as e:
        # Missing form field
        logger.error(f"Missing form field: {e}")
        return render_template('error.html.j2',
            error_type="validation",
            error_title="Missing Required Field",
            error_message=f"Required field missing: {e}",
            show_pods=False,
            pods=[]), 400

    except Exception as e:
        # Generic error
        logger.error(f"Deployment preview failed: {e}")
        return render_template('error.html.j2',
            error_type="server_error",
            error_title="Server Error",
            error_message=f"Failed to process form: {e}",
            show_pods=False,
            pods=[]), 500
```

**Validation**: Submit form - should handle validation (will error until success template created).

---

### Task 5: Update view_pod() Route to Pass mode=edit
**File**: `demo/backend/app.py`
**Action**: MODIFY
**Pattern**: Line 225 render_template call

**Implementation**:
Change lines 225-228 from:
```python
        # Render form with spec data
        return render_template('form.html.j2',
                               customer=customer,
                               env=env,
                               spec=spec)
```

To:
```python
        # D5A: Render form with mode=edit, inputs enabled
        return render_template('form.html.j2',
                               mode='edit',
                               customer=customer,
                               env=env,
                               spec=spec)
```

**Validation**: Visit `/pod/advworks/dev` - should load with mode=edit (will show old template until Task 6).

---

### Task 6: Update form.html.j2 for Dual Modes
**File**: `demo/backend/templates/form.html.j2`
**Action**: MODIFY
**Pattern**: Follow existing form structure

**Implementation**:

**Step 6a**: Update title and breadcrumb (lines 1-18)
- Title should handle both modes
- Breadcrumb should only show for edit mode

Change lines 6 and 12-17 to:
```jinja2
    <title>{% if mode == 'edit' %}{{ customer }} / {{ env }}{% else %}Create New Pod{% endif %} - Spec Editor</title>

    <!-- Breadcrumb Navigation (edit mode only) -->
    {% if mode == 'edit' %}
    <nav class="mb-6 text-sm">
        <a href="/" class="text-blue-600 hover:underline">Home</a>
        <span class="text-gray-400 mx-2">/</span>
        <span class="text-gray-700 font-medium">{{ customer }}</span>
        <span class="text-gray-400 mx-2">/</span>
        <span class="text-gray-700 font-medium">{{ env }}</span>
    </nav>
    {% endif %}
```

**Step 6b**: Update header section (lines 20-52)

Replace entire header section (lines 20-52) with:
```jinja2
        <!-- Header -->
        <header class="mb-8">
            {% if mode == 'edit' %}
                <!-- Edit Mode: Show customer/env as badges -->
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
            {% else %}
                <!-- Create Mode: Simple title -->
                <h1 class="text-3xl font-bold text-gray-900 mb-4">
                    Create New Pod
                </h1>
            {% endif %}
        </header>
```

**Step 6c**: Update form opening tag and add customer/env fields (replace lines 54-73)

Replace form opening and computed name section with:
```jinja2
        <!-- Pod Configuration Form -->
        <main>
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-xl font-semibold text-gray-800 mb-4">
                    Pod Configuration
                </h2>

                <form method="POST" action="/deploy" class="space-y-6">
                    <!-- Customer and Environment Fields -->
                    {% if mode == 'edit' %}
                        <!-- Edit Mode: Hidden inputs -->
                        <input type="hidden" name="customer" value="{{ customer }}">
                        <input type="hidden" name="environment" value="{{ env }}">
                        <input type="hidden" name="mode" value="edit">
                    {% else %}
                        <!-- Create Mode: Dropdowns -->
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="customer" class="block text-sm font-medium text-gray-700 mb-2">
                                    Customer *
                                </label>
                                <select name="customer" id="customer" required
                                        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <option value="">-- Select Customer --</option>
                                    <option value="advworks">advworks</option>
                                    <option value="northwind">northwind</option>
                                    <option value="contoso">contoso</option>
                                </select>
                            </div>

                            <div>
                                <label for="environment" class="block text-sm font-medium text-gray-700 mb-2">
                                    Environment *
                                </label>
                                <select name="environment" id="environment" required
                                        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <option value="">-- Select Environment --</option>
                                    <option value="dev">dev (Development)</option>
                                    <option value="stg">stg (Staging)</option>
                                    <option value="prd">prd (Production)</option>
                                </select>
                            </div>
                        </div>
                        <input type="hidden" name="mode" value="new">
                    {% endif %}

                    <!-- Computed Instance Name Preview -->
                    <div class="bg-gray-50 p-4 rounded border border-gray-200">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Full Instance Name Preview
                        </label>
                        <p class="text-lg font-mono text-gray-900">
                            <span id="customer-part">{{ customer if mode == 'edit' else '?' }}</span>-<span id="env-part">{{ env if mode == 'edit' else '?' }}</span>-<span id="name-part">{{ spec.spec.compute.instance_name if mode == 'edit' else '?' }}</span>
                        </p>
                        <p class="text-xs text-gray-500 mt-1">
                            Format: {customer}-{environment}-{instance_name}
                        </p>
                    </div>
```

**Step 6d**: Update compute inputs to remove disabled (replace lines 75-102)

Replace Compute section with:
```jinja2
                    <!-- Compute Section -->
                    <div class="border-t pt-6">
                        <h3 class="text-lg font-semibold text-gray-800 mb-4">Compute</h3>

                        <div class="space-y-4">
                            <div>
                                <label for="instance_name" class="block text-sm font-medium text-gray-700 mb-2">
                                    Instance Name *
                                </label>
                                <input type="text"
                                       name="instance_name"
                                       id="instance_name"
                                       value="{{ spec.spec.compute.instance_name if mode == 'edit' else '' }}"
                                       required
                                       pattern="[a-z0-9-]+"
                                       placeholder="e.g., web1, app1"
                                       class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                <small class="text-gray-600 text-xs">Lowercase letters, numbers, hyphens only</small>
                            </div>

                            <div>
                                <label for="instance_type" class="block text-sm font-medium text-gray-700 mb-2">
                                    Instance Type *
                                </label>
                                <input type="text"
                                       name="instance_type"
                                       id="instance_type"
                                       value="{{ spec.spec.compute.instance_type if mode == 'edit' else 't4g.nano' }}"
                                       required
                                       placeholder="t4g.nano"
                                       class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            </div>
                        </div>
                    </div>
```

**Step 6e**: Update security section (replace lines 104-118)

Replace Security section with:
```jinja2
                    <!-- Security Section -->
                    <div class="border-t pt-6">
                        <h3 class="text-lg font-semibold text-gray-800 mb-4">Security</h3>

                        <div class="flex items-center">
                            <input type="checkbox"
                                   name="waf_enabled"
                                   id="waf_enabled"
                                   {% if mode == 'edit' and spec.spec.security.waf.enabled %}checked{% endif %}
                                   class="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500">
                            <label for="waf_enabled" class="ml-3 text-sm font-medium text-gray-700">
                                Web Application Firewall (WAF) Enabled
                            </label>
                        </div>
                    </div>
```

**Step 6f**: Update action buttons (replace lines 120-132)

Replace Action Buttons section with:
```jinja2
                    <!-- Action Buttons -->
                    <div class="border-t pt-6 flex justify-between">
                        <a href="/"
                           class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                            ← Back to Home
                        </a>

                        <button type="submit"
                                class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
                            Preview Deployment
                        </button>
                    </div>
                </form>
            </div>
        </main>
```

**Step 6g**: Add live JavaScript for computed name (before closing </body> tag)

Add before line 150 (`</body>`):
```jinja2
    <!-- Live Preview JavaScript -->
    <script>
        // Update computed instance name as user types/selects
        const customerPart = document.getElementById('customer-part');
        const envPart = document.getElementById('env-part');
        const namePart = document.getElementById('name-part');

        {% if mode == 'new' %}
        // Create mode: Listen to dropdowns and input
        const customerSelect = document.getElementById('customer');
        const envSelect = document.getElementById('environment');
        const nameInput = document.getElementById('instance_name');

        customerSelect.addEventListener('change', () => {
            customerPart.textContent = customerSelect.value || '?';
        });

        envSelect.addEventListener('change', () => {
            envPart.textContent = envSelect.value || '?';
        });

        nameInput.addEventListener('input', () => {
            namePart.textContent = nameInput.value || '?';
        });
        {% else %}
        // Edit mode: Only listen to instance_name input
        const nameInput = document.getElementById('instance_name');

        nameInput.addEventListener('input', () => {
            namePart.textContent = nameInput.value || '{{ spec.spec.compute.instance_name }}';
        });
        {% endif %}
    </script>
```

**Step 6h**: Update footer text (line 145-147)

Change:
```jinja2
            <p class="mt-2">
                Demo Phase D4B - Pod Detail View (Read-only)
            </p>
```

To:
```jinja2
            <p class="mt-2">
                Demo Phase D5A - Form Operations
            </p>
```

**Validation**: Visit `/pod/advworks/dev` and `/pod/new` - forms should render, inputs enabled, dropdowns shown for create mode, live preview works.

---

### Task 7: Create success.html.j2 Template
**File**: `demo/backend/templates/success.html.j2`
**Action**: CREATE
**Pattern**: Follow error.html.j2 structure and Tailwind styling

**Implementation**:
```jinja2
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deployment Preview - Spec Editor</title>
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
            <div class="bg-white rounded-lg shadow-md p-8">
                <!-- Success Icon -->
                <div class="text-center mb-6">
                    <div class="text-6xl mb-4">✅</div>
                    <h2 class="text-3xl font-bold text-gray-900 mb-2">
                        {% if preview_mode %}
                        Deployment Preview
                        {% else %}
                        Deployment Started
                        {% endif %}
                    </h2>
                </div>

                <!-- Mode-specific message -->
                {% if mode == 'new' %}
                    <p class="text-lg text-gray-700 mb-4">
                        {% if preview_mode %}
                        Would create new pod: <strong class="font-mono">{{ customer }}/{{ env }}</strong>
                        {% else %}
                        Creating new pod: <strong class="font-mono">{{ customer }}/{{ env }}</strong>
                        {% endif %}
                    </p>
                {% else %}
                    <p class="text-lg text-gray-700 mb-4">
                        {% if preview_mode %}
                        Would update pod: <strong class="font-mono">{{ customer }}/{{ env }}</strong>
                        {% else %}
                        Updating pod: <strong class="font-mono">{{ customer }}/{{ env }}</strong>
                        {% endif %}
                    </p>
                {% endif %}

                <!-- Deployment Inputs Preview (Tailwind Card) -->
                <div class="bg-gray-50 p-6 rounded-lg border border-gray-200 mb-6">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">
                        {% if preview_mode %}
                        Workflow Inputs (Preview)
                        {% else %}
                        Workflow Inputs (Sent)
                        {% endif %}
                    </h3>
                    <dl class="space-y-2">
                        <div class="flex">
                            <dt class="font-medium text-gray-700 w-40">Customer:</dt>
                            <dd class="font-mono text-gray-900">{{ deployment_inputs.customer }}</dd>
                        </div>
                        <div class="flex">
                            <dt class="font-medium text-gray-700 w-40">Environment:</dt>
                            <dd class="font-mono text-gray-900">{{ deployment_inputs.environment }}</dd>
                        </div>
                        <div class="flex">
                            <dt class="font-medium text-gray-700 w-40">Instance Name:</dt>
                            <dd class="font-mono text-gray-900">{{ deployment_inputs.instance_name }}</dd>
                        </div>
                        <div class="flex">
                            <dt class="font-medium text-gray-700 w-40">Instance Type:</dt>
                            <dd class="font-mono text-gray-900">{{ deployment_inputs.instance_type }}</dd>
                        </div>
                        <div class="flex">
                            <dt class="font-medium text-gray-700 w-40">WAF Enabled:</dt>
                            <dd class="font-mono text-gray-900">{{ deployment_inputs.waf_enabled }}</dd>
                        </div>
                    </dl>
                </div>

                <!-- D5A Note -->
                {% if preview_mode %}
                <div class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
                    <p class="text-blue-700">
                        <strong>Phase D5A:</strong> This is a preview only. Phase D5B will wire up the actual GitHub Actions workflow_dispatch trigger.
                    </p>
                </div>
                {% else %}
                <!-- D5B: Action run URL -->
                {% if action_url %}
                    <p class="mb-4">
                        View progress: <a href="{{ action_url }}" target="_blank" class="text-blue-600 hover:underline font-medium">GitHub Actions Run →</a>
                    </p>
                {% endif %}
                <p class="text-gray-600 mb-6">
                    The deployment typically takes 3-5 minutes to complete.
                </p>
                {% endif %}

                <!-- Navigation -->
                <div class="flex gap-4">
                    <a href="/pod/{{ customer }}/{{ env }}"
                       class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                        View Pod
                    </a>
                    <a href="/"
                       class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                        Back to Home
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
            <p class="mt-2">
                Demo Phase D5A - Form Operations
            </p>
        </footer>
    </div>
</body>
</html>
```

**Validation**: Submit form - success page should display with preview.

---

### Task 8: Add Conflict Error Icon to error.html.j2
**File**: `demo/backend/templates/error.html.j2`
**Action**: MODIFY
**Pattern**: Existing error icon conditionals at lines 22-32

**Implementation**:

Add after line 24 (after validation error):
```jinja2
                    {% elif error_type == 'conflict' %}
                    <div class="text-6xl mb-4">⚠️</div>
```

**Validation**: Try to create existing pod (advworks/dev) - should show conflict error with ⚠️ icon.

---

### Task 9: Add "Create New Pod" Button to index.html.j2
**File**: `demo/backend/templates/index.html.j2`
**Action**: MODIFY
**Pattern**: Existing header structure at lines 11-18

**Implementation**:

Replace header section (lines 11-18) with:
```jinja2
        <header class="mb-8">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-4xl font-bold text-gray-900 mb-2">
                        Spec Editor - Pod Management
                    </h1>
                    <p class="text-lg text-gray-600">
                        View and manage infrastructure pod configurations
                    </p>
                </div>
                <a href="/pod/new"
                   class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-md hover:shadow-lg">
                    + Create New Pod
                </a>
            </div>
        </header>
```

**Validation**: Visit `/` - button should appear in top right, clicking goes to `/pod/new`.

---

## Risk Assessment

**Risk: Live JavaScript preview breaks in edge cases**
- **Likelihood**: Low
- **Impact**: Low (doesn't affect form submission)
- **Mitigation**: Simple event listeners on standard inputs, tested in modern browsers

**Risk: Form validation errors show after submission instead of inline**
- **Likelihood**: Medium
- **Impact**: Medium (slightly worse UX than inline validation)
- **Mitigation**: Clarifying question confirmed error banner at top is acceptable. Browser HTML5 validation provides some inline feedback.

**Risk: Duplicate check race condition (two users create same pod)**
- **Likelihood**: Very Low (demo environment, single user)
- **Impact**: Low (GitHub API would handle the conflict)
- **Mitigation**: Acceptable for demo scope

**Risk: Template syntax errors causing 500 errors**
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**: Incremental testing after each template change, follow existing template patterns exactly

**Risk: Missing form fields cause KeyError**
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**: Added explicit KeyError handler in POST /deploy route

## Integration Points

**Flask Routes**:
- New: `GET /pod/new` → `new_pod()`
- New: `POST /deploy` → `deploy()`
- Modified: `GET /pod/<customer>/<env>` → `view_pod()` (now passes mode=edit)

**Templates**:
- Modified: `form.html.j2` (dual mode support)
- New: `success.html.j2` (deployment preview)
- Modified: `error.html.j2` (conflict icon)
- Modified: `index.html.j2` (create button)

**Validation Functions**:
- New: `validate_instance_name()` (stricter than validate_path_component)
- Existing: `validate_path_component()` (reused for customer/env)
- Existing: `list_all_pods()` (reused for error recovery)

## VALIDATION GATES (DEMO-SPECIFIC)

**Note**: This is a demo Flask app, not the production Lambda backend. Standard validation gates from `spec/stack.md` (black, mypy, pytest) do NOT apply.

**Demo Validation Approach**: Manual testing via browser

**After Each Task**:
1. Check Flask starts without errors: `just dev`
2. Check console for Python syntax errors
3. Visit affected routes in browser
4. Verify expected behavior

**Manual Test Checklist** (run after all code tasks complete):

### Edit Mode Tests:
- [ ] Visit `/pod/advworks/dev` - form loads
- [ ] Customer/env shown as badges (not inputs)
- [ ] Instance name, instance type, WAF are editable
- [ ] Live preview updates as you type instance name
- [ ] Submit with valid data shows preview page
- [ ] Preview shows correct deployment inputs
- [ ] "View Pod" link works from preview

### Create Mode Tests:
- [ ] Visit `/pod/new` - empty form loads
- [ ] Customer dropdown has 3 options (advworks, northwind, contoso)
- [ ] Environment dropdown has 3 options (dev, stg, prd)
- [ ] Live preview updates as you select customer/env/name
- [ ] Submit with valid data shows preview page
- [ ] Try to create advworks/dev → 409 error with helpful message

### Validation Tests:
- [ ] Submit with empty instance_name → browser validation error
- [ ] Submit instance_name "WEB1" (uppercase) → server error banner
- [ ] Submit instance_name "-web1" (leading hyphen) → server error banner
- [ ] Submit instance_name "web_1" (underscore) → server error banner
- [ ] Submit instance_name "web-1" (valid) → success

### Navigation Tests:
- [ ] Home page shows "Create New Pod" button (top right)
- [ ] Click button → goes to `/pod/new`
- [ ] "Back to Home" links work from all pages
- [ ] Breadcrumb works in edit mode

### Error Handling Tests:
- [ ] 409 conflict error shows ⚠️ icon
- [ ] All error pages have "Back to Home" link
- [ ] Validation errors show helpful messages

**Enforcement Rules**:
- If Flask won't start → Fix Python syntax errors
- If routes return 500 → Check Flask console for stack trace
- If templates don't render → Check Jinja2 syntax
- If validation fails → Fix logic, re-test

**No automated gates** - This is acceptable for demo scope per spec.

## Validation Sequence

**Per-Task Validation**:
1. Save file
2. Check Flask console for reload errors
3. Visit affected route in browser
4. Verify expected change visible

**Final Validation** (after Task 9):
1. Restart Flask: `just dev`
2. Run all manual test checklist items above
3. Verify no console errors or warnings
4. Test all navigation flows
5. Test both edit and create modes end-to-end

**Success Criteria**:
- All manual tests pass
- No 500 errors
- No Python exceptions in Flask console
- Live preview works smoothly
- Forms submit and show preview correctly

## Plan Quality Assessment

**Complexity Score**: 6/10 (MEDIUM - At threshold, user approved override)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Existing Flask patterns at demo/backend/app.py:80-248
✅ Template patterns at demo/backend/templates/*.j2
✅ All clarifying questions answered
✅ Validation approach confirmed (manual browser testing)
✅ No new dependencies needed
✅ Pure additive changes (no breaking changes)
✅ Similar dual-mode pattern used in many Flask apps

⚠️ Template changes are large (~100 LoC in form.html.j2)
⚠️ JavaScript live preview adds client-side complexity (mitigated: simple event listeners)

**Assessment**: High confidence implementation. Building on solid D4A/D4B foundation with clear patterns to follow. Template changes are straightforward conditionals. Main risk is Jinja2 syntax errors, which are easily caught and fixed during incremental testing.

**Estimated one-pass success probability**: 85%

**Reasoning**:
- Flask route patterns are well-established from D4A/D4B
- Template structure is consistent and documented
- Validation helpers follow existing pattern
- User confirmed all design decisions upfront
- Manual testing approach is appropriate for demo scope
- Only uncertainty is potential template syntax mistakes (15% risk)
