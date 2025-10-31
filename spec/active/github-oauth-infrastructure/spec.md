# Feature: GitHub OAuth Infrastructure - Production Deployment

## Metadata
**Phase**: 3 of 3
**Type**: infrastructure
**Estimated Time**: 30 minutes
**Prerequisites**: Phase 1 (Backend) and Phase 2 (Frontend) must be complete

## Origin
With OAuth backend and frontend complete, this final phase deploys the authentication system to production. We'll add OAuth credentials to AWS Secrets Manager, update App Runner configuration, deploy the changes, and complete the cutover by removing the old service account PAT.

**This is Phase 3**: Infrastructure deployment and production cutover.

## Outcome
OAuth authentication system fully deployed to production. Service account PAT (`GH_TOKEN`) eliminated. All GitHub API operations use user tokens. Clean cutover with zero downtime.

**Delivers**:
- OAuth Client Secret in AWS Secrets Manager
- OAuth Client ID in App Runner environment variables
- Updated Terraform configuration
- Successful deployment to App Runner
- Service account PAT removed
- Rollback plan documented

## User Story
As a **platform operator**
I want **OAuth credentials deployed securely**
So that **users can authenticate and the old service account is decommissioned**

## Context

### Current State (After Phase 1 & 2)
- Backend OAuth endpoints functional (Phase 1)
- Frontend UI complete (Phase 2)
- **But**: Code not deployed to production
- **Still using**: Service account PAT (`GH_TOKEN`) in Secrets Manager

### Desired State (Phase 3)
- OAuth credentials securely stored in Secrets Manager
- App Runner configured with OAuth environment variables
- Application deployed with OAuth enabled
- Service account PAT removed (cutover complete)
- All operations using user tokens

## Technical Requirements

### 1. Manual Prerequisites

#### Register GitHub OAuth App

**Before deployment**, register OAuth App:

1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in details:
   - **Application name**: `action-spec` (or `action-spec-dev` for staging)
   - **Homepage URL**: `https://i84mr8vpmd.us-east-2.awsapprunner.com`
   - **Authorization callback URL**: `https://i84mr8vpmd.us-east-2.awsapprunner.com/auth/callback`
   - **Description**: (optional) "Spec editor OAuth authentication"

4. Save and copy:
   - **Client ID**: Public identifier (e.g., `Iv1.1234abcd5678efgh`)
   - **Client Secret**: Generate and copy immediately (only shown once)

5. Store credentials:
   ```bash
   # For Terraform
   export TF_VAR_github_oauth_client_id="Iv1...."
   export TF_VAR_github_oauth_client_secret="abc123..."
   ```

---

### 2. Terraform Changes

#### Add OAuth Secret (`infra/tools/aws/secrets.tf`)

**Add after existing `github_token` secret**:

```hcl
# New OAuth secret
resource "aws_secretsmanager_secret" "github_oauth_client_secret" {
  name                    = "action-spec/github-oauth-client-secret"
  description             = "GitHub OAuth App client secret for user authentication"
  recovery_window_in_days = 7

  tags = merge(
    local.common_tags,
    {
      "Name" = "action-spec-github-oauth-secret"
    }
  )
}

resource "aws_secretsmanager_secret_version" "github_oauth_client_secret" {
  secret_id     = aws_secretsmanager_secret.github_oauth_client_secret.id
  secret_string = var.github_oauth_client_secret
}
```

**Important**: Keep existing `github_token` secret initially for rollback safety. Remove in step 5 after cutover validated.

---

#### Add Variables (`infra/tools/aws/variables.tf`)

**Add after existing variables**:

```hcl
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

---

#### Update App Runner Config (`infra/tools/aws/main.tf`)

**Add OAuth env vars to `runtime_environment_variables`**:

```hcl
runtime_environment_variables = {
  AWS_REGION               = var.aws_region
  GH_REPO                  = var.github_repo
  SPECS_PATH               = "infra"
  WORKFLOW_BRANCH          = var.github_branch
  GITHUB_OAUTH_CLIENT_ID   = var.github_oauth_client_id  # NEW
  FLASK_SECRET_KEY         = random_password.flask_secret.result  # NEW (see below)
}
```

**Add OAuth secret to `runtime_environment_secrets`**:

```hcl
runtime_environment_secrets = {
  GITHUB_OAUTH_CLIENT_SECRET = aws_secretsmanager_secret.github_oauth_client_secret.arn  # NEW
  GH_TOKEN                   = aws_secretsmanager_secret.github_token.arn  # KEEP for now
}
```

**Add Flask secret key generation** (new resource):

```hcl
# Generate secure Flask secret key for sessions
resource "random_password" "flask_secret" {
  length  = 32
  special = true
}
```

**Add to `required_providers`** (if not already present):

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
```

---

#### Update IAM Permissions (`infra/tools/aws/iam.tf`)

**Add OAuth secret access to instance role**:

```hcl
# Update secrets-manager-access policy to include OAuth secret
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
        Resource = [
          aws_secretsmanager_secret.github_token.arn,
          aws_secretsmanager_secret.github_oauth_client_secret.arn  # NEW
        ]
      }
    ]
  })
}
```

---

### 3. Deployment Process

#### Step 1: Validate Terraform

```bash
cd infra/tools/aws

# Set OAuth credentials
export TF_VAR_github_oauth_client_id="Iv1...."
export TF_VAR_github_oauth_client_secret="abc123..."

# Validate configuration
tofu validate

# Expected: "Success! The configuration is valid."
```

#### Step 2: Review Plan

```bash
tofu plan
```

**Expected changes**:
- **Add**: `aws_secretsmanager_secret.github_oauth_client_secret`
- **Add**: `aws_secretsmanager_secret_version.github_oauth_client_secret`
- **Add**: `random_password.flask_secret`
- **Update**: `aws_apprunner_service.action_spec` (new env vars)
- **Update**: `aws_iam_role_policy.app_runner_secrets` (OAuth secret access)

**Review carefully**: Ensure no unexpected changes.

#### Step 3: Apply Changes

```bash
tofu apply
```

**Confirmation**: Type `yes` when prompted

**Expected output**:
```
...
Apply complete! Resources: 3 added, 2 changed, 0 destroyed.

Outputs:
app_runner_service_url = "https://i84mr8vpmd.us-east-2.awsapprunner.com"
```

**Deployment time**: 3-5 minutes (App Runner redeploys with new config)

#### Step 4: Verify Deployment

**Check service status**:
```bash
tofu output app_runner_service_status
# Expected: "RUNNING"
```

**Test OAuth flow**:
```bash
# Get service URL
SERVICE_URL=$(tofu output -raw app_runner_service_url)

# Open in browser
echo "Visit: $SERVICE_URL"
open "$SERVICE_URL"  # macOS
# or: xdg-open "$SERVICE_URL"  # Linux
```

**Manual verification**:
1. Visit service URL in browser
2. Click "Login with GitHub"
3. Complete OAuth authorization
4. Verify redirected back with user menu visible
5. Verify user avatar and name displayed
6. Click logout
7. Verify session cleared

**API verification**:
```bash
# Health check (still uses service account for now)
curl "$SERVICE_URL/health"
# Expected: {"status": "healthy", ...}

# Try authenticated endpoint (should require login)
curl "$SERVICE_URL/api/auth/user"
# Expected: 401 or redirect to login
```

---

### 4. Production Cutover

After OAuth verified working:

#### Step 1: Update Backend to Require OAuth

**Change**: Make OAuth mandatory (remove service account fallback)

This was likely already done in Phase 1, but verify:
- All GitHub API calls use `github_api_call()` wrapper
- No endpoints fall back to `GH_TOKEN` environment variable
- `/api/auth/user` endpoint is the only way to authenticate

#### Step 2: Remove Service Account PAT

**Update `infra/tools/aws/secrets.tf`**:

```hcl
# DELETE: Service account PAT no longer needed
# Comment out or remove:
# resource "aws_secretsmanager_secret" "github_token" { ... }
# resource "aws_secretsmanager_secret_version" "github_token" { ... }
```

**Update `infra/tools/aws/main.tf`**:

```hcl
runtime_environment_secrets = {
  GITHUB_OAUTH_CLIENT_SECRET = aws_secretsmanager_secret.github_oauth_client_secret.arn
  # REMOVE: GH_TOKEN line
}
```

**Update `infra/tools/aws/iam.tf`**:

```hcl
# Remove github_token.arn from secrets policy
Resource = [
  aws_secretsmanager_secret.github_oauth_client_secret.arn
  # REMOVE: aws_secretsmanager_secret.github_token.arn
]
```

**Update `infra/tools/aws/variables.tf`**:

```hcl
# REMOVE or comment out:
# variable "github_token" { ... }
```

#### Step 3: Apply Cutover

```bash
cd infra/tools/aws

# Review changes (should remove GH_TOKEN references)
tofu plan

# Apply
tofu apply
```

**Expected**: Service redeploys without GH_TOKEN

#### Step 4: Delete Old Secret (Optional)

After verifying OAuth works:

```bash
# Delete secret from AWS (with recovery window)
aws secretsmanager delete-secret \
  --secret-id action-spec/github-token \
  --region us-east-2

# Or force delete immediately (no recovery)
aws secretsmanager delete-secret \
  --secret-id action-spec/github-token \
  --region us-east-2 \
  --force-delete-without-recovery
```

---

### 5. Rollback Plan

If OAuth fails in production:

#### Emergency Rollback

**Step 1**: Restore service account PAT

```bash
cd infra/tools/aws

# Revert Terraform changes (git checkout previous commit)
git checkout HEAD~1 -- secrets.tf main.tf variables.tf iam.tf

# Re-add GH_TOKEN to environment
export TF_VAR_github_token="ghp_..."

# Apply old configuration
tofu apply
```

**Step 2**: Verify service recovered

```bash
# Check health
curl "$(tofu output -raw app_runner_service_url)/health"
```

#### Gradual Rollback

**If OAuth partially works**, can temporarily keep both:
- Keep OAuth endpoints deployed
- Restore `GH_TOKEN` as fallback
- Debug OAuth issues
- Remove `GH_TOKEN` again after fixing

---

## Validation Criteria

### Infrastructure
- [ ] OAuth Client Secret created in Secrets Manager
- [ ] OAuth Client ID in environment variables
- [ ] Flask secret key generated and set
- [ ] IAM policy grants OAuth secret access
- [ ] Terraform apply succeeds with no errors
- [ ] App Runner service status: RUNNING

### OAuth Flow
- [ ] Can visit service URL in browser
- [ ] Login button visible
- [ ] Click login redirects to GitHub
- [ ] Complete authorization on GitHub
- [ ] Redirected back to app with user menu
- [ ] User avatar and name displayed
- [ ] Logout clears session

### Cutover Complete
- [ ] Service account PAT (`GH_TOKEN`) removed from Secrets Manager
- [ ] `GH_TOKEN` removed from App Runner environment
- [ ] IAM policy no longer references old secret
- [ ] All GitHub operations use user tokens
- [ ] Health check still passes

### Production Verification
- [ ] No errors in CloudWatch Logs
- [ ] Service accessible from public internet
- [ ] OAuth callback URL matches registered app
- [ ] HTTPS working correctly (no mixed content)
- [ ] Cookies set correctly (HttpOnly, Secure, SameSite)

## Success Metrics

- OAuth credentials deployed securely
- Zero downtime during deployment
- All users can authenticate successfully
- Service account PAT eliminated
- Rollback plan tested and documented
- < 5 minutes deployment time (excluding OAuth app registration)

## Testing Strategy

### Pre-Deployment Testing

1. **Terraform validation**:
   ```bash
   tofu validate
   tofu plan | grep -E "^\s*(Plan:|No changes)"
   ```

2. **OAuth App registration**:
   - Verify callback URL matches production domain
   - Test credentials locally first

### Post-Deployment Testing

1. **Smoke tests**:
   - Health check endpoint
   - Login flow end-to-end
   - Logout flow
   - API operations with user token

2. **Security verification**:
   ```bash
   # Check cookie attributes in browser devtools
   # Should see: HttpOnly; Secure; SameSite=Lax
   ```

3. **Monitoring**:
   ```bash
   # Check CloudWatch Logs for errors
   aws logs tail /aws/apprunner/action-spec --follow
   ```

## Dependencies

### Prerequisites
- **Phase 1**: Backend OAuth endpoints deployed
- **Phase 2**: Frontend UI deployed
- GitHub OAuth App registered manually
- AWS credentials configured locally

### Terraform Resources
- AWS Secrets Manager (existing)
- App Runner (existing)
- IAM roles and policies (existing)
- Random provider (new dependency)

### Environment Variables Required
- `TF_VAR_github_oauth_client_id`
- `TF_VAR_github_oauth_client_secret`
- `TF_VAR_github_token` (initially, removed after cutover)

## Migration Strategy

### Approach: Parallel Deployment → Cutover

1. **Phase 3a**: Deploy OAuth alongside existing PAT (both work)
2. **Validation**: Test OAuth thoroughly
3. **Phase 3b**: Remove PAT (cutover)
4. **Monitoring**: Watch for issues

### Advantages
- Zero downtime
- Easy rollback (just restore PAT)
- Gradual cutover
- Can test OAuth in production before commitment

### Risks
- Brief period where both auth methods exist
- Need to ensure backend prefers OAuth over PAT

## Out of Scope

**Not in Phase 3**:
- Multi-region deployment (AWS us-east-2 only)
- Staging environment (deploying directly to production)
- Automated deployment pipeline (manual `tofu apply`)
- Monitoring/alerting setup (Phase 2 of App Runner observability)

## Next Steps

After Phase 3 complete:
- **Monitor**: Watch CloudWatch Logs for errors
- **Document**: Update README with OAuth setup instructions
- **Iterate**: Gather user feedback, refine UX

## Related

- **Linear**: D2A-31
- **Previous Phases**:
  - Phase 1: `spec/active/github-oauth-backend/spec.md`
  - Phase 2: `spec/active/github-oauth-frontend/spec.md`
- **Infrastructure**: `infra/tools/aws/` Terraform configuration
