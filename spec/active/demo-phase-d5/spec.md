# Feature: Pod Creation & Editing with Workflow Dispatch (Demo Phase D5)

## Origin
This is Phase 3 of the D4 spec split. D4A established Flask foundation and pod listing. D4B added read-only pod detail view. D5 adds write operations: editing existing pods and creating new pods via workflow_dispatch triggers.

## Outcome
A complete spec-editor application that:
- Allows editing existing pod configurations via web form
- Allows creating new pods with customer/env selection
- Validates inputs and prevents overwriting existing pods
- Triggers GitHub Actions workflow_dispatch with form data
- Shows deployment status with link to action run
- Handles all write operation errors gracefully

**Shippable**: Yes - delivers complete CRUD operations for pod management.

## User Story
**As an** operations engineer
**I want** to edit existing pod configurations via a web form
**So that** I can update instance names and WAF settings without manual workflow_dispatch

**As an** operations engineer
**I want** to create new pods via a web form
**So that** I can provision new customer environments without manually creating files

**As a** developer
**I want** strict validation to prevent overwrites
**So that** existing pods aren't accidentally destroyed

## Context

**Discovery**:
- D4A proved GitHub API integration works
- D4B proved spec parsing and form rendering works
- Now enable write operations with workflow_dispatch
- Need both "edit existing" and "add new" modes in same form

**Current State** (after D4B):
- Flask app with pod listing and detail view
- Form displays spec values (read-only)
- All inputs disabled with note about D5

**Desired State**:
- Edit mode: Form pre-populated, customer/env readonly
- Add mode: Empty form with customer/env dropdowns
- Submit button triggers workflow_dispatch
- Server validates no overwrites for new pods
- Success shows action run URL
- Comprehensive error handling for failures

## Technical Requirements

### 1. Form Modes

**Edit Existing (`GET /pod/<customer>/<env>`)** - from D4B:
- Customer/env shown as readonly badges (not inputs)
- Instance name, instance type, WAF pre-populated from spec.yml
- Form action: `POST /deploy` with hidden `mode=edit`
- Submit button: "Deploy Changes"

**Add New (`GET /pod/new`)** - NEW:
- Customer dropdown: advworks, northwind, contoso
- Environment dropdown: dev, stg, prd
- Instance name: empty text input (required)
- Instance type: text input (default: "t4g.nano")
- WAF enabled: checkbox (default: unchecked)
- Form action: `POST /deploy` with hidden `mode=new`
- Submit button: "Create Pod"

### 2. Form Template Updates

**Update form.html.j2**:
```jinja2
{% if mode == 'edit' %}
  {# Readonly context section #}
  <div class="context">
    <h2>{{ spec.metadata.customer }}</h2>
    <span class="badge badge-{{ env_badge_color(spec.metadata.environment) }}">
      {{ spec.metadata.environment }}
    </span>
  </div>

  {# Hidden fields for edit mode #}
  <input type="hidden" name="customer" value="{{ spec.metadata.customer }}">
  <input type="hidden" name="environment" value="{{ spec.metadata.environment }}">
  <input type="hidden" name="mode" value="edit">

{% else %}
  {# mode == 'new' - Dropdowns for selection #}
  <div class="form-group">
    <label for="customer">Customer *</label>
    <select name="customer" id="customer" required>
      <option value="">-- Select Customer --</option>
      <option value="advworks">advworks</option>
      <option value="northwind">northwind</option>
      <option value="contoso">contoso</option>
    </select>
  </div>

  <div class="form-group">
    <label for="environment">Environment *</label>
    <select name="environment" id="environment" required>
      <option value="">-- Select Environment --</option>
      <option value="dev">dev (Development)</option>
      <option value="stg">stg (Staging)</option>
      <option value="prd">prd (Production)</option>
    </select>
  </div>

  <input type="hidden" name="mode" value="new">
{% endif %}

{# Common fields - always editable #}
<div class="form-group">
  <label for="instance_name">Instance Name *</label>
  <input type="text" name="instance_name" id="instance_name"
         value="{{ spec.spec.compute.instance_name if mode == 'edit' else '' }}"
         required pattern="[a-z0-9-]+">
  <small>Lowercase letters, numbers, hyphens only</small>
</div>

<div class="form-group">
  <label for="instance_type">Instance Type *</label>
  <input type="text" name="instance_type" id="instance_type"
         value="{{ spec.spec.compute.instance_type if mode == 'edit' else 't4g.nano' }}"
         required>
</div>

<div class="form-group">
  <label>
    <input type="checkbox" name="waf_enabled" id="waf_enabled"
           {{ 'checked' if mode == 'edit' and spec.spec.security.waf.enabled else '' }}>
    Enable WAF Protection
  </label>
</div>

<div class="computed-name">
  Full instance name:
  <strong id="full-name">
    <span id="customer-part">{{ spec.metadata.customer if mode == 'edit' else '?' }}</span>-<span id="env-part">{{ spec.metadata.environment if mode == 'edit' else '?' }}</span>-<span id="name-part">{{ spec.spec.compute.instance_name if mode == 'edit' else '?' }}</span>
  </strong>
</div>

<button type="submit" class="btn-primary">
  {{ 'Deploy Changes' if mode == 'edit' else 'Create Pod' }}
</button>
```

### 3. New Routes

**`GET /pod/new`** - NEW:
```python
@app.route('/pod/new')
def new_pod():
    if not repo:
        return "Error: GitHub client not initialized", 500

    return render_template('form.html.j2',
                           mode='new',
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

**`POST /deploy`** - NEW (handles both modes):
```python
@app.route('/deploy', methods=['POST'])
def deploy():
    if not repo:
        return "Error: GitHub client not initialized", 500

    try:
        # Extract form data
        customer = validate_path_component(request.form['customer'], 'customer')
        env = validate_path_component(request.form['environment'], 'environment')
        instance_name = validate_instance_name(request.form['instance_name'])
        instance_type = request.form['instance_type']
        waf_enabled = request.form.get('waf_enabled') == 'on'
        mode = request.form.get('mode', 'edit')

        # CRITICAL: For new pods, check if spec already exists
        if mode == 'new':
            path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"
            try:
                repo.get_contents(path)
                # File exists - reject with 409 Conflict
                return render_template('error.html',
                    error_code=409,
                    error_title="Pod Already Exists",
                    error_message=f"Pod {customer}/{env} already exists.",
                    error_action=f"<a href='/pod/{customer}/{env}'>Edit it instead</a> or choose a different customer/environment combination."
                ), 409
            except:
                # File doesn't exist - good to proceed
                pass

        # Trigger workflow_dispatch
        workflow = repo.get_workflow('deploy-pod.yml')
        success = workflow.create_dispatch(
            ref='main',  # or current branch
            inputs={
                'customer': customer,
                'environment': env,
                'instance_name': instance_name,
                'instance_type': instance_type,
                'waf_enabled': str(waf_enabled).lower()
            }
        )

        if success:
            # Get latest workflow run (approximation - may not be exact)
            runs = workflow.get_runs(branch='main')
            latest_run = runs[0] if runs.totalCount > 0 else None

            return render_template('success.html',
                customer=customer,
                env=env,
                action_url=latest_run.html_url if latest_run else None,
                mode=mode
            )
        else:
            raise Exception("workflow_dispatch failed")

    except ValueError as e:
        # Validation error
        return render_template('error.html',
            error_code=400,
            error_title="Invalid Input",
            error_message=str(e)
        ), 400

    except Exception as e:
        app.logger.error(f"Deployment failed: {e}")
        return render_template('error.html',
            error_code=500,
            error_title="Deployment Failed",
            error_message=str(e)
        ), 500
```

### 4. Input Validation

**Add validation helpers**:
```python
import re

def validate_path_component(value, param_name):
    """Validate customer/environment parameters"""
    if not value or len(value) > 50:
        raise ValueError(f"{param_name} must be 1-50 characters")

    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValueError(f"{param_name} contains invalid characters (use a-z, 0-9, -, _ only)")

    if '..' in value or '/' in value or '\\' in value:
        app.logger.warning(f"Path traversal attempt detected: {param_name}={value}")
        raise ValueError(f"{param_name} contains illegal path characters")

    return value

def validate_instance_name(value):
    """Validate instance_name (stricter than customer/env)"""
    if not value or len(value) > 30:
        raise ValueError("instance_name must be 1-30 characters")

    if not re.match(r'^[a-z0-9-]+$', value):
        raise ValueError("instance_name must be lowercase letters, numbers, and hyphens only")

    if value.startswith('-') or value.endswith('-'):
        raise ValueError("instance_name cannot start or end with hyphen")

    return value
```

### 5. New Templates

**success.html.j2** - NEW:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Deployment Started</title>
    <style>/* Match site style */</style>
</head>
<body>
    <div class="container">
        <h1>✅ Deployment Started</h1>

        {% if mode == 'new' %}
            <p>Creating new pod: <strong>{{ customer }}/{{ env }}</strong></p>
        {% else %}
            <p>Updating pod: <strong>{{ customer }}/{{ env }}</strong></p>
        {% endif %}

        {% if action_url %}
            <p>View progress: <a href="{{ action_url }}" target="_blank">GitHub Actions Run</a></p>
        {% else %}
            <p>Check the <a href="https://github.com/{{ GH_REPO }}/actions" target="_blank">Actions tab</a> for the latest run.</p>
        {% endif %}

        <p>The deployment typically takes 3-5 minutes to complete.</p>

        <div class="actions">
            <a href="/pod/{{ customer }}/{{ env }}" class="btn">View Pod</a>
            <a href="/" class="btn-secondary">Back to Home</a>
        </div>
    </div>
</body>
</html>
```

**error.html.j2** - Enhanced from D4B:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Error {{ error_code }}</title>
    <style>/* Match site style */</style>
</head>
<body>
    <div class="container">
        <h1>{{ error_title }}</h1>
        <p class="error-message">{{ error_message }}</p>

        {% if error_action %}
            <div class="error-action">{{ error_action | safe }}</div>
        {% endif %}

        <div class="actions">
            <a href="javascript:history.back()" class="btn">Go Back</a>
            <a href="/" class="btn-secondary">Home</a>
        </div>
    </div>
</body>
</html>
```

### 6. Update Navigation

**Add "Create New Pod" button to index.html.j2**:
```html
<div class="header">
    <h1>Pod Manager</h1>
    <a href="/pod/new" class="btn-primary">+ Create New Pod</a>
</div>
```

## Architecture (D5 Additions)

```
┌─────────────────────────┐
│   Browser               │
└───────────┬─────────────┘
            │
            ├─ GET /                          (D4A)
            ├─ GET /health                    (D4A)
            ├─ GET /pod/advworks/dev          (D4B - edit mode)
            ├─ GET /pod/new                   (D5 - add mode)
            └─ POST /deploy                   (D5 - NEW)
            │
┌───────────▼─────────────┐
│   Flask App (app.py)    │
│   D5 Additions:         │
│   - /pod/new route      │
│   - /deploy route       │
│   - Validation helpers  │
│   - workflow_dispatch   │
└───────────┬─────────────┘
            │
            ├─ Check if spec exists (mode=new)
            ├─ workflow.create_dispatch()
            └─ Get latest run URL
            │
┌───────────▼─────────────┐
│   GitHub API            │
│   - Check file exists   │
│   - Trigger workflow    │
│   - Get run status      │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│   GitHub Actions        │
│   deploy-pod.yml        │
│   - Receives inputs     │
│   - Renders spec.yml    │
│   - Runs terraform      │
│   - Commits spec.yml    │
└─────────────────────────┘
```

## Implementation Punch List

### Form Template Updates (5 tasks)
- [ ] Add mode parameter support to form.html.j2
- [ ] Add customer/env dropdowns for mode=new
- [ ] Add readonly badges for mode=edit
- [ ] Add JavaScript to update computed name preview (optional)
- [ ] Update submit button text based on mode

### New Routes (3 tasks)
- [ ] Implement `GET /pod/new` route
- [ ] Implement `POST /deploy` route
- [ ] Update `GET /pod/<customer>/<env>` to pass mode=edit

### Validation (4 tasks)
- [ ] Add `validate_path_component()` helper
- [ ] Add `validate_instance_name()` helper
- [ ] Add duplicate check for mode=new
- [ ] Add input sanitization for all form fields

### Workflow Dispatch Integration (4 tasks)
- [ ] Add PyGithub workflow_dispatch call
- [ ] Map form fields to workflow inputs
- [ ] Handle workflow dispatch errors
- [ ] Retrieve latest run URL after dispatch

### New Templates (2 tasks)
- [ ] Create success.html.j2
- [ ] Enhance error.html.j2 with action support

### Navigation Updates (2 tasks)
- [ ] Add "Create New Pod" button to index.html.j2
- [ ] Update breadcrumbs to show mode

### Testing (8 tasks)
- [ ] Test edit existing pod (advworks/dev)
- [ ] Test create new pod (new customer/env combo)
- [ ] Test duplicate prevention (try to create advworks/dev)
- [ ] Test validation errors (invalid instance_name)
- [ ] Test workflow dispatch success
- [ ] Test workflow dispatch failure
- [ ] Test all error pages render correctly
- [ ] End-to-end test: create → workflow runs → AWS shows resource

**Total: 28 tasks**

## Validation Criteria

**Must Pass Before Shipping D5**:

**Edit Mode**:
- [ ] Can edit existing pod (advworks/dev)
- [ ] Customer/env shown as readonly badges
- [ ] Form pre-populated with current spec values
- [ ] Submit triggers workflow_dispatch with correct inputs
- [ ] Success page shows action run URL

**Add Mode**:
- [ ] Can access `/pod/new`
- [ ] Form shows customer/env dropdowns
- [ ] Form shows empty instance_name field
- [ ] Submit creates new pod via workflow
- [ ] Duplicate check prevents overwriting existing pod (409 error)

**Validation**:
- [ ] Invalid instance_name rejected (uppercase, spaces, special chars)
- [ ] Path traversal attempts blocked
- [ ] Missing required fields rejected
- [ ] All validation errors show helpful messages

**Integration**:
- [ ] Workflow receives correct inputs
- [ ] Workflow runs successfully
- [ ] Terraform creates/updates infrastructure
- [ ] Can verify changes in AWS console
- [ ] Multiple sequential deploys work

## Success Metrics

**Quantitative**:
- Form submission → workflow dispatch < 2 seconds
- Duplicate check completes < 500ms
- Zero unhandled exceptions
- All HTTP status codes correct (200, 400, 409, 500)

**Qualitative**:
- Workflow inputs match form exactly
- Error messages are actionable
- Success page provides clear next steps
- Form UX is consistent between modes

**Customer Value**:
- Can create new pod without touching GitHub UI
- Can edit pod without manual workflow_dispatch
- Prevented from accidentally overwriting pods
- Can verify deployment started via action link

## Dependencies

**Blocked By**:
- D4A and D4B must be complete
- GH_TOKEN must have `workflow` scope (not just `repo`)
- GitHub Action `deploy-pod.yml` must exist with workflow_dispatch trigger

**Blocks**:
- D6 (Docker Packaging) - needs complete app to containerize
- D7 (Integration Testing) - needs full CRUD to test

**Extends**:
- D4B's form.html.j2 template
- D4A's GitHub client and caching
- Existing workflow_dispatch inputs from deploy-pod.yml

## Constraints

**GitHub Token Scopes Required**:
- `repo` (read/write repository)
- `workflow` (trigger workflow_dispatch)

**Workflow Requirements**:
- Must accept inputs: customer, environment, instance_name, instance_type, waf_enabled
- Must handle both new pod creation and existing pod updates
- Must create spec.yml if it doesn't exist
- Must commit spec.yml after successful terraform apply

**Security**:
- All user input validated server-side
- No SQL injection risk (no database)
- XSS prevented by Flask auto-escaping
- CSRF protection (consider adding in follow-up)

**Scope Boundaries**:
- No real-time deployment status polling (link to GitHub Actions only)
- No rollback capability (manual via Git/Terraform)
- No multi-pod bulk operations
- No spec.yml direct editing (form fields only)

## Edge Cases Handled

**Duplicate Prevention**:
1. User tries to create existing pod → 409 with link to edit
2. Race condition (two users create same pod) → GitHub handles via file locks
3. Spec exists but is invalid → User can still "create" (overwrites with valid spec)

**Workflow Dispatch**:
1. Token lacks workflow scope → 403 error with helpful message
2. Workflow file doesn't exist → 404 error with setup instructions
3. Workflow dispatch succeeds but can't get run URL → Show generic actions link
4. Multiple rapid dispatches → All queue successfully (GitHub handles)

**Input Validation**:
1. Instance name with uppercase → Reject with message
2. Instance name too long → Reject with max length
3. Empty required fields → Browser validation + server check
4. XSS attempt in instance_name → Auto-escaped by Flask

**Form Modes**:
1. Direct access to `/pod/new` with no auth → Works (no auth in MVP)
2. Edit mode with customer/env mismatch → Can't happen (URL defines them)
3. Mode parameter tampering → Server validates against spec existence

## Next Steps After D5

1. **Ship D5** - Complete CRUD operations
2. **Phase D6** - Docker packaging (Dockerfile + compose)
3. **Phase D7** - Scale to 9 pods and integration testing
4. **Follow-up** - Client-side validation for better UX (optional)
5. **Follow-up** - Real-time action status polling (optional)

## Out of Scope (Deferred)

**Client-side validation** (nice-to-have):
- JavaScript to check duplicate customer/env combos
- Real-time validation of instance_name pattern
- Live preview of full instance name
- → Can defer to D5B or later

**CSRF protection**:
- Flask-WTF for CSRF tokens
- → Can defer to security hardening phase

**Authentication**:
- No login required for MVP
- → Can defer to production hardening

**Rollback operations**:
- No "undo" button for deployments
- Users must manually revert via Git/Terraform
- → Can defer to advanced features

---

**Specification Status**: Ready for Planning
**Estimated Effort**: 2-3 hours
**Target PR Size**: ~300 LoC addition to D4B, 2 new templates
**Complexity**: 6/10 (Medium - workflow_dispatch integration + dual modes)
