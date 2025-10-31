# Implementation Plan: AWS App Runner Deployment - Phase 1

Generated: 2025-10-31
Specification: spec.md

## Understanding

This plan implements Phase 1 of the App Runner deployment: creating the core Terraform infrastructure to deploy action-spec to AWS App Runner. The deployment will:

- Use OpenTofu/Terraform to define infrastructure as code
- Deploy from GitHub source using Personal Access Token authentication
- Store GitHub token in AWS Secrets Manager
- Auto-deploy on every push to main branch
- Use existing S3 backend for state management
- Validate deployment with health check endpoint

**Key Design Decisions**:
1. PAT authentication for both App Runner deployment and runtime API calls (simplicity)
2. Reuse existing S3 backend bucket with new state key path
3. Auto-deployment enabled for continuous delivery
4. Manual validation via curl to /health endpoint

## Relevant Files

### Reference Patterns (existing code to follow)

- `infra/advworks/dev/backend.tf` - S3 backend configuration pattern
- `infra/advworks/dev/providers.tf` - AWS provider setup pattern
- `infra/advworks/dev/variables.tf` - Variable definition pattern
- `.gitignore` (lines 28-42) - Terraform ignore patterns already configured
- `Dockerfile` - Production-ready multi-stage build for App Runner

### Files to Create

- `infra/tools/backend.tf` - S3 state backend configuration
- `infra/tools/providers.tf` - AWS provider configuration
- `infra/tools/variables.tf` - Input variables
- `infra/tools/.envrc` - Direnv configuration to load .env.local
- `infra/tools/iam.tf` - IAM roles and policies for App Runner
- `infra/tools/secrets.tf` - Secrets Manager for GitHub token
- `infra/tools/main.tf` - App Runner service and auto-scaling
- `infra/tools/outputs.tf` - Output values (URLs, ARNs)
- `infra/tools/README.md` - Quick start deployment guide

### Files to Modify

- `.env.local` - Add `TF_VAR_github_token=$GH_TOKEN`
- `.gitignore` - Verify `.envrc` pattern exists (should already be covered)

## Architecture Impact

- **Subsystems affected**: Infrastructure (new), AWS Cloud (App Runner, IAM, Secrets Manager)
- **New dependencies**: None (OpenTofu assumed installed, AWS CLI assumed configured)
- **Breaking changes**: None (new infrastructure, doesn't affect existing deployments)

## Task Breakdown

### Task 1: Create directory structure and environment setup
**Files**: `infra/tools/` directory, `.env.local`, `infra/tools/.envrc`
**Action**: CREATE directory, MODIFY .env.local, CREATE .envrc

**Implementation**:
```bash
# Create directory
mkdir -p infra/tools

# Add to .env.local (append)
echo "TF_VAR_github_token=\$GH_TOKEN" >> .env.local

# Create .envrc
cat > infra/tools/.envrc << 'EOF'
# Load environment from root .env.local
dotenv ../../.env.local
EOF
```

**Validation**:
```bash
cd infra/tools
direnv allow  # If using direnv
# Or manually: set -a; source ../../.env.local; set +a
echo $TF_VAR_github_token  # Should output token value
```

---

### Task 2: Create backend configuration
**File**: `infra/tools/backend.tf`
**Action**: CREATE
**Pattern**: Reference `infra/advworks/dev/backend.tf`

**Implementation**:
```hcl
terraform {
  backend "s3" {
    bucket         = "jxp-demo-terraform-backend-store"
    key            = "tools/app-runner/terraform.tfstate"
    region         = "us-west-2"  # Bucket location
    dynamodb_table = "terraform-lock"
    encrypt        = true

    # Credentials loaded from environment or ~/.aws/credentials
  }
}
```

**Validation**:
```bash
cd infra/tools
tofu init  # Should succeed without errors
```

---

### Task 3: Create provider configuration
**File**: `infra/tools/providers.tf`
**Action**: CREATE
**Pattern**: Reference `infra/advworks/dev/providers.tf`

**Implementation**:
```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Credentials loaded from:
  # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  # 2. ~/.aws/credentials (AWS_PROFILE)
  # 3. ~/.aws/config

  default_tags {
    tags = {
      Project     = "action-spec"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}
```

**Validation**:
```bash
tofu validate  # Should pass
```

---

### Task 4: Create variables
**File**: `infra/tools/variables.tf`
**Action**: CREATE

**Implementation**:
```hcl
variable "aws_region" {
  description = "AWS region for App Runner service"
  type        = string
  default     = "us-east-2"
}

variable "github_repo" {
  description = "GitHub repository (org/repo)"
  type        = string
  default     = "trakrf/action-spec"
}

variable "github_branch" {
  description = "Branch to deploy"
  type        = string
  default     = "main"
}

variable "github_token" {
  description = "GitHub token for API access (loaded from .env.local via TF_VAR_github_token)"
  type        = string
  sensitive   = true
  # No default - must be provided via environment
}

variable "cpu" {
  description = "App Runner CPU allocation (0.25, 0.5, 1, 2, 4 vCPU)"
  type        = string
  default     = "0.5"
}

variable "memory" {
  description = "App Runner memory (0.5, 1, 2, 3, 4 GB)"
  type        = string
  default     = "1"
}

variable "max_instances" {
  description = "Maximum auto-scaling instances"
  type        = number
  default     = 2
}
```

**Validation**:
```bash
tofu validate  # Should pass
tofu plan  # Should show github_token as required
```

---

### Task 5: Create IAM instance role
**File**: `infra/tools/iam.tf`
**Action**: CREATE

**Implementation**:
```hcl
# IAM role for App Runner instance (runtime execution)
resource "aws_iam_role" "app_runner_instance" {
  name = "action-spec-app-runner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "action-spec-app-runner-instance-role"
  }
}

# Policy for Secrets Manager access
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
        Resource = aws_secretsmanager_secret.github_token.arn
      }
    ]
  })
}

# Policy for CloudWatch Logs (needed for Phase 2, but harmless to add now)
resource "aws_iam_role_policy" "app_runner_logs" {
  name = "cloudwatch-logs-access"
  role = aws_iam_role.app_runner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/apprunner/*"
      }
    ]
  })
}

# IAM role for App Runner service (build/deployment access)
resource "aws_iam_role" "app_runner_access" {
  name = "action-spec-app-runner-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "action-spec-app-runner-access-role"
  }
}
```

**Validation**:
```bash
tofu validate  # Should pass
tofu plan  # Should show IAM roles to be created
```

---

### Task 6: Create Secrets Manager secret
**File**: `infra/tools/secrets.tf`
**Action**: CREATE

**Implementation**:
```hcl
resource "aws_secretsmanager_secret" "github_token" {
  name                    = "action-spec/github-token"
  description             = "GitHub Personal Access Token for action-spec App Runner"
  recovery_window_in_days = 7

  tags = {
    Application = "action-spec"
  }
}

resource "aws_secretsmanager_secret_version" "github_token" {
  secret_id     = aws_secretsmanager_secret.github_token.id
  secret_string = var.github_token
}
```

**Validation**:
```bash
tofu validate  # Should pass
tofu plan  # Should show secret creation (value hidden)
```

---

### Task 7: Create App Runner service
**File**: `infra/tools/main.tf`
**Action**: CREATE

**Implementation**:
```hcl
# Auto-scaling configuration
resource "aws_apprunner_auto_scaling_configuration_version" "action_spec" {
  auto_scaling_configuration_name = "action-spec-autoscaling"
  max_concurrency                 = 100
  max_size                        = var.max_instances
  min_size                        = 1

  tags = {
    Name = "action-spec-autoscaling"
  }
}

# App Runner service
resource "aws_apprunner_service" "action_spec" {
  service_name = "action-spec"

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_access.arn
    }

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
          build_command                 = ""  # Uses Dockerfile
          start_command                 = ""  # Uses Dockerfile CMD
          port                          = "8080"

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

  tags = {
    Name = "action-spec"
  }
}
```

**Validation**:
```bash
tofu validate  # Should pass
tofu plan  # Should show App Runner service creation
```

---

### Task 8: Create outputs
**File**: `infra/tools/outputs.tf`
**Action**: CREATE

**Implementation**:
```hcl
output "app_runner_service_url" {
  description = "Public URL of the App Runner service"
  value       = "https://${aws_apprunner_service.action_spec.service_url}"
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.action_spec.arn
}

output "app_runner_service_id" {
  description = "ID of the App Runner service"
  value       = aws_apprunner_service.action_spec.service_id
}

output "app_runner_service_status" {
  description = "Status of the App Runner service"
  value       = aws_apprunner_service.action_spec.status
}

output "secret_arn" {
  description = "ARN of the GitHub token secret"
  value       = aws_secretsmanager_secret.github_token.arn
  sensitive   = true
}
```

**Validation**:
```bash
tofu validate  # Should pass
tofu plan  # Should show outputs
```

---

### Task 9: Create README documentation
**File**: `infra/tools/README.md`
**Action**: CREATE

**Implementation**:
```markdown
# Action-Spec App Runner Deployment

AWS App Runner deployment for action-spec using OpenTofu/Terraform.

## Prerequisites

- AWS account with credentials configured
- OpenTofu installed (>= 1.5.0)
- GitHub token with repo and workflow permissions
- direnv installed (optional but recommended)

## Quick Start

### 1. Environment Setup

Add to `.env.local` (in repo root):
```bash
TF_VAR_github_token=$GH_TOKEN
```

### 2. Initialize Terraform

```bash
cd infra/tools

# Load environment (if using direnv)
direnv allow

# Or manually
set -a; source ../../.env.local; set +a

# Initialize
tofu init
```

### 3. Review Plan

```bash
tofu plan
```

Expected output: ~10 resources to create (IAM roles, secrets, App Runner service)

### 4. Apply Infrastructure

```bash
tofu apply
```

Type `yes` to confirm. Deployment takes 5-10 minutes.

### 5. Verify Deployment

```bash
# Get service URL from outputs
tofu output app_runner_service_url

# Test health endpoint
curl https://<service-url>/health

# Expected: {"status": "healthy"}
```

### 6. Access Application

Open the service URL in your browser. The action-spec UI should load.

## Common Commands

| Command | Purpose |
|---------|---------|
| `tofu plan` | Preview infrastructure changes |
| `tofu apply` | Apply infrastructure changes |
| `tofu destroy` | Remove all infrastructure |
| `tofu output` | Show output values |
| `tofu show` | Show current state |

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-2` | AWS region for deployment |
| `github_repo` | `trakrf/action-spec` | GitHub repository |
| `github_branch` | `main` | Branch to deploy |
| `github_token` | *required* | GitHub PAT (from .env.local) |
| `cpu` | `0.5` | vCPU allocation |
| `memory` | `1` | Memory in GB |
| `max_instances` | `2` | Max auto-scaling instances |

Override via environment variables (`TF_VAR_*`) or create `terraform.tfvars`.

## Troubleshooting

### `tofu init` fails
- Check AWS credentials: `aws sts get-caller-identity`
- Verify S3 bucket exists: `aws s3 ls s3://jxp-demo-terraform-backend-store`

### `tofu plan` fails with "github_token is required"
- Verify `.env.local` has `TF_VAR_github_token=$GH_TOKEN`
- Check environment: `echo $TF_VAR_github_token` (should show token)

### `tofu apply` succeeds but service won't start
- Check App Runner console for deployment logs
- Verify GitHub token has correct permissions
- Check Dockerfile builds successfully locally

### Service status stuck on "OPERATION_IN_PROGRESS"
- Wait 5-10 minutes for initial deployment
- Check AWS App Runner console for detailed status

## Next Steps

After Phase 1 is complete:
- Phase 2: Add CloudWatch monitoring and comprehensive documentation
- Configure custom domain (optional)
- Set up SNS alerts (optional)

## Cleanup

To remove all infrastructure:

```bash
tofu destroy
```

**Note**: Secrets have a 7-day recovery window. To permanently delete:
```bash
aws secretsmanager delete-secret --secret-id action-spec/github-token --force-delete-without-recovery
```
```

**Validation**:
```bash
# Verify README renders properly
cat infra/tools/README.md
```

---

### Task 10: Validate Terraform syntax
**Files**: All `.tf` files
**Action**: VALIDATE

**Implementation**:
```bash
cd infra/tools
tofu fmt -check  # Check formatting
tofu fmt         # Auto-format if needed
tofu validate    # Validate syntax
```

**Validation**:
All commands should pass without errors.

---

### Task 11: Run Terraform plan
**Files**: All Terraform configuration
**Action**: PLAN

**Implementation**:
```bash
cd infra/tools
set -a; source ../../.env.local; set +a
tofu plan -out=tfplan
```

**Validation**:
- Plan should show ~10 resources to create
- No errors should occur
- github_token should not be displayed in plan output (marked sensitive)

---

### Task 12: Apply infrastructure
**Files**: All Terraform configuration
**Action**: APPLY

**Implementation**:
```bash
cd infra/tools
tofu apply tfplan
```

**Validation**:
- Apply should succeed
- All resources created successfully
- Outputs displayed (service URL, ARNs)

---

### Task 13: Wait for App Runner service to be RUNNING
**Files**: N/A
**Action**: MONITOR

**Implementation**:
```bash
# Check status
aws apprunner list-services --region us-east-2

# Or via Terraform
tofu output app_runner_service_status
```

**Validation**:
- Service status = "RUNNING"
- May take 5-10 minutes for initial build and deployment

---

### Task 14: Test health endpoint
**Files**: N/A
**Action**: VALIDATE

**Implementation**:
```bash
# Get URL
SERVICE_URL=$(tofu output -raw app_runner_service_url)

# Test health check
curl -i $SERVICE_URL/health
```

**Validation**:
- HTTP 200 response
- Response body: `{"status": "healthy"}` or similar

---

### Task 15: Test application UI
**Files**: N/A
**Action**: VALIDATE

**Implementation**:
```bash
# Get URL
SERVICE_URL=$(tofu output -raw app_runner_service_url)

# Open in browser or curl
curl -i $SERVICE_URL/
```

**Validation**:
- HTTP 200 response
- HTML content returned (Vue app)
- Can open in browser and see UI

---

### Task 16: Verify .gitignore coverage
**Files**: `.gitignore`
**Action**: VERIFY

**Implementation**:
```bash
# Check if .envrc is ignored
git check-ignore infra/tools/.envrc

# Should output the file path (meaning it's ignored)

# Verify no Terraform secrets in git
git status infra/tools/
```

**Validation**:
- `.envrc` is ignored
- No `.tfstate`, `.tfvars`, or `.terraform/` files shown in git status

---

### Task 17: Document next steps
**Files**: N/A
**Action**: DOCUMENT

**Implementation**:
Document Phase 1 completion and prepare for Phase 2:

1. Service URL: (output from Terraform)
2. Service Status: RUNNING
3. Health check: Passing
4. Ready for Phase 2: ✅

**Validation**:
Can provide working service URL to stakeholders.

---

## Risk Assessment

### Risk: App Runner build fails due to Dockerfile issues
**Mitigation**: Dockerfile is already tested locally. If build fails, check App Runner logs in console.

### Risk: GitHub authentication fails
**Mitigation**: Using PAT stored in Secrets Manager. Verify token has `repo` scope before apply.

### Risk: Service takes longer than expected to start
**Mitigation**: Initial Docker build can take 5-10 minutes. Plan for this in validation timeline.

### Risk: Health check endpoint not responding
**Mitigation**: Verify Flask app is configured correctly. Check CloudWatch logs (Phase 2 will make this easier).

### Risk: Terraform state locking conflicts
**Mitigation**: Using DynamoDB locking. If locked, wait or manually release lock if needed.

## Integration Points

- **S3 Backend**: Stores state in `jxp-demo-terraform-backend-store` bucket
- **Secrets Manager**: Stores GitHub token, referenced by App Runner
- **IAM**: Roles created for App Runner instance and access
- **App Runner**: Pulls from GitHub, builds Docker image, runs service
- **GitHub**: Source repository for code, target for API calls from app

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY Terraform file creation (Tasks 2-9):
- **Gate 1**: Terraform syntax validation
  ```bash
  tofu validate
  ```

After all Terraform files complete (Task 10):
- **Gate 2**: Terraform formatting check
  ```bash
  tofu fmt -check
  ```

After Terraform plan (Task 11):
- **Gate 3**: Plan succeeds without errors
  ```bash
  tofu plan -out=tfplan
  ```

After Terraform apply (Task 12):
- **Gate 4**: Apply succeeds
  ```bash
  tofu apply tfplan
  ```

After service deployment (Tasks 13-15):
- **Gate 5**: Service status = RUNNING
- **Gate 6**: Health endpoint returns 200
- **Gate 7**: UI loads successfully

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

1. After each `.tf` file: `tofu validate`
2. After all files: `tofu fmt -check && tofu validate`
3. Before apply: `tofu plan -out=tfplan`
4. After apply: Wait for RUNNING status
5. Final: Test health endpoint and UI

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM-LOW)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Similar patterns found in codebase at `infra/advworks/dev/`
✅ All clarifying questions answered
✅ Terraform provides strong validation before apply
✅ Existing Dockerfile is tested and working
✅ AWS App Runner documentation is comprehensive
⚠️ App Runner is new to this codebase (no existing reference)
⚠️ GitHub PAT authentication for App Runner requires testing

**Assessment**: High confidence in implementation success. Terraform's validation gates and existing infrastructure patterns provide strong foundation. Primary unknown is App Runner-specific configuration, but AWS documentation is clear.

**Estimated one-pass success probability**: 85%

**Reasoning**: Terraform's validation mechanisms catch most errors before apply. The main risk is App Runner-specific configuration (GitHub auth, health check timing), but these are well-documented. Existing infrastructure patterns make backend/provider setup straightforward. The Dockerfile is already tested, reducing build failure risk.
