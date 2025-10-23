# Feature: Pod Form Operations - Edit & Create UI (Demo Phase D5A)

## Origin
This is Phase 1 of the D5 spec split. D5 was split into D5A (form operations) and D5B (GitHub API integration) to separate UI logic from external API integration. This phase builds the complete form UI for editing and creating pods, with simulated deployment for testing.

## Outcome
A complete pod management UI that:
- Allows editing existing pod configurations via web form
- Allows creating new pods with customer/env selection
- Validates all inputs and prevents duplicate pods
- Shows a preview of what deployment would trigger
- Has comprehensive error handling
- Is fully testable without GitHub workflow permissions

**Shippable**: Yes - delivers complete UI/UX, ready for D5B to wire up GitHub Actions.

## User Story
**As an** operations engineer
**I want** to edit existing pod configurations via a web form
**So that** I can modify instance names and WAF settings through a friendly UI

**As an** operations engineer
**I want** to create new pods via a web form
**So that** I can set up new customer environments without manual file creation

**As a** developer testing the UI
**I want** to see what deployment inputs would be sent
**So that** I can verify the form logic without triggering actual workflows

## Context

**Discovery**:
- D4A proved GitHub API integration works for reading
- D4B proved spec parsing and form rendering works
- Now enable write operations with form submission
- Split out GitHub API to keep context manageable

**Current State** (after D4B):
- Flask app with pod listing and read-only detail view
- Form displays spec values with all inputs disabled
- GET /pod/<customer>/<env> route shows existing pods
- Comprehensive error handling for read operations

**Desired State**:
- Edit mode: Form pre-populated, inputs enabled, customer/env readonly
- Create mode: Empty form with customer/env dropdowns
- Submit validates inputs and checks for duplicates
- Success page shows deployment preview (not actual workflow)
- All validation and error handling working
- Ready for D5B to add workflow_dispatch integration

## Technical Requirements

### 1. Form Modes

**Edit Existing (`GET /pod/<customer>/<env>`)** - Update from D4B:
- Customer/env shown as readonly badges (not form inputs)
- Instance name, instance type, WAF enabled for editing
- All inputs now enabled (remove disabled attributes)
- Form submits to: `POST /deploy`
- Hidden input: `mode=edit`
- Submit button: "Preview Deployment"

**Create New (`GET /pod/new`)** - NEW:
- Customer dropdown: advworks, northwind, contoso
- Environment dropdown: dev, stg, prd
- Instance name: empty text input (required)
- Instance type: text input (default: "t4g.nano")
- WAF enabled: checkbox (default: unchecked)
- Form submits to: `POST /deploy`
- Hidden input: `mode=new`
- Submit button: "Preview Deployment"

### 2. Form Template Updates

**Update form.html.j2** - Add mode parameter support:

```jinja2
{# Context: Customer and Environment #}
{% if mode == 'edit' %}
  {# Edit mode: Show as readonly badges #}
  <div class="context-section">
    <h2 class="text-3xl font-bold capitalize">{{ customer }}</h2>
    {% if env == 'dev' %}
    <span class="px-4 py-2 bg-green-100 text-green-800 rounded-full">dev</span>
    {% elif env == 'stg' %}
    <span class="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-full">stg</span>
    {% elif env == 'prd' %}
    <span class="px-4 py-2 bg-red-100 text-red-800 rounded-full">prd</span>
    {% endif %}
  </div>

  <input type="hidden" name="customer" value="{{ customer }}">
  <input type="hidden" name="environment" value="{{ env }}">
  <input type="hidden" name="mode" value="edit">

{% else %}
  {# Create mode: Show dropdowns #}
  <div class="form-group">
    <label for="customer">Customer *</label>
    <select name="customer" id="customer" required class="form-select">
      <option value="">-- Select Customer --</option>
      <option value="advworks">advworks</option>
      <option value="northwind">northwind</option>
      <option value="contoso">contoso</option>
    </select>
  </div>

  <div class="form-group">
    <label for="environment">Environment *</label>
    <select name="environment" id="environment" required class="form-select">
      <option value="">-- Select Environment --</option>
      <option value="dev">dev (Development)</option>
      <option value="stg">stg (Staging)</option>
      <option value="prd">prd (Production)</option>
    </select>
  </div>

  <input type="hidden" name="mode" value="new">
{% endif %}

{# Common fields - always editable (no disabled attribute) #}
<div class="form-group">
  <label for="instance_name">Instance Name *</label>
  <input type="text"
         name="instance_name"
         id="instance_name"
         value="{{ spec.spec.compute.instance_name if mode == 'edit' else '' }}"
         required
         pattern="[a-z0-9-]+"
         class="form-input">
  <small class="text-gray-600">Lowercase letters, numbers, hyphens only</small>
</div>

<div class="form-group">
  <label for="instance_type">Instance Type *</label>
  <input type="text"
         name="instance_type"
         id="instance_type"
         value="{{ spec.spec.compute.instance_type if mode == 'edit' else 't4g.nano' }}"
         required
         class="form-input">
</div>

<div class="form-group">
  <label class="flex items-center">
    <input type="checkbox"
           name="waf_enabled"
           id="waf_enabled"
           {% if mode == 'edit' and spec.spec.security.waf.enabled %}checked{% endif %}
           class="form-checkbox">
    <span class="ml-2">Enable WAF Protection</span>
  </label>
</div>

{# Computed name preview #}
<div class="bg-gray-50 p-4 rounded border">
  <label class="block text-sm font-medium text-gray-700 mb-2">
    Full Instance Name Preview
  </label>
  <p class="text-lg font-mono text-gray-900">
    <span id="customer-part">{{ customer if mode == 'edit' else '?' }}</span>-<span id="env-part">{{ env if mode == 'edit' else '?' }}</span>-<span id="name-part">{{ spec.spec.compute.instance_name if mode == 'edit' else '?' }}</span>
  </p>
</div>

<button type="submit" class="btn-primary">
  Preview Deployment
</button>
```

### 3. New Routes

**`GET /pod/new`** - NEW:
```python
@app.route('/pod/new')
def new_pod():
    """Create new pod form"""
    if not repo:
        return "Error: GitHub client not initialized", 500

    # Empty spec structure for template
    return render_template('form.html.j2',
                           mode='new',
                           customer='',
                           env='',
                           spec={
                               'metadata': {'customer': '', 'environment': ''},
                               'spec': {
                                   'compute': {
                                       'instance_name': '',
                                       'instance_type': 't4g.nano'
                                   },
                                   'security': {'waf': {'enabled': False}}
                               }
                           })
```

**`POST /deploy`** - NEW (validation only, no workflow dispatch):
```python
@app.route('/deploy', methods=['POST'])
def deploy():
    """Handle form submission - validate and preview (D5A: no actual deployment)"""
    if not repo:
        return "Error: GitHub client not initialized", 500

    try:
        # Extract and validate form data
        customer = validate_path_component(request.form['customer'], 'customer')
        env = validate_path_component(request.form['environment'], 'environment')
        instance_name = validate_instance_name(request.form['instance_name'])
        instance_type = request.form['instance_type'].strip()
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
                pods = list_all_pods()
                return render_template('error.html.j2',
                    error_type="conflict",
                    error_title="Pod Already Exists",
                    error_message=f"Pod {customer}/{env} already exists. Choose a different customer/environment combination or edit the existing pod.",
                    show_pods=True,
                    pods=pods), 409
            except:
                # File doesn't exist - good to proceed
                pass

        # D5A: Preview deployment inputs (no actual workflow trigger)
        deployment_inputs = {
            'customer': customer,
            'environment': env,
            'instance_name': instance_name,
            'instance_type': instance_type,
            'waf_enabled': str(waf_enabled).lower()
        }

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

    except Exception as e:
        logger.error(f"Deployment preview failed: {e}")
        return render_template('error.html.j2',
            error_type="server_error",
            error_title="Server Error",
            error_message=f"Failed to process form: {e}",
            show_pods=False,
            pods=[]), 500
```

**Update `GET /pod/<customer>/<env>`** - Pass mode parameter:
```python
@app.route('/pod/<customer>/<env>')
def view_pod(customer, env):
    """Pod detail page: show spec.yml configuration in editable form"""
    try:
        # Validate input parameters
        customer = validate_path_component(customer, "customer")
        env = validate_path_component(env, "environment")

        # Fetch and parse spec
        spec = fetch_spec(customer, env)

        # D5A: Render form with mode=edit, inputs enabled
        return render_template('form.html.j2',
                               mode='edit',
                               customer=customer,
                               env=env,
                               spec=spec)

    except ValueError as e:
        # ... existing error handling ...
```

### 4. Input Validation

**Add `validate_instance_name()` helper** - NEW:
```python
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

Note: `validate_path_component()` already exists from D4B at app.py:80-106

### 5. New Templates

**success.html.j2** - NEW:
```html
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

                <!-- Deployment Inputs Preview -->
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
                        View progress: <a href="{{ action_url }}" target="_blank" class="text-blue-600 hover:underline">GitHub Actions Run</a>
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

**error.html.j2** - Update to handle conflict errors:

Add to existing error type checks:
```jinja2
{% elif error_type == 'conflict' %}
<div class="text-6xl mb-4">⚠️</div>
```

The template already has the structure, just needs the conflict icon added.

### 6. Navigation Updates

**Update index.html.j2** - Add "Create New Pod" button:

Add before the pod listing grid:
```jinja2
<div class="flex items-center justify-between mb-8">
    <h1 class="text-4xl font-bold text-gray-900">
        Pod Manager
    </h1>
    <a href="/pod/new"
       class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
        + Create New Pod
    </a>
</div>
```

## Architecture (D5A Additions)

```
┌─────────────────────────┐
│   Browser               │
└───────────┬─────────────┘
            │
            ├─ GET /                          (D4A)
            ├─ GET /health                    (D4A)
            ├─ GET /pod/advworks/dev          (D4B → D5A update: mode=edit)
            ├─ GET /pod/new                   (D5A - NEW)
            └─ POST /deploy                   (D5A - NEW: validation + preview)
            │
┌───────────▼─────────────┐
│   Flask App (app.py)    │
│   D5A Additions:        │
│   - /pod/new route      │
│   - /deploy route       │
│   - validate_instance_  │
│     name() helper       │
│   - Duplicate check     │
│   - Preview mode        │
└───────────┬─────────────┘
            │
            ├─ Check if spec exists (mode=new)
            └─ Return preview (no workflow trigger)
```

## Implementation Punch List

### Form Template Updates (6 tasks)
- [ ] Add mode parameter support to form.html.j2
- [ ] Add customer/env dropdowns for mode=new
- [ ] Add readonly customer/env badges for mode=edit
- [ ] Remove disabled attributes from all editable inputs
- [ ] Update submit button text to "Preview Deployment"
- [ ] Add computed name preview section

### New Routes (3 tasks)
- [ ] Implement GET /pod/new route
- [ ] Implement POST /deploy route (validation + preview only)
- [ ] Update GET /pod/<customer>/<env> to pass mode=edit

### Validation (3 tasks)
- [ ] Add validate_instance_name() helper
- [ ] Add duplicate check for mode=new in /deploy
- [ ] Add instance_type empty check

### New Templates (2 tasks)
- [ ] Create success.html.j2 with preview mode support
- [ ] Update error.html.j2 to handle conflict (409) errors

### Navigation Updates (1 task)
- [ ] Add "Create New Pod" button to index.html.j2

### Testing (8 tasks)
- [ ] Test GET /pod/new displays empty form
- [ ] Test GET /pod/advworks/dev shows editable form
- [ ] Test POST /deploy with valid edit data shows preview
- [ ] Test POST /deploy with valid new data shows preview
- [ ] Test POST /deploy duplicate creation returns 409
- [ ] Test validate_instance_name rejects uppercase
- [ ] Test validate_instance_name rejects leading/trailing hyphens
- [ ] Test all navigation links work (home, create, back)

**Total: 23 tasks**

## Validation Criteria

**Must Pass Before Shipping D5A**:

**Edit Mode**:
- [ ] Can access existing pod (advworks/dev)
- [ ] Form inputs are enabled (not disabled)
- [ ] Customer/env shown as readonly badges
- [ ] Form pre-populated with current spec values
- [ ] Submit shows deployment preview page
- [ ] Preview shows correct workflow inputs

**Create Mode**:
- [ ] Can access /pod/new
- [ ] Form shows customer/env dropdowns
- [ ] Form shows empty instance_name field
- [ ] Dropdowns have all 3 customers and 3 envs
- [ ] Submit shows deployment preview page
- [ ] Duplicate check prevents creating advworks/dev (409 error)

**Validation**:
- [ ] Invalid instance_name rejected (uppercase: "WEB1")
- [ ] Invalid instance_name rejected (leading hyphen: "-web1")
- [ ] Invalid instance_name rejected (trailing hyphen: "web1-")
- [ ] Invalid instance_name rejected (special chars: "web_1")
- [ ] Path traversal attempts blocked (customer: "../etc")
- [ ] Missing required fields rejected (empty instance_name)
- [ ] All validation errors show helpful messages

**Navigation**:
- [ ] "Create New Pod" button visible on home page
- [ ] Clicking button goes to /pod/new
- [ ] "Back to Home" links work from all pages
- [ ] "View Pod" link works from preview page

## Success Metrics

**Quantitative**:
- Form loads < 1 second
- Validation completes < 500ms
- Zero unhandled exceptions in Flask logs
- All HTTP status codes correct (200, 400, 409, 500)

**Qualitative**:
- Preview page clearly shows what deployment will do
- Error messages are actionable
- Form UX is consistent between modes
- Validation feedback is immediate

**Readiness for D5B**:
- All form inputs validated correctly
- Deployment inputs structure matches workflow_dispatch schema
- Success template has placeholder for action_url
- Error handling covers all edge cases

## Dependencies

**Blocked By**:
- D4A and D4B must be complete and shipped
- GH_TOKEN must have `repo` scope (for duplicate check)

**Blocks**:
- D5B (GitHub API Integration) - needs this UI complete

**Extends**:
- D4B's form.html.j2 template (adds dual modes)
- D4B's error.html.j2 template (adds conflict type)
- D4A's GitHub client (for duplicate checking)

## Constraints

**No GitHub Workflow Scope Required**:
- D5A only needs `repo` scope (read/write files)
- Does NOT trigger workflow_dispatch
- Can be fully tested without workflow permissions

**Scope Boundaries (Deferred to D5B)**:
- No workflow_dispatch triggering
- No action run URL retrieval
- No real deployment (preview only)

## Edge Cases Handled

**Duplicate Prevention**:
1. User tries to create existing pod → 409 with helpful message
2. User tries to create advworks/dev → 409 "already exists, edit instead"
3. User tries to create new customer/env → Passes duplicate check

**Input Validation**:
1. Instance name "WEB1" (uppercase) → Reject "must be lowercase"
2. Instance name "-web1" (leading hyphen) → Reject "cannot start with hyphen"
3. Instance name "web1-" (trailing hyphen) → Reject "cannot end with hyphen"
4. Instance name "web_1" (underscore) → Reject "hyphens only, no underscores"
5. Instance name "web-1" (valid) → Accept
6. Empty instance_type → Reject "cannot be empty"

**Form Modes**:
1. Direct access to /pod/new → Works (shows create form)
2. Direct access to /pod/advworks/dev → Works (shows edit form)
3. Mode parameter tampering → Server validates against spec existence

## Next Steps After D5A

1. **Ship D5A** - Complete form UI with preview
2. **Demo Preview Mode** - Show that validation and duplicate checking works
3. **Phase D5B** - Add workflow_dispatch integration (1 hour)
4. **Phase D6** - Docker packaging
5. **Phase D7** - Scale to 9 pods and integration testing

---

**Specification Status**: Ready for Planning
**Estimated Effort**: 1.5-2 hours
**Target PR Size**: ~250 LoC (1 new file, 4 modified files)
**Complexity**: 5/10 (Medium-Low - builds on D4A/D4B patterns, no external API)
