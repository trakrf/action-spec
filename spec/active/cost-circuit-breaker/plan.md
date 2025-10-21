# Implementation Plan: AWS Cost Circuit Breaker
Generated: 2025-10-21
Specification: spec.md

## Understanding

This feature implements automated AWS cost monitoring with budget alerts to prevent unexpected charges. The MVP focuses on monitoring and alerting only (no auto-remediation), establishing the foundation for future emergency shutdown capabilities.

**Core Requirements:**
- AWS Budget resource tracking monthly spend ($10 default limit)
- SNS topic for notification delivery
- Email alerts at two thresholds: 80% warning, 100% critical
- Configurable via Terraform variables (no hardcoded values)
- Standard HCL compatible with both Terraform and OpenTofu

**Key Design Decisions (from clarifying questions):**
1. ✅ Use standard HCL (compatible with Terraform and OpenTofu)
2. ✅ Create new infrastructure/ directory structure
3. ✅ Use existing S3 backend (bucket: jxp-demo-terraform-backend-store, lock table: terraform-state)
4. ✅ Create terraform.tfvars.example + document TF_VAR_alert_email approach
5. ✅ Manual testing steps in README with optional automation for future
6. ✅ Create providers.tf in demo environment (credentials from .aws/config or .env.local)

## Relevant Files

**Reference Patterns**:
- `PRD.md` (lines 364-405) - Budget resource structure and notification configuration
- `.env.local.example` - AWS credential pattern (AWS_REGION=us-west-2)
- `.gitignore` (lines 31-44) - Terraform exclusion patterns already configured

**Files to Create**:

**Module Files** (`infrastructure/modules/cost-controls/`):
- `main.tf` - SNS topic and Budget resources
- `variables.tf` - Input variables (budget_amount, alert_email, project_name)
- `outputs.tf` - SNS topic ARN and Budget ID
- `README.md` - Module documentation and testing instructions

**Demo Environment** (`infrastructure/environments/demo/`):
- `main.tf` - Root module instantiation
- `variables.tf` - Environment-specific variables
- `outputs.tf` - Pass-through outputs from module
- `providers.tf` - AWS provider configuration
- `backend.tf` - S3 backend configuration
- `terraform.tfvars.example` - Example variable values (template for users)

**Documentation**:
- `infrastructure/README.md` - Getting started guide, deployment instructions

## Architecture Impact

- **Subsystems affected**: Infrastructure (AWS Budgets, SNS)
- **New dependencies**: None (AWS provider already standard)
- **Breaking changes**: None (purely additive, first infrastructure code)

## Task Breakdown

### Task 1: Create Directory Structure
**Files**: Directory scaffolding
**Action**: CREATE

**Implementation**:
```bash
mkdir -p infrastructure/modules/cost-controls
mkdir -p infrastructure/environments/demo
```

**Validation**:
```bash
# Verify directories exist
ls -la infrastructure/modules/cost-controls
ls -la infrastructure/environments/demo
```

---

### Task 2: Create Module Variables
**File**: `infrastructure/modules/cost-controls/variables.tf`
**Action**: CREATE

**Pattern**: Follow PRD.md variable naming (lines 368, 379, 402)

**Implementation**:
```hcl
variable "budget_amount" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 10

  validation {
    condition     = var.budget_amount > 0
    error_message = "Budget amount must be greater than 0"
  }
}

variable "alert_email" {
  description = "Email address for budget alert notifications"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "Must be a valid email address"
  }
}

variable "project_name" {
  description = "Project name for resource tagging and naming"
  type        = string

  validation {
    condition     = length(var.project_name) > 0
    error_message = "Project name cannot be empty"
  }
}

variable "warning_threshold" {
  description = "Percentage of budget for warning notification"
  type        = number
  default     = 80

  validation {
    condition     = var.warning_threshold > 0 && var.warning_threshold <= 100
    error_message = "Warning threshold must be between 0 and 100"
  }
}

variable "critical_threshold" {
  description = "Percentage of budget for critical notification"
  type        = number
  default     = 100

  validation {
    condition     = var.critical_threshold > 0 && var.critical_threshold <= 100
    error_message = "Critical threshold must be between 0 and 100"
  }
}
```

**Validation**:
```bash
cd infrastructure/modules/cost-controls
terraform init
terraform validate
```

---

### Task 3: Create SNS Topic Resource
**File**: `infrastructure/modules/cost-controls/main.tf`
**Action**: CREATE

**Pattern**: Standard SNS topic with email subscription

**Implementation**:
```hcl
# SNS Topic for budget alerts
resource "aws_sns_topic" "budget_alerts" {
  name         = "${var.project_name}-budget-alerts"
  display_name = "${var.project_name} Budget Alerts"

  tags = {
    Name        = "${var.project_name}-budget-alerts"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "cost-monitoring"
  }
}

# Email subscription to SNS topic
resource "aws_sns_topic_subscription" "budget_email" {
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
```

**Validation**:
```bash
terraform validate
terraform fmt -check
```

---

### Task 4: Create Budget Resource with Notifications
**File**: `infrastructure/modules/cost-controls/main.tf` (append)
**Action**: MODIFY (append to existing main.tf)

**Pattern**: Reference PRD.md lines 367-389 for budget structure

**Implementation**:
```hcl
# AWS Budget with notification thresholds
resource "aws_budgets_budget" "monthly_cost" {
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_amount)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Include all costs
  cost_filter {
    name = "Service"
    values = []  # Empty = all services
  }

  # Warning notification at 80% (forecasted or actual)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.warning_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.warning_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # Critical notification at 100% (actual only, also sends to SNS)
  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = var.critical_threshold
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.critical_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # Cost includes taxes, support charges, excludes credits
  cost_types {
    include_credit             = false
    include_discount           = true
    include_other_subscription = true
    include_recurring          = true
    include_refund             = false
    include_subscription       = true
    include_support            = true
    include_tax                = true
    include_upfront            = true
    use_blended                = false
  }

  tags = {
    Name      = "${var.project_name}-monthly-budget"
    Project   = var.project_name
    ManagedBy = "terraform"
    Purpose   = "cost-monitoring"
  }
}
```

**Validation**:
```bash
terraform validate
terraform fmt -check
```

---

### Task 5: Create Module Outputs
**File**: `infrastructure/modules/cost-controls/outputs.tf`
**Action**: CREATE

**Implementation**:
```hcl
output "sns_topic_arn" {
  description = "ARN of the SNS topic for budget alerts"
  value       = aws_sns_topic.budget_alerts.arn
}

output "sns_topic_name" {
  description = "Name of the SNS topic"
  value       = aws_sns_topic.budget_alerts.name
}

output "budget_id" {
  description = "ID of the AWS Budget"
  value       = aws_budgets_budget.monthly_cost.id
}

output "budget_name" {
  description = "Name of the AWS Budget"
  value       = aws_budgets_budget.monthly_cost.name
}
```

**Validation**:
```bash
terraform validate
```

---

### Task 6: Create Module README
**File**: `infrastructure/modules/cost-controls/README.md`
**Action**: CREATE

**Implementation**:
```markdown
# Cost Controls Module

AWS Budget monitoring with SNS alert notifications for cost overrun protection.

## Features

- Monthly budget tracking (default: $10 USD)
- Two-tier alerting:
  - **Warning**: 80% of budget (forecasted or actual)
  - **Critical**: 100% of budget (actual spend)
- Email notifications with spend details
- SNS topic integration for future automation

## Usage

```hcl
module "cost_controls" {
  source = "../../modules/cost-controls"

  project_name  = "action-spec"
  budget_amount = 10
  alert_email   = "alerts@example.com"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_name | Project name for resource naming | string | - | yes |
| budget_amount | Monthly budget limit in USD | number | 10 | no |
| alert_email | Email for budget alerts | string | - | yes |
| warning_threshold | Warning percentage | number | 80 | no |
| critical_threshold | Critical percentage | number | 100 | no |

## Outputs

| Name | Description |
|------|-------------|
| sns_topic_arn | ARN of budget alerts SNS topic |
| budget_id | ID of the AWS Budget resource |

## Testing

### Manual Testing (Recommended for MVP)

1. Deploy with low threshold for faster testing:
   ```hcl
   budget_amount = 1
   ```

2. Confirm SNS email subscription (check email inbox)

3. Trigger test notification via AWS Console:
   - Go to AWS Budgets → Select budget → Edit
   - Change threshold to current spend level
   - Save (triggers notification)

4. Verify email delivery (within 5 minutes)

5. Restore production threshold:
   ```hcl
   budget_amount = 10
   ```

### Automated Testing (Future Enhancement)

Consider using:
- `terraform-compliance` for policy testing
- AWS CLI to simulate budget events
- Integration tests with LocalStack

## Cost

- AWS Budgets: **Free** (first 2 budgets per account)
- SNS Email: **~$0.50/month** (negligible for email notifications)
- **Total: < $1/month**

## Security

- SNS topic restricted to AWS Budgets service principal
- Email variable marked `sensitive` (not logged)
- No secrets in Terraform state (email in variables only)

## Future Enhancements

- Lambda auto-remediation at 100% threshold
- Slack notifications via SNS → Lambda
- CloudWatch dashboard integration
- Per-service budget breakdowns
```

**Validation**:
```bash
# Verify markdown renders correctly
cat README.md
```

---

### Task 7: Create Demo Environment Main Configuration
**File**: `infrastructure/environments/demo/main.tf`
**Action**: CREATE

**Implementation**:
```hcl
# Demo environment - Cost controls deployment

module "cost_controls" {
  source = "../../modules/cost-controls"

  project_name  = var.project_name
  budget_amount = var.budget_amount
  alert_email   = var.alert_email

  # Use defaults for thresholds (80% warning, 100% critical)
}
```

**Validation**:
```bash
cd infrastructure/environments/demo
terraform validate
```

---

### Task 8: Create Demo Environment Variables
**File**: `infrastructure/environments/demo/variables.tf`
**Action**: CREATE

**Implementation**:
```hcl
variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
  default     = "action-spec"
}

variable "budget_amount" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 10
}

variable "alert_email" {
  description = "Email address for budget alerts"
  type        = string
  sensitive   = true

  # No default - must be provided by user
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}
```

**Validation**:
```bash
terraform validate
```

---

### Task 9: Create Demo Environment Outputs
**File**: `infrastructure/environments/demo/outputs.tf`
**Action**: CREATE

**Implementation**:
```hcl
output "sns_topic_arn" {
  description = "ARN of the budget alerts SNS topic"
  value       = module.cost_controls.sns_topic_arn
}

output "budget_id" {
  description = "ID of the AWS Budget"
  value       = module.cost_controls.budget_id
}

output "budget_name" {
  description = "Name of the AWS Budget"
  value       = module.cost_controls.budget_name
}

output "next_steps" {
  description = "Next steps after deployment"
  value       = <<-EOT
    ✅ Budget deployed successfully!

    Next steps:
    1. Check email (${var.alert_email}) for SNS subscription confirmation
    2. Click confirmation link in email
    3. Monitor AWS Budgets console for alerts
    4. Budget will alert at ${var.budget_amount * 0.8} USD (80%) and ${var.budget_amount} USD (100%)

    To test alerts, temporarily lower budget_amount to $1 and wait for forecast.
  EOT
}
```

**Validation**:
```bash
terraform validate
```

---

### Task 10: Create AWS Provider Configuration
**File**: `infrastructure/environments/demo/providers.tf`
**Action**: CREATE

**Pattern**: Use AWS credentials from .aws/config or .env.local

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
  # 1. Environment variables (TF_VAR_*, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  # 2. ~/.aws/credentials (AWS_PROFILE)
  # 3. ~/.aws/config

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "demo"
      ManagedBy   = "terraform"
    }
  }
}
```

**Validation**:
```bash
terraform validate
```

---

### Task 11: Create S3 Backend Configuration
**File**: `infrastructure/environments/demo/backend.tf`
**Action**: CREATE

**Pattern**: Use existing S3 backend (bucket: jxp-demo-terraform-backend-store, lock table: terraform-state)

**Implementation**:
```hcl
terraform {
  backend "s3" {
    bucket         = "jxp-demo-terraform-backend-store"
    key            = "demo/cost-controls/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "terraform-state"
    encrypt        = true

    # Credentials loaded from environment or ~/.aws/credentials
  }
}
```

**Validation**:
```bash
# Validate syntax
terraform validate

# Test backend initialization (requires AWS credentials)
terraform init
```

---

### Task 12: Create Terraform Variables Example
**File**: `infrastructure/environments/demo/terraform.tfvars.example`
**Action**: CREATE

**Implementation**:
```hcl
# Copy this file to terraform.tfvars and fill in your values
# DO NOT commit terraform.tfvars (it's in .gitignore)

# Project identification
project_name = "action-spec"

# Budget configuration
budget_amount = 10  # USD per month

# Alert email (REQUIRED - must be a valid email address)
# You will receive a confirmation email from AWS SNS
alert_email = "your-email@example.com"

# AWS region (should match your AWS CLI config)
aws_region = "us-west-2"
```

**Validation**:
```bash
# Verify file exists and is readable
cat terraform.tfvars.example
```

---

### Task 13: Create Infrastructure README
**File**: `infrastructure/README.md`
**Action**: CREATE

**Implementation**:
```markdown
# Infrastructure

Terraform/OpenTofu infrastructure for ActionSpec demo environment.

## Prerequisites

- Terraform >= 1.5.0 or OpenTofu >= 1.6.0
- AWS CLI configured with credentials
- Valid email address for budget alerts

## Quick Start

### 1. Configure Variables

```bash
cd environments/demo
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set your alert email:
```hcl
alert_email = "your-email@example.com"
```

**Alternative**: Use environment variable (avoids file):
```bash
export TF_VAR_alert_email="your-email@example.com"
```

### 2. Initialize Terraform

```bash
terraform init
```

This configures the S3 backend for state storage.

### 3. Review Plan

```bash
terraform plan
```

Expected resources:
- 1 SNS topic
- 1 SNS email subscription
- 1 AWS Budget

### 4. Deploy

```bash
terraform apply
```

Type `yes` to confirm.

### 5. Confirm SNS Subscription

Check your email for "AWS Notification - Subscription Confirmation"
Click the confirmation link (expires in 3 days)

### 6. Verify Outputs

```bash
terraform output
```

You should see:
- SNS topic ARN
- Budget ID
- Next steps message

## Testing Budget Alerts

### Quick Test (Recommended)

1. Temporarily lower threshold:
   ```hcl
   budget_amount = 1
   ```

2. Apply changes:
   ```bash
   terraform apply
   ```

3. Wait for AWS forecast to trigger (usually within 24 hours)

4. Restore production threshold:
   ```hcl
   budget_amount = 10
   ```

### Manual Trigger (AWS Console)

1. Go to [AWS Budgets Console](https://console.aws.amazon.com/billing/home#/budgets)
2. Select your budget
3. Edit notification threshold to current spend
4. Save (triggers immediate alert)
5. Check email within 5 minutes

## Project Structure

```
infrastructure/
├── modules/
│   └── cost-controls/       # Reusable budget module
│       ├── main.tf          # SNS + Budget resources
│       ├── variables.tf     # Module inputs
│       ├── outputs.tf       # Module outputs
│       └── README.md        # Module documentation
└── environments/
    └── demo/                # Demo environment
        ├── main.tf          # Module instantiation
        ├── variables.tf     # Environment variables
        ├── outputs.tf       # Pass-through outputs
        ├── providers.tf     # AWS provider config
        ├── backend.tf       # S3 state backend
        └── terraform.tfvars.example
```

## Environment Variables

Terraform recognizes these environment variables:

```bash
# AWS Credentials (if not using ~/.aws/credentials)
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-west-2"

# Terraform Variables (alternative to terraform.tfvars)
export TF_VAR_alert_email="your-email@example.com"
export TF_VAR_budget_amount="10"
export TF_VAR_project_name="action-spec"
```

## Validation

### Syntax Check
```bash
terraform validate
```

### Formatting
```bash
terraform fmt -check -recursive
```

### Linting (Optional)
```bash
# Install tflint
brew install tflint  # macOS
# or: https://github.com/terraform-linters/tflint

tflint --init
tflint
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

Type `yes` to confirm.

**Note**: SNS subscriptions may remain active. Check AWS Console if needed.

## Cost

- AWS Budgets: **Free** (first 2 budgets)
- SNS: **~$0.50/month** (email notifications)
- **Total: < $1/month**

## Troubleshooting

### "Error: No valid credential sources"

Solution: Configure AWS credentials
```bash
aws configure
# or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

### "Error: Backend configuration changed"

Solution: Reinitialize backend
```bash
terraform init -reconfigure
```

### "Email not confirmed"

Check spam folder for AWS SNS confirmation email
Link expires in 3 days - request new subscription if expired

### "Budget not triggering alerts"

- Verify SNS subscription is confirmed (AWS Console → SNS → Subscriptions)
- Check current AWS spend (AWS Console → Billing)
- Wait 24 hours for forecast to calculate
- Try manual trigger via AWS Console

## Security

- ✅ Email variable marked `sensitive` (not logged)
- ✅ No secrets in Terraform state
- ✅ S3 backend uses encryption
- ✅ DynamoDB state locking enabled
- ⚠️ terraform.tfvars in .gitignore (never commit)

## Next Steps

After MVP deployment:
- [ ] Add Lambda auto-remediation at 100% threshold
- [ ] CloudWatch dashboard for cost visualization
- [ ] Slack notifications via SNS → Lambda
- [ ] Per-service budget breakdowns
```

**Validation**:
```bash
# Verify markdown renders
cat infrastructure/README.md
```

---

## Risk Assessment

**Risk**: SNS email subscription requires manual confirmation
- **Mitigation**: Clear instructions in README and terraform output message; email confirmation link expires in 3 days

**Risk**: Budget notifications may not trigger immediately
- **Mitigation**: Document testing strategy with low threshold; provide manual trigger instructions via AWS Console

**Risk**: Terraform state stored remotely could fail if S3/DynamoDB unavailable
- **Mitigation**: S3 backend already exists and verified; state locking prevents concurrent modifications

**Risk**: Email variable could be committed accidentally
- **Mitigation**: Variable marked `sensitive = true`; terraform.tfvars in .gitignore; example file uses placeholder

**Risk**: AWS provider credentials not configured
- **Mitigation**: Comprehensive documentation in README; support for env vars, AWS CLI profiles, and .aws/credentials

## Integration Points

- **S3 Backend**: State stored at `s3://jxp-demo-terraform-backend-store/demo/cost-controls/terraform.tfstate`
- **DynamoDB**: State locking via `terraform-state` table
- **AWS Provider**: Credentials from .aws/config or environment variables
- **SNS**: Email delivery requires user confirmation
- **AWS Budgets**: Automatic monitoring of all AWS services

## VALIDATION GATES (MANDATORY)

**NOTE**: This is a Terraform/infrastructure feature. Standard npm validation commands from `spec/stack.md` are NOT applicable.

**Terraform-specific validation commands:**

After EVERY Terraform file creation or modification:

1. **Syntax Validation**:
   ```bash
   terraform validate
   ```

2. **Format Check**:
   ```bash
   terraform fmt -check
   ```

3. **Plan Generation** (requires AWS credentials):
   ```bash
   terraform plan
   ```

**Enforcement Rules:**
- If `terraform validate` fails → Fix syntax immediately
- If `terraform fmt -check` fails → Run `terraform fmt` to auto-fix
- If `terraform plan` fails → Fix resource configuration
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes validation.**

**Final validation (before commit):**
```bash
# From infrastructure/environments/demo/
terraform init
terraform validate
terraform fmt -recursive ../..
terraform plan  # Review resource changes
```

## Validation Sequence

**Per Task**:
- Task 1: Directory existence check
- Tasks 2-13: `terraform validate` + `terraform fmt -check`

**Before Commit**:
```bash
cd infrastructure/environments/demo
terraform init
terraform validate
terraform fmt -check -recursive ../..
```

**After Deploy (Manual)**:
- Confirm SNS email subscription
- Verify budget appears in AWS Console
- Test alert with low threshold

## Plan Quality Assessment

**Complexity Score**: 4/10 (LOW-MEDIUM)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ Reference pattern found in PRD.md (lines 364-405)
- ✅ All clarifying questions answered (6/6)
- ✅ Standard Terraform module pattern (well-established)
- ✅ AWS Budgets and SNS are mature services
- ✅ Existing S3 backend simplifies state management
- ✅ No new dependencies (AWS provider standard)
- ⚠️ SNS email confirmation requires manual step (documented)
- ⚠️ First infrastructure code for project (greenfield)

**Assessment**: High confidence implementation. Requirements are clear, Terraform patterns are well-established, and AWS Budgets service is mature and stable. Main risk is manual email confirmation step, which is well-documented with clear instructions.

**Estimated one-pass success probability**: 85%

**Reasoning**: Terraform syntax is deterministic and can be validated before deployment. The AWS services (Budgets, SNS) are mature with stable APIs. The 15% risk accounts for potential AWS credential configuration issues and the manual SNS email confirmation step. All technical implementation is straightforward with clear patterns to follow from PRD.md.
