# Implementation Plan: Demo Phase D1 - Foundation Infrastructure & Terraform Module
Generated: 2025-01-23
Specification: spec.md

## Understanding

This phase establishes the infrastructure foundation for the spec-editor demo by creating:
1. A reusable Terraform module (`demo/tfmodules/pod/`) for EC2 deployment
2. One implementation (`demo/infra/advworks/dev/`) that proves the pattern works
3. YAML-driven configuration (spec.yml) that drives infrastructure deployment
4. Instance naming convention solving customer pain point #1: `advworks-dev-web1` vs "host1"

**Key Pattern**: yamldecode + module + user_data (Docker) = immediately testable infrastructure

**Strategic Goal**: Prove the pattern with ONE pod before scaling to 9 in Phase D7.

## Clarifying Questions - Answered

1. **Region strategy**: Configurable via variable (c)
2. **S3 backend**: Use existing `jxp-demo-terraform-backend-store` bucket
3. **Provider config**: Each pod gets provider.tf (matches customer pattern) (a)
4. **Security group**: Default in module with override capability (c)
5. **Validation**: Hybrid - tofu validate/plan, manual apply (c)

## Relevant Files

**Reference Patterns** (existing code to follow):

- `infrastructure/environments/demo/backend.tf` - S3 backend pattern with DynamoDB locking
- `infrastructure/environments/demo/providers.tf` (lines 1-27) - Provider configuration with default_tags
- `infrastructure/environments/demo/variables.tf` (lines 1-26) - Variable patterns (description, type, default, sensitive)
- `infrastructure/modules/cost-controls/main.tf` (lines 1-78) - Module structure with tagging standards
- `infrastructure/modules/cost-controls/variables.tf` - Module variable patterns

**Files to Create**:

**Module Files** (demo/tfmodules/pod/):
- `demo/tfmodules/pod/main.tf` - Module orchestration, terraform block, module metadata
- `demo/tfmodules/pod/variables.tf` - Input variables (customer, environment, instance_name, etc.)
- `demo/tfmodules/pod/outputs.tf` - Outputs (instance_id, public_ip, demo_url, instance_name)
- `demo/tfmodules/pod/data.tf` - Data sources (Ubuntu AMI lookup, default VPC)
- `demo/tfmodules/pod/ec2.tf` - EC2 instance resource with user_data
- `demo/tfmodules/pod/security_groups.tf` - Security group allowing 80/22

**Implementation Files** (demo/infra/advworks/dev/):
- `demo/infra/advworks/dev/main.tf` - Calls pod module, yamldecode pattern
- `demo/infra/advworks/dev/spec.yml` - YAML configuration for advworks/dev
- `demo/infra/advworks/dev/backend.tf` - S3 backend configuration
- `demo/infra/advworks/dev/providers.tf` - AWS provider with default_tags
- `demo/infra/advworks/dev/variables.tf` - aws_region variable

**Files to Modify**:
- None (all new files)

## Architecture Impact

- **Subsystems affected**: Infrastructure (Terraform/OpenTofu only)
- **New dependencies**: None (Terraform/OpenTofu already in use)
- **Breaking changes**: None (net new infrastructure)
- **State management**: New state file at `demo/advworks/dev/terraform.tfstate` in S3

## Task Breakdown

### Task 1: Create Module Directory Structure
**Files**: demo/tfmodules/pod/ (directory)
**Action**: CREATE

**Implementation**:
```bash
mkdir -p demo/tfmodules/pod
mkdir -p demo/infra/advworks/dev
```

**Validation**:
```bash
ls -la demo/tfmodules/pod
ls -la demo/infra/advworks/dev
```

---

### Task 2: Create Module Variables
**File**: `demo/tfmodules/pod/variables.tf`
**Action**: CREATE
**Pattern**: Reference `infrastructure/modules/cost-controls/variables.tf`

**Implementation**:
```hcl
variable "customer" {
  description = "Customer name for resource naming and tagging"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.customer))
    error_message = "Customer must be lowercase alphanumeric with hyphens only"
  }
}

variable "environment" {
  description = "Environment name (dev, stg, prd)"
  type        = string

  validation {
    condition     = contains(["dev", "stg", "prd"], var.environment)
    error_message = "Environment must be dev, stg, or prd"
  }
}

variable "instance_name" {
  description = "User-friendly instance name (e.g., web1, app1)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.nano"
}

variable "demo_message" {
  description = "Message displayed by http-echo service"
  type        = string
  default     = "Hello from ActionSpec Demo"
}

variable "waf_enabled" {
  description = "Enable WAF protection (Phase D2)"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "security_group_id" {
  description = "Optional: Override default security group"
  type        = string
  default     = null
}
```

**Validation**:
```bash
cd demo/tfmodules/pod
tofu validate
```

---

### Task 3: Create Module Data Sources
**File**: `demo/tfmodules/pod/data.tf`
**Action**: CREATE

**Implementation**:
```hcl
# Latest Ubuntu 22.04 LTS ARM64 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Default VPC for demo (Phase D1 only)
data "aws_vpc" "default" {
  default = true
}

# Default subnets in default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
```

**Validation**:
```bash
cd demo/tfmodules/pod
tofu validate
```

---

### Task 4: Create Module Security Group
**File**: `demo/tfmodules/pod/security_groups.tf`
**Action**: CREATE

**Implementation**:
```hcl
# Security group for demo pods
# Phase D1: Allow HTTP (80) and SSH (22) from anywhere
# Phase D2: Will tighten when ALB is added
resource "aws_security_group" "pod" {
  count = var.security_group_id == null ? 1 : 0

  name_prefix = "${var.customer}-${var.environment}-pod-"
  description = "Security group for ${var.customer} ${var.environment} pod"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP from anywhere (demo only)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from anywhere (demo only)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-pod-sg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  lifecycle {
    create_before_destroy = true
  }
}

locals {
  security_group_id = var.security_group_id != null ? var.security_group_id : aws_security_group.pod[0].id
}
```

**Validation**:
```bash
cd demo/tfmodules/pod
tofu validate
```

---

### Task 5: Create Module EC2 Resource
**File**: `demo/tfmodules/pod/ec2.tf`
**Action**: CREATE

**Implementation**:
```hcl
resource "aws_instance" "pod" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  # Use first available subnet from default VPC
  subnet_id = data.aws_subnets.default.ids[0]

  # Assign public IP for demo access
  associate_public_ip_address = true

  # Security group (default or override)
  vpc_security_group_ids = [local.security_group_id]

  # User data: Install Docker and run http-echo
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Install Docker via official script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh

    # Run http-echo on port 80
    docker run -d \
      --name demo-app \
      --restart unless-stopped \
      -p 80:5678 \
      hashicorp/http-echo:latest \
      -text="${var.demo_message}"

    # Log completion
    echo "User data completed at $(date)" >> /var/log/user-data.log
  EOF

  # Customer-specific naming convention
  tags = {
    Name        = "${var.customer}-${var.environment}-${var.instance_name}"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
    InstanceName = var.instance_name
  }

  # Enable detailed monitoring (helpful for debugging)
  monitoring = true

  # Instance metadata service v2 (security best practice)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
}
```

**Validation**:
```bash
cd demo/tfmodules/pod
tofu validate
```

---

### Task 6: Create Module Outputs
**File**: `demo/tfmodules/pod/outputs.tf`
**Action**: CREATE
**Pattern**: Reference `infrastructure/modules/cost-controls/outputs.tf`

**Implementation**:
```hcl
output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.pod.id
}

output "public_ip" {
  description = "Public IP address of the instance"
  value       = aws_instance.pod.public_ip
}

output "instance_name" {
  description = "Full instance name tag"
  value       = aws_instance.pod.tags["Name"]
}

output "demo_url" {
  description = "HTTP URL to test the demo app (wait ~2 min after apply)"
  value       = "http://${aws_instance.pod.public_ip}/"
}

output "security_group_id" {
  description = "Security group ID used by the instance"
  value       = local.security_group_id
}
```

**Validation**:
```bash
cd demo/tfmodules/pod
tofu validate
```

---

### Task 7: Create Module Main (Orchestration)
**File**: `demo/tfmodules/pod/main.tf`
**Action**: CREATE

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

# Module metadata
# This module creates a demo pod (EC2 instance) for the ActionSpec demo
# Phase D1: EC2 only (no ALB, no WAF)
# Phase D2: Will add ALB + conditional WAF
```

**Validation**:
```bash
cd demo/tfmodules/pod
tofu validate
tofu fmt -check
```

**Commit Checkpoint**: Module structure complete (7 files)
```bash
git add demo/tfmodules/
git commit -m "feat(demo): create pod Terraform module for Phase D1

- Add reusable pod module with EC2, security group, data sources
- Implement customer-specific naming convention
- Add user_data with Docker + http-echo for immediate testing
- Support configurable region and security group override

Module outputs: instance_id, public_ip, demo_url, instance_name

Ref: spec/active/demo-phase-d1/spec.md"
```

---

### Task 8: Create spec.yml Configuration
**File**: `demo/infra/advworks/dev/spec.yml`
**Action**: CREATE

**Implementation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  customer: advworks
  environment: dev
spec:
  compute:
    instance_name: web1
    instance_type: t4g.nano
    demo_message: "Hello from AdventureWorks Development"
  security:
    waf:
      enabled: false
```

**Validation**:
```bash
cat demo/infra/advworks/dev/spec.yml
# Verify YAML syntax
python3 -c "import yaml; yaml.safe_load(open('demo/infra/advworks/dev/spec.yml'))"
```

---

### Task 9: Create Implementation Main
**File**: `demo/infra/advworks/dev/main.tf`
**Action**: CREATE

**Implementation**:
```hcl
# Read configuration from spec.yml
locals {
  spec = yamldecode(file("${path.module}/spec.yml"))
}

# Call pod module with spec-driven configuration
module "pod" {
  source = "../../../tfmodules/pod"

  customer      = local.spec.metadata.customer
  environment   = local.spec.metadata.environment
  instance_name = local.spec.spec.compute.instance_name
  instance_type = local.spec.spec.compute.instance_type
  demo_message  = local.spec.spec.compute.demo_message
  waf_enabled   = local.spec.spec.security.waf.enabled
  aws_region    = var.aws_region
}

# Outputs for easy access
output "instance_id" {
  description = "EC2 instance ID"
  value       = module.pod.instance_id
}

output "demo_url" {
  description = "Test the app at this URL (wait ~2 min after apply)"
  value       = module.pod.demo_url
}

output "instance_name" {
  description = "Full instance name"
  value       = module.pod.instance_name
}
```

**Validation**:
```bash
cd demo/infra/advworks/dev
tofu validate
```

---

### Task 10: Create Implementation Backend Config
**File**: `demo/infra/advworks/dev/backend.tf`
**Action**: CREATE
**Pattern**: Reference `infrastructure/environments/demo/backend.tf`

**Implementation**:
```hcl
terraform {
  backend "s3" {
    bucket         = "jxp-demo-terraform-backend-store"
    key            = "demo/advworks/dev/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true

    # Credentials loaded from environment or ~/.aws/credentials
  }
}
```

**Validation**:
```bash
cd demo/infra/advworks/dev
tofu validate
```

---

### Task 11: Create Implementation Provider Config
**File**: `demo/infra/advworks/dev/providers.tf`
**Action**: CREATE
**Pattern**: Reference `infrastructure/environments/demo/providers.tf`

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
      Project     = "action-spec-demo"
      Customer    = "advworks"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}
```

**Validation**:
```bash
cd demo/infra/advworks/dev
tofu validate
```

---

### Task 12: Create Implementation Variables
**File**: `demo/infra/advworks/dev/variables.tf`
**Action**: CREATE

**Implementation**:
```hcl
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}
```

**Validation**:
```bash
cd demo/infra/advworks/dev
tofu validate
tofu fmt -check
```

**Commit Checkpoint**: Implementation complete (5 files)
```bash
git add demo/infra/
git commit -m "feat(demo): create advworks/dev pod implementation

- Add spec.yml with customer configuration
- Implement main.tf using yamldecode + module pattern
- Configure S3 backend (jxp-demo-terraform-backend-store)
- Add provider with customer-specific default tags

Proves pattern before scaling to 9 pods in Phase D7

Ref: spec/active/demo-phase-d1/spec.md"
```

---

### Task 13: Initialize and Validate Implementation
**File**: demo/infra/advworks/dev/
**Action**: VALIDATE

**Implementation**:
```bash
cd demo/infra/advworks/dev

# Initialize Terraform (downloads providers, configures backend)
tofu init

# Validate configuration
tofu validate

# Format check
tofu fmt -check -recursive

# Generate plan to verify what will be created
tofu plan -out=phase-d1.tfplan

# Review plan output:
# Should show:
# - 1 EC2 instance (advworks-dev-web1)
# - 1 Security group
# - Data sources (AMI, VPC, subnets)
# - Outputs (instance_id, demo_url, instance_name)
```

**Expected Plan Output**:
```
Plan: 2 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + demo_url      = "http://X.X.X.X/"
  + instance_id   = (known after apply)
  + instance_name = "advworks-dev-web1"
```

**Validation**:
- ✅ tofu init succeeds without errors
- ✅ tofu validate passes
- ✅ tofu plan shows 2 resources (EC2 + SG)
- ✅ Plan shows correct instance name: "advworks-dev-web1"
- ✅ Plan includes outputs: demo_url, instance_id, instance_name

**STOP HERE** - Do not run `tofu apply` yet. User will apply manually when ready.

---

## Risk Assessment

**Risk 1: AMI lookup fails**
- **Impact**: tofu plan fails with "no AMI found"
- **Mitigation**: Data source filters for Ubuntu 22.04 ARM64, owned by Canonical (099720109477)
- **Recovery**: Check AWS region has ARM64 AMIs, adjust filter if needed

**Risk 2: Default VPC not available**
- **Impact**: Data source fails, no VPC found
- **Mitigation**: Use default VPC (common in AWS accounts)
- **Recovery**: Create VPC manually or adjust data source to use specific VPC ID

**Risk 3: S3 backend bucket doesn't exist**
- **Impact**: tofu init fails with "bucket not found"
- **Mitigation**: Using existing bucket `jxp-demo-terraform-backend-store` from Phase 1
- **Recovery**: Verify bucket exists: `aws s3 ls s3://jxp-demo-terraform-backend-store`

**Risk 4: DynamoDB lock table doesn't exist**
- **Impact**: Concurrent operations may conflict
- **Mitigation**: Using existing table `terraform-lock` from Phase 1
- **Recovery**: Verify table exists: `aws dynamodb describe-table --table-name terraform-lock`

**Risk 5: User data fails silently**
- **Impact**: Instance boots but http-echo doesn't run
- **Mitigation**: User data logs to /var/log/user-data.log, set -e for early exit
- **Recovery**: SSH to instance, check: `cat /var/log/user-data.log`, `docker ps`

**Risk 6: Security group too permissive**
- **Impact**: Security audit flags 0.0.0.0/0 on ports 80/22
- **Mitigation**: Explicitly documented as "demo only", will tighten in Phase D2
- **Recovery**: No recovery needed - this is intentional for demo

## Integration Points

- **S3 Backend**: Integrates with existing `jxp-demo-terraform-backend-store` bucket
- **DynamoDB**: Uses existing `terraform-lock` table for state locking
- **AWS Provider**: Uses existing credentials from environment or ~/.aws/
- **Module Pattern**: Establishes reusable pattern for Phase D7 (8 more pods)

## VALIDATION GATES (MANDATORY)

**Note**: This is infrastructure code (Terraform). Standard validation gates don't apply.

**Infrastructure Validation Gates**:

**Gate 1: Syntax & Formatting**
```bash
cd demo/tfmodules/pod && tofu fmt -check -recursive
cd demo/infra/advworks/dev && tofu fmt -check -recursive
```
If fails: Run `tofu fmt -recursive` to auto-fix

**Gate 2: Configuration Validation**
```bash
cd demo/tfmodules/pod && tofu validate
cd demo/infra/advworks/dev && tofu validate
```
If fails: Check syntax errors, variable references, resource dependencies

**Gate 3: Plan Generation**
```bash
cd demo/infra/advworks/dev && tofu plan -out=phase-d1.tfplan
```
If fails: Check data sources, provider configuration, variable values

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Do not proceed to manual apply until all gates pass

## Validation Sequence

**After Each Task Group**:
1. After Task 1-7 (Module): `cd demo/tfmodules/pod && tofu validate && tofu fmt -check`
2. After Task 8-12 (Implementation): `cd demo/infra/advworks/dev && tofu validate && tofu fmt -check`
3. After Task 13 (Final): `cd demo/infra/advworks/dev && tofu init && tofu plan`

**Final Manual Validation** (user performs):
```bash
cd demo/infra/advworks/dev

# Apply the plan
tofu apply phase-d1.tfplan

# Capture outputs
DEMO_URL=$(tofu output -raw demo_url)
echo "Demo URL: $DEMO_URL"

# Wait for user_data to complete (~2 minutes)
echo "Waiting 120 seconds for Docker installation..."
sleep 120

# Test http-echo
echo "Testing demo app..."
curl $DEMO_URL

# Expected output: "Hello from AdventureWorks Development"

# Optional: SSH to instance for debugging
INSTANCE_IP=$(echo $DEMO_URL | sed 's|http://||' | sed 's|/||')
ssh ubuntu@$INSTANCE_IP
# Check logs: cat /var/log/user-data.log
# Check container: docker ps
```

## Plan Quality Assessment

**Complexity Score**: 7/10 (MEDIUM-HIGH)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec - all file structures defined
✅ Similar patterns found in codebase at infrastructure/environments/demo/
✅ Similar patterns found in codebase at infrastructure/modules/cost-controls/
✅ All clarifying questions answered (5/5)
✅ User has 10 years Terraform experience ("YOLO mode")
✅ Existing test patterns: Manual tofu plan/apply validation
✅ Using existing S3 backend and DynamoDB table (proven pattern)
⚠️ New module pattern in this repo (first demo/ infrastructure)
⚠️ User data script not testable until apply (Docker install takes ~2 min)

**Assessment**: High confidence in plan execution. Terraform patterns are well-understood, existing infrastructure provides proven backend configuration, and user has deep Terraform expertise. Main risk is user_data script behavior, but design includes logging and Docker restart policy for resilience.

**Estimated one-pass success probability**: 85%

**Reasoning**:
- Clear file structure with detailed examples reduces syntax errors
- Existing backend configuration minimizes state management risks
- Module pattern is standard Terraform best practice
- User data script is simple and includes error handling
- Risk is primarily in runtime (Docker install, http-echo startup) not config
- User's 10 years experience significantly increases success probability

**Recommended Approach**:
1. Build all files (Tasks 1-12)
2. Run validation gates (tofu validate, tofu plan)
3. User reviews plan output manually
4. User applies when confident (tofu apply)
5. User validates http-echo after ~2 min wait

---

## Post-Implementation Notes

**After successful apply**:
- Document actual IP address and demo_url in spec/active/demo-phase-d1/log.md
- Capture tofu output for reference
- Test curl command with actual URL
- Optional: SSH to instance to verify Docker container

**For Phase D7** (scale to 9 pods):
- Copy demo/infra/advworks/dev/ to other customer/env combinations
- Modify spec.yml for each (customer, environment, instance_name, demo_message)
- Each gets unique state file in S3 (demo/{customer}/{env}/terraform.tfstate)
- Proves pattern is reusable with minimal changes

**Cleanup** (when demo complete):
```bash
cd demo/infra/advworks/dev
tofu destroy -auto-approve
```
