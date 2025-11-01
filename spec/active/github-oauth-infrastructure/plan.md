# Implementation Plan: GitHub OAuth Infrastructure - Production Deployment
Generated: 2025-10-31
Specification: spec.md

## Understanding

This is **Phase 3 of 3** for GitHub OAuth implementation. Backend (Phase 1) and frontend (Phase 2) are complete. This phase deploys OAuth credentials to AWS production environment via Terraform/OpenTofu.

**Key decisions**:
- **Hard cutover**: Remove service account PAT (`GH_TOKEN`) immediately - no dual-auth period
- **Production-only**: Deploy directly to production (POC/demo environment)
- **Manual OAuth registration**: Detailed instructions provided as prerequisite
- **Infrastructure-as-Code**: All changes via Terraform, no manual AWS console changes

**Outcome**: OAuth authentication fully deployed. Users authenticate with GitHub. Service account PAT eliminated.

---

## Relevant Files

**Reference Patterns**:
- `infra/tools/aws/secrets.tf` (lines 1-14) - Existing secret pattern to mirror for OAuth secret
- `infra/tools/aws/variables.tf` (lines 19-24) - Existing sensitive variable pattern
- `infra/tools/aws/iam.tf` (lines 24-40) - Secrets Manager IAM policy to update
- `infra/tools/aws/main.tf` (lines 31-40) - App Runner environment configuration

**Files to Modify**:
1. `infra/tools/aws/providers.tf` - Add `random` provider for Flask secret generation
2. `infra/tools/aws/secrets.tf` - Add OAuth secret, **remove** GH_TOKEN secret
3. `infra/tools/aws/variables.tf` - Add OAuth variables, **remove** github_token variable
4. `infra/tools/aws/main.tf` - Add OAuth env vars, add Flask secret, **remove** GH_TOKEN
5. `infra/tools/aws/iam.tf` - Update secrets policy to reference OAuth secret only

**Files to Create**: None (infrastructure-only changes)

---

## Architecture Impact

**Subsystems affected**:
- Infrastructure (Terraform/AWS): Secrets Manager, App Runner, IAM
- Application (Flask backend): Receives OAuth credentials via environment variables

**New dependencies**:
- `hashicorp/random ~> 3.0` (Terraform provider for generating Flask secret key)

**Breaking changes**:
- **HARD CUTOVER**: Service account PAT removed immediately
- All GitHub operations require user authentication via OAuth
- No fallback to service account token

---

## Task Breakdown

### Task 1: Register GitHub OAuth App (Manual Prerequisite)

**Action**: MANUAL (human prerequisite)

**Steps**:

1. Navigate to https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in registration form:
   - **Application name**: `action-spec`
   - **Homepage URL**: `https://i84mr8vpmd.us-east-2.awsapprunner.com`
   - **Authorization callback URL**: `https://i84mr8vpmd.us-east-2.awsapprunner.com/auth/callback`
   - **Description**: (optional) `"Spec editor OAuth authentication"`

4. Click **"Register application"**

5. On the app details page:
   - Copy **Client ID** (format: `Iv1.1234abcd5678efgh`)
   - Click **"Generate a new client secret"**
   - Copy **Client Secret** immediately (only shown once)

6. Export credentials for Terraform:
   ```bash
   export TF_VAR_github_oauth_client_id="Iv1.YOUR_CLIENT_ID"
   export TF_VAR_github_oauth_client_secret="YOUR_CLIENT_SECRET"
   ```

**Validation**:
- Client ID starts with `Iv1.` or `Iv23.`
- Client Secret is a long hexadecimal string
- Callback URL exactly matches: `https://i84mr8vpmd.us-east-2.awsapprunner.com/auth/callback`
- Environment variables set: `echo $TF_VAR_github_oauth_client_id` returns value

**Critical**: Callback URL mismatch will cause OAuth to fail silently after GitHub authorization.

---

### Task 2: Add Random Provider

**File**: `infra/tools/aws/providers.tf`
**Action**: MODIFY
**Pattern**: Follow existing AWS provider structure (lines 4-9)

**Implementation**:

Add to `required_providers` block:

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {  # ADD THIS BLOCK
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
```

**Why**: Need `random` provider to generate secure Flask secret key for session management.

**Validation**:
```bash
cd infra/tools/aws
tofu init  # Initialize new provider
# Expected: "Initializing provider plugins... random v3.x.x"
```

---

### Task 3: Update Secrets Configuration

**File**: `infra/tools/aws/secrets.tf`
**Action**: MODIFY (add OAuth secret, remove GH_TOKEN)
**Pattern**: Mirror existing `github_token` secret structure (lines 1-14)

**Implementation**:

**REPLACE entire file** with:

```hcl
# OAuth Client Secret (replaces service account PAT)
resource "aws_secretsmanager_secret" "github_oauth_client_secret" {
  name                    = "action-spec/github-oauth-client-secret"
  description             = "GitHub OAuth App client secret for user authentication"
  recovery_window_in_days = 7

  tags = {
    Application = "action-spec"
  }
}

resource "aws_secretsmanager_secret_version" "github_oauth_client_secret" {
  secret_id     = aws_secretsmanager_secret.github_oauth_client_secret.id
  secret_string = var.github_oauth_client_secret
}
```

**What changed**:
- ✅ Added OAuth secret resource
- ❌ **Removed** `github_token` secret and version resources (hard cutover)

**Validation**: None yet (validate in Task 6 after all Terraform changes)

---

### Task 4: Update Variables

**File**: `infra/tools/aws/variables.tf`
**Action**: MODIFY (add OAuth variables, remove github_token)
**Pattern**: Follow existing sensitive variable pattern (lines 19-24)

**Implementation**:

**REPLACE** `github_token` variable (lines 19-24) with OAuth variables:

```hcl
# REMOVE these lines:
# variable "github_token" {
#   description = "GitHub token for API access (loaded from .env.local via TF_VAR_github_token)"
#   type        = string
#   sensitive   = true
# }

# ADD these lines:
variable "github_oauth_client_id" {
  description = "GitHub OAuth App Client ID (public identifier)"
  type        = string
}

variable "github_oauth_client_secret" {
  description = "GitHub OAuth App Client Secret (sensitive)"
  type        = string
  sensitive   = true
}
```

**What changed**:
- ✅ Added `github_oauth_client_id` (public, no sensitive flag)
- ✅ Added `github_oauth_client_secret` (sensitive = true)
- ❌ **Removed** `github_token` variable

**Validation**: None yet (validate in Task 6)

---

### Task 5: Update App Runner Configuration

**File**: `infra/tools/aws/main.tf`
**Action**: MODIFY (add OAuth env vars, Flask secret, remove GH_TOKEN)
**Pattern**: Existing `runtime_environment_variables` block (lines 31-36)

**Implementation**:

**Step 5a**: Add Flask secret key generation resource at **top of file** (before `aws_apprunner_auto_scaling_configuration_version`):

```hcl
# Generate secure Flask secret key for session management
resource "random_password" "flask_secret" {
  length  = 32
  special = true
}
```

**Step 5b**: Update `runtime_environment_variables` (lines 31-36):

```hcl
runtime_environment_variables = {
  AWS_REGION               = var.aws_region
  GH_REPO                  = var.github_repo
  SPECS_PATH               = "infra"
  WORKFLOW_BRANCH          = var.github_branch
  GITHUB_OAUTH_CLIENT_ID   = var.github_oauth_client_id  # ADD
  FLASK_SECRET_KEY         = random_password.flask_secret.result  # ADD
}
```

**Step 5c**: Update `runtime_environment_secrets` (lines 38-40):

```hcl
runtime_environment_secrets = {
  GITHUB_OAUTH_CLIENT_SECRET = aws_secretsmanager_secret.github_oauth_client_secret.arn
  # REMOVE: GH_TOKEN line
}
```

**What changed**:
- ✅ Added `GITHUB_OAUTH_CLIENT_ID` to public env vars
- ✅ Added `FLASK_SECRET_KEY` generated by `random_password` resource
- ✅ Added `GITHUB_OAUTH_CLIENT_SECRET` to secrets (from Secrets Manager)
- ❌ **Removed** `GH_TOKEN` from secrets

**Backend expectations** (from `backend/auth.py:49`):
- `GITHUB_OAUTH_CLIENT_ID` - required for OAuth login redirect
- `GITHUB_OAUTH_CLIENT_SECRET` - required for token exchange
- `FLASK_SECRET_KEY` - required for session signing (from `backend/app.py`)

**Validation**: None yet (validate in Task 6)

---

### Task 6: Update IAM Permissions

**File**: `infra/tools/aws/iam.tf`
**Action**: MODIFY (update secrets policy to OAuth secret only)
**Pattern**: Existing `app_runner_secrets` policy (lines 24-40)

**Implementation**:

Update `Resource` array in `aws_iam_role_policy.app_runner_secrets` (line 36):

```hcl
resource "aws_iam_role_policy" "app_runner_secrets" {
  name = "secrets-manager-access"
  role = aws_iam_role.app_runner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.github_oauth_client_secret.arn  # CHANGE THIS LINE
        # REMOVE: aws_secretsmanager_secret.github_token.arn
      }
    ]
  })
}
```

**What changed**:
- ✅ IAM policy now grants access to OAuth secret
- ❌ **Removed** reference to `github_token` secret (no longer exists)

**Why single resource**: Only one secret now (OAuth client secret). Changed from array `[...]` to single resource.

**Validation**:
```bash
cd infra/tools/aws
tofu validate
# Expected: "Success! The configuration is valid."

tofu plan
# Expected changes summary:
#   - Add: aws_secretsmanager_secret.github_oauth_client_secret
#   - Add: aws_secretsmanager_secret_version.github_oauth_client_secret
#   - Add: random_password.flask_secret
#   - Delete: aws_secretsmanager_secret.github_token
#   - Delete: aws_secretsmanager_secret_version.github_token
#   - Update: aws_apprunner_service.action_spec (env vars changed)
#   - Update: aws_iam_role_policy.app_runner_secrets (resource changed)
```

**Critical checks**:
- No unexpected resource deletions
- App Runner service shows "update in-place" (not "destroy and recreate")
- IAM policy update shows resource change from array to single ARN

---

### Task 7: Deploy to Production

**File**: `infra/tools/aws/` (deployment)
**Action**: EXECUTE
**Pattern**: Standard Terraform workflow

**Implementation**:

```bash
cd infra/tools/aws

# Ensure OAuth credentials are set
echo $TF_VAR_github_oauth_client_id    # Should print Client ID
echo $TF_VAR_github_oauth_client_secret  # Should print Client Secret

# Apply changes
tofu apply
```

**Interactive prompt**:
```
Plan: 3 to add, 2 to change, 2 to destroy.

Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value:
```

Type: `yes`

**Expected output**:
```
aws_secretsmanager_secret.github_oauth_client_secret: Creating...
random_password.flask_secret: Creating...
random_password.flask_secret: Creation complete after 0s [id=...]
aws_secretsmanager_secret.github_oauth_client_secret: Creation complete after 2s [id=...]
aws_secretsmanager_secret_version.github_oauth_client_secret: Creating...
aws_secretsmanager_secret_version.github_oauth_client_secret: Creation complete after 1s [id=...]
aws_iam_role_policy.app_runner_secrets: Modifying... [id=...]
aws_iam_role_policy.app_runner_secrets: Modifications complete after 2s [id=...]
aws_apprunner_service.action_spec: Modifying... [id=...]
aws_apprunner_service.action_spec: Still modifying... [10s elapsed]
aws_apprunner_service.action_spec: Still modifying... [20s elapsed]
...
aws_apprunner_service.action_spec: Modifications complete after 3m42s [id=...]

Apply complete! Resources: 3 added, 2 changed, 2 destroyed.

Outputs:
app_runner_service_url = "https://i84mr8vpmd.us-east-2.awsapprunner.com"
```

**Deployment time**: 3-5 minutes (App Runner redeploys container with new env vars)

**Validation**:
```bash
# Check service status
tofu output app_runner_service_url
# Expected: "https://i84mr8vpmd.us-east-2.awsapprunner.com"

# Wait for deployment to complete
tofu show | grep status
# Wait until: status = "RUNNING"
```

---

### Task 8: Verify OAuth Flow (End-to-End)

**Action**: MANUAL VERIFICATION
**Pattern**: Complete OAuth authorization flow

**Steps**:

1. **Get service URL**:
   ```bash
   SERVICE_URL=$(tofu output -raw app_runner_service_url)
   echo "Visit: $SERVICE_URL"
   ```

2. **Open in browser** (use appropriate command for your OS):
   ```bash
   # macOS:
   open "$SERVICE_URL"

   # Linux:
   xdg-open "$SERVICE_URL"

   # Or manually navigate to: https://i84mr8vpmd.us-east-2.awsapprunner.com
   ```

3. **Test login flow**:
   - [ ] Page loads successfully
   - [ ] Click "Login with GitHub" button (from Phase 2 frontend)
   - [ ] Redirected to `https://github.com/login/oauth/authorize?client_id=...`
   - [ ] GitHub shows authorization prompt for "action-spec" app
   - [ ] Click "Authorize {your-username}"
   - [ ] Redirected back to `https://i84mr8vpmd.us-east-2.awsapprunner.com/auth/callback?code=...`
   - [ ] Finally redirected to app homepage
   - [ ] User menu visible in UI (avatar + username)

4. **Verify session**:
   - [ ] User avatar displayed
   - [ ] Username displayed
   - [ ] Refresh page - still authenticated (session persists)

5. **Test logout**:
   - [ ] Click "Logout" button
   - [ ] Redirected to logged-out state
   - [ ] User menu disappears
   - [ ] Login button visible again

6. **API verification**:
   ```bash
   # Health check (should work)
   curl "$SERVICE_URL/health"
   # Expected: {"status": "healthy", ...}

   # Unauthenticated API call (should fail or redirect)
   curl "$SERVICE_URL/api/auth/user"
   # Expected: 401 Unauthorized or redirect response
   ```

**Validation**: All checkboxes above must pass.

**If OAuth fails**:
- Check CloudWatch Logs: `aws logs tail /aws/apprunner/action-spec/service --follow`
- Common issues:
  - Callback URL mismatch → Check GitHub OAuth app settings
  - Missing env vars → Check `tofu show | grep GITHUB_OAUTH`
  - Session not persisting → Check `FLASK_SECRET_KEY` is set
  - 500 errors → Check CloudWatch for Python exceptions

---

### Task 9: Verify Production Cutover

**Action**: VERIFY
**Pattern**: Confirm old service account PAT fully removed

**Verification checklist**:

1. **Secrets Manager cleanup**:
   ```bash
   # Check if old secret still exists (should NOT exist)
   aws secretsmanager describe-secret \
     --secret-id action-spec/github-token \
     --region us-east-2
   # Expected: ResourceNotFoundException
   ```

2. **App Runner environment**:
   ```bash
   # Verify GH_TOKEN not in environment
   tofu show | grep GH_TOKEN
   # Expected: No results (only GITHUB_OAUTH_CLIENT_SECRET should exist)

   # Verify OAuth vars present
   tofu show | grep GITHUB_OAUTH
   # Expected:
   #   GITHUB_OAUTH_CLIENT_ID = "Iv1...."
   #   GITHUB_OAUTH_CLIENT_SECRET = arn:aws:secretsmanager:...
   ```

3. **IAM policy**:
   ```bash
   # Verify IAM only references OAuth secret
   tofu show | grep secretsmanager
   # Expected: Only oauth-client-secret ARN, no github-token ARN
   ```

4. **CloudWatch Logs** (no errors):
   ```bash
   # Check recent logs for errors
   aws logs tail /aws/apprunner/action-spec/service \
     --since 5m \
     --filter-pattern "ERROR"
   # Expected: No ERROR lines related to missing GH_TOKEN
   ```

**Validation**: All checks pass. Old PAT completely eliminated. OAuth is the only authentication method.

---

## Risk Assessment

### Risk: Callback URL Mismatch
**Description**: GitHub OAuth app callback URL doesn't match production URL
**Impact**: OAuth fails silently after GitHub authorization (user sees error page)
**Mitigation**:
- Exact callback URL in spec: `https://i84mr8vpmd.us-east-2.awsapprunner.com/auth/callback`
- Verify in Task 1 validation step
- Test end-to-end in Task 8

### Risk: Missing Environment Variables
**Description**: Terraform doesn't set `TF_VAR_github_oauth_client_*` before apply
**Impact**: `tofu apply` fails with "variable not set" error
**Mitigation**:
- Explicit export step in Task 1
- Validation check in Task 7 before apply: `echo $TF_VAR_github_oauth_client_id`

### Risk: Hard Cutover Breaks Service
**Description**: Removing GH_TOKEN immediately with no rollback path
**Impact**: If OAuth fails, service is non-functional
**Mitigation**:
- **User doesn't care** (POC/demo environment, can fix manually)
- Git history preserves old Terraform config for manual restoration if needed
- Service recovers automatically once env vars are fixed

### Risk: Flask Secret Key Regeneration on Redeploy
**Description**: `random_password` generates new secret on each `tofu apply`, invalidating sessions
**Impact**: Users logged out on every deployment
**Mitigation**:
- Terraform state preserves `random_password` value (only generates once)
- Subsequent applies reuse same value unless resource is destroyed
- **No mitigation needed** - this is expected Terraform behavior

---

## Integration Points

**AWS Services**:
- **Secrets Manager**: Stores OAuth client secret securely
- **App Runner**: Receives OAuth credentials via environment variables
- **IAM**: Grants App Runner permission to read OAuth secret
- **CloudWatch Logs**: Monitors deployment and OAuth flow for errors

**Application Integration**:
- **Backend** (`backend/auth.py`): Expects `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`
- **Backend** (`backend/app.py`): Expects `FLASK_SECRET_KEY` for session management
- **Frontend** (Phase 2): Already deployed with login UI, no changes needed

**Terraform Resources**:
- New: `aws_secretsmanager_secret.github_oauth_client_secret`
- New: `aws_secretsmanager_secret_version.github_oauth_client_secret`
- New: `random_password.flask_secret`
- Updated: `aws_apprunner_service.action_spec` (env vars)
- Updated: `aws_iam_role_policy.app_runner_secrets` (IAM permissions)
- **Removed**: `aws_secretsmanager_secret.github_token`
- **Removed**: `aws_secretsmanager_secret_version.github_token`

---

## VALIDATION GATES (MANDATORY)

This is an **infrastructure-only** feature. Standard linting/testing gates don't apply. Instead:

### Gate 1: Terraform Validation (after Task 6)
```bash
cd infra/tools/aws
tofu validate
```
**Pass criteria**: "Success! The configuration is valid."
**If fail**: Fix Terraform syntax errors, re-run validation

### Gate 2: Terraform Plan Review (after Task 6)
```bash
tofu plan
```
**Pass criteria**:
- Plan shows exactly 3 additions, 2 changes, 2 deletions
- No unexpected resource changes
- App Runner service updates in-place (not destroy/recreate)

**If fail**: Review plan output, identify unexpected changes, fix Terraform config

### Gate 3: Deployment Success (Task 7)
```bash
tofu apply
```
**Pass criteria**: "Apply complete! Resources: 3 added, 2 changed, 2 destroyed."
**If fail**: Check error message, fix issue, re-run apply

### Gate 4: OAuth Flow End-to-End (Task 8)
Manual testing checklist (all must pass):
- [ ] Login redirects to GitHub
- [ ] GitHub authorization completes
- [ ] Redirected back to app
- [ ] User menu visible
- [ ] Logout clears session

**If fail**:
- Check CloudWatch Logs for errors
- Verify callback URL matches GitHub OAuth app settings
- Verify environment variables set correctly: `tofu show | grep GITHUB_OAUTH`

---

## Validation Sequence

**After each Terraform file modification (Tasks 2-6)**:
- No validation needed (defer to Task 6)

**After all Terraform changes complete (end of Task 6)**:
- Run Gate 1: `tofu validate`
- Run Gate 2: `tofu plan` (review carefully)

**After deployment (Task 7)**:
- Run Gate 3: Verify `tofu apply` succeeds
- Wait 3-5 minutes for App Runner deployment

**After deployment complete (Task 8)**:
- Run Gate 4: Manual OAuth flow test (all checkboxes)

**Final verification (Task 9)**:
- Confirm old PAT fully removed from all AWS resources

---

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM-LOW)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec (Phase 3 of well-defined 3-phase plan)
✅ Existing Terraform patterns found in codebase at `infra/tools/aws/*.tf`
✅ Backend expectations validated from `backend/auth.py` and `.env.local.example`
✅ All clarifying questions answered (hard cutover, OpenTofu, production-only)
✅ Infrastructure-only changes (no code changes, reduces risk)
⚠️ Manual OAuth app registration required (prerequisite, not automatable)
⚠️ Hard cutover with no rollback path (but user doesn't care - POC environment)
⚠️ No existing test suite for infrastructure (manual verification only)

**Assessment**: High-confidence infrastructure deployment. Well-understood OAuth pattern with clear validation steps. Main risks are operational (callback URL typos, missing env vars) rather than architectural.

**Estimated one-pass success probability**: 75%

**Reasoning**: Infrastructure changes are straightforward Terraform modifications following existing patterns. OAuth app registration is manual but well-documented. Hard cutover increases risk slightly, but POC environment allows for quick manual fixes if needed. Most likely failure mode is callback URL mismatch or missing environment variables, both easily debugged via CloudWatch Logs and quickly fixed.
