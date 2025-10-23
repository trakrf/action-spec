# Feature: Demo Phase D1 - Foundation Infrastructure & Terraform Module

## Origin
This specification implements Phase D1 of the spec-editor demo project (see `demo/SPEC.md`). This is the foundation phase that establishes the infrastructure pattern before scaling to multiple customers and environments.

## Outcome
A working Terraform module pattern that:
1. Reads configuration from YAML spec files
2. Deploys EC2 instances with customer-specific naming conventions
3. Makes instances immediately testable via HTTP
4. Proves the pattern works before scaling to 9 pods in Phase D7

After Phase D1: Can manually deploy `advworks/dev` pod with correct naming (`advworks-dev-web1`) and verify it's accessible.

## User Story
As a DevOps engineer demonstrating infrastructure automation
I want to establish a reusable Terraform module pattern driven by YAML specs
So that I can prove the concept works before scaling to multiple customers/environments

## Context

**Discovery**: Customer has three pain points:
1. Instance naming chaos ("host1" doesn't identify customer/environment)
2. Manual workflow inputs (typing 15 fields every deployment)
3. Unwanted traffic to app servers (need WAF protection)

**Current State**: Planning phase complete, ready to build

**Desired State**: Working Terraform module that:
- Reads from spec.yml (yamldecode pattern)
- Creates EC2 with naming convention: `{customer}-{environment}-{instance_name}`
- Runs http-echo via user_data (Docker) for immediate testability
- Can be replicated for 9 pods (Phase D7)

**Strategy**: Start with ONE pod (advworks/dev) to prove pattern, then scale

## Technical Requirements

### File Structure
```
demo/
  infra/
    advworks/
      dev/
        main.tf          # Implementation (calls module)
        spec.yml         # Configuration
        backend.tf       # S3 state config
  tfmodules/
    pod/                 # Reusable module
      main.tf           # Module orchestration
      ec2.tf            # EC2 resource
      variables.tf      # Module inputs
      outputs.tf        # Module outputs
      data.tf           # AMI lookup, etc
```

### spec.yml Schema
```yaml
apiVersion: v1
kind: Pod
metadata:
  customer: advworks       # Used in naming
  environment: dev         # Used in naming
spec:
  compute:
    instance_name: web1    # User-friendly name
    instance_type: t4g.nano  # ARM-based, cheap
    demo_message: "Hello from AdventureWorks Development"
  security:
    waf:
      enabled: false       # Phase D1: no WAF yet (Phase D2)
```

### Implementation Pattern
```hcl
# demo/infra/advworks/dev/main.tf
locals {
  spec = yamldecode(file("${path.module}/spec.yml"))
}

module "pod" {
  source = "../../../tfmodules/pod"

  customer      = local.spec.metadata.customer
  environment   = local.spec.metadata.environment
  instance_name = local.spec.spec.compute.instance_name
  instance_type = local.spec.spec.compute.instance_type
  demo_message  = local.spec.spec.compute.demo_message
  waf_enabled   = local.spec.spec.security.waf.enabled
}

output "instance_id" {
  value = module.pod.instance_id
}

output "demo_url" {
  value = module.pod.demo_url
  description = "Test the app at this URL (wait ~2 min after apply)"
}
```

### Module Requirements

**EC2 Resource** (`demo/tfmodules/pod/ec2.tf`):
- Use latest Ubuntu AMI (data source lookup)
- Instance type from spec
- **Network configuration**:
  - `associate_public_ip_address = true` (required for demo access)
  - Default VPC/subnet acceptable for Phase D1
  - Security group: allow inbound 80 (HTTP) and 22 (SSH) from anywhere (demo only)
- User data script:
  - Install Docker via get.docker.com
  - Run hashicorp/http-echo on port 80
  - Auto-restart on failure
- Tags:
  - `Name`: `{customer}-{environment}-{instance_name}` (e.g., "advworks-dev-web1")
  - `Customer`: from spec
  - `Environment`: from spec
  - `ManagedBy`: "Terraform"

**Variables** (`demo/tfmodules/pod/variables.tf`):
- `customer` (string)
- `environment` (string)
- `instance_name` (string)
- `instance_type` (string, default: "t4g.nano")
- `demo_message` (string)
- `waf_enabled` (bool, default: false) - for Phase D2

**Outputs** (`demo/tfmodules/pod/outputs.tf`):
- `instance_id` - EC2 instance ID
- `public_ip` - Public IP address
- `instance_name` - Full name tag value
- `demo_url` - Friendly output: `http://{public_ip}/` for easy testing

**Backend Config** (`demo/infra/advworks/dev/backend.tf`):
- S3 backend for state storage
- Use existing action-spec S3 bucket from Phase 1
- Key: `demo/advworks/dev/terraform.tfstate`

### User Data Script
```bash
#!/bin/bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Run http-echo on boot
docker run -d \
  --name demo-app \
  --restart unless-stopped \
  -p 80:5678 \
  hashicorp/http-echo:latest \
  -text="${var.demo_message}"
```

**Timing**: ~2 minutes for Docker install + container start

## Validation Criteria

### Acceptance Tests
```bash
cd demo/infra/advworks/dev
terraform init
# ✅ Should initialize without errors
# ✅ Should show module source: "../../../tfmodules/pod"

terraform plan
# ✅ Should show EC2 instance creation
# ✅ Should show Name tag: "advworks-dev-web1"
# ✅ Should show user_data with Docker install

terraform apply -auto-approve
# ✅ Should create EC2 instance successfully
# ✅ Should output: demo_url = "http://1.2.3.4/"

# Wait for user_data to complete
sleep 120

# Test http-echo is running (use URL from output)
curl $(terraform output -raw demo_url)
# ✅ Should return: "Hello from AdventureWorks Development"

# Alternative: copy/paste URL from output into browser
```

### Success Criteria
- [ ] spec.yml file created with correct schema
- [ ] Module structure exists in demo/tfmodules/pod/
- [ ] Implementation calls module from demo/infra/advworks/dev/
- [ ] Terraform init/plan/apply succeeds
- [ ] EC2 instance created with name: "advworks-dev-web1"
- [ ] Instance has public IP assigned
- [ ] Instance tagged with Customer, Environment, ManagedBy
- [ ] Security group allows HTTP (80) and SSH (22)
- [ ] Terraform outputs `demo_url` with clickable HTTP link
- [ ] Instance accessible via HTTP after ~2 minutes
- [ ] http-echo returns expected demo_message
- [ ] Pattern is reusable (ready for Phase D7 scaling)

## Constraints

### Phase D1 Scope Limitations
- **ONE pod only**: advworks/dev (not 9 pods - that's Phase D7)
- **EC2 only**: No ALB, no WAF (those come in Phase D2)
- **Manual testing**: No automation yet (GitHub Actions in Phase D3)
- **Basic networking**: Default VPC acceptable for demo
- **Simple security group**: Allow 80/22 from anywhere (demo only - will tighten in Phase D2)

### Out of Scope
- ❌ Multiple pods (Phase D7)
- ❌ ALB configuration (Phase D2)
- ❌ WAF configuration (Phase D2)
- ❌ GitHub Actions workflow (Phase D3)
- ❌ Flask frontend (Phase D4-D5)
- ❌ Docker packaging (Phase D6)
- ❌ ACM certificates / HTTPS (extra credit - HTTP sufficient for demo)

## Design Decisions

**Why start with one pod?**
- Prove pattern works before scaling
- Faster iteration during development
- Easier debugging with fewer moving parts
- Phase D7 becomes practice reps (copy/paste 8 more times)

**Why user_data instead of custom AMI?**
- No AMI baking pipeline needed
- Easy to modify (just change user_data)
- Boots in ~2 minutes (acceptable for demo)
- Shows modern containerized approach

**Why t4g.nano?**
- Cheapest option (~$3/month)
- ARM-based (modern)
- Sufficient for http-echo demo

**Why yamldecode pattern?**
- Keeps config separate from Terraform code
- Familiar format for customers (YAML > HCL for config)
- Easy to version control and review
- Scales to 9 pods without code duplication

**Why module structure?**
- Reusable across all 9 pods
- Testable in isolation
- Follows Terraform best practices
- Can version/tag modules later if needed

## Next Steps (After D1)

**Phase D2**: Add ALB + conditional WAF to module
**Phase D3**: GitHub Actions workflow_dispatch integration
**Phase D4**: Flask app to read specs
**Phase D5**: Flask app to trigger workflows
**Phase D6**: Docker packaging and EC2 deployment
**Phase D7**: Scale to 9 pods, integration testing, demo scripts

## References

- Full demo spec: `demo/SPEC.md`
- Related: Customer pain points (naming, manual inputs, WAF protection)
- Existing infrastructure: Phase 1 S3 backend from PRD.md
