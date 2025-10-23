# Feature: GitHub Action - Workflow Dispatch for Pod Deployment

## Origin
This specification is Phase D3 of the spec-editor demo implementation. Following successful completion of Phase D2 (ALB + Conditional WAF), we now need to automate infrastructure deployment via GitHub Actions to enable the spec-editor UI to programmatically deploy customer pods.

## Outcome
Customers can deploy infrastructure pods via GitHub UI or API (workflow_dispatch) instead of manually running OpenTofu locally. The spec-editor Flask app will use this workflow to deploy infrastructure when users submit the form.

## User Story
As an **infrastructure operator**
I want to **trigger pod deployments via GitHub Actions**
So that **I can automate deployments from the spec-editor UI without requiring local Terraform access**

## Context

**Discovery**: Phases D1-D2 established the OpenTofu module pattern and infrastructure components (EC2, ALB, WAF). Now we need programmatic deployment.

**Current State**:
- OpenTofu modules work locally: `demo/tfmodules/pod/`
- One pod exists: `demo/infra/advworks/dev/`
- Manual workflow: `cd demo/infra/advworks/dev && tofu apply`

**Desired State**:
- GitHub Action that accepts inputs: `customer`, `environment`, `instance_name`, `waf_enabled`
- Workflow fetches existing spec.yml, updates it with input values, commits changes
- Workflow runs tofu plan/apply for the specified pod
- Flask app (Phase D5) can trigger deployments via GitHub API
- Users can also manually trigger from GitHub UI for testing

## Technical Requirements

### Workflow Inputs
- `customer` (string, required): Customer name (e.g., `advworks`, `northwind`, `contoso`)
- `environment` (string, required): Environment (e.g., `dev`, `stg`, `prd`)
- `instance_name` (string, required): User-friendly instance name (e.g., `web1`, `app1`)
- `waf_enabled` (boolean, default: false): Enable WAF protection on ALB

### Workflow Behavior
1. **Checkout code**: Get latest repository state
2. **Fetch existing spec.yml**: Read from `demo/infra/{customer}/{environment}/spec.yml`
3. **Update spec.yml**: Merge input values into existing spec
   - Update `spec.compute.instance_name` from workflow input
   - Update `spec.security.waf.enabled` from workflow input
   - Preserve all other fields (tags, instance_type, etc.)
4. **Commit spec.yml**: Push updated spec back to repo
   - Creates audit trail of changes
   - Enables GitOps pattern
   - Commit message: `deploy: Update {customer}/{environment} - instance={instance_name}, waf={waf_enabled}`
5. **Configure AWS credentials**: Use GitHub secrets (KISS approach)
6. **Run OpenTofu**:
   - `cd demo/infra/{customer}/{environment}`
   - `tofu init`
   - `tofu plan -out=tfplan`
   - `tofu apply tfplan`

### Security & Permissions
- AWS credentials via GitHub repository secrets:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_REGION` (default: us-east-2)
- OpenTofu state in S3 (already configured in Phase D1)
- Workflow requires `contents: write` permission for committing spec.yml

### Error Handling
- OpenTofu plan failures → annotate workflow run, fail fast
- Apply failures → preserve state, report error with context
- Invalid inputs → fail fast with clear message
- YAML parsing errors → report and exit
- Git commit conflicts → fail and notify (manual resolution needed)

## Implementation Details

### Workflow File Structure
```yaml
# .github/workflows/deploy-pod.yml
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
      contents: write      # For committing spec.yml

    env:
      POD_PATH: demo/infra/${{ inputs.customer }}/${{ inputs.environment }}
      SPEC_FILE: demo/infra/${{ inputs.customer }}/${{ inputs.environment }}/spec.yml

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python for YAML processing
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install PyYAML
        run: pip install pyyaml

      - name: Update spec.yml
        run: |
          python3 << 'EOF'
          import yaml

          # Read existing spec
          with open('${{ env.SPEC_FILE }}', 'r') as f:
              spec = yaml.safe_load(f)

          # Update fields from workflow inputs
          spec['spec']['compute']['instance_name'] = '${{ inputs.instance_name }}'
          spec['spec']['security']['waf']['enabled'] = ${{ inputs.waf_enabled }}

          # Write updated spec
          with open('${{ env.SPEC_FILE }}', 'w') as f:
              yaml.dump(spec, f, default_flow_style=False, sort_keys=False)

          print("Updated spec.yml:")
          print(yaml.dump(spec, default_flow_style=False, sort_keys=False))
          EOF

      - name: Commit spec.yml
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add ${{ env.SPEC_FILE }}

          # Only commit if there are changes
          if git diff --staged --quiet; then
            echo "No changes to spec.yml, skipping commit"
          else
            git commit -m "deploy: Update ${{ inputs.customer }}/${{ inputs.environment }} - instance=${{ inputs.instance_name }}, waf=${{ inputs.waf_enabled }}"
            git push
          fi

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

      - name: OpenTofu Init
        working-directory: ${{ env.POD_PATH }}
        run: tofu init

      - name: OpenTofu Plan
        working-directory: ${{ env.POD_PATH }}
        run: tofu plan -out=tfplan

      - name: OpenTofu Apply
        working-directory: ${{ env.POD_PATH }}
        run: tofu apply -auto-approve tfplan

      - name: Output deployment info
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
          tofu output -json > /tmp/tf_output.json || echo "{}"
          echo "**OpenTofu Outputs:**" >> $GITHUB_STEP_SUMMARY
          echo '```json' >> $GITHUB_STEP_SUMMARY
          cat /tmp/tf_output.json >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
```

### YAML Update Strategy
- Use Python with PyYAML (included in GitHub Actions runner)
- Preserve existing structure and fields
- Only update specific paths:
  - `spec.compute.instance_name`
  - `spec.security.waf.enabled`
- Maintains comments if we switch to `ruamel.yaml` later (future enhancement)

## Validation Criteria

### Manual Testing (GitHub UI)
- [ ] Navigate to Actions tab → Deploy Pod workflow
- [ ] Click "Run workflow"
- [ ] Fill inputs: `advworks`, `dev`, `app1`, `true` (enable WAF)
- [ ] Workflow completes successfully
- [ ] spec.yml committed with updated values
- [ ] Git log shows commit: `deploy: Update advworks/dev - instance=app1, waf=true`
- [ ] AWS Console shows EC2 instance: `advworks-dev-app1`
- [ ] ALB exists with WAF association
- [ ] Instance is accessible via ALB DNS (http-echo responds)

### Automated Testing (gh CLI)
```bash
# Trigger via CLI
gh workflow run deploy-pod.yml \
  -f customer=advworks \
  -f environment=dev \
  -f instance_name=app1 \
  -f waf_enabled=true

# Wait for completion
gh run watch

# Verify spec.yml was updated
git pull
grep 'instance_name: app1' demo/infra/advworks/dev/spec.yml
grep 'enabled: true' demo/infra/advworks/dev/spec.yml

# Verify infrastructure
INSTANCE_NAME=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=advworks-dev-app1" \
  --query 'Reservations[0].Instances[0].Tags[?Key==`Name`].Value' \
  --output text)

echo "Instance name: $INSTANCE_NAME"
# Should equal: advworks-dev-app1
```

### Edge Cases to Test
- [ ] No changes (re-deploy with same values) → should skip commit
- [ ] Toggle WAF: false → true → false (verify idempotency)
- [ ] Change instance name twice in succession (verify state updates)
- [ ] Invalid customer/environment combo → should fail gracefully

## Success Criteria

**Phase D3 is complete when**:
- [ ] Workflow file exists: `.github/workflows/deploy-pod.yml`
- [ ] Manual trigger from GitHub UI works end-to-end
- [ ] All 4 inputs accepted and validated
- [ ] spec.yml fetched, updated, committed successfully
- [ ] OpenTofu init/plan/apply run successfully
- [ ] Infrastructure deployed matches workflow inputs
- [ ] Git history shows deployment commits
- [ ] Workflow can be called via GitHub API (tested with `gh` CLI)
- [ ] Clear error messages on failure (YAML parse, OpenTofu, AWS auth)

**Acceptance Test**:
```bash
# Starting state: advworks/dev has instance_name=web1, waf=false
# Trigger workflow: instance_name=app1, waf=true
# Expected results:
# 1. Commit appears in git log
# 2. spec.yml contains new values
# 3. AWS shows advworks-dev-app1 with WAF
# 4. http-echo accessible via ALB
```

## Dependencies

**Requires**:
- ✅ Phase D1: OpenTofu modules and spec.yml structure
- ✅ Phase D2: ALB + WAF modules
- ⚠️ AWS credentials configured as GitHub secrets:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_REGION` (optional, defaults to us-east-2)
- ✅ S3 backend for OpenTofu state

**Enables**:
- Phase D4: Flask app can discover pods via GitHub API
- Phase D5: Flask app can trigger deployments via this workflow

## Decisions Made

1. **AWS Authentication**: Using GitHub secrets (KISS approach)
   - Simpler than OIDC for MVP
   - Can migrate to OIDC later if needed

2. **spec.yml Update Strategy**: Full implementation
   - Fetch existing spec.yml
   - Update specific fields with PyYAML
   - Commit changes back to repo
   - Creates audit trail and GitOps workflow

3. **Commit Behavior**: Always commit when changes detected
   - Skip commit if no changes (idempotent)
   - Use descriptive commit message with deployment details

4. **Error Handling**: Fail fast with context
   - YAML parsing errors → show file path and error
   - OpenTofu failures → show plan/apply output
   - Git conflicts → fail and notify (manual resolution)

## Out of Scope for D3

Deferred to later phases or future work:
- [ ] OpenTofu plan PR comments (nice-to-have for visibility)
- [ ] Multi-region support (MVP uses us-east-2 only)
- [ ] OpenTofu state locking UI (rely on S3 DynamoDB backend)
- [ ] Parallel pod deployments (one at a time for MVP)
- [ ] OIDC authentication (secrets sufficient for now)
- [ ] Preserve YAML comments (PyYAML doesn't support, would need ruamel.yaml)
- [ ] Rollback on failure (operator can revert git commit manually)

## Implementation Notes

**File Location**: `.github/workflows/deploy-pod.yml`

**Estimated Effort**: 1-2 hours
- 30 min: Write workflow YAML
- 15 min: Add AWS secrets to GitHub
- 30 min: Test YAML update logic (Python script)
- 30 min: Test full workflow end-to-end
- 15 min: Verify commit and infrastructure

**Testing Strategy**:
1. Start with `advworks/dev` (known-good pod from D1)
2. Test with WAF disabled first (simpler, verifies basic flow)
3. Test with WAF enabled (verify Phase D2 integration)
4. Test changing instance_name (verify spec.yml updates)
5. Test re-running same inputs (verify idempotency)

**OpenTofu Version**: Using 1.8.0 (latest stable as of spec creation)

**Setup Steps**:
```bash
# Add AWS credentials to GitHub secrets
# Settings → Secrets and variables → Actions → New repository secret
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_REGION (optional)
```

## References

- Main spec: `demo/SPEC.md` (Phase D3 section: lines 471-495)
- OpenTofu modules: `demo/tfmodules/pod/`
- Example pod: `demo/infra/advworks/dev/`
- GitHub Actions docs: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch
- OpenTofu docs: https://opentofu.org/docs/
- setup-opentofu action: https://github.com/opentofu/setup-opentofu
- PyYAML docs: https://pyyaml.org/wiki/PyYAMLDocumentation
