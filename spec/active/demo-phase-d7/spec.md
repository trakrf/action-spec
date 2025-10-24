# Feature: Infrastructure Routing for Self-Hosted Demo (Demo Phase D7)

## Origin
Phases D1-D6 delivered a containerized spec-editor application with CI/CD, but the infrastructure routing doesn't expose both the spec-editor and demo application through the ALB for end-to-end demo. The current setup works for local testing (`docker compose`) but doesn't align with production deployment where both services need to be accessible via path-based routing behind the WAF.

## Outcome
A production-ready demo deployment where:
- Spec-editor is accessible via ALB at `/spec` path
- Echo server (demo app) is accessible via ALB at `/` path
- Both services are protected by WAF
- Docker compose port configuration matches production
- Full "dogfooding" demo narrative: tool managing its own infrastructure

**Shippable**: Yes - enables the complete demo story with WAF validation.

## User Story
**As a** demo presenter
**I want** both spec-editor and demo app accessible through the ALB with path-based routing
**So that** I can demonstrate the full workflow: access the tool, deploy changes, and validate WAF protection

**As a** DevOps engineer
**I want** the spec-editor to manage the infrastructure it runs on
**So that** I can show "dogfooding" - the tool deploying updates to its own hosting environment

**As a** security engineer
**I want** to demonstrate WAF blocking malicious requests to both applications
**So that** I can prove the security layer works for all protected services

## Context

**Discovery**:
- D6 delivered containerized spec-editor with CI/CD (✅ complete)
- Integration testing already validated (✅ done before D6 merge)
- Current deployment workflow includes success message with GitHub Action URL (from D5)
- Manual validation process works: GitHub Actions → AWS Console → curl tests

**Current State** (after D6):
- Spec-editor runs in Docker on EC2 (port 5000)
- Demo app runs in Docker on EC2 (port 8080 mapped to 80)
- ALB exists but doesn't route to spec-editor
- No path-based routing configured
- EC2 security group doesn't allow traffic to port 5000
- Docker compose uses port 8080 (doesn't match production port 80)

**Desired State**:
- Docker compose: demo-app on host port 80 (matches production)
- EC2 security group: allows ingress on port 5000 (spec-editor access)
- ALB listener rules:
  - Path `/spec*` → Target group for spec-editor (port 5000)
  - Path `/*` (default) → Target group for demo app (port 80)
- Health checks for both target groups
- Both services protected by WAF

**Demo Flow Enabled**:
1. Access spec-editor: `http://alb-url/spec` → Form UI
2. Edit pod configuration and deploy
3. Access echo server: `http://alb-url/` → Request echo
4. Test WAF blocking: `curl http://alb-url/malicious-path` → 403 Forbidden
5. Test WAF allowing: `curl http://alb-url/` → 200 OK
6. **Narrative**: "The tool just deployed changes to the infrastructure it's running on"

## Technical Requirements

### 1. Docker Compose Port Alignment

**File**: `demo/docker-compose.yml`

**Change**: Update demo-app port mapping to match production

**Current**:
```yaml
demo-app:
  ports:
    - "8080:8080"
```

**Desired**:
```yaml
demo-app:
  ports:
    - "80:8080"  # Host port 80 matches production
```

**Rationale**: Local docker compose should mirror production port configuration for consistency.

### 2. EC2 Security Group - Spec-Editor Access

**File**: `demo/infra/advworks/dev/main.tf` (or wherever security groups are defined)

**Change**: Add ingress rule for port 5000

**Current**: Security group allows 80, 443, 22 (SSH)

**Add**:
```hcl
# Allow spec-editor access (port 5000)
ingress {
  description = "Spec-editor UI"
  from_port   = 5000
  to_port     = 5000
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]  # Or restrict to trusted IPs
}
```

**Rationale**: ALB needs to reach spec-editor on EC2 port 5000.

### 3. WAF Route Filtering - Allow /spec Path

**File**: `demo/infra/common/main.tf` (or wherever WAF rules are defined)

**Change**: Update WAF allowed paths to include `/spec`

**Current**: WAF may only allow specific paths (e.g., `/`, `/api/*`)

**Add**: Allow `/spec` and `/spec/*` paths to reach spec-editor

**Example** (depends on current WAF implementation):
```hcl
# If using path allowlist
allowed_paths = [
  "/",
  "/api/*",
  "/spec",      # NEW: Allow spec-editor root
  "/spec/*"     # NEW: Allow spec-editor sub-paths
]
```

**Rationale**: Without this, WAF will block access to spec-editor UI.

### 4. ALB Path-Based Routing

**File**: `demo/infra/common/main.tf` (or wherever ALB is defined)

**Changes**:

#### A. Create Target Group for Spec-Editor
```hcl
resource "aws_lb_target_group" "spec_editor" {
  name     = "${var.pod_name}-spec-editor"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"  # Spec-editor home page
    matcher             = "200"
  }

  tags = {
    Name = "${var.pod_name}-spec-editor-tg"
  }
}

# Register EC2 instances with spec-editor target group
resource "aws_lb_target_group_attachment" "spec_editor" {
  for_each         = aws_instance.pod
  target_group_arn = aws_lb_target_group.spec_editor.arn
  target_id        = each.value.id
  port             = 5000
}
```

#### B. Update/Create Target Group for Demo App
```hcl
resource "aws_lb_target_group" "demo_app" {
  name     = "${var.pod_name}-demo-app"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
  }

  tags = {
    Name = "${var.pod_name}-demo-app-tg"
  }
}

# Register EC2 instances with demo-app target group
resource "aws_lb_target_group_attachment" "demo_app" {
  for_each         = aws_instance.pod
  target_group_arn = aws_lb_target_group.demo_app.arn
  target_id        = each.value.id
  port             = 80
}
```

#### C. Add Listener Rules for Path-Based Routing
```hcl
# Rule 1: /spec* → spec-editor target group
resource "aws_lb_listener_rule" "spec_editor" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.spec_editor.arn
  }

  condition {
    path_pattern {
      values = ["/spec*"]
    }
  }
}

# Rule 2: /* (default) → demo-app target group
resource "aws_lb_listener_rule" "demo_app" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.demo_app.arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }
}
```

**Note**: Adjust based on existing ALB configuration. If ALB listener already has default action, path-based rules take precedence by priority.

### 5. Update User Data Script (Optional)

**File**: `demo/infra/advworks/dev/main.tf` (user_data section)

**Consideration**: Ensure both services start on boot

**Current**: Likely starts demo-app on port 80

**Verify**: Both `spec-editor` (port 5000) and `demo-app` (port 80) start via Docker compose or systemd

**Example** (if using docker compose):
```bash
# In user_data script
cd /home/ec2-user/spec-editor
docker compose up -d
```

This should start both services as defined in docker-compose.yml.

### 6. Custom Domain for Demo (Optional, Recommended)

**DNS Configuration**: Point CNAME to demo instance

**Setup**:
1. Create CNAME record in `trakrf.id` DNS:
   ```
   demo.trakrf.id  CNAME  <alb-dns-name>
   ```
   OR point to specific EC2 instance if not using ALB for demo entry

2. Access demo via clean URL:
   - Spec-editor: `http://demo.trakrf.id/spec`
   - Demo app: `http://demo.trakrf.id/`

**Benefits**:
- Professional appearance (vs `ec2-xx-xx-xx-xx.compute-1.amazonaws.com`)
- Easy to remember and share
- Consistent branding
- Can be reused across demo resets

**Note**: DNS propagation may take 5-60 minutes. Set up before demo day.

## Implementation Punch List

### Docker Changes (1 task)
- [ ] Update `demo/docker-compose.yml` - change demo-app port to `80:8080`

### Terraform Changes (4 tasks)
- [ ] Add port 5000 ingress rule to EC2 security group
- [ ] Update WAF allowed paths to include `/spec` and `/spec/*`
- [ ] Create spec-editor target group with health check on `/` (home page)
- [ ] Create demo-app target group with health check on `/` (echo response)

### ALB Routing (2 tasks)
- [ ] Add listener rule: `/spec*` → spec-editor target group (priority 100)
- [ ] Add listener rule: `/*` → demo-app target group (priority 200)

### Testing (5 tasks)
- [ ] Local: `docker compose up`, verify demo-app on port 80
- [ ] Deploy: Apply Terraform changes to advworks/dev pod
- [ ] Verify: Access `http://alb-url/spec` → spec-editor UI loads
- [ ] Verify: Access `http://alb-url/` → echo server responds
- [ ] WAF test: curl malicious path → blocked, curl normal path → allowed

### Optional: Custom Domain (1 task)
- [ ] Create CNAME: `demo.trakrf.id` → ALB DNS name or EC2 public DNS

**Total: 12 tasks (13 with optional domain)**

## Validation Criteria

**Must Pass Before Shipping D7**:

**Docker Compose**:
- [ ] `docker compose up -d` starts both services
- [ ] demo-app accessible on host port 80
- [ ] spec-editor accessible on host port 5000
- [ ] No port conflicts

**Terraform Apply**:
- [ ] `terraform plan` shows expected changes (target groups, rules, security group)
- [ ] `terraform apply` succeeds without errors
- [ ] Resources created: 2 target groups, 2 listener rules, 1 security group rule

**ALB Routing**:
- [ ] `curl http://<alb-url>/spec` returns spec-editor HTML (200 OK)
- [ ] `curl http://<alb-url>/` returns echo server response (200 OK)
- [ ] Both paths route to correct backend services

**Health Checks**:
- [ ] Spec-editor target group shows healthy instances
- [ ] Demo-app target group shows healthy instances
- [ ] ALB considers both target groups healthy

**WAF Protection**:
- [ ] WAF allows `/spec` path (spec-editor accessible)
- [ ] `curl http://<alb-url>/spec` returns 200 OK (not blocked by WAF)
- [ ] `curl http://<alb-url>/` passes through WAF (allowed)
- [ ] `curl http://<alb-url>/<malicious-pattern>` blocked by WAF (403)
- [ ] Both applications protected by WAF rules

**End-to-End Demo Flow**:
- [ ] Access spec-editor at `http://demo.trakrf.id/spec` (or ALB URL)
- [ ] View pod list (e.g., advworks/dev)
- [ ] Edit pod configuration (e.g., change instance count)
- [ ] Submit deployment → GitHub Action triggered
- [ ] Deployment succeeds → infrastructure updated
- [ ] Access demo app at `http://demo.trakrf.id/` → works
- [ ] Test WAF blocking → malicious requests rejected
- [ ] **"Dogfooding" narrative verified**: Tool manages its own infrastructure

**Optional: Custom Domain**:
- [ ] CNAME record resolves: `demo.trakrf.id` → ALB or EC2
- [ ] Professional URL works in demo presentation
- [ ] No 404 or DNS errors

## Success Metrics

**Quantitative**:
- ALB routing latency < 50ms (path-based routing overhead)
- Health check response time < 3s for both services
- Zero 5xx errors after deployment
- Both target groups maintain 100% healthy instances

**Qualitative**:
- Clean demo flow (no manual steps beyond initial access)
- Professional presentation (no errors, smooth transitions)
- Clear security demonstration (WAF visibly blocking attacks)
- "Wow factor" - dogfooding narrative resonates

**Customer Value**:
- Single entry point (ALB) for all demo services
- WAF protection demonstrated on real traffic
- Infrastructure-as-code managing production workload
- Scalable pattern (easy to add more services via path routing)

## Dependencies

**Blocked By**:
- D6 must be complete (Docker packaging) ✅
- Terraform modules must exist for ALB and security groups ✅
- EC2 instances must be running Docker compose ✅

**Blocks**:
- Full demo presentation (depends on this routing)
- WAF demonstration (needs both services accessible)

**Requires**:
- Access to AWS account with Terraform apply permissions
- Existing ALB and EC2 infrastructure (from prior phases)
- Docker compose running on EC2 instances

## Constraints

**Scope Boundaries**:
- No application code changes (only infrastructure)
- No delete functionality (out of scope - safety concerns)
- No scaling to 9 pods yet (want unprovisioned for live demo)
- No UX polish (focus on making existing functionality work)

**Infrastructure Limitations**:
- ALB listener rules limited to 100 per listener (not a concern for 2 rules)
- Health check interval minimum 5 seconds (current: 30s is fine)
- Target group attachment limit: 1000 instances per group (not a concern)

**Demo Constraints**:
- Must be presentable "as-is" (no time for UX improvements)
- Must work reliably (smooth process flow critical)
- Must demonstrate WAF blocking (core value prop)

## Edge Cases Handled

**Docker Compose**:
1. Port 80 already in use → docker compose fails with clear error
2. Both services try to bind same port → Caught in compose config validation
3. Service doesn't start → docker compose logs show error

**Terraform**:
1. Target group already exists → Use data source or import
2. Listener rule priority conflict → Terraform plan shows conflict
3. Health check fails → Target group shows unhealthy, ALB doesn't route

**ALB Routing**:
1. Path pattern overlap (`/spec` vs `/spec/health`) → More specific pattern wins
2. No matching path → Default rule applies (demo-app)
3. Both target groups unhealthy → ALB returns 503

**WAF**:
1. WAF rule blocks legitimate traffic → Review WAF logs, adjust rules
2. WAF allows malicious traffic → Tighten WAF rules
3. WAF not attached to ALB → Traffic passes unfiltered (visible in demo)

## Next Steps After D7

1. **Ship D7** - Infrastructure routing complete
2. **Practice Demo** - Run through full demo flow multiple times
3. **Optional UX Polish** - If time permits, improve UI/styling
4. **Demo Day Prep** - Pre-deploy infrastructure, prepare talking points

## Out of Scope (Future Enhancements)

**Delete Functionality** (D8 candidate):
- Pod deletion via spec-editor UI
- Safety measures: confirmation prompts, dry-run mode
- Terraform destroy automation
- Backup/snapshot before delete

**UX Improvements** (D9 candidate):
- Better CSS/styling (professional look)
- Loading spinners and toast notifications
- Real-time deployment status updates
- Responsive design for mobile

**Advanced Routing** (Future):
- Subdomain-based routing (`spec.example.com`, `app.example.com`)
- HTTPS/TLS termination at ALB
- Custom domain names
- Blue/green deployment routing

---

**Specification Status**: Ready for Planning
**Estimated Effort**: 2-3 hours
**Target PR Size**: ~100 LoC (mostly Terraform HCL)
**Complexity**: 3/10 (Low - standard infrastructure configuration)
