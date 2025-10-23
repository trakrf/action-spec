# Implementation Plan: Demo Phase D2 - ALB + Conditional WAF
Generated: 2025-01-23
Specification: spec.md

## Understanding

Phase D2 builds on Phase D1's EC2 infrastructure by adding:
1. **Application Load Balancer (ALB)** - Routes traffic to EC2, provides health checks
2. **Conditional WAF** - Toggleable via `waf_enabled` variable, includes:
   - Custom rate limiting (100 req/min per IP)
   - Custom path filtering (allowlist: `/health`, `/api/v1/*`)
   - AWS managed rule sets (CommonRuleSet + KnownBadInputsRuleSet)
3. **Enhanced demo container** - Switch from `hashicorp/http-echo` to `mendhak/http-https-echo` for visible request path verification

**Key Design Decisions** (from clarifying questions):
- Keep direct EC2 access (0.0.0.0/0) to enable demo contrast: WAF-protected ALB vs unrestricted direct access
- Include both managed rule sets for comprehensive protection (addresses customer probe concerns)
- Use `mendhak/http-https-echo` container to show request paths in responses
- ALB health check uses `/health` path (matches WAF allowed paths)
- Strict path allowlist: only `/health` and `/api/v1/*` allowed (root `/` blocked)

## Relevant Files

**Reference Patterns** (existing code to follow):

- `demo/tfmodules/pod/security_groups.tf` (lines 4-45) - Conditional resource creation using `count`, security group structure with lifecycle
- `demo/tfmodules/pod/data.tf` (lines 22-42) - Conditional data sources and locals pattern
- `demo/tfmodules/pod/variables.tf` (lines 38-42) - WAF variable already exists, validation pattern
- `demo/tfmodules/pod/ec2.tf` (lines 50-56) - Standard tagging pattern (Customer, Environment, ManagedBy)

**Files to Create**:

- `demo/tfmodules/pod/alb.tf` - ALB, target group, listener, ALB security group
- `demo/tfmodules/pod/waf.tf` - Conditional WAF resources (regex pattern set, web ACL, association)

**Files to Modify**:

- `demo/tfmodules/pod/security_groups.tf` (lines 11-17) - Add ingress rule for HTTP from ALB security group
- `demo/tfmodules/pod/outputs.tf` (after line 24) - Add ALB and WAF outputs
- `demo/tfmodules/pod/ec2.tf` (lines 38-43) - Update user_data to use `mendhak/http-https-echo` container
- `demo/infra/advworks/dev/spec.yml` (verify only) - Ensure `security.waf.enabled: false` exists

## Architecture Impact

- **Subsystems affected**: Infrastructure (Terraform AWS resources only)
- **New dependencies**: None (using existing AWS provider ~> 5.0)
- **Breaking changes**: None (additive changes, backward compatible)
  - ALB is new, doesn't affect existing EC2 direct access
  - WAF is conditional (default: disabled)
  - Container change improves demo without breaking functionality

## Task Breakdown

### Task 1: Update EC2 user_data to use mendhak/http-https-echo
**File**: `demo/tfmodules/pod/ec2.tf`
**Action**: MODIFY (lines 38-43)
**Pattern**: Reference existing user_data structure (lines 18-47)

**Implementation**:
```bash
# Replace hashicorp/http-echo with mendhak/http-https-echo
# Old:
docker run -d \
  --name demo-app \
  --restart unless-stopped \
  -p 80:5678 \
  hashicorp/http-echo:latest \
  -text='${var.demo_message}'

# New:
docker run -d \
  --name demo-app \
  --restart unless-stopped \
  -p 80:8080 \
  mendhak/http-https-echo:latest
```

**Rationale**:
- `mendhak/http-https-echo` returns JSON with request details (path, headers, IP)
- Makes WAF path filtering demonstrations visible (response shows which path was requested)
- Runs on port 8080 (map to host port 80)
- No need for `-text` flag (returns request echo automatically)

**Validation**:
- Terraform plan should show user_data change only
- No validation commands (Terraform syntax check via `terraform validate`)

---

### Task 2: Create ALB Security Group
**File**: `demo/tfmodules/pod/alb.tf` (NEW)
**Action**: CREATE
**Pattern**: Reference `security_groups.tf` (lines 4-45) for security group structure

**Implementation**:
```hcl
# Security group for ALB
resource "aws_security_group" "alb" {
  name_prefix = "${var.customer}-${var.environment}-alb-"
  description = "Security group for ${var.customer} ${var.environment} ALB"
  vpc_id      = local.vpc_id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound (for health checks)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-alb-sg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  lifecycle {
    create_before_destroy = true
  }
}
```

**Validation**:
- Run `terraform validate` in `demo/tfmodules/pod/`
- Should pass syntax check

---

### Task 3: Create Application Load Balancer
**File**: `demo/tfmodules/pod/alb.tf`
**Action**: APPEND
**Pattern**: Follow AWS resource naming convention from `ec2.tf` (line 51)

**Implementation**:
```hcl
# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.customer}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.all.ids

  enable_deletion_protection = false  # Demo setting

  tags = {
    Name        = "${var.customer}-${var.environment}-alb"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

**Note**: Requires data source for all subnets (multi-AZ requirement for ALB) - handled in Task 4.

**Validation**:
- Run `terraform validate`
- Wait for data source in Task 4

---

### Task 4: Add data source for all subnets (ALB requires 2+ AZs)
**File**: `demo/tfmodules/pod/data.tf`
**Action**: MODIFY (append after line 42)
**Pattern**: Follow existing data source structure (lines 29-36)

**Implementation**:
```hcl
# All subnets for ALB (requires multi-AZ)
data "aws_subnets" "all" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}
```

**Rationale**: ALB requires subnets in at least 2 availability zones. The existing `data.aws_subnets.default` only grabs one subnet for EC2. This new data source gets all subnets for ALB.

**Validation**:
- Run `terraform validate`
- Check that both `data.aws_subnets.default` and `data.aws_subnets.all` exist

---

### Task 5: Create Target Group and Attachment
**File**: `demo/tfmodules/pod/alb.tf`
**Action**: APPEND
**Pattern**: Reference AWS documentation for target group health check configuration

**Implementation**:
```hcl
# Target group for EC2 instances
resource "aws_lb_target_group" "main" {
  name     = "${var.customer}-${var.environment}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = local.vpc_id

  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-tg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Attach EC2 instance to target group
resource "aws_lb_target_group_attachment" "main" {
  target_group_arn = aws_lb_target_group.main.arn
  target_id        = aws_instance.pod.id
  port             = 80
}
```

**Validation**:
- Run `terraform validate`
- Should pass

---

### Task 6: Create ALB Listener
**File**: `demo/tfmodules/pod/alb.tf`
**Action**: APPEND

**Implementation**:
```hcl
# HTTP listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }

  tags = {
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

**Validation**:
- Run `terraform validate`
- Full `alb.tf` should be syntactically correct

---

### Task 7: Update EC2 Security Group for ALB ingress
**File**: `demo/tfmodules/pod/security_groups.tf`
**Action**: MODIFY (add ingress rule after line 17)
**Pattern**: Follow existing ingress rule structure (lines 11-17)

**Implementation**:
Add new ingress block after the SSH ingress rule (after line 25):

```hcl
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
```

**Note**: This allows HTTP from ALB security group. Direct access from 0.0.0.0/0 (lines 11-17) remains for demo purposes.

**Validation**:
- Run `terraform validate`
- Check that both ingress rules exist (HTTP from anywhere + HTTP from ALB)

---

### Task 8: Create WAF regex pattern set for allowed paths
**File**: `demo/tfmodules/pod/waf.tf` (NEW)
**Action**: CREATE
**Pattern**: Follow conditional resource creation pattern from `security_groups.tf` (line 5)

**Implementation**:
```hcl
# Regex pattern set for allowed paths
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

  tags = {
    Name        = "${var.customer}-${var.environment}-allowed-paths"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

**Validation**:
- Run `terraform validate`
- Should pass

---

### Task 9: Create WAF Web ACL with custom rules and managed rule groups
**File**: `demo/tfmodules/pod/waf.tf`
**Action**: APPEND
**Pattern**: Reference spec.md lines 219-299 for complete WAF configuration

**Implementation**:
```hcl
resource "aws_wafv2_web_acl" "main" {
  count = var.waf_enabled ? 1 : 0

  name  = "${var.customer}-${var.environment}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rule 1: Rate limiting (priority 1)
  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 100
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: Path filtering (priority 2)
  rule {
    name     = "BlockUnauthorizedPaths"
    priority = 2

    action {
      block {}
    }

    statement {
      not_statement {
        statement {
          regex_pattern_set_reference_statement {
            arn = aws_wafv2_regex_pattern_set.allowed_paths[0].arn

            field_to_match {
              uri_path {}
            }

            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-path-block"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed Rules - Common Rule Set (OWASP Top 10)
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.customer}-${var.environment}-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-waf"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

**Note**:
- Managed rule groups use `override_action { none {} }` not `action { block {} }`
- Custom rules (rate limit, path filter) use `action { block {} }`

**Validation**:
- Run `terraform validate`
- Should pass

---

### Task 10: Create WAF Association with ALB
**File**: `demo/tfmodules/pod/waf.tf`
**Action**: APPEND
**Pattern**: Conditional resource creation (lines 1-4)

**Implementation**:
```hcl
# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "alb" {
  count = var.waf_enabled ? 1 : 0

  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main[0].arn
}
```

**Validation**:
- Run `terraform validate`
- Complete `waf.tf` should be syntactically correct

---

### Task 11: Add ALB and WAF outputs
**File**: `demo/tfmodules/pod/outputs.tf`
**Action**: MODIFY (append after line 24)
**Pattern**: Follow existing output structure (lines 1-24)

**Implementation**:
```hcl
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "alb_url" {
  description = "HTTP URL to access via ALB (wait ~60s for health checks)"
  value       = "http://${aws_lb.main.dns_name}/"
}

output "waf_enabled" {
  description = "Whether WAF is enabled"
  value       = var.waf_enabled
}

output "waf_web_acl_id" {
  description = "ID of WAF Web ACL (empty if disabled)"
  value       = var.waf_enabled ? aws_wafv2_web_acl.main[0].id : ""
}

output "waf_web_acl_arn" {
  description = "ARN of WAF Web ACL (empty if disabled)"
  value       = var.waf_enabled ? aws_wafv2_web_acl.main[0].arn : ""
}
```

**Validation**:
- Run `terraform validate`
- Should pass

---

### Task 12: Verify spec.yml has WAF configuration
**File**: `demo/infra/advworks/dev/spec.yml`
**Action**: VERIFY (read-only check)
**Pattern**: Should match spec.md lines 168-182

**Expected content**:
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

**Action**: Read the file and confirm `security.waf.enabled: false` exists.

**If missing**: The spec.yml already has this from Phase D1 (verified in research). No changes needed.

**Validation**:
- Visual inspection only

---

### Task 13: Run Terraform plan with WAF disabled (default)
**Directory**: `demo/infra/advworks/dev/`
**Action**: TEST
**Pattern**: Follow spec.md Test 1 (lines 339-359)

**Commands**:
```bash
cd demo/infra/advworks/dev
terraform init -upgrade  # Ensure latest AWS provider
terraform validate
terraform plan
```

**Expected output**:
- Plan should show:
  - ALB, target group, listener, ALB security group (new)
  - EC2 security group modification (new ingress rule)
  - EC2 user_data change (new container)
  - Module outputs updated
  - **NO** WAF resources (waf_enabled = false by default)

**Validation**:
- No errors in plan
- Resource count matches expectations (~8-10 new resources)

---

### Task 14: Apply Terraform and test ALB routing
**Directory**: `demo/infra/advworks/dev/`
**Action**: TEST
**Pattern**: Follow spec.md Test 1 (lines 348-359)

**Commands**:
```bash
terraform apply -auto-approve

# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "ALB DNS: $ALB_DNS"

# Wait for health checks to pass (~60 seconds)
echo "Waiting 60 seconds for health checks..."
sleep 60

# Test ALB routing to EC2
echo "Testing ALB access..."
curl http://$ALB_DNS/health

# Test direct EC2 access (should still work)
EC2_IP=$(terraform output -raw public_ip)
echo "Testing direct EC2 access..."
curl http://$EC2_IP/health
```

**Expected results**:
- ALB returns JSON with `"path": "/health"`
- Direct EC2 returns same JSON (both unrestricted without WAF)
- Both return HTTP 200

**Validation**:
- Both curl commands succeed
- JSON response shows correct path
- Health checks passing in AWS console (target group shows healthy)

---

### Task 15: Enable WAF and test path filtering
**Directory**: `demo/infra/advworks/dev/`
**Action**: TEST
**Pattern**: Follow spec.md Test 2 and Test 3 (lines 361-412)

**Commands**:
```bash
# Edit spec.yml - change enabled: false → true
vim spec.yml  # Or use sed/editor

# Apply with WAF enabled
terraform plan  # Should show WAF resources being created
terraform apply -auto-approve

# Test allowed paths (should return 200)
echo "Testing allowed paths..."
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/health
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/api/v1/users
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/api/v1/orders/123

# Test blocked paths (should return 403)
echo "Testing blocked paths..."
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/admin
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/api/v2/users

# Test malicious patterns (managed rules should block)
echo "Testing managed rule blocks..."
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/.env
curl -A "sqlmap" -w "\nHTTP %{http_code}\n" http://$ALB_DNS/

# Test direct EC2 access (should bypass WAF)
echo "Testing direct EC2 (bypasses WAF)..."
curl http://$EC2_IP/admin  # Should work (no WAF on direct access)
```

**Expected results**:
- `/health` and `/api/v1/*` return 200 with JSON
- `/`, `/admin`, `/api/v2/*` return 403 (WAF block)
- `.env` and `sqlmap` requests return 403 (managed rules block)
- Direct EC2 access returns 200 for any path (demonstrates contrast)

**Validation**:
- Path filtering works as expected
- Managed rules block malicious patterns
- Direct EC2 access proves WAF is ALB-specific

---

### Task 16: Test rate limiting
**Directory**: `demo/infra/advworks/dev/`
**Action**: TEST
**Pattern**: Follow spec.md Test 4 (lines 414-442)

**Commands**:
```bash
# Test rapid requests (should trigger rate limit after 3-5 requests)
echo "Testing rate limiting (100 req/min)..."
for i in {1..10}; do
  echo -n "Request $i: "
  curl -s -o /dev/null -w "HTTP %{http_code}\n" http://$ALB_DNS/health
done

# Wait for rate limit window to reset
echo "Waiting 65 seconds for rate limit reset..."
sleep 65

# Verify reset
echo "Testing after reset..."
curl -w "HTTP %{http_code}\n" http://$ALB_DNS/health
```

**Expected results**:
- Requests 1-3: HTTP 200
- Requests 4-10: HTTP 403 (rate limit triggered)
- After 65 second wait: HTTP 200 (limit reset)

**Validation**:
- Rate limiting triggers within 3-5 rapid requests
- Limit resets after 1 minute window

---

### Task 17: Test WAF toggle (disable WAF)
**Directory**: `demo/infra/advworks/dev/`
**Action**: TEST
**Pattern**: Follow spec.md Test 5 (lines 444-458)

**Commands**:
```bash
# Edit spec.yml - change enabled: true → false
vim spec.yml

# Apply to remove WAF
terraform plan  # Should show WAF resources being destroyed
terraform apply -auto-approve

# Test previously blocked paths (should now work)
echo "Testing without WAF..."
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/admin
curl -w "\nHTTP %{http_code}\n" http://$ALB_DNS/.env
```

**Expected results**:
- All paths return 200 (no WAF blocking)
- JSON shows request paths correctly
- Demonstrates WAF toggle functionality

**Validation**:
- WAF resources destroyed cleanly
- Previously blocked paths now accessible
- Idempotent (re-running terraform plan shows no changes)

---

### Task 18: Verify Terraform outputs
**Directory**: `demo/infra/advworks/dev/`
**Action**: TEST
**Pattern**: Follow spec.md Test 6 (lines 460-469)

**Commands**:
```bash
terraform output
```

**Expected outputs**:
```
instance_id = "i-xxxxx"
public_ip = "xx.xx.xx.xx"
instance_name = "advworks-dev-web1"
demo_url = "http://xx.xx.xx.xx/"
security_group_id = "sg-xxxxx"
alb_dns_name = "advworks-dev-alb-xxxxx.us-east-2.elb.amazonaws.com"
alb_arn = "arn:aws:elasticloadbalancing:us-east-2:..."
alb_url = "http://advworks-dev-alb-xxxxx.us-east-2.elb.amazonaws.com/"
waf_enabled = false (or true, depending on current state)
waf_web_acl_id = "" (or actual ID if enabled)
waf_web_acl_arn = "" (or actual ARN if enabled)
```

**Validation**:
- All expected outputs present
- ALB DNS name accessible via browser
- WAF outputs conditional based on enabled state

---

## Risk Assessment

**Risk**: ALB health checks fail due to path filtering blocking `/health`
**Mitigation**: Health check path `/health` matches WAF allowed paths. If issues occur, verify regex pattern allows exact match `^/health$`.

**Risk**: Rate limiting blocks health checks
**Mitigation**: Rate limiting is per IP. ALB health checks come from AWS IP ranges and won't exceed 100 req/min (checks every 30s = 2 req/min).

**Risk**: Managed rule groups block legitimate traffic
**Mitigation**: Demo uses simple echo container with no complex inputs. If blocks occur, check CloudWatch metrics to identify which rule triggered, consider excluding that rule.

**Risk**: Multi-AZ subnet requirement fails in regions with < 2 AZs
**Mitigation**: Using default VPC which typically has subnets in multiple AZs. If single-AZ region used, ALB creation will fail with clear error message.

**Risk**: Container image `mendhak/http-https-echo` unavailable or changes behavior
**Mitigation**: Popular image (1.5k+ stars), stable. If unavailable, can substitute `ealen/echo-server` with minimal changes.

**Risk**: WAF regex pattern syntax errors
**Mitigation**: Using simple regex patterns tested in spec. Pattern `^/health$` and `^/api/v1/.*` are standard POSIX regex supported by WAFv2.

## Integration Points

**ALB Integration**:
- References `aws_instance.pod.id` for target group attachment
- References `local.vpc_id` from data.tf for security group and target group
- References `aws_security_group.alb.id` for ALB security groups

**WAF Integration**:
- References `aws_lb.main.arn` for WAF association
- References `aws_wafv2_regex_pattern_set.allowed_paths[0].arn` for path filtering rule
- Conditional creation tied to `var.waf_enabled`

**Security Group Integration**:
- EC2 security group adds ingress rule referencing `aws_security_group.alb.id`
- Maintains existing 0.0.0.0/0 HTTP access for demo contrast

**Outputs Integration**:
- New ALB outputs provide DNS name for testing
- WAF outputs use conditional expressions to handle enabled/disabled states

## VALIDATION GATES (MANDATORY)

**CRITICAL**: Terraform has different validation than application code. For this infrastructure-only change:

**Gate 1: Terraform Validate**
```bash
cd demo/tfmodules/pod
terraform validate
```
Must pass with no errors.

**Gate 2: Terraform Plan (Syntax Check)**
```bash
cd demo/infra/advworks/dev
terraform init
terraform plan
```
Must complete without syntax errors. Review plan output for expected resources.

**Gate 3: Manual Testing**
Follow Tasks 13-18 for comprehensive testing:
- ALB routing works
- Health checks pass
- WAF path filtering blocks/allows correctly
- Rate limiting triggers
- WAF toggle works (enable/disable)
- Direct EC2 access demonstrates WAF bypass

**Enforcement Rules**:
- If terraform validate fails → Fix syntax immediately
- If terraform plan fails → Fix resource configuration
- If manual tests fail → Debug using CloudWatch logs, AWS console
- After 3 failed attempts → Stop and ask for help

**Note**: No Python/mypy/pytest validation needed (infrastructure only).

## Validation Sequence

**After each Terraform task (1-11)**:
```bash
cd demo/tfmodules/pod
terraform validate
```

**After completing all Terraform code (Task 12)**:
```bash
cd demo/infra/advworks/dev
terraform init -upgrade
terraform validate
terraform plan
```

**Final validation (Tasks 13-18)**:
- Full integration testing with actual AWS resources
- Verify all success criteria from spec.md (lines 473-503)

## Plan Quality Assessment

**Complexity Score**: 5/10 (WELL-SCOPED)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec with complete Terraform examples
✅ Similar patterns found in Phase D1 codebase (`security_groups.tf`, `data.tf`)
✅ All clarifying questions answered (container choice, security stance, path filtering)
✅ Existing conditional resource pattern to follow (count-based resources)
✅ Terraform AWS provider well-documented, stable resources (ALB, WAF)
✅ Demo-focused (no production edge cases to handle)
⚠️ WAF regex pattern set - minor risk if syntax issues (mitigated: simple patterns)
⚠️ Rate limiting behavior - may need tuning if 100 req/min too aggressive (mitigated: can adjust in waf.tf)

**Assessment**: High confidence implementation. Phase D1 provides solid foundation, AWS resources are straightforward, and spec includes complete examples. Main risks are WAF configuration edge cases, mitigated by comprehensive testing.

**Estimated one-pass success probability**: 85%

**Reasoning**:
- Terraform syntax validation catches most errors early
- AWS provider handles resource dependencies automatically
- Complete testing suite (Tasks 13-18) validates all functionality
- 15% risk allocated to: WAF regex edge cases, rate limiting tuning, multi-AZ subnet availability, unforeseen AWS API behaviors

---

## Summary

**Total Tasks**: 18 (11 implementation + 7 testing)
**Files Created**: 2 (alb.tf, waf.tf)
**Files Modified**: 4 (ec2.tf, security_groups.tf, data.tf, outputs.tf)
**Files Verified**: 1 (spec.yml)

**Critical Path**:
1. Update EC2 container (Task 1)
2. Create ALB infrastructure (Tasks 2-6)
3. Update security groups (Task 7)
4. Create WAF resources (Tasks 8-10)
5. Add outputs (Task 11)
6. Comprehensive testing (Tasks 13-18)

**Ready to build!**
