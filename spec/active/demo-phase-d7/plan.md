# Implementation Plan: Infrastructure Routing for Self-Hosted Demo (Demo Phase D7)

Generated: 2025-01-24T12:30:00Z
Specification: spec.md

## Understanding

Phase D7 adds path-based ALB routing to enable the complete demo flow. The spec-editor (port 5000) and demo-app (port 80) will both be accessible through the ALB with WAF protection. This enables the "dogfooding" narrative where the spec-editor manages the infrastructure it runs on.

**Key Requirements**:
- Docker compose: Change demo-app from port 8080 to port 80 (matches production)
- EC2 security group: Add ingress rule for port 5000 (spec-editor access from ALB)
- WAF: Add `/spec` and `/spec/*` to allowed paths regex pattern
- ALB: Create spec-editor target group (port 5000) with health check on `/`
- ALB: Create demo-app target group (port 80) with health check on `/`
- ALB: Add listener rule for `/spec*` → spec-editor (priority 100)
- ALB: Keep existing default action → demo-app

**User Decisions from Clarifying Questions**:
1. WAF: Add `/spec` paths to existing allowed_paths regex pattern set
2. Health checks: Same settings for both target groups (30s interval, 5s timeout)
3. ALB routing: Add `/spec*` rule (priority 100), keep existing default action (minimal changes)
4. Docker compose: Change HTTP_PORT=80 to match host port (enables testing both direct EC2 and ALB)

## Relevant Files

**Reference Patterns** (existing code to follow):
- `demo/tfmodules/pod/alb.tf` (lines 54-86) - Existing target group pattern (port 80, health check config)
- `demo/tfmodules/pod/alb.tf` (lines 88-104) - Existing HTTP listener with default action
- `demo/tfmodules/pod/security_groups.tf` (lines 11-17) - Existing ingress rule pattern
- `demo/tfmodules/pod/waf.tf` (lines 1-22) - Existing regex pattern set for allowed paths
- `demo/docker-compose.yml` (lines 29-37) - Existing demo-app service configuration

**Files to Modify**:
- `demo/docker-compose.yml` - Update demo-app port mapping and HTTP_PORT
- `demo/tfmodules/pod/security_groups.tf` - Add port 5000 ingress rule
- `demo/tfmodules/pod/waf.tf` - Add `/spec` paths to allowed_paths regex
- `demo/tfmodules/pod/alb.tf` - Add spec-editor target group, demo-app target group, listener rules

## Architecture Impact

- **Subsystems affected**: Docker (local), AWS (EC2 security groups, ALB, WAF)
- **New dependencies**: None
- **Breaking changes**: None (additive only)

**Integration points**:
- ALB listener rules integrate with existing HTTP listener
- Target groups attach to existing EC2 instance
- WAF regex pattern extends existing allowed paths
- Security group adds to existing ingress rules

## Task Breakdown

### Task 1: Update Docker Compose Port Configuration

**File**: `demo/docker-compose.yml`
**Action**: MODIFY
**Pattern**: Reference lines 29-37 (existing demo-app config)

**Implementation**:
Change demo-app service from port 8080 to port 80:

```yaml
demo-app:
  image: mendhak/http-https-echo:latest
  container_name: demo-app
  ports:
    - "80:80"  # Changed from "8080:8080"
  restart: unless-stopped
  environment:
    - HTTP_PORT=80  # Changed from HTTP_PORT=8080
```

**Rationale**: Matches production port configuration. Enables testing both direct EC2 access (http://ec2-ip:80) and ALB routing (http://alb-url/) during demo.

**Validation**:
```bash
cd demo
docker compose config  # Validate YAML syntax
docker compose up -d
docker ps | grep demo-app  # Should show 0.0.0.0:80->80/tcp
curl http://localhost:80/  # Should return echo response
docker compose down
```

---

### Task 2: Add Port 5000 Ingress to EC2 Security Group

**File**: `demo/tfmodules/pod/security_groups.tf`
**Action**: MODIFY
**Pattern**: Reference lines 11-17 (existing ingress rule pattern)

**Implementation**:
Add ingress rule for port 5000 after the existing port 80 rule (around line 17):

```hcl
  ingress {
    description = "HTTP from anywhere (demo only)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NEW: Allow spec-editor access
  ingress {
    description = "Spec-editor from anywhere (demo only)"
    from_port   = 5000
    to_port     = 5000
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
```

**Rationale**: ALB needs to reach spec-editor on EC2 port 5000. Using 0.0.0.0/0 for demo simplicity (could restrict to ALB security group in production).

**Validation**:
```bash
cd demo/infra/advworks/dev
terraform fmt
terraform validate
terraform plan  # Should show 1 ingress rule added
```

---

### Task 3: Add /spec Paths to WAF Allowed Paths

**File**: `demo/tfmodules/pod/waf.tf`
**Action**: MODIFY
**Pattern**: Reference lines 1-22 (existing regex pattern set)

**Implementation**:
Add `/spec` regex patterns to the allowed_paths regex pattern set (after line 14):

```hcl
resource "aws_wafv2_regex_pattern_set" "allowed_paths" {
  count = var.waf_enabled ? 1 : 0

  name  = "${var.customer}-${var.environment}-allowed-paths"
  scope = "REGIONAL"

  regular_expression {
    regex_string = "^/health$"
  }

  regular_expression {
    regex_string = "^/api/v1/.*"
  }

  # NEW: Allow spec-editor paths
  regular_expression {
    regex_string = "^/spec$"
  }

  regular_expression {
    regex_string = "^/spec/.*"
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-allowed-paths"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

**Rationale**: WAF BlockUnauthorizedPaths rule blocks all paths not matching the allowed_paths regex set. Without this, spec-editor UI would be blocked.

**Validation**:
```bash
cd demo/infra/advworks/dev
terraform fmt
terraform validate
terraform plan  # Should show 2 regex patterns added to regex_pattern_set
```

---

### Task 4: Create Spec-Editor Target Group

**File**: `demo/tfmodules/pod/alb.tf`
**Action**: MODIFY
**Pattern**: Reference lines 54-86 (existing target group pattern)

**Implementation**:
Add spec-editor target group after the existing target group (around line 79):

```hcl
# Target group for spec-editor (port 5000)
resource "aws_lb_target_group" "spec_editor" {
  name     = "${var.customer}-${var.environment}-spec-tg"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = local.vpc_id

  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-spec-tg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Attach EC2 instance to spec-editor target group
resource "aws_lb_target_group_attachment" "spec_editor" {
  target_group_arn = aws_lb_target_group.spec_editor.arn
  target_id        = aws_instance.pod.id
  port             = 5000
}
```

**Rationale**: Separate target group for spec-editor on port 5000. Health check on `/` (spec-editor home page) with same settings as existing target group.

**Validation**:
```bash
cd demo/infra/advworks/dev
terraform fmt
terraform validate
terraform plan  # Should show aws_lb_target_group.spec_editor will be created
```

---

### Task 5: Rename Existing Target Group (for clarity)

**File**: `demo/tfmodules/pod/alb.tf`
**Action**: MODIFY
**Pattern**: Reference lines 54-86 (existing target group)

**Implementation**:
Rename the existing `aws_lb_target_group.main` to `aws_lb_target_group.demo_app` for clarity:

**Before**:
```hcl
# Target group for EC2 instances
resource "aws_lb_target_group" "main" {
  name     = "${var.customer}-${var.environment}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = local.vpc_id
```

**After**:
```hcl
# Target group for demo-app (port 80)
resource "aws_lb_target_group" "demo_app" {
  name     = "${var.customer}-${var.environment}-demo-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = local.vpc_id
```

**Also update references**:
- Line 82-86: Change `aws_lb_target_group_attachment.main` to `aws_lb_target_group_attachment.demo_app`
- Line 83: Change target_group_arn reference from `.main.arn` to `.demo_app.arn`
- Line 96: Change default_action target_group_arn from `.main.arn` to `.demo_app.arn`

**Rationale**: Clear naming distinguishes demo-app target group from spec-editor target group.

**Note**: This will cause Terraform to destroy and recreate the target group. This is safe for demo but will cause brief downtime during apply.

**Validation**:
```bash
cd demo/infra/advworks/dev
terraform fmt
terraform validate
terraform plan  # Should show target group will be recreated with new name
```

---

### Task 6: Add Listener Rule for /spec Path

**File**: `demo/tfmodules/pod/alb.tf`
**Action**: MODIFY
**Pattern**: New resource (no existing listener rules)

**Implementation**:
Add listener rule after the HTTP listener resource (around line 104):

```hcl
# HTTP listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.demo_app.arn
  }

  tags = {
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# NEW: Route /spec* to spec-editor
resource "aws_lb_listener_rule" "spec_editor" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.spec_editor.arn
  }

  condition {
    path_pattern {
      values = ["/spec", "/spec/*"]
    }
  }

  tags = {
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

**Rationale**: Routes `/spec` and `/spec/*` requests to spec-editor target group (port 5000). Priority 100 ensures this rule is evaluated before default action. Default action forwards all other paths (including `/`) to demo-app.

**Validation**:
```bash
cd demo/infra/advworks/dev
terraform fmt
terraform validate
terraform plan  # Should show aws_lb_listener_rule.spec_editor will be created
```

---

### Task 7: Terraform Plan Review

**File**: N/A (validation task)
**Action**: VALIDATE

**Implementation**:
Review the complete Terraform plan to ensure changes are correct:

```bash
cd demo/infra/advworks/dev
terraform plan -out=plan.tfplan

# Expected changes:
# + aws_lb_target_group.spec_editor (new)
# + aws_lb_target_group_attachment.spec_editor (new)
# + aws_lb_listener_rule.spec_editor (new)
# ~ aws_lb_target_group.demo_app (recreate due to name change)
# ~ aws_lb_target_group_attachment.demo_app (recreate)
# ~ aws_security_group.pod (1 ingress rule added)
# ~ aws_wafv2_regex_pattern_set.allowed_paths (2 regex patterns added)
```

**Checks**:
- ✅ No unexpected resource deletions
- ✅ Target group recreation is expected (name change)
- ✅ Listener rule priority is 100 (correct)
- ✅ Path patterns are `/spec` and `/spec/*`
- ✅ Security group has port 5000 ingress
- ✅ WAF regex includes `/spec$` and `/spec/.*`

**Validation**:
If plan looks correct, proceed. If unexpected changes, review and fix before applying.

---

### Task 8: Apply Terraform Changes

**File**: N/A (deployment task)
**Action**: DEPLOY

**Implementation**:
Apply Terraform changes to deploy routing configuration:

```bash
cd demo/infra/advworks/dev
terraform apply plan.tfplan

# Monitor for errors
# Expected: ~30-60 seconds for target group recreation and health checks
```

**Wait for health checks**:
```bash
# Check target group health (wait ~30-60s)
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw spec_editor_tg_arn) \
  --region us-east-2

# Should show: HealthCheckPort: 5000, State: healthy
```

**Validation**:
```bash
terraform show | grep "aws_lb_listener_rule.spec_editor"
# Should show listener rule created

terraform show | grep "aws_lb_target_group.spec_editor"
# Should show spec-editor target group

terraform show | grep "aws_lb_target_group.demo_app"
# Should show demo-app target group
```

---

### Task 9: Test ALB Routing to Spec-Editor

**File**: N/A (testing task)
**Action**: VALIDATE

**Implementation**:
Test that ALB routes `/spec` requests to spec-editor:

```bash
# Get ALB URL from Terraform output
ALB_URL=$(cd demo/infra/advworks/dev && terraform output -raw alb_url)

# Test spec-editor path
curl -I http://${ALB_URL}/spec

# Expected:
# HTTP/1.1 200 OK
# Content-Type: text/html
# (spec-editor home page)

# Test with full path
curl http://${ALB_URL}/spec | head -50

# Expected: HTML content with spec-editor UI
```

**Validation**:
- ✅ Returns 200 OK
- ✅ Content-Type is text/html
- ✅ Response contains spec-editor UI HTML
- ✅ No 403 Forbidden (WAF allows /spec)
- ✅ No 404 Not Found (routing works)

---

### Task 10: Test ALB Routing to Demo-App

**File**: N/A (testing task)
**Action**: VALIDATE

**Implementation**:
Test that ALB routes root path to demo-app:

```bash
# Get ALB URL
ALB_URL=$(cd demo/infra/advworks/dev && terraform output -raw alb_url)

# Test root path
curl http://${ALB_URL}/

# Expected: JSON echo response from demo-app
# {
#   "path": "/",
#   "headers": {...},
#   "method": "GET",
#   ...
# }

# Test another path (should go to demo-app)
curl http://${ALB_URL}/test/path

# Expected: JSON echo response with "path": "/test/path"
```

**Validation**:
- ✅ Returns 200 OK
- ✅ Content-Type is application/json
- ✅ Response is echo server JSON
- ✅ No 403 Forbidden (WAF allows root)

---

### Task 11: Test WAF Protection

**File**: N/A (testing task)
**Action**: VALIDATE

**Implementation**:
Test that WAF blocks unauthorized paths while allowing spec-editor:

```bash
ALB_URL=$(cd demo/infra/advworks/dev && terraform output -raw alb_url)

# Test allowed paths
curl -I http://${ALB_URL}/spec              # Should return 200
curl -I http://${ALB_URL}/spec/pods         # Should return 200
curl -I http://${ALB_URL}/                  # Should return 200
curl -I http://${ALB_URL}/health            # Should return 200

# Test blocked paths
curl -I http://${ALB_URL}/admin             # Should return 403
curl -I http://${ALB_URL}/../../etc/passwd  # Should return 403
curl -I http://${ALB_URL}/api/v2/test       # Should return 403 (only /api/v1/* allowed)
```

**Validation**:
- ✅ `/spec` returns 200 (allowed)
- ✅ `/spec/*` returns 200 (allowed)
- ✅ `/` returns 200 (allowed by default action)
- ✅ `/health` returns 200 (explicitly allowed)
- ✅ `/admin` returns 403 (blocked by WAF)
- ✅ `/../../etc/passwd` returns 403 (blocked by WAF)
- ✅ `/api/v2/*` returns 403 (not in allowed paths)

---

### Task 12: Test End-to-End Demo Flow

**File**: N/A (testing task)
**Action**: VALIDATE

**Implementation**:
Walk through the complete demo flow to ensure everything works:

```bash
ALB_URL=$(cd demo/infra/advworks/dev && terraform output -raw alb_url)

# 1. Access spec-editor via ALB
open "http://${ALB_URL}/spec"
# Browser should show spec-editor UI with pod list

# 2. In browser: Select advworks/dev pod
# 3. In browser: View current configuration
# 4. In browser: Make a small change (e.g., add a tag)
# 5. In browser: Submit deployment
# Expected: Success message with GitHub Action URL

# 6. Access demo-app via ALB
curl http://${ALB_URL}/ | jq .
# Should show echo server response

# 7. Test WAF blocking
curl -I http://${ALB_URL}/malicious
# Should return 403 Forbidden

# 8. **Dogfooding moment**: The spec-editor just triggered a deployment
# that could update the infrastructure it's running on!
```

**Validation**:
- ✅ Spec-editor accessible at `/spec`
- ✅ Can view and edit pod configurations
- ✅ Deployment triggers GitHub Action
- ✅ Demo-app accessible at `/`
- ✅ WAF blocks malicious paths
- ✅ Complete demo narrative works

---

## Risk Assessment

**Risk**: Target group name change causes brief downtime during Terraform apply
**Mitigation**: Expected behavior. Health checks recover in ~30-60 seconds. Apply during non-critical time.

**Risk**: WAF blocks legitimate traffic if regex patterns are too strict
**Mitigation**: Patterns are specific (`^/spec$` and `^/spec/.*`). Test after apply. If issues, adjust regex.

**Risk**: Health check fails on spec-editor if service not running
**Mitigation**: Ensure docker compose is running on EC2 instance before Terraform apply. Check with `docker ps`.

**Risk**: Port 80 conflict on local machine during docker compose testing
**Mitigation**: Stop conflicting service or remap port temporarily. This is local testing only.

**Risk**: Confusion between direct EC2 access and ALB access during demo
**Mitigation**: Document both URLs clearly. Use ALB URL for primary demo, direct EC2 as backup.

## Integration Points

**Docker Compose**:
- Port change from 8080 to 80 affects local testing
- HTTP_PORT environment variable change affects container behavior
- Both services (spec-editor + demo-app) must run for full demo

**Terraform**:
- ALB listener rules integrate with existing HTTP listener
- Target groups attach to existing EC2 instance
- Security group rule adds to existing ingress rules
- WAF regex patterns extend existing allowed_paths

**WAF**:
- New `/spec` patterns integrated into existing BlockUnauthorizedPaths rule
- No changes to rate limiting or other WAF rules
- Both spec-editor and demo-app protected

**Demo Flow**:
- Spec-editor accessible via ALB at `/spec`
- Demo-app accessible via ALB at `/`
- Both accessible directly via EC2 (ports 5000 and 80) for troubleshooting
- WAF validates protection for both services

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

Since this is infrastructure/config (not code), validation differs from typical development:

**After Each Terraform Task**:
- Gate 1: Syntax Validation
  ```bash
  cd demo/tfmodules/pod
  terraform fmt -check
  terraform validate
  ```
  **Must pass** - Fix syntax errors immediately

- Gate 2: Plan Review
  ```bash
  cd demo/infra/advworks/dev
  terraform plan
  ```
  **Must review** - Ensure no unexpected changes

- Gate 3: Apply Success
  ```bash
  cd demo/infra/advworks/dev
  terraform apply
  ```
  **Must succeed** - No errors during apply

**After Docker Compose Task**:
- Gate 1: YAML Validation
  ```bash
  cd demo
  docker compose config
  ```
  **Must pass** - No YAML syntax errors

- Gate 2: Container Start
  ```bash
  docker compose up -d
  docker ps
  ```
  **Must pass** - Both containers running

- Gate 3: Functional Test
  ```bash
  curl http://localhost:80/
  curl http://localhost:5000/
  ```
  **Must pass** - Both services respond

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

**Task 1 (Docker Compose)**:
```bash
cd demo
docker compose config
docker compose up -d
curl http://localhost:80/
docker compose down
```

**Task 2-6 (Terraform Changes)**:
```bash
cd demo/tfmodules/pod
terraform fmt
terraform validate

cd ../../infra/advworks/dev
terraform plan
```

**Task 7-8 (Terraform Apply)**:
```bash
cd demo/infra/advworks/dev
terraform plan -out=plan.tfplan
# Review plan carefully
terraform apply plan.tfplan
# Monitor for errors
```

**Task 9-12 (End-to-End Testing)**:
```bash
ALB_URL=$(cd demo/infra/advworks/dev && terraform output -raw alb_url)

# Test spec-editor
curl -I http://${ALB_URL}/spec

# Test demo-app
curl http://${ALB_URL}/

# Test WAF
curl -I http://${ALB_URL}/malicious

# Full demo flow in browser
open "http://${ALB_URL}/spec"
```

## Plan Quality Assessment

**Complexity Score**: 3/10 (LOW)

**Breakdown**:
- File Impact: 4 files modified, 0 new = 1pt
- Subsystems: Docker + AWS = 2 subsystems = 1pt
- Tasks: 12 tasks = 2pts
- Dependencies: 0 new packages = 0pts
- Pattern Novelty: Following existing patterns = 0pts

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Existing Terraform patterns to follow (alb.tf, waf.tf, security_groups.tf)
✅ All clarifying questions answered
✅ Standard AWS/Terraform infrastructure changes
✅ Similar patterns already working (existing target group, listener, WAF rules)
✅ Low risk - additive changes only
✅ Easy rollback if issues (Terraform destroy resources)

⚠️ Minor uncertainty: Target group recreation may cause brief downtime

**Assessment**: Straightforward infrastructure configuration following established patterns. High confidence due to clear requirements, existing reference code, and simple additive changes.

**Estimated one-pass success probability**: 85%

**Reasoning**: Standard Terraform/Docker configuration with clear patterns to follow. Main risk is target group recreation causing brief downtime (expected) and potential WAF regex issues (easily fixed). Docker compose change is trivial. Overall low complexity with high confidence.
