# Feature: AWS App Runner Production Deployment

## Origin
This specification originated from Linear issue **D2A-30** (PR-4b: App Runner deployment + handoff). The goal is to create a production-ready deployment of the action-spec tool using AWS App Runner as a portfolio demo that can later be migrated to client accounts.

## Outcome
A fully automated, infrastructure-as-code deployment of action-spec to AWS App Runner, with:
- Managed via OpenTofu/Terraform in `infra/tools/`
- GitHub source-based deployment (no container registry needed)
- Production-grade security (IAM, Secrets Manager)
- Observability (CloudWatch Logs, Alarms)
- Complete documentation for operations and maintenance

## User Story
As a **DevOps engineer**
I want **to deploy action-spec to AWS App Runner with full IaC**
So that **I can demonstrate a production-ready, scalable deployment that can be replicated for clients**

## Context

### Discovery
- App Runner supports direct GitHub source deployment (simpler than ECR-based)
- Existing Dockerfile is production-ready (multi-stage, health checks, Gunicorn)
- Current deployments (advworks, northwind) use EC2+ALB pattern
- This is a lighter-weight serverless alternative for the same app

### Current State
- Manual Docker builds and local testing working
- Production Dockerfile exists with proper health checks
- No automated cloud deployment
- Secrets managed locally via .env.local

### Desired State
- Push to GitHub → App Runner automatically deploys
- Infrastructure defined in code (OpenTofu)
- Secrets stored in AWS Secrets Manager
- CloudWatch monitoring and alerting
- Self-service operations via documentation

## Technical Requirements

### Infrastructure Organization
- **Location**: `infra/tools/` (new directory for non-customer-specific tools)
- **IaC Tool**: OpenTofu (open-source Terraform fork)
- **State Backend**: S3 + DynamoDB (same pattern as existing infra)
- **Region**: `us-east-2` (primary)

### Required AWS Resources

#### 1. IAM Roles and Policies
- **App Runner Instance Role**:
  - Read access to Secrets Manager (specific secret ARN)
  - CloudWatch Logs write permissions
  - Scoped to least-privilege
- **App Runner Access Role**:
  - GitHub connection permissions (if using GitHub connector)
  - ECR read (not needed for GitHub source deployment)

#### 2. AWS Secrets Manager
- **Secret Name**: `action-spec/github-token` (or configurable)
- **Contents**: GitHub Personal Access Token with repo and workflow permissions
- **Source**: Value from `.env.local` (GH_TOKEN) or GitHub Actions secret
- **Rotation**: Manual (document process in OPERATIONS.md)

#### 3. App Runner Service
- **Source**: GitHub repository (`trakrf/action-spec`)
- **Branch**: `main` (or configurable)
- **Build Command**: Use Dockerfile (multi-stage build)
- **Start Command**: Defined in Dockerfile (`gunicorn ...`)
- **Runtime**: Docker
- **Port**: 8080
- **CPU**: 0.5 vCPU (or 1 vCPU based on load testing)
- **Memory**: 1 GB
- **Auto-scaling**:
  - Min instances: 1
  - Max instances: 2 (cost control for demo)
  - Concurrency: 100 (default)
- **Health Check**:
  - Path: `/health`
  - Interval: 30s
  - Timeout: 5s
  - Healthy threshold: 1
  - Unhealthy threshold: 5

#### 4. Environment Variables
App Runner service configured with:
```bash
AWS_REGION=us-east-2
GH_REPO=trakrf/action-spec
SPECS_PATH=infra  # Path to spec files in repo
WORKFLOW_BRANCH=main
# GH_TOKEN loaded from Secrets Manager reference
```

#### 5. CloudWatch Resources
- **Log Group**: `/aws/apprunner/action-spec-service`
- **Retention**: 7 days (cost-effective for demo, configurable)
- **Log Streaming**: Enabled for application and service logs

#### 6. CloudWatch Alarms
- **5xx Error Rate Alarm**:
  - Metric: `5XXError` from App Runner metrics
  - Threshold: > 5 errors in 5 minutes
  - Action: SNS notification (optional, can configure later)
- **CPU Utilization Alarm**:
  - Metric: `CPUUtilization`
  - Threshold: > 80% for 5 minutes
  - Action: SNS notification (helps identify need for scaling)

### OpenTofu/Terraform Structure

```
infra/tools/
├── backend.tf           # S3 state backend configuration
├── providers.tf         # AWS provider configuration
├── variables.tf         # Input variables
├── .envrc               # Direnv config to load ../../.env.local (gitignored)
├── main.tf              # Main App Runner resources
├── iam.tf               # IAM roles and policies
├── secrets.tf           # Secrets Manager resources
├── monitoring.tf        # CloudWatch logs and alarms
├── outputs.tf           # Output values (URLs, ARNs)
└── README.md            # Quick start guide
```

### Environment Variables Strategy

**Recommended Approach**: Add Terraform variable to `.env.local`

Simply add this line to your existing `.env.local`:
```bash
# .env.local
GH_TOKEN=ghp_xxxxxxxxxxxx
TF_VAR_github_token=$GH_TOKEN  # Terraform reads this automatically
```

Then use direnv to auto-load:
```bash
# infra/tools/.envrc
dotenv ../../.env.local
```

Or manually source before running Terraform:
```bash
set -a; source .env.local; set +a
cd infra/tools && tofu apply
```

### Variables to Support
```hcl
variable "aws_region" {
  description = "AWS region for App Runner service"
  default     = "us-east-2"
}

variable "github_repo" {
  description = "GitHub repository (org/repo)"
  default     = "trakrf/action-spec"
}

variable "github_branch" {
  description = "Branch to deploy"
  default     = "main"
}

variable "github_token" {
  description = "GitHub token for API access (loaded from .env.local via TF_VAR_github_token)"
  sensitive   = true
  # No default - must be provided via environment or tfvars
}

variable "cpu" {
  description = "App Runner CPU allocation (0.25, 0.5, 1, 2, 4)"
  default     = "0.5"
}

variable "memory" {
  description = "App Runner memory in GB (0.5, 1, 2, 3, 4)"
  default     = "1"
}

variable "max_instances" {
  description = "Maximum auto-scaling instances"
  default     = 2
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  default     = 7
}
```

### Expected Outputs
```hcl
output "app_runner_service_url" {
  description = "Public URL of the App Runner service"
  value       = aws_apprunner_service.action_spec.service_url
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.action_spec.arn
}

output "app_runner_service_id" {
  description = "ID of the App Runner service"
  value       = aws_apprunner_service.action_spec.service_id
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.app_runner.name
}

output "secret_arn" {
  description = "ARN of the GitHub token secret"
  value       = aws_secretsmanager_secret.github_token.arn
}
```

## Security Requirements

- **Secrets**: Never commit GitHub token to git; load from `.env.local` via `TF_VAR_github_token` environment variable
- **IAM**: Least-privilege policies, scoped to specific resources
- **HTTPS**: App Runner provides automatic HTTPS (certificate managed by AWS)
- **Network**: Public App Runner service (no VPC required for demo)
- **Logging**: All access and application logs sent to CloudWatch
- **.gitignore**: Ensure `infra/tools/.envrc` is ignored (`.env.local` already ignored at root)

## Deployment Process

### Initial Setup
1. Create `infra/tools/` directory structure
2. Configure S3 backend and DynamoDB table for state (or use existing)
3. Add `TF_VAR_github_token=$GH_TOKEN` to `.env.local` (root level)
4. Source environment: `set -a; source ../../.env.local; set +a` (or use direnv)
5. Run `tofu init` to initialize backend
6. Run `tofu plan` to preview changes
7. Run `tofu apply` to create resources
8. Access service at output URL
9. Test health endpoint and full workflow

### Updates
- **Code changes**: Push to GitHub → App Runner auto-deploys
- **Infrastructure changes**: Update .tf files → `tofu apply`
- **Secret rotation**: Update in Secrets Manager console or via Terraform

## Documentation Requirements

### docs/DEPLOYMENT.md
- Prerequisites (AWS credentials, OpenTofu installed, direnv optional)
- How to add `TF_VAR_github_token=$GH_TOKEN` to `.env.local`
- Step-by-step deployment guide
- Troubleshooting common issues
- How to update the deployment
- How to destroy resources

### docs/OPERATIONS.md
- How to view logs in CloudWatch
- How to update GitHub token secret
- How to scale App Runner service
- How to monitor alarms
- How to debug deployment failures
- Cost monitoring tips

### infra/tools/README.md
- Quick start guide
- How to set up `.envrc` for automatic variable loading from root `.env.local`
- Variable descriptions
- Common commands (`tofu plan`, `tofu apply`, `tofu destroy`)

## Validation Criteria

- [ ] OpenTofu code successfully creates all resources
- [ ] App Runner service deploys from GitHub source
- [ ] Health check at `https://<service-url>/health` returns 200 OK
- [ ] Application loads blueprint from GitHub (test with actual repo)
- [ ] Can edit spec values in UI
- [ ] Can trigger workflow_dispatch (requires valid GH_TOKEN)
- [ ] CloudWatch logs show application output
- [ ] CloudWatch alarms are created and in OK state
- [ ] `tofu destroy` cleanly removes all resources
- [ ] Documentation is complete and accurate
- [ ] Can replicate deployment in a fresh AWS account

## Edge Cases and Considerations

- **GitHub Connector**: App Runner may require GitHub connection setup (one-time per account)
- **Cold Starts**: First request after idle may take 5-10s (App Runner warming up)
- **Build Time**: Initial deployment takes 3-5 minutes (Docker build + deploy)
- **Cost**: Estimate ~$5-10/month for demo usage (1 instance, minimal traffic)
- **Token Expiration**: GitHub tokens expire; document rotation process
- **Multi-Region**: This spec is single-region; multi-region would need separate deployments

## Success Metrics

- Deployment time: < 10 minutes from `tofu apply` to working service
- Uptime: > 99% (measured via CloudWatch health checks)
- Build success rate: > 95% (GitHub pushes trigger successful deploys)
- Documentation completeness: Team member can deploy without help

## Future Enhancements (Out of Scope)

- Custom domain with Route53
- WAF rules for App Runner service
- SNS topic for alarm notifications
- CI/CD pipeline for Terraform changes
- Multi-environment support (dev, staging, prod)
- VPC connector for private resource access

## References

- Linear Issue: [D2A-30](https://linear.app/trakrf/issue/D2A-30)
- AWS App Runner Docs: https://docs.aws.amazon.com/apprunner/
- OpenTofu Docs: https://opentofu.org/docs/
- Existing infrastructure patterns: `infra/advworks/`, `infra/northwind/`
- Production Dockerfile: `/Dockerfile`
