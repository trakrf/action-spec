# Implementation Plan: GitHub Action - Workflow Dispatch for Pod Deployment
Generated: 2025-10-23
Specification: spec.md

## Understanding

This feature creates a GitHub Actions workflow that automates OpenTofu-based infrastructure deployment for customer pods. The workflow accepts inputs (customer, environment, instance_name, waf_enabled), updates the corresponding spec.yml file, commits the changes, and runs OpenTofu to deploy the infrastructure.

**Key behaviors**:
- Workflow is manually triggered via GitHub UI or API (workflow_dispatch)
- Updates existing spec.yml with new values before deployment
- Commits spec.yml changes to create audit trail (GitOps pattern)
- Runs OpenTofu init/plan/apply to deploy infrastructure
- Works on any branch (demo from feature branch to avoid main branch protection)
- Fails fast with clear error messages if anything goes wrong

**Design decisions from clarification**:
- Use actions/checkout@v5 to match current repo standards
- Smart error handling - fail fast with clear messages, avoid over-complication
- Direct commit/push to triggering branch (branching strategy deferred to customer)
- PyYAML with error handling + structure validation for safety
- Run `tofu init` every time (simple, reliable, optimize later)
- List required secrets in plan, user will configure them

## Relevant Files

**Reference Patterns** (existing code to follow):
- `.github/workflows/security-scan.yml` (lines 1-76) - Existing workflow structure, uses actions/checkout@v5
- `demo/infra/advworks/dev/spec.yml` (lines 1-14) - Example spec.yml structure to validate against

**Files to Create**:
- `.github/workflows/deploy-pod.yml` - GitHub Actions workflow for pod deployment
  - Implements workflow_dispatch with 4 inputs
  - Python script to update spec.yml with error handling
  - OpenTofu init/plan/apply steps
  - Deployment summary output

**Files to Modify**:
- None (this is a net-new workflow)

## Architecture Impact
- **Subsystems affected**: GitHub Actions, Git (commits), AWS (via OpenTofu)
- **New dependencies**: None (PyYAML pre-installed in GitHub Actions runner, opentofu/setup-opentofu action)
- **Breaking changes**: None (additive feature)

## Task Breakdown

### Task 1: Create workflow file structure
**File**: `.github/workflows/deploy-pod.yml`
**Action**: CREATE
**Pattern**: Reference `.github/workflows/security-scan.yml` structure

**Implementation**:
```yaml
name: Deploy Pod

on:
  workflow_dispatch:
    inputs:
      customer:
        description: 'Customer name'
        required: true
        type: choice
        options:
          - advworks
          - northwind
          - contoso
      environment:
        description: 'Environment'
        required: true
        type: choice
        options:
          - dev
          - stg
          - prd
      instance_name:
        description: 'Instance name (e.g., web1, app1)'
        required: true
        type: string
      waf_enabled:
        description: 'Enable WAF protection'
        required: false
        type: boolean
        default: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write      # Required for committing spec.yml

    env:
      POD_PATH: demo/infra/${{ inputs.customer }}/${{ inputs.environment }}
      SPEC_FILE: demo/infra/${{ inputs.customer }}/${{ inputs.environment }}/spec.yml
```

**Validation**:
- File exists at `.github/workflows/deploy-pod.yml`
- YAML is valid (no syntax errors)
- Contains all 4 required inputs with correct types

---

### Task 2: Add checkout and Python setup steps
**File**: `.github/workflows/deploy-pod.yml`
**Action**: MODIFY (append to jobs.deploy.steps)
**Pattern**: Use actions/checkout@v5 like security-scan.yml

**Implementation**:
```yaml
    steps:
      - name: Checkout code
        uses: actions/checkout@v5
        with:
          fetch-depth: 0  # Full history for clean commits

      - name: Setup Python for YAML processing
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install PyYAML
        run: pip install pyyaml
```

**Validation**:
- Checkout step uses @v5
- Python version specified (3.12)
- PyYAML installation step present

---

### Task 3: Add spec.yml update script with error handling
**File**: `.github/workflows/deploy-pod.yml`
**Action**: MODIFY (append to jobs.deploy.steps)
**Pattern**: Python inline script with try/except and structure validation

**Implementation**:
```yaml
      - name: Update spec.yml
        run: |
          python3 << 'EOF'
          import yaml
          import sys
          import os

          spec_file = os.environ['SPEC_FILE']
          instance_name = '${{ inputs.instance_name }}'
          waf_enabled = '${{ inputs.waf_enabled }}'

          # Convert string boolean to Python boolean
          waf_enabled_bool = waf_enabled.lower() == 'true'

          try:
              # Read existing spec
              with open(spec_file, 'r') as f:
                  spec = yaml.safe_load(f)

              # Validate structure
              if not spec or 'spec' not in spec:
                  print(f"❌ ERROR: Invalid spec.yml structure - missing 'spec' key")
                  sys.exit(1)

              if 'compute' not in spec['spec']:
                  print(f"❌ ERROR: Invalid spec.yml structure - missing 'spec.compute' key")
                  sys.exit(1)

              if 'security' not in spec['spec'] or 'waf' not in spec['spec']['security']:
                  print(f"❌ ERROR: Invalid spec.yml structure - missing 'spec.security.waf' key")
                  sys.exit(1)

              # Update fields from workflow inputs
              spec['spec']['compute']['instance_name'] = instance_name
              spec['spec']['security']['waf']['enabled'] = waf_enabled_bool

              # Write updated spec
              with open(spec_file, 'w') as f:
                  yaml.dump(spec, f, default_flow_style=False, sort_keys=False)

              print(f"✅ Updated spec.yml:")
              print(f"   instance_name: {instance_name}")
              print(f"   waf.enabled: {waf_enabled_bool}")

          except FileNotFoundError:
              print(f"❌ ERROR: spec.yml not found at {spec_file}")
              print(f"   Valid combinations: advworks/dev, advworks/stg, advworks/prd, northwind/dev, northwind/prd, contoso/dev")
              sys.exit(1)
          except yaml.YAMLError as e:
              print(f"❌ ERROR: Failed to parse YAML: {e}")
              sys.exit(1)
          except Exception as e:
              print(f"❌ ERROR: Unexpected error updating spec.yml: {e}")
              sys.exit(1)
          EOF
```

**Validation**:
- Script handles FileNotFoundError with helpful message
- Script validates spec.yml structure before updating
- Script converts boolean string to Python bool correctly
- Script prints clear success/error messages

---

### Task 4: Add git commit step with idempotency
**File**: `.github/workflows/deploy-pod.yml`
**Action**: MODIFY (append to jobs.deploy.steps)
**Pattern**: Standard git commit flow with diff check

**Implementation**:
```yaml
      - name: Commit spec.yml
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add ${{ env.SPEC_FILE }}

          # Only commit if there are changes
          if git diff --staged --quiet; then
            echo "✅ No changes to spec.yml, skipping commit"
          else
            git commit -m "deploy: Update ${{ inputs.customer }}/${{ inputs.environment }} - instance=${{ inputs.instance_name }}, waf=${{ inputs.waf_enabled }}"
            git push
            echo "✅ Committed and pushed spec.yml changes"
          fi
```

**Validation**:
- Git config sets bot user/email
- Checks for changes before committing (idempotent)
- Commit message includes all relevant details
- Pushes to current branch

---

### Task 5: Add AWS credentials and OpenTofu setup
**File**: `.github/workflows/deploy-pod.yml`
**Action**: MODIFY (append to jobs.deploy.steps)
**Pattern**: Standard AWS credentials action + OpenTofu setup

**Implementation**:
```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION || 'us-east-2' }}

      - name: Setup OpenTofu
        uses: opentofu/setup-opentofu@v1
        with:
          tofu_version: 1.8.0
```

**Validation**:
- AWS credentials action uses @v4
- Region defaults to us-east-2 if not set
- OpenTofu version pinned to 1.8.0

---

### Task 6: Add OpenTofu init/plan/apply steps
**File**: `.github/workflows/deploy-pod.yml`
**Action**: MODIFY (append to jobs.deploy.steps)
**Pattern**: Standard OpenTofu workflow

**Implementation**:
```yaml
      - name: OpenTofu Init
        working-directory: ${{ env.POD_PATH }}
        run: tofu init

      - name: OpenTofu Plan
        working-directory: ${{ env.POD_PATH }}
        run: tofu plan -out=tfplan

      - name: OpenTofu Apply
        working-directory: ${{ env.POD_PATH }}
        run: tofu apply -auto-approve tfplan
```

**Validation**:
- All steps use working-directory env var
- Plan saves to tfplan file
- Apply uses saved plan with auto-approve

---

### Task 7: Add deployment summary output
**File**: `.github/workflows/deploy-pod.yml`
**Action**: MODIFY (append to jobs.deploy.steps)
**Pattern**: GitHub Actions step summary

**Implementation**:
```yaml
      - name: Output deployment info
        if: success()
        working-directory: ${{ env.POD_PATH }}
        run: |
          echo "### Deployment Complete! :rocket:" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Customer:** ${{ inputs.customer }}" >> $GITHUB_STEP_SUMMARY
          echo "**Environment:** ${{ inputs.environment }}" >> $GITHUB_STEP_SUMMARY
          echo "**Instance Name:** ${{ inputs.instance_name }}" >> $GITHUB_STEP_SUMMARY
          echo "**WAF Enabled:** ${{ inputs.waf_enabled }}" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY

          # Show OpenTofu outputs if available
          if tofu output -json > /tmp/tf_output.json 2>/dev/null; then
            echo "**OpenTofu Outputs:**" >> $GITHUB_STEP_SUMMARY
            echo '```json' >> $GITHUB_STEP_SUMMARY
            cat /tmp/tf_output.json >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
          fi
```

**Validation**:
- Only runs on success
- Shows all input parameters
- Gracefully handles missing OpenTofu outputs

---

## Risk Assessment

**Risk**: Invalid customer/environment combination causes workflow to fail
- **Mitigation**: Python script validates file exists and provides helpful error message listing valid combinations

**Risk**: AWS credentials not configured or incorrect
- **Mitigation**: AWS action will fail fast with clear error; document required secrets in plan

**Risk**: OpenTofu state locking conflicts if multiple deployments run simultaneously
- **Mitigation**: S3 backend (from Phase D1) has DynamoDB locking; workflow will wait or fail with lock error

**Risk**: Git push fails due to branch protection or conflicts
- **Mitigation**: Demo from feature branch to avoid main protection; conflicts unlikely since spec.yml is pod-specific

**Risk**: PyYAML formatting differences cause unexpected spec.yml changes
- **Mitigation**: Using `sort_keys=False` preserves order; acceptable tradeoff for MVP

## Integration Points

**GitHub Secrets** (required configuration):
- `AWS_ACCESS_KEY_ID` - AWS access key for OpenTofu
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for OpenTofu
- `AWS_REGION` - AWS region (optional, defaults to us-east-2)

**Git Integration**:
- Commits to current branch with descriptive message
- Uses github-actions[bot] as committer
- Creates audit trail of all deployments

**OpenTofu Integration**:
- Expects S3 backend configured (from Phase D1)
- Uses existing pod modules at `demo/tfmodules/pod/`
- Works with spec.yml structure from Phases D1-D2

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

Since this is a GitHub Actions workflow (not application code), validation is different:

**After creating the workflow**:
1. **YAML Syntax**: Validate YAML is well-formed
   ```bash
   # Use GitHub's workflow validator or yamllint
   yamllint .github/workflows/deploy-pod.yml
   ```

2. **Workflow Integrity**: Check workflow is recognized by GitHub
   ```bash
   # Push workflow and check Actions tab
   git add .github/workflows/deploy-pod.yml
   git commit -m "feat(demo): add workflow_dispatch for pod deployment"
   git push
   # Navigate to Actions tab - workflow should appear in left sidebar
   ```

3. **Manual Test**: Trigger workflow from GitHub UI
   - Navigate to Actions → Deploy Pod
   - Click "Run workflow"
   - Fill inputs: `advworks`, `dev`, `web1`, `false`
   - Verify workflow completes successfully

4. **Verify Behavior**: Check all expected outcomes
   ```bash
   # Check spec.yml was updated
   git pull
   cat demo/infra/advworks/dev/spec.yml
   # Should show instance_name: web1, waf.enabled: false

   # Check git log
   git log --oneline -1
   # Should show: deploy: Update advworks/dev - instance=web1, waf=false
   ```

**Enforcement Rules**:
- If workflow YAML is invalid → Fix syntax errors
- If workflow doesn't appear in Actions → Check YAML structure and permissions
- If workflow fails → Read error messages, fix issue, re-trigger
- After 3 failed attempts → Stop and review plan

**Do not proceed to next task until current task passes validation.**

## Validation Sequence

**Per-Task Validation**:
- Task 1-7: Check YAML syntax after each addition
- Tasks 1-7: Verify no syntax errors with `yamllint` or GitHub's validator

**Final Validation**:
1. Push workflow to feature branch
2. Verify workflow appears in Actions tab
3. Trigger workflow manually with test inputs
4. Verify all steps complete successfully
5. Verify spec.yml updated and committed
6. Verify infrastructure deployed (check AWS Console or outputs)

**Success Criteria** (from spec):
- [ ] Workflow file exists: `.github/workflows/deploy-pod.yml`
- [ ] Manual trigger from GitHub UI works end-to-end
- [ ] All 4 inputs accepted and validated
- [ ] spec.yml fetched, updated, committed successfully
- [ ] OpenTofu init/plan/apply run successfully
- [ ] Infrastructure deployed matches workflow inputs
- [ ] Git history shows deployment commits
- [ ] Clear error messages on failure

## Plan Quality Assessment

**Complexity Score**: 3/10 (LOW)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ Similar workflow patterns found in codebase (security-scan.yml)
- ✅ All clarifying questions answered
- ✅ Existing spec.yml structure to validate against (demo/infra/advworks/dev/spec.yml)
- ✅ Standard GitHub Actions patterns (workflow_dispatch is well-documented)
- ✅ OpenTofu setup action available (opentofu/setup-opentofu@v1)
- ⚠️ AWS credentials must be pre-configured (user dependency)
- ⚠️ First workflow_dispatch in this repo (no existing reference)

**Assessment**: High confidence implementation. Workflow structure is straightforward, error handling is smart but not over-complicated, and validation strategy is clear. Main risk is AWS credentials configuration, which is user-managed.

**Estimated one-pass success probability**: 85%

**Reasoning**: Standard GitHub Actions patterns with good error handling. The main unknowns are AWS credentials configuration and OpenTofu integration, but both have clear failure modes. Python script is simple with good validation. Most likely issues will be minor syntax errors or credential configuration, both easily fixed.

## Setup Required Before Testing

**GitHub Secrets** (user must configure):
```
Repository Settings → Secrets and variables → Actions → New repository secret

Required:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY

Optional (defaults to us-east-2):
- AWS_REGION
```

**Verify Pre-requisites**:
- [ ] Phase D1 complete: `demo/infra/advworks/dev/` exists with spec.yml and OpenTofu config
- [ ] Phase D2 complete: ALB and WAF modules exist in `demo/tfmodules/pod/`
- [ ] S3 backend configured for OpenTofu state
- [ ] AWS credentials have permissions to create EC2, ALB, WAF resources

## Testing Strategy

**Test Sequence**:
1. **Baseline test**: Deploy advworks/dev with existing values (should be idempotent)
   - Inputs: `advworks`, `dev`, `web1`, `false`
   - Expected: No spec.yml changes, OpenTofu shows no changes

2. **Update test**: Change instance name
   - Inputs: `advworks`, `dev`, `app1`, `false`
   - Expected: spec.yml updated, new EC2 instance deployed

3. **WAF toggle test**: Enable WAF
   - Inputs: `advworks`, `dev`, `app1`, `true`
   - Expected: spec.yml updated, WAF created and attached to ALB

4. **Error handling test**: Try invalid combination
   - Inputs: `contoso`, `prd`, `test1`, `false`
   - Expected: Workflow fails with helpful error (file not found)

**Validation per test**:
- Check GitHub Actions workflow status
- Check spec.yml changes in git log
- Check AWS Console for infrastructure changes
- Verify error messages are clear and helpful
