# Implementation Plan: GitHub Actions Workflow Integration (Demo Phase D5B)
Generated: 2025-10-24
Specification: spec.md

## Understanding

This phase completes the deployment feature by wiring up GitHub Actions workflow_dispatch integration. D5A built the complete form UI with validation and preview mode. D5B replaces the preview mode with actual workflow triggering, enabling end-to-end deployments from form submission to AWS infrastructure updates.

**Key Design Decisions from Clarifying Questions**:
- Check current imports, only add GithubException if missing (it is - needs adding)
- Use 2-second delay for run URL retrieval (simple, acceptable for demo)
- Health check returns 200 OK with scope info (informational, not critical)
- Generic exception handler sufficient for unexpected errors (logs for debugging)
- Add fallback link to Actions tab when action_url is None (POLS for users)

**Architecture**: This is a demo Flask app building on D5A. Manual browser testing required. The workflow_dispatch API integration is straightforward - the main work is comprehensive error handling.

## Relevant Files

**Reference Patterns** (existing code to follow):
- `demo/backend/app.py` (lines 8, 312-399) - Current imports and POST /deploy route structure
- `demo/backend/app.py` (lines 401-438) - Health check pattern for adding scope check
- `demo/backend/app.py` (lines 230-248, 260-277) - Error handling patterns with render_template
- `demo/backend/templates/success.html.j2` (lines 90-100) - action_url display logic
- `demo/backend/templates/error.html.j2` (lines 22-34) - Error icon conditionals

**Files to Create**:
- None (all modifications to existing files)

**Files to Modify**:
- `demo/backend/app.py` (~90 LoC additions/changes):
  - Add GithubException to imports (line 8)
  - Replace preview mode with workflow_dispatch in /deploy route (lines 353-369)
  - Add workflow scope check to /health endpoint (lines 413-423)
- `demo/backend/templates/error.html.j2` (~6 LoC addition):
  - Add forbidden and api_error icons (after line 31)
- `demo/backend/templates/success.html.j2` (~10 LoC addition):
  - Add fallback link when action_url is None (lines 92-96)

## Architecture Impact

- **Subsystems affected**: Flask backend (GitHub API integration)
- **New dependencies**: None (using existing PyGithub library)
- **Breaking changes**: None (purely additive - preview mode still works if workflow fails)

## Task Breakdown

### Task 1: Add GithubException Import
**File**: `demo/backend/app.py`
**Action**: MODIFY
**Pattern**: Existing import at line 8

**Implementation**:
Change line 8 from:
```python
from github.GithubException import BadCredentialsException, RateLimitExceededException
```

To:
```python
from github.GithubException import BadCredentialsException, RateLimitExceededException, GithubException
```

**Validation**: Start Flask (`python3 app.py`), no import errors.

---

### Task 2: Replace Preview Mode with Workflow Dispatch in /deploy Route
**File**: `demo/backend/app.py`
**Action**: MODIFY
**Pattern**: Lines 353-369 (current preview implementation)

**Implementation**:

Replace lines 353-369 (from "# D5A: Preview deployment inputs" through the return statement) with:

```python
        # D5B: Trigger workflow_dispatch
        workflow_file = 'deploy-pod.yml'

        # Get workflow object
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
            'waf_enabled': str(waf_enabled).lower()
        }

        logger.info(f"Triggering workflow_dispatch for {customer}/{env} with inputs: {workflow_inputs}")

        # Trigger workflow dispatch
        try:
            success = workflow.create_dispatch(
                ref='main',
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
```

**Validation**: Visit `/pod/advworks/dev`, submit form, check Flask logs for "Triggering workflow_dispatch".

---

### Task 3: Add GithubException Handler to Exception Chain
**File**: `demo/backend/app.py`
**Action**: MODIFY
**Pattern**: Exception handlers at lines 371-399

**Implementation**:

Add between the KeyError handler (line 389) and the generic Exception handler (line 391):

```python
    except GithubException as e:
        # GitHub API error (not caught by specific handlers above)
        logger.error(f"GitHub API error: {e}")
        return render_template('error.html.j2',
            error_type="api_error",
            error_title="GitHub API Error",
            error_message=f"Failed to trigger deployment: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}",
            show_pods=False,
            pods=[]), 503
```

**Note**: This catches GithubException errors that weren't caught by the specific 403/404/422 handlers in the workflow_dispatch try block.

**Validation**: All error paths should render appropriate error pages.

---

### Task 4: Add Workflow Scope Check to /health Endpoint
**File**: `demo/backend/app.py`
**Action**: MODIFY
**Pattern**: Health endpoint at lines 401-438

**Implementation**:

Insert after line 412 (after getting rate limit, before the return statement):

```python
        # D5B: Check workflow scope (best-effort)
        has_workflow_scope = False
        try:
            # Try to list workflows (requires workflow scope)
            workflows = repo.get_workflows()
            has_workflow_scope = workflows.totalCount > 0
        except:
            pass
```

Then update the return statement (line 414) to include scope info:

```python
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
```

**Validation**: Visit `/health`, check JSON includes `scopes` object with `workflow: true/false`.

---

### Task 5: Add Forbidden and API Error Icons to error.html.j2
**File**: `demo/backend/templates/error.html.j2`
**Action**: MODIFY
**Pattern**: Error icon conditionals at lines 22-34

**Implementation**:

Add after the `conflict` error type (line 27), before `server_error`:

```jinja2
                    {% elif error_type == 'forbidden' %}
                    <div class="text-6xl mb-4">🔒</div>
                    {% elif error_type == 'api_error' %}
                    <div class="text-6xl mb-4">🔌</div>
```

**Validation**: Trigger 403 error (remove workflow scope), should show 🔒 icon.

---

### Task 6: Add Fallback Link to success.html.j2
**File**: `demo/backend/templates/success.html.j2`
**Action**: MODIFY
**Pattern**: Action URL display at lines 90-100

**Implementation**:

Replace lines 92-96 (the `{% if action_url %}` block) with:

```jinja2
                {% if action_url %}
                    <p class="mb-4">
                        View progress: <a href="{{ action_url }}" target="_blank" class="text-blue-600 hover:underline font-medium">GitHub Actions Run →</a>
                    </p>
                {% else %}
                    <p class="mb-4">
                        View progress: <a href="https://github.com/trakrf/action-spec/actions" target="_blank" class="text-blue-600 hover:underline font-medium">GitHub Actions Tab →</a>
                    </p>
                    <p class="text-sm text-gray-500 mb-4">
                        (Could not retrieve specific run URL - check the Actions tab for the latest run)
                    </p>
                {% endif %}
```

**Validation**: Submit form, success page should show either specific run URL or fallback Actions link.

---

## Risk Assessment

**Risk: Workflow dispatch succeeds but URL retrieval fails (race condition)**
- **Likelihood**: Low-Medium
- **Impact**: Low (user sees fallback link, can still find run)
- **Mitigation**: 2-second delay helps, fallback link ensures users can always check status

**Risk: Missing workflow scope causes all deployments to fail**
- **Likelihood**: Medium (easy to forget scope during setup)
- **Impact**: High (complete feature failure)
- **Mitigation**: Health check shows scope status, 403 error has clear "update GH_TOKEN" message

**Risk: Workflow file renamed or deleted**
- **Likelihood**: Very Low (stable file in repo)
- **Impact**: Medium (all deployments fail)
- **Mitigation**: 404 error with clear message about checking .github/workflows/

**Risk: Multiple rapid submissions get wrong run URL**
- **Likelihood**: Low (rare in demo usage)
- **Impact**: Low (user sees wrong run, but deployment still works)
- **Mitigation**: Acceptable for demo scope, documented in spec as known limitation

**Risk: GitHub API rate limiting**
- **Likelihood**: Very Low (demo usage well under limits)
- **Impact**: Medium (deployments blocked temporarily)
- **Mitigation**: Existing rate limit handler shows reset time

## Integration Points

**GitHub API Calls**:
- `repo.get_workflow(workflow_file)` - Get workflow object
- `workflow.create_dispatch(ref, inputs)` - Trigger workflow_dispatch
- `workflow.get_runs(branch)` - Get recent runs for URL retrieval
- `repo.get_workflows()` - Check workflow scope in health check

**Template Variables**:
- `preview_mode`: False (actual deployment, not preview)
- `action_url`: String URL or None (triggers fallback link logic)
- `deployment_inputs`: Dict passed to workflow_dispatch
- New error types: `forbidden`, `api_error`

**Error Handling Flow**:
1. Validation errors (400) - existing from D5A
2. Workflow not found (404) - new
3. Permission denied (403) - new
4. Invalid inputs (422) - new
5. GitHub API errors (503) - new
6. Generic errors (500) - existing

## VALIDATION GATES (DEMO-SPECIFIC)

**Note**: This is a demo Flask app, not the production Lambda backend. Standard validation gates from `spec/stack.md` (black, mypy, pytest) do NOT apply.

**Demo Validation Approach**: Manual testing via browser + GitHub Actions UI verification

**After Each Task**:
1. Check Flask starts without errors: `python3 demo/backend/app.py`
2. Check console for Python syntax errors
3. Visit affected routes in browser
4. Verify expected behavior

**Manual Test Checklist** (run after all code tasks complete):

### Workflow Dispatch Tests:
- [ ] Submit form for existing pod (edit mode) → workflow triggers
- [ ] Submit form for new pod (create mode) → workflow triggers
- [ ] Check GitHub Actions UI → see run with correct inputs
- [ ] Verify workflow completes successfully (green checkmark)
- [ ] Check AWS Console → resource created/updated

### URL Retrieval Tests:
- [ ] Success page shows action_url link → clicks to correct run
- [ ] If URL fails to retrieve → shows fallback Actions tab link
- [ ] Fallback link goes to repository Actions page

### Error Handling Tests:
- [ ] Remove workflow scope from token → 403 error with "update GH_TOKEN" message
- [ ] Rename workflow file → 404 error with "check .github/workflows" message
- [ ] Invalid workflow inputs (if possible) → 422 error
- [ ] Network issues (disconnect) → 503 error with retry message

### Health Check Tests:
- [ ] Visit /health → JSON includes `scopes.workflow: true`
- [ ] Remove workflow scope → /health shows `scopes.workflow: false`
- [ ] Health check still returns 200 OK (informational)

### End-to-End Test:
- [ ] Form → Workflow → AWS resource created/updated
- [ ] Can track progress via action_url or fallback link
- [ ] Terraform changes visible in workflow logs
- [ ] Resource matches form inputs (instance type, WAF, etc.)

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

**Final Validation** (after Task 6):
1. Restart Flask: `python3 demo/backend/app.py`
2. Run all manual test checklist items above
3. Verify no console errors or warnings
4. Test workflow dispatch end-to-end
5. Verify GitHub Actions workflow completes successfully
6. Check AWS Console for created/updated resources

**Success Criteria**:
- All manual tests pass
- Workflow triggers successfully
- Action URL displayed (or fallback shown)
- No 500 errors
- No Python exceptions in Flask console
- GitHub Actions workflow completes with green checkmark
- AWS resource matches form inputs

## Plan Quality Assessment

**Complexity Score**: 2/10 (LOW)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Building on solid D5A foundation (app.py:312-399)
✅ PyGithub workflow_dispatch API is straightforward
✅ All clarifying questions answered (POLS approach)
✅ Existing error handling patterns to follow (app.py:230-277)
✅ Template structure already supports preview_mode toggle
✅ Workflow file exists and has workflow_dispatch trigger
✅ No new dependencies needed

⚠️ URL retrieval has known race condition (acceptable for demo)

**Assessment**: High confidence implementation. This is a straightforward API integration with well-documented error handling. The main work is adding comprehensive error messages for different failure modes. D5A did the hard work of form validation and UI - D5B just wires up the GitHub API.

**Estimated one-pass success probability**: 90%

**Reasoning**: The PyGithub API is mature and well-documented. The spec provides exact error handling code. The only uncertainty is the 2-second delay for URL retrieval, which may need tuning, but the fallback link ensures users always have a way to check status. The comprehensive error handling covers all likely failure modes (missing scope, missing workflow, invalid inputs, network issues).
