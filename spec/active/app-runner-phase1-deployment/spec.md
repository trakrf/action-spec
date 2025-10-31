# Feature: AWS App Runner Deployment - Phase 1 (Core Infrastructure)

## Origin
This is **Phase 1 of 2** for the App Runner deployment from Linear issue **D2A-30**.

**Parent Spec**: `spec/active/app-runner-deployment/spec.md`

**Phase Strategy**:
- **Phase 1** (this): Core infrastructure + working deployment
- **Phase 2** (next): Monitoring, alarms, and comprehensive documentation

## Outcome
A working AWS App Runner deployment of action-spec with:
- Complete Terraform infrastructure in `infra/tools/`
- GitHub source-based deployment configured
- Secrets Manager integration for GitHub token
- Basic health check validation
- Essential documentation for initial deployment

## User Story
As a **DevOps engineer**
I want **to deploy action-spec to AWS App Runner with IaC**
So that **I have a working cloud deployment that can be enhanced with monitoring**

## Context

### Why Phase 1 First?
- **Get it working**: Validate the core deployment architecture
- **Fast feedback**: Can test App Runner integration immediately
- **Reduce risk**: If there are issues with App Runner setup, catch them early
- **Ship value**: Can demonstrate working deployment before adding observability

### What's Included in Phase 1
✅ All Terraform infrastructure files
✅ IAM roles and policies
✅ Secrets Manager setup
✅ App Runner service configuration
✅ Basic README for deployment
✅ Working health check validation

### What's Deferred to Phase 2
⏭️ CloudWatch logs configuration (monitoring.tf)
⏭️ CloudWatch alarms (5xx errors, CPU)
⏭️ Comprehensive DEPLOYMENT.md
⏭️ Comprehensive OPERATIONS.md
⏭️ Enhanced README with troubleshooting

## Technical Requirements

### Infrastructure Organization
- **Location**: `infra/tools/` (new directory)
- **IaC Tool**: OpenTofu (Terraform-compatible)
- **State Backend**: S3 + DynamoDB (existing: `jxp-demo-terraform-backend-store`)
- **Region**: `us-east-2`

### File Structure to Create

```
infra/tools/
├── backend.tf           # S3 state backend (adapt from infra/advworks/dev/backend.tf)
├── providers.tf         # AWS provider (adapt from infra/advworks/dev/providers.tf)
├── variables.tf         # Input variables
├── .envrc               # Direnv config: dotenv ../../.env.local
├── main.tf              # App Runner service
├── iam.tf               # IAM roles and policies
├── secrets.tf           # Secrets Manager
├── outputs.tf           # Service URL, ARNs
└── README.md            # Quick start deployment guide
```

### Required AWS Resources

#### 1. S3 Backend Configuration (backend.tf)
```hcl
terraform {
  backend "s3" {
    bucket         = "jxp-demo-terraform-backend-store"
    key            = "tools/app-runner/terraform.tfstate"  # New path
    region         = "us-west-2"  # Bucket location
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
```

#### 2. Provider Configuration (providers.tf)
- Require Terraform >= 1.5.0
- AWS provider ~> 5.0
- Region: us-east-2
- Default tags: Project=action-spec-demo, Environment=prod, ManagedBy=terraform

#### 3. Variables (variables.tf)
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
  description = "GitHub token (from .env.local via TF_VAR_github_token)"
  sensitive   = true
}

variable "cpu" {
  description = "App Runner CPU (0.25, 0.5, 1, 2, 4 vCPU)"
  default     = "0.5"
}

variable "memory" {
  description = "App Runner memory (0.5, 1, 2, 3, 4 GB)"
  default     = "1"
}

variable "max_instances" {
  description = "Max auto-scaling instances"
  default     = 2
}
```

#### 4. IAM Roles (iam.tf)
**App Runner Instance Role**:
- Name: `action-spec-app-runner-instance-role`
- Assume role policy: App Runner service principal
- Permissions:
  - Read from Secrets Manager (specific secret ARN)
  - Write to CloudWatch Logs (basic permissions for Phase 2)

**App Runner Access Role** (optional for this phase):
- If using GitHub connector, configure access role
- For now, use source code repository approach

#### 5. Secrets Manager (secrets.tf)
- Secret name: `action-spec/github-token`
- Value: From `var.github_token` (loaded from .env.local)
- Recovery window: 7 days (for safety)

#### 6. App Runner Service (main.tf)
```hcl
resource "aws_apprunner_service" "action_spec" {
  service_name = "action-spec"

  source_configuration {
    auto_deployments_enabled = true

    code_repository {
      repository_url = "https://github.com/${var.github_repo}"

      source_code_version {
        type  = "BRANCH"
        value = var.github_branch
      }

      code_configuration {
        configuration_source = "API"

        code_configuration_values {
          runtime                       = "DOCKER"
          build_command                = ""  # Uses Dockerfile
          start_command                = ""  # Uses Dockerfile CMD
          port                         = "8080"
          runtime_environment_variables = {
            AWS_REGION      = var.aws_region
            GH_REPO         = var.github_repo
            SPECS_PATH      = "infra"
            WORKFLOW_BRANCH = var.github_branch
          }
          runtime_environment_secrets = {
            GH_TOKEN = aws_secretsmanager_secret.github_token.arn
          }
        }
      }
    }
  }

  instance_configuration {
    cpu               = var.cpu
    memory            = var.memory
    instance_role_arn = aws_iam_role.app_runner_instance.arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.action_spec.arn
}

resource "aws_apprunner_auto_scaling_configuration_version" "action_spec" {
  auto_scaling_configuration_name = "action-spec-autoscaling"
  max_concurrency                 = 100
  max_size                        = var.max_instances
  min_size                        = 1
}
```

#### 7. Outputs (outputs.tf)
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

output "secret_arn" {
  description = "ARN of the GitHub token secret"
  value       = aws_secretsmanager_secret.github_token.arn
}
```

### Environment Setup

#### .env.local (modify existing)
Add this line:
```bash
TF_VAR_github_token=$GH_TOKEN
```

#### .gitignore (verify)
Ensure these patterns exist:
```
.envrc
*.tfvars
.terraform/
*.tfstate
```

### Documentation (README.md)

Create `infra/tools/README.md` with:
- Prerequisites (AWS credentials, OpenTofu, direnv)
- Quick start: 5 commands to deploy
- How to set up `.envrc`
- How to add TF_VAR_github_token to .env.local
- Common commands (init, plan, apply, destroy)
- Troubleshooting basics

## Validation Criteria

Phase 1 is complete when:

- [ ] All 9 Terraform files created and syntactically valid
- [ ] `.envrc` created and `.env.local` updated
- [ ] `.gitignore` verified for Terraform patterns
- [ ] `tofu init` succeeds
- [ ] `tofu plan` shows expected resources (no errors)
- [ ] `tofu apply` succeeds and creates all resources
- [ ] App Runner service status is "RUNNING"
- [ ] Health check at `https://<service-url>/health` returns 200 OK
- [ ] Can access UI at `https://<service-url>/`
- [ ] README.md is complete and accurate
- [ ] `tofu destroy` cleanly removes all resources (test in safe way)

## Success Metrics

- Deployment time: < 10 minutes from `tofu apply` to RUNNING status
- Health check: Returns 200 within 2 minutes of deployment
- Clean destroy: All resources removed without errors

## Out of Scope (Phase 2)

- CloudWatch log group creation
- CloudWatch alarms (5xx, CPU)
- Comprehensive DEPLOYMENT.md documentation
- Comprehensive OPERATIONS.md documentation
- Troubleshooting guides
- Cost monitoring documentation

## References

- Parent spec: `spec/active/app-runner-deployment/spec.md`
- Linear issue: [D2A-30](https://linear.app/trakrf/issue/D2A-30)
- Pattern reference: `infra/advworks/dev/backend.tf`, `providers.tf`
- Production Dockerfile: `/Dockerfile`
- AWS App Runner docs: https://docs.aws.amazon.com/apprunner/
