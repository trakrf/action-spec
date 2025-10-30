# GitHub Personal Access Token Setup

## Overview
ActionSpec uses a GitHub Personal Access Token (PAT) to authenticate with GitHub for reading spec files and creating pull requests. This guide walks through token creation, storage in AWS SSM Parameter Store, and validation.

## Prerequisites
- GitHub account with access to repositories
- AWS CLI installed and configured
- AWS account with SSM Parameter Store access

## Step 1: Create GitHub Personal Access Token

1. **Navigate to GitHub Settings**:
   - Go to https://github.com/settings/tokens
   - Or: Settings > Developer Settings > Personal Access Tokens > Tokens (classic)

2. **Generate New Token**:
   - Click **"Generate new token (classic)"**
   - Name: `ActionSpec Lambda Access`
   - Expiration: **90 days** (recommended for security)
   - Select scopes:
     - ✅ `repo` (Full control of private repositories)
       - Includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`
   - Click **"Generate token"**

3. **Copy Token Immediately**:
   - ⚠️ **CRITICAL**: Copy the token now - you won't see it again
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Store securely (password manager recommended)

## Step 2: Store Token in AWS SSM Parameter Store

### Option A: Using AWS CLI (Recommended)

```bash
aws ssm put-parameter \
  --name /actionspec/github-token \
  --type SecureString \
  --value "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  --description "GitHub PAT for ActionSpec Lambda functions" \
  --region us-west-2
```

**Expected output**:
```json
{
    "Version": 1,
    "Tier": "Standard"
}
```

### Option B: Using AWS Console

1. Navigate to **AWS Systems Manager** > **Parameter Store**
2. Click **"Create parameter"**
3. Configure parameter:
   - **Name**: `/actionspec/github-token`
   - **Description**: `GitHub PAT for ActionSpec Lambda functions`
   - **Tier**: Standard
   - **Type**: **SecureString** (encrypted at rest)
   - **KMS Key**: `alias/aws/ssm` (default AWS managed key)
   - **Value**: Paste your GitHub PAT
4. Click **"Create parameter"**

## Step 3: Verify Setup

### Test SSM Parameter Retrieval

```bash
# Test parameter exists and is retrievable
aws ssm get-parameter \
  --name /actionspec/github-token \
  --with-decryption \
  --region us-west-2 \
  --query 'Parameter.Value' \
  --output text
```

**Expected**: Your GitHub PAT should be displayed (starts with `ghp_`)

### Test Lambda Can Retrieve Token

Run integration test script:

```bash
./scripts/test-github-integration.sh
```

This script:
1. Retrieves token from SSM
2. Authenticates with GitHub
3. Fetches a test spec file from action-spec repository
4. Reports success/failure

**Expected output**:
```
✅ SSM Parameter retrieved successfully
✅ GitHub authentication successful (rate limit: 5000/5000)
✅ Test spec file fetched successfully (567 bytes)

All tests passed!
```

## Step 4: Configure Lambda Execution Role

The Lambda execution role needs permission to read the SSM parameter.

### Check Existing Permissions

```bash
# Get Lambda execution role ARN
aws lambda get-function \
  --function-name actionspec-form-generator \
  --query 'Configuration.Role' \
  --output text

# Check role policies
aws iam list-attached-role-policies --role-name <role-name>
```

### Required IAM Policy

The SAM template (`template.yaml`) already includes this policy for functions that need GitHub access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMGetParameter",
      "Effect": "Allow",
      "Action": ["ssm:GetParameter"],
      "Resource": "arn:aws:ssm:us-west-2:*:parameter/actionspec/github-token"
    }
  ]
}
```

If deploying manually, attach this policy to the Lambda execution role.

## Security Best Practices

### Token Rotation

**Recommended schedule**: Every 90 days

```bash
# Generate new token in GitHub (follow Step 1)

# Update SSM parameter
aws ssm put-parameter \
  --name /actionspec/github-token \
  --type SecureString \
  --value "ghp_NEW_TOKEN_HERE" \
  --overwrite \
  --region us-west-2
```

Lambda will pick up new token on next invocation (thanks to `@lru_cache` clearing on restart).

### Environment Separation

Use different tokens for dev/prod:

```bash
# Development
aws ssm put-parameter \
  --name /actionspec/dev/github-token \
  --type SecureString \
  --value "ghp_DEV_TOKEN" \
  --region us-west-2

# Production
aws ssm put-parameter \
  --name /actionspec/prod/github-token \
  --type SecureString \
  --value "ghp_PROD_TOKEN" \
  --region us-west-2
```

Update Lambda `GITHUB_TOKEN_SSM_PARAM` environment variable accordingly.

### Least Privilege

- **Minimum scope**: `repo` (required for private repos)
- **Read-only alternative**: `public_repo` (only if all specs are in public repos)
- **Future**: Consider GitHub Apps for better security (higher rate limits, fine-grained permissions)

### Monitoring

**Track token usage** in GitHub Settings > Personal Access Tokens:
- Last used timestamp
- API rate limit consumption
- Suspicious activity

**CloudWatch metrics** to monitor:
- Lambda invocation errors (may indicate auth failures)
- `AuthenticationError` exceptions in logs

## Troubleshooting

### Error: "Parameter not found"

**Cause**: SSM parameter doesn't exist or name mismatch

**Solution**:
```bash
# List all parameters
aws ssm describe-parameters --region us-west-2

# Verify exact parameter name
aws ssm get-parameter --name /actionspec/github-token --region us-west-2
```

### Error: "Bad credentials"

**Cause**: Token is expired, revoked, or invalid

**Solution**:
1. Check token expiration in GitHub Settings
2. Verify token has `repo` scope
3. Generate new token and update SSM parameter

### Error: "AccessDeniedException" (Lambda)

**Cause**: Lambda execution role lacks `ssm:GetParameter` permission

**Solution**:
```bash
# Check Lambda role
aws lambda get-function --function-name actionspec-form-generator \
  --query 'Configuration.Role'

# Attach required policy (if missing)
aws iam attach-role-policy \
  --role-name <lambda-role-name> \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

### Error: "Rate limit exceeded"

**Cause**: Too many GitHub API requests

**Authenticated rate limit**: 5000 requests/hour

**Solution**:
- Wait for rate limit reset (check `X-RateLimit-Reset` header)
- Exponential backoff should handle this automatically
- Consider GitHub App for 15,000 requests/hour

## Tech Debt: Terraform Automation

**Current**: Manual SSM parameter creation via AWS CLI/Console

**Future** (tracked in overengineered/PRD.md):
- Automate SSM parameter creation via Terraform
- Read token from `terraform.tfvars` or environment variable
- Follow 12-factor app principles (config from environment)

**Target**:
```hcl
# infrastructure/modules/backend/ssm.tf
resource "aws_ssm_parameter" "github_token" {
  name        = "/actionspec/${var.environment}/github-token"
  description = "GitHub PAT for ActionSpec Lambda functions"
  type        = "SecureString"
  value       = var.github_token  # From terraform.tfvars or TF_VAR_github_token

  lifecycle {
    ignore_changes = [value]  # Allow manual rotation without Terraform drift
  }
}
```

**Usage**:
```bash
# Option 1: terraform.tfvars (gitignored)
echo 'github_token = "ghp_YOUR_TOKEN_HERE"' >> terraform.tfvars
terraform apply

# Option 2: Environment variable (CI/CD)
export TF_VAR_github_token="ghp_YOUR_TOKEN_HERE"
terraform apply

# Option 3: GitHub Secrets (GitHub Actions)
# Store token in repo secrets, reference as ${{ secrets.GITHUB_TOKEN }}
```

## Additional Resources

- [GitHub PAT Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [AWS SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
