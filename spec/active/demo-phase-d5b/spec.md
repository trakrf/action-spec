# Feature: GitHub Actions Workflow Integration (Demo Phase D5B)

## Origin
This is Phase 2 of the D5 spec split. D5A built the complete form UI with validation and preview mode. D5B adds the GitHub Actions workflow_dispatch integration to trigger actual deployments. This completes the write operations feature.

## Outcome
A fully functional deployment system that:
- Triggers GitHub Actions workflow_dispatch with form inputs
- Shows actual action run URLs to users
- Handles GitHub API errors gracefully
- Completes the end-to-end deployment workflow
- Updates infrastructure via Terraform when forms are submitted

**Shippable**: Yes - delivers complete deployment functionality, completes Demo Phase D5.

## User Story
**As an** operations engineer
**I want** form submissions to trigger actual infrastructure deployments
**So that** I can provision and update pods through the UI

**As a** user waiting for deployment
**I want** to see the GitHub Actions run URL
**So that** I can monitor progress and check logs

**As a** developer
**I want** comprehensive error handling for GitHub API failures
**So that** users get helpful messages when deployments fail

## Context

**Discovery**:
- D5A proved all form logic, validation, and UI works
- D5A establishes deployment_inputs structure
- Now wire up workflow_dispatch to trigger real deployments
- GitHub Actions workflow already built in D3

**Current State** (after D5A):
- Complete form UI for edit and create modes
- All validation working (instance_name, duplicates, etc.)
- Preview mode shows what deployment would do
- Success page has placeholder for action_url

**Desired State**:
- POST /deploy actually triggers workflow_dispatch
- Success page shows real GitHub Actions run URL
- Comprehensive error handling for API failures
- End-to-end: form submit → workflow runs → AWS updates

## Technical Requirements

### 1. Workflow Dispatch Integration

**Update POST /deploy route** - Replace preview with actual trigger:

```python
@app.route('/deploy', methods=['POST'])
def deploy():
    """Handle form submission - trigger GitHub Actions workflow"""
    if not repo:
        return "Error: GitHub client not initialized", 500

    try:
        # Extract and validate form data (unchanged from D5A)
        customer = validate_path_component(request.form['customer'], 'customer')
        env = validate_path_component(request.form['environment'], 'environment')
        instance_name = validate_instance_name(request.form['instance_name'])
        instance_type = request.form['instance_type'].strip()
        waf_enabled = request.form.get('waf_enabled') == 'on'
        mode = request.form.get('mode', 'edit')

        if not instance_type:
            raise ValueError("instance_type cannot be empty")

        # Duplicate check for new pods (unchanged from D5A)
        if mode == 'new':
            path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"
            try:
                repo.get_contents(path)
                pods = list_all_pods()
                return render_template('error.html.j2',
                    error_type="conflict",
                    error_title="Pod Already Exists",
                    error_message=f"Pod {customer}/{env} already exists.",
                    show_pods=True,
                    pods=pods), 409
            except:
                pass

        # D5B: Trigger workflow_dispatch (NEW)
        workflow_file = 'deploy-pod.yml'

        try:
            workflow = repo.get_workflow(workflow_file)
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_file}: {e}")
            return render_template('error.html.j2',
                error_type="not_found",
                error_title="Workflow Not Found",
                error_message=f"GitHub workflow '{workflow_file}' not found. Check .github/workflows/ directory.",
                show_pods=False,
                pods=[]), 404

        # Prepare workflow inputs
        workflow_inputs = {
            'customer': customer,
            'environment': env,
            'instance_name': instance_name,
            'instance_type': instance_type,
            'waf_enabled': str(waf_enabled).lower()  # GitHub expects string "true"/"false"
        }

        logger.info(f"Triggering workflow_dispatch for {customer}/{env} with inputs: {workflow_inputs}")

        # Trigger workflow dispatch
        try:
            success = workflow.create_dispatch(
                ref='main',  # Trigger on main branch
                inputs=workflow_inputs
            )
        except GithubException as e:
            logger.error(f"workflow_dispatch failed: {e.status} - {e.data}")

            # Handle specific GitHub API errors
            if e.status == 403:
                return render_template('error.html.j2',
                    error_type="forbidden",
                    error_title="Permission Denied",
                    error_message="GitHub token lacks 'workflow' scope. Update GH_TOKEN with workflow permissions.",
                    show_pods=False,
                    pods=[]), 403
            elif e.status == 404:
                return render_template('error.html.j2',
                    error_type="not_found",
                    error_title="Workflow Not Found",
                    error_message=f"Workflow '{workflow_file}' or branch 'main' not found.",
                    show_pods=False,
                    pods=[]), 404
            elif e.status == 422:
                return render_template('error.html.j2',
                    error_type="validation",
                    error_title="Invalid Workflow Inputs",
                    error_message=f"Workflow rejected inputs: {e.data.get('message', 'Unknown error')}",
                    show_pods=False,
                    pods=[]), 422
            else:
                raise  # Re-raise for generic handler

        if not success:
            raise Exception("workflow_dispatch returned False")

        # D5B: Get latest workflow run URL (best-effort)
        action_url = None
        try:
            # Wait briefly for GitHub to create the run
            import time
            time.sleep(2)

            runs = workflow.get_runs(branch='main')
            if runs.totalCount > 0:
                latest_run = runs[0]
                action_url = latest_run.html_url
                logger.info(f"Latest workflow run: {action_url}")
        except Exception as e:
            logger.warning(f"Could not retrieve workflow run URL: {e}")
            # Non-fatal - continue without URL

        # Success
        return render_template('success.html.j2',
            mode=mode,
            customer=customer,
            env=env,
            deployment_inputs=workflow_inputs,
            preview_mode=False,  # D5B: actual deployment
            action_url=action_url)

    except ValueError as e:
        # Validation error
        logger.warning(f"Validation error in /deploy: {e}")
        return render_template('error.html.j2',
            error_type="validation",
            error_title="Invalid Input",
            error_message=str(e),
            show_pods=True,
            pods=list_all_pods()), 400

    except GithubException as e:
        # GitHub API error
        logger.error(f"GitHub API error: {e}")
        return render_template('error.html.j2',
            error_type="api_error",
            error_title="GitHub API Error",
            error_message=f"Failed to trigger deployment: {e.data.get('message', str(e))}",
            show_pods=False,
            pods=[]), 503

    except Exception as e:
        # Generic error
        logger.error(f"Deployment failed: {e}")
        return render_template('error.html.j2',
            error_type="server_error",
            error_title="Deployment Failed",
            error_message=str(e),
            show_pods=False,
            pods=[]), 500
```

### 2. Import Updates

**Add to imports at top of app.py**:
```python
from github.GithubException import GithubException
import time
```

Note: `GithubException` might already be imported from D4A. If so, just add `time`.

### 3. Error Template Updates

**Update error.html.j2** - Add new error type icons:

```jinja2
{% if error_type == 'not_found' %}
<div class="text-6xl mb-4">🔍</div>
{% elif error_type == 'validation' %}
<div class="text-6xl mb-4">⚠️</div>
{% elif error_type == 'server_error' %}
<div class="text-6xl mb-4">💥</div>
{% elif error_type == 'service_unavailable' %}
<div class="text-6xl mb-4">🚫</div>
{% elif error_type == 'conflict' %}
<div class="text-6xl mb-4">⚠️</div>
{% elif error_type == 'forbidden' %}
<div class="text-6xl mb-4">🔒</div>
{% elif error_type == 'api_error' %}
<div class="text-6xl mb-4">🔌</div>
{% else %}
<div class="text-6xl mb-4">❌</div>
{% endif %}
```

### 4. Success Template Updates

**Update success.html.j2** - Handle actual deployment mode:

The template already supports `preview_mode` flag from D5A. In D5B:
- `preview_mode=False` shows "Deployment Started" messaging
- `action_url` is populated with actual GitHub Actions run URL
- Fallback to generic Actions tab link if URL retrieval fails

No template changes needed - D5A template already handles this!

### 5. GitHub Token Permissions

**Required GH_TOKEN scopes**:
- `repo` - Read/write repository (already required by D4A)
- `workflow` - Trigger workflow_dispatch (NEW for D5B)

**Validation**: Health check endpoint should verify workflow scope

Update `/health` endpoint to check permissions:
```python
@app.route('/health')
def health():
    """Health check: validate GitHub connectivity and permissions"""
    try:
        # Test connectivity
        repo.get_contents(SPECS_PATH)

        # Get rate limit info
        rate_limit = github.get_rate_limit()
        remaining = rate_limit.core.remaining
        limit = rate_limit.core.limit
        reset_timestamp = rate_limit.core.reset.timestamp()

        # D5B: Check workflow scope (best-effort)
        has_workflow_scope = False
        try:
            # Try to list workflows (requires workflow scope)
            workflows = repo.get_workflows()
            has_workflow_scope = workflows.totalCount > 0
        except:
            pass

        return jsonify({
            "status": "healthy",
            "github": "connected",
            "repo": GH_REPO,
            "scopes": {
                "repo": True,  # If we got here, we have repo scope
                "workflow": has_workflow_scope
            },
            "rate_limit": {
                "remaining": remaining,
                "limit": limit,
                "reset_at": int(reset_timestamp)
            }
        })

    except RateLimitExceededException as e:
        # ... existing error handling ...
```

## Architecture (D5B Additions)

```
┌─────────────────────────┐
│   Browser               │
└───────────┬─────────────┘
            │
            └─ POST /deploy                   (D5A → D5B: add workflow trigger)
            │
┌───────────▼─────────────┐
│   Flask App (app.py)    │
│   D5B Additions:        │
│   - workflow.create_    │
│     dispatch()          │
│   - Get run URL         │
│   - GitHub API error    │
│     handling            │
└───────────┬─────────────┘
            │
            ├─ repo.get_workflow('deploy-pod.yml')
            ├─ workflow.create_dispatch(inputs={...})
            └─ workflow.get_runs() → latest URL
            │
┌───────────▼─────────────┐
│   GitHub API            │
│   - Trigger workflow    │
│   - Return run status   │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│   GitHub Actions        │
│   deploy-pod.yml        │
│   - Receives inputs     │
│   - Runs Terraform      │
│   - Updates AWS         │
└─────────────────────────┘
```

## Implementation Punch List

### Workflow Dispatch Integration (4 tasks)
- [ ] Import GithubException and time module
- [ ] Add workflow.get_workflow() call in /deploy
- [ ] Add workflow.create_dispatch() with input mapping
- [ ] Add 2-second delay and get_runs() for URL retrieval

### Error Handling (4 tasks)
- [ ] Handle 403 Forbidden (missing workflow scope)
- [ ] Handle 404 Not Found (workflow file missing)
- [ ] Handle 422 Invalid Inputs (workflow validation failure)
- [ ] Handle generic GithubException gracefully

### Template Updates (2 tasks)
- [ ] Add 'forbidden' and 'api_error' icons to error.html.j2
- [ ] Verify success.html.j2 handles preview_mode=False correctly

### Health Check Update (1 task)
- [ ] Add workflow scope check to /health endpoint

### Testing (8 tasks)
- [ ] Test edit existing pod triggers workflow
- [ ] Test create new pod triggers workflow
- [ ] Test workflow inputs are correct (check GitHub Actions UI)
- [ ] Test action_url is displayed (or fallback link shown)
- [ ] Test 403 error when token lacks workflow scope
- [ ] Test 404 error when workflow file missing
- [ ] Test 422 error when inputs are invalid
- [ ] End-to-end: form → workflow → AWS shows resource

**Total: 19 tasks**

## Validation Criteria

**Must Pass Before Shipping D5B**:

**Workflow Dispatch**:
- [ ] Form submission triggers GitHub Actions workflow
- [ ] Workflow receives correct inputs (verify in Actions UI)
- [ ] Workflow runs successfully (green checkmark)
- [ ] Success page shows action run URL (clickable link)
- [ ] If URL retrieval fails, shows fallback link to Actions tab

**Error Handling**:
- [ ] Missing workflow scope → 403 with "update GH_TOKEN" message
- [ ] Missing workflow file → 404 with helpful error
- [ ] Invalid inputs → 422 with validation message
- [ ] Network errors → 503 with retry suggestion
- [ ] All error pages provide actionable guidance

**Integration**:
- [ ] Workflow creates/updates EC2 instance
- [ ] Terraform apply succeeds in Actions log
- [ ] AWS Console shows updated resource
- [ ] Can verify changes match form inputs
- [ ] Multiple sequential deploys work correctly

**Health Check**:
- [ ] /health endpoint shows workflow scope status
- [ ] Can diagnose permission issues via /health

## Success Metrics

**Quantitative**:
- workflow_dispatch trigger < 2 seconds
- Action run URL retrieved 95%+ of the time
- Zero unhandled exceptions
- All HTTP status codes correct

**Qualitative**:
- Users can monitor deployment progress via action URL
- Error messages clearly explain what went wrong
- GitHub API errors don't crash the app
- Fallback link works when URL retrieval fails

**Customer Value**:
- End-to-end deployment works (form → AWS)
- Can track deployment progress in real-time
- Clear feedback when something fails
- No need to manually trigger workflows

## Dependencies

**Blocked By**:
- D5A must be complete and shipped
- GH_TOKEN must have `workflow` scope
- GitHub Action `deploy-pod.yml` must exist with workflow_dispatch trigger
- Workflow must accept inputs: customer, environment, instance_name, instance_type, waf_enabled

**Blocks**:
- D6 (Docker Packaging) - needs complete app
- D7 (Integration Testing) - needs full deployment working

**Requires**:
- D3 GitHub Actions workflow (already built)
- D5A form UI and validation (dependency)

## Constraints

**GitHub Token Scopes**:
- `repo` - Read/write repository
- `workflow` - **NEW**: Trigger workflow_dispatch

**Workflow Requirements**:
- Must be named `deploy-pod.yml`
- Must have `workflow_dispatch` trigger
- Must accept all 5 inputs as strings
- Must handle both new and existing pods

**API Limitations**:
- workflow.create_dispatch() returns boolean, not run object
- Must query get_runs() separately to get URL
- 2-second delay needed for run to appear
- Latest run may not be the one we triggered (race condition possible)

**Scope Boundaries**:
- No real-time status polling (link to GitHub Actions only)
- No rollback capability (manual via Git/Terraform)
- URL retrieval is best-effort (fallback link if fails)

## Edge Cases Handled

**Workflow Dispatch**:
1. Token lacks workflow scope → 403 error with clear message
2. Workflow file doesn't exist → 404 error with setup help
3. Workflow dispatch succeeds but can't get run URL → Show generic Actions link
4. Multiple rapid dispatches → All queue successfully (GitHub handles)
5. Workflow inputs invalid → 422 error with GitHub's message

**Race Conditions**:
1. Latest run isn't ours (someone else triggered) → User sees wrong URL (acceptable - rare)
2. Run not visible after 2 seconds → Show fallback link (acceptable)

**Network Issues**:
1. GitHub API timeout → 503 error with retry message
2. Rate limit exceeded → Show remaining quota and reset time
3. Repository access denied → Clear error about token permissions

## Next Steps After D5B

1. **Ship D5B** - Complete deployment feature
2. **Verify End-to-End** - Form → Workflow → AWS resource created
3. **Phase D6** - Docker packaging (Dockerfile + compose)
4. **Phase D7** - Scale to 9 pods and integration testing
5. **Demo** - Show complete spec-editor workflow

## Out of Scope (Future Enhancements)

**Real-time status polling**:
- Poll GitHub Actions API for run status
- Show progress bar or status updates
- Notify when deployment completes
- → Can defer to D5C or later

**Improved run URL accuracy**:
- Store dispatch timestamp, match against run start time
- Use workflow run event metadata to confirm match
- → Complex, defer to future

**CSRF protection**:
- Flask-WTF for CSRF tokens
- → Can defer to security hardening phase

**Rollback operations**:
- "Undo" button to revert deployment
- Git revert + Terraform destroy
- → Can defer to advanced features

---

**Specification Status**: Ready for Planning
**Estimated Effort**: 1 hour
**Target PR Size**: ~100 LoC (0 new files, 2 modified files)
**Complexity**: 4/10 (Medium-Low - straightforward API integration)
