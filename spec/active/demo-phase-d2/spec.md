# Feature: Demo Phase D2 - ALB + Conditional WAF

## Origin
This specification follows Phase D1 (Foundation Infrastructure) of the spec-editor demo. Phase D1 established the basic EC2 infrastructure with naming conventions and Docker-based http-echo service. Phase D2 adds production-grade networking with Application Load Balancer and optional Web Application Firewall.

## Outcome
Complete the infrastructure modules with ALB routing and conditional WAF protection, enabling the demo to showcase both traffic management and security features that customers need.

**What changes**:
- EC2 instances become targets behind an ALB instead of direct access
- WAF protection can be toggled on/off via Terraform variable
- Infrastructure pattern supports production-grade multi-tenant deployments

## User Story
As a **customer deploying production infrastructure**
I want **my application servers behind a load balancer with optional WAF protection**
So that **I can distribute traffic, enable health checks, and protect against common web attacks**

## Context

**Current State** (after Phase D1):
- ✅ EC2 instances with proper naming convention (`{customer}-{env}-{instance_name}`)
- ✅ Terraform module structure (`demo/tfmodules/pod/`)
- ✅ http-echo running on EC2 instances via Docker user_data
- ✅ Single pod deployed (`advworks/dev`)
- ⚠️ EC2 instances exposed directly (no load balancer)
- ⚠️ No WAF protection

**Desired State** (after Phase D2):
- ✅ ALB routes traffic to EC2 instances
- ✅ Security groups properly configured (ALB ↔ EC2)
- ✅ WAF can be conditionally created and associated with ALB
- ✅ Infrastructure ready for multi-tenant scaling in Phase D7

**Why This Matters**:
This phase addresses two of the three customer pain points:
1. **Unwanted traffic to app servers** - WAF blocks malicious requests via path filtering and rate limiting
2. **Production readiness** - ALB provides health checks and traffic distribution

**Customer Value Demonstrated**:
- Path filtering shows immediate, visible protection (try `/admin` → blocked)
- Rate limiting proves DDoS protection (3-5 rapid requests → blocked)
- Both features are simple curl tests that clearly show WAF working

**Future Evolution** (out of scope for Phase D2):
- Path regex patterns could be exposed in Flask UI form (currently hardcoded)
- Would enable customers to customize allowed paths per environment
- Example: Dev allows all paths, Staging/Prod restrict to specific APIs

## Technical Requirements

### ALB Module (`demo/tfmodules/pod/alb.tf`)

1. **Application Load Balancer**
   - Name: `{customer}-{env}-alb`
   - Scheme: `internet-facing`
   - Load balancer type: `application`
   - Subnets: Use default VPC subnets (multi-AZ for production readiness)
   - Security group: Allow inbound HTTP (port 80) from `0.0.0.0/0`
   - Tags: Standard tagging (`Customer`, `Environment`, `ManagedBy`)

2. **Target Group**
   - Name: `{customer}-{env}-tg`
   - Protocol: `HTTP`
   - Port: `80`
   - Target type: `instance`
   - Health check:
     - Path: `/`
     - Matcher: `200`
     - Interval: `30s`
     - Timeout: `5s`
     - Healthy threshold: `2`
     - Unhealthy threshold: `2`
   - Register EC2 instance as target

3. **Listener**
   - Protocol: `HTTP`
   - Port: `80`
   - Default action: Forward to target group

4. **Security Group for ALB**
   - Ingress: HTTP (port 80) from `0.0.0.0/0`
   - Egress: All traffic (for health checks to instances)

5. **Security Group Updates for EC2**
   - Add ingress rule: HTTP (port 80) from ALB security group
   - Keep existing rules (SSH, etc.)

### WAF Module (`demo/tfmodules/pod/waf.tf`)

1. **Conditional Resource Creation**
   ```hcl
   resource "aws_wafv2_web_acl" "main" {
     count = var.waf_enabled ? 1 : 0
     # ... WAF configuration
   }

   resource "aws_wafv2_web_acl_association" "alb" {
     count = var.waf_enabled ? 1 : 0
     # ... Association configuration
   }
   ```

2. **WAF Web ACL Configuration**
   - Name: `{customer}-{env}-waf`
   - Scope: `REGIONAL` (for ALB)
   - Default action: `ALLOW`
   - **Custom Rules** (evaluated in priority order):
     - **Rule 1 - Rate Limiting** (Priority: 1):
       - Name: `RateLimitRule`
       - Action: `BLOCK`
       - Limit: `100 requests per 1 minute` per IP
       - Demonstrates: DDoS protection
     - **Rule 2 - Path Blocklist** (Priority: 2):
       - Name: `BlockUnauthorizedPaths`
       - Action: `BLOCK`
       - Match: URI path does NOT match `^/(health|api/v1/.*)$`
       - Logic: Block requests to any path except /health or /api/v1/*
       - Demonstrates: Path-based access control (allowlist pattern)
   - **Managed rule groups** (Priority: 3+):
     - `AWSManagedRulesCommonRuleSet` (OWASP Top 10)
     - `AWSManagedRulesKnownBadInputsRuleSet` (bad inputs)
   - CloudWatch metrics enabled

3. **WAF Association**
   - Associate WAF ACL with ALB ARN
   - Only created when `var.waf_enabled = true`

### Variables (`demo/tfmodules/pod/variables.tf`)

Add new variable:
```hcl
variable "waf_enabled" {
  description = "Enable WAF protection for ALB"
  type        = bool
  default     = false
}
```

### Outputs (`demo/tfmodules/pod/outputs.tf`)

Add new outputs:
```hcl
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "waf_enabled" {
  description = "Whether WAF is enabled"
  value       = var.waf_enabled
}

output "waf_web_acl_id" {
  description = "ID of WAF Web ACL (empty if disabled)"
  value       = var.waf_enabled ? aws_wafv2_web_acl.main[0].id : ""
}
```

### Update spec.yml

Ensure `spec.yml` includes WAF configuration:
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
      enabled: false  # <-- Can be toggled
```

## Implementation Notes

### Security Group Flow
```
Internet → ALB Security Group (0.0.0.0/0:80)
         → ALB
         → EC2 Security Group (ALB SG:80)
         → EC2 Instance
```

### Conditional WAF Pattern
- Using `count` for conditional creation (not `for_each`)
- WAF resources only created when `var.waf_enabled = true`
- Must use array access: `aws_wafv2_web_acl.main[0].id`
- Outputs handle conditional: `var.waf_enabled ? resource[0].id : ""`

### WAF Custom Rules Configuration
**Implementation** (in `waf.tf`):
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
}

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

  # Rule 2: Path blocklist (priority 2)
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

  # Managed rule groups (priority 3+)
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 3
    # ...
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.customer}-${var.environment}-waf"
    sampled_requests_enabled   = true
  }
}
```

**Rule Behaviors**:

1. **Rate Limiting** (Priority 1):
   - `limit = 100`: Maximum 100 requests per 1-minute window
   - `aggregate_key_type = "IP"`: Per source IP address
   - **Demo-aggressive**: ~3-5 rapid curl requests trigger the limit
   - CloudWatch metrics: `{customer}-{env}-rate-limit`

2. **Path Filtering** (Priority 2):
   - Regex pattern set defines allowed paths: `/health`, `/api/v1/*`
   - Uses `not_statement` to block non-matching paths
   - **Demo scenarios**:
     - `GET /health` → 200 OK ✅
     - `GET /api/v1/users` → 200 OK ✅
     - `GET /admin` → 403 BLOCKED ✅
     - `GET /` → 403 BLOCKED ✅
   - CloudWatch metrics: `{customer}-{env}-path-block`

**Note**: AWS WAFv2 evaluates rules in priority order. Rate limiting (priority 1) is checked before path filtering (priority 2).

### Data Sources Required
```hcl
# demo/tfmodules/pod/data.tf
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
```

## Test Criteria

### Test 1: ALB with WAF Disabled (Default)
```bash
cd demo/infra/advworks/dev
terraform plan
# Should show:
# - ALB, target group, listener
# - Security groups
# - NO WAF resources

terraform apply -auto-approve

# Get ALB DNS
ALB_DNS=$(terraform output -raw alb_dns_name)

# Wait for health checks (~60s)
sleep 60

# Test ALB routing to EC2
curl http://$ALB_DNS/
# Expected: "Hello from AdventureWorks Development"
```

### Test 2: Enable WAF via spec.yml
```bash
# Edit spec.yml
# Change: enabled: false → true

terraform plan
# Should show:
# + aws_wafv2_web_acl.main[0]
# + aws_wafv2_web_acl_association.alb[0]

terraform apply -auto-approve

# Test normal request (should pass)
curl http://$ALB_DNS/
# Expected: 200 response with "Hello from AdventureWorks Development"

# Test malicious pattern (should block)
curl http://$ALB_DNS/.env
# Expected: 403 Forbidden (WAF block)

# Test scanner pattern
curl -A "sqlmap" http://$ALB_DNS/
# Expected: 403 Forbidden (WAF block)
```

### Test 3: Path Filtering (Allowlist)
```bash
# Test allowed paths
echo "Testing allowed paths..."
curl -w "HTTP %{http_code}\n" http://$ALB_DNS/health
# Expected: HTTP 200 (allowed)

curl -w "HTTP %{http_code}\n" http://$ALB_DNS/api/v1/users
# Expected: HTTP 200 (allowed - matches ^/api/v1/.*)

curl -w "HTTP %{http_code}\n" http://$ALB_DNS/api/v1/orders/123
# Expected: HTTP 200 (allowed - matches ^/api/v1/.*)

# Test blocked paths
echo "Testing blocked paths..."
curl -w "HTTP %{http_code}\n" http://$ALB_DNS/
# Expected: HTTP 403 (blocked - root not in allowlist)

curl -w "HTTP %{http_code}\n" http://$ALB_DNS/admin
# Expected: HTTP 403 (blocked - not in allowlist)

curl -w "HTTP %{http_code}\n" http://$ALB_DNS/api/v2/users
# Expected: HTTP 403 (blocked - only v1 API allowed)

curl -w "HTTP %{http_code}\n" http://$ALB_DNS/.env
# Expected: HTTP 403 (blocked by path filter, also would be blocked by managed rules)
```

### Test 4: Rate Limiting (Demo-Aggressive)
```bash
# Test rapid requests exceed rate limit (100 req/min = very low threshold)
echo "Testing rate limiting with rapid requests..."
for i in {1..10}; do
  echo -n "Request $i: "
  curl -s -o /dev/null -w "HTTP %{http_code}\n" http://$ALB_DNS/
done

# Expected output (100 req/min = ~1.67 req/sec):
# Request 1: HTTP 200
# Request 2: HTTP 200
# Request 3: HTTP 200
# Request 4: HTTP 403  ← Rate limit triggered!
# Request 5: HTTP 403
# Request 6: HTTP 403
# ...
# (Limit triggers after 3-5 rapid requests)

# Verify blocked requests don't reach EC2
docker logs $(docker ps -q --filter "name=demo-app") --tail 20
# Should only see 3-4 log entries (before rate limit kicked in)
# Demonstrates WAF protecting upstream service from flood

# Wait 60+ seconds for rate limit window to reset
sleep 65
curl http://$ALB_DNS/
# Expected: HTTP 200 (limit reset)
```

### Test 5: Disable WAF (Idempotency)
```bash
# Change back: enabled: true → false

terraform plan
# Should show:
# - aws_wafv2_web_acl.main[0]
# - aws_wafv2_web_acl_association.alb[0]

terraform apply -auto-approve

# Verify WAF removed
curl http://$ALB_DNS/.env
# Expected: 200 or 404 (not 403 - no WAF blocking)
```

### Test 6: Outputs
```bash
terraform output
# Should show:
# instance_id = "i-xxxxx"
# alb_dns_name = "advworks-dev-alb-xxxxx.us-east-2.elb.amazonaws.com"
# alb_arn = "arn:aws:elasticloadbalancing:us-east-2:..."
# waf_enabled = true/false
# waf_web_acl_id = "xxxx" or ""
```

## Validation Criteria

**Must Pass**:
- [ ] ALB created with correct naming convention
- [ ] Target group registers EC2 instance successfully
- [ ] Health checks pass after ~60 seconds
- [ ] HTTP traffic routes through ALB to EC2
- [ ] Security groups allow ALB → EC2 communication
- [ ] WAF creates/destroys based on `var.waf_enabled`
- [ ] WAF blocks malicious requests when enabled (`.env`, `sqlmap`)
- [ ] **Path filtering allows `/health` and `/api/v1/*`**
- [ ] **Path filtering blocks `/`, `/admin`, `/api/v2/*`, etc.**
- [ ] **Rate limiting triggers after 3-5 rapid requests (100 req/min)**
- [ ] **Blocked requests return 403 and don't reach EC2**
- [ ] Terraform apply is idempotent (no changes on re-run)
- [ ] Module outputs include ALB DNS and WAF status

**Should Not Happen**:
- ❌ Direct EC2 access bypasses ALB (optional - can lock down)
- ❌ Health checks fail or timeout
- ❌ WAF blocks legitimate traffic
- ❌ Terraform errors when toggling WAF on/off
- ❌ Security group conflicts or circular dependencies

## Success Criteria

**Working Infrastructure When**:
- ✅ Can access http-echo via ALB DNS name
- ✅ EC2 instance shows healthy in target group
- ✅ WAF toggle works: `false → true → false` without errors
- ✅ WAF blocks common attack patterns (`.env`, `sqlmap`)
- ✅ Module outputs provide necessary information for Flask app
- ✅ Pattern ready to scale to 9 pods in Phase D7

**Demonstration Flow**:
1. Show current state: EC2 only (Phase D1)
2. Apply Phase D2: Add ALB + WAF (enabled)
3. **Test path filtering**:
   - `curl /health` → 200 OK ✅
   - `curl /api/v1/users` → 200 OK ✅
   - `curl /admin` → 403 BLOCKED ✅
   - `curl /` → 403 BLOCKED ✅
4. Test malicious patterns: `.env`, `sqlmap` → Blocked ✅
5. **Test rate limiting**: Run rapid curl loop (100 req/min limit)
   - First 3-5 requests: 200 OK ✅
   - Requests 4-6+: 403 Forbidden ✅
   - Verify EC2 logs only show 3-5 successful requests (blocked requests never reach backend)
6. Disable WAF via spec.yml
7. Test blocked paths: Now accessible (demonstrates toggle)

## Dependencies

**Requires (Phase D1)**:
- ✅ EC2 instance with http-echo running
- ✅ Terraform module structure (`demo/tfmodules/pod/`)
- ✅ spec.yml with security.waf configuration
- ✅ AWS credentials configured

**Provides (for Phase D3)**:
- ✅ ALB DNS name for workflow outputs
- ✅ WAF toggle pattern for Flask UI
- ✅ Complete infrastructure module ready for automation

## Phase Scope

**In Scope**:
- ALB with target group and listener
- WAF with AWS managed rule sets
- **Custom WAF rules**:
  - Rate limiting rule (100 req/min per IP)
  - Path filtering rule (allowlist: `/health`, `/api/v1/*`)
- Conditional WAF creation via Terraform count
- Security group configuration
- Health checks
- Demo scripts to test path filtering and rate limiting

**Out of Scope** (Future Phases):
- HTTPS/TLS (demo uses HTTP only)
- **Configurable path regex via spec.yml** (hardcoded for Phase D2, could be exposed in Flask UI later)
- Route53 DNS records (using ALB DNS directly)
- Multiple EC2 instances behind ALB (single instance for demo)
- Cross-zone load balancing configuration
- Access logs for ALB/WAF
- Auto Scaling Groups
- Additional custom WAF rules (SQL injection detection, XSS, etc.)

## File Changes

```
demo/tfmodules/pod/
  ├── alb.tf          # NEW: ALB, target group, listener
  ├── waf.tf          # NEW: Conditional WAF resources
  ├── ec2.tf          # MODIFY: Add security group ingress from ALB
  ├── variables.tf    # MODIFY: Add waf_enabled variable
  ├── outputs.tf      # MODIFY: Add ALB and WAF outputs
  └── data.tf         # MODIFY: Add VPC/subnet data sources

demo/infra/advworks/dev/
  └── spec.yml        # VERIFY: Has security.waf.enabled field
```

## Effort Estimate
**1-2 hours** (as documented in demo/SPEC.md)

Breakdown:
- ALB module: 30-45 min
- WAF module: 30-45 min
- Testing and validation: 30 min

## Next Steps
After Phase D2 completion → **Phase D3: GitHub Action - Workflow Dispatch**
