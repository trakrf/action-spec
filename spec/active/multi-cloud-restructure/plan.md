# Implementation Plan: Multi-Cloud Infrastructure Restructure
Generated: 2025-10-31
Specification: spec.md

## Understanding
This is a pure directory restructure to prepare for multi-cloud deployments. We're moving all existing AWS Terraform files from `infra/tools/` into `infra/tools/aws/`, creating a root README to document the multi-cloud approach, and verifying that the existing AWS deployment continues working without interruption. This is a **zero-downtime refactor** that touches no application code - only infrastructure-as-code organization.

The key insight: Terraform state lives in S3 with an absolute path, so moving the `.tf` files doesn't affect state access. We just need to run `tofu init -reconfigure` to tell Terraform where to find the moved files.

## Relevant Files

**Reference Patterns** (existing code to understand):
- `infra/tools/*.tf` - All current AWS infrastructure files
- `infra/tools/backend.tf` - S3 backend configuration (key path must stay same)

**Files to Create**:
- `infra/tools/README.md` - Multi-cloud overview and navigation
- `infra/tools/aws/` - Directory for AWS-specific files

**Files to Move** (not modify):
- `infra/tools/main.tf` → `infra/tools/aws/main.tf`
- `infra/tools/providers.tf` → `infra/tools/aws/providers.tf`
- `infra/tools/backend.tf` → `infra/tools/aws/backend.tf`
- `infra/tools/variables.tf` → `infra/tools/aws/variables.tf`
- `infra/tools/ecr.tf` → `infra/tools/aws/ecr.tf`
- `infra/tools/iam.tf` → `infra/tools/aws/iam.tf`
- `infra/tools/secrets.tf` → `infra/tools/aws/secrets.tf`
- `infra/tools/outputs.tf` → `infra/tools/aws/outputs.tf`
- `infra/tools/README.md` → `infra/tools/aws/README.md`

**Files to Check for References**:
- Root `README.md` - May reference `infra/tools`
- `.github/workflows/*.yml` - May reference `infra/tools`
- Any `.envrc` files
- Any deployment scripts

## Architecture Impact
- **Subsystems affected**: Infrastructure (Terraform only)
- **New dependencies**: None
- **Breaking changes**: None (state preserved, paths updated)

## Task Breakdown

### Task 1: Backup Current Terraform State
**Action**: BACKUP (safety measure)

**Implementation**:
```bash
cd infra/tools
tofu state pull > backup-$(date +%Y%m%d-%H%M%S).tfstate
```

**Purpose**: Safety net in case something goes wrong during restructure.

**Validation**:
- Backup file exists and is not empty
- File contains valid JSON (Terraform state format)

---

### Task 2: Create AWS Subdirectory
**Action**: CREATE

**Implementation**:
```bash
mkdir -p infra/tools/aws
```

**Validation**:
- Directory exists: `test -d infra/tools/aws`

---

### Task 3: Move All Terraform Files to AWS Subdirectory
**Action**: MOVE

**Implementation**:
```bash
cd infra/tools
mv main.tf aws/
mv providers.tf aws/
mv backend.tf aws/
mv variables.tf aws/
mv ecr.tf aws/
mv iam.tf aws/
mv secrets.tf aws/
mv outputs.tf aws/
mv README.md aws/
```

**Validation**:
- All `.tf` files moved: `ls infra/tools/*.tf` should return no results
- All files present in aws/: `ls infra/tools/aws/*.tf` should list all 8 files
- README moved: `test -f infra/tools/aws/README.md`

---

### Task 4: Verify Backend Configuration Unchanged
**Action**: VERIFY

**File**: `infra/tools/aws/backend.tf`

**Check**:
```hcl
terraform {
  backend "s3" {
    bucket = "jxp-demo-terraform-backend-store"
    key    = "action-spec/terraform.tfstate"  # Must stay the same
    region = "us-east-2"
  }
}
```

**Validation**:
- `key` value is exactly `"action-spec/terraform.tfstate"`
- No modifications to backend.tf during move
- Use: `git diff infra/tools/aws/backend.tf`

---

### Task 5: Reinitialize Terraform in New Location
**Action**: CONFIGURE

**Implementation**:
```bash
cd infra/tools/aws
tofu init -reconfigure
```

**Expected Output**:
```
Initializing the backend...
Successfully configured the backend "s3"!
...
Terraform has been successfully initialized!
```

**Validation**:
- Exit code 0 (success)
- `.terraform/` directory created in `infra/tools/aws/`
- No errors about missing state

---

### Task 6: Verify State Intact
**Action**: VERIFY

**Implementation**:
```bash
cd infra/tools/aws
tofu show
```

**Expected Output**: Should display existing infrastructure (App Runner service, ECR repo, IAM roles, secrets, etc.)

**Validation**:
- Output shows existing resources
- No errors about missing state
- Resource count matches pre-move state

---

### Task 7: Verify No Infrastructure Drift
**Action**: VERIFY

**Implementation**:
```bash
cd infra/tools/aws
tofu plan
```

**Expected Output**:
```
No changes. Your infrastructure matches the configuration.
```

**Validation**:
- Exit code 0 (success)
- Output explicitly states "No changes"
- No resources to add/change/destroy

**If drift detected**: STOP and investigate before proceeding.

---

### Task 8: Search for Hardcoded Path References
**Action**: SEARCH

**Implementation**:
```bash
# From repo root
grep -r "infra/tools" \
  --exclude-dir=node_modules \
  --exclude-dir=.git \
  --exclude-dir=venv \
  --exclude-dir=.terraform \
  --exclude="*.tfstate*" \
  --exclude-dir=playwright-report \
  .
```

**Expected Matches**:
- `spec/active/multi-cloud-restructure/spec.md` (the spec itself)
- `spec/active/multi-cloud-restructure/plan.md` (this plan)
- Possibly root README.md
- Possibly GitHub Actions workflows

**Action for each match**: Evaluate if path needs updating to `infra/tools/aws/`

**Validation**:
- All references reviewed
- Non-spec references updated or determined to be safe

---

### Task 9: Create Root Multi-Cloud README
**Action**: CREATE

**File**: `infra/tools/README.md`

**Content** (from spec lines 122-214):
```markdown
# Action-Spec Infrastructure

Multi-cloud deployment configurations for action-spec.

## Available Deployments

### AWS (App Runner + ECR)
- **Path**: `infra/tools/aws/`
- **Services**: App Runner, ECR, Secrets Manager
- **Cost**: ~$10-20/month for demo
- **Status**: ✅ Production-ready
- **Docs**: [infra/tools/aws/README.md](./aws/README.md)

### Azure (Container Apps + ACR)
- **Path**: `infra/tools/azure/`
- **Services**: Container Apps, ACR, Key Vault
- **Cost**: ~$10-20/month for demo
- **Status**: 🚧 Planned
- **Spec**: `spec/active/azure-deployment/spec.md`

### GCP (Cloud Run + Artifact Registry)
- **Path**: `infra/tools/gcp/`
- **Services**: Cloud Run, Artifact Registry, Secret Manager
- **Cost**: ~$5-15/month for demo (scales to zero)
- **Status**: 🚧 Planned
- **Spec**: `spec/active/gcp-deployment/spec.md`

## Quick Start

Choose your cloud provider and follow the respective README:

- **AWS**: `cd infra/tools/aws && cat README.md`
- **Azure**: Coming soon
- **GCP**: Coming soon

All deployments use the same Docker image from the repository root.

## Architecture

All three cloud deployments follow the same pattern:
1. **Container Registry**: Store Docker images
2. **Managed Container Service**: Run the application
3. **Secret Management**: Store GitHub token securely
4. **Auto-scaling**: 1-2 instances based on load
5. **Health Checks**: Monitor `/health` endpoint

## Deployment Philosophy

- **Same Docker image** across all clouds
- **Same environment variables** (GH_REPO, GH_TOKEN, etc.)
- **Infrastructure as Code** using Terraform/OpenTofu
- **Minimal manual steps** (<15 minutes to deploy)
- **Cost-effective** for demo/low-traffic workloads

## Adding a New Cloud Provider

To add a new cloud provider:

1. Create directory: `infra/tools/<cloud>/`
2. Map services to cloud equivalents (see existing implementations)
3. Copy Terraform structure from AWS/Azure/GCP
4. Update this README with new cloud details
5. Create comprehensive README in cloud directory
6. Test deployment end-to-end

## Common Tasks

### Building the Docker Image

All clouds use the same image:
```bash
# From repo root
docker build -t action-spec:latest .
```

### Environment Variables

All clouds need these variables:
- `GH_TOKEN` - GitHub Personal Access Token
- `GH_REPO` - GitHub repository (org/repo format)
- `SPECS_PATH` - Path to specs directory (default: "infra")
- `WORKFLOW_BRANCH` - Branch to deploy (default: "main")

### Terraform State

Each cloud provider has its own state file:
- AWS: S3 backend
- Azure: Azure Storage backend (planned)
- GCP: GCS backend (planned)

No shared state between clouds - they are completely independent.
```

**Validation**:
- File created at correct path
- Content matches template
- Markdown renders correctly

---

### Task 10: Update Any Found References
**Action**: MODIFY

**Depends on**: Task 8 (search results)

**For each reference found**:
- Determine if it needs to point to `infra/tools/aws/` (specific) or `infra/tools/` (general)
- Update accordingly
- Test that reference still works

**Common updates**:
- GitHub Actions: `working-directory: infra/tools/aws`
- Documentation: Update deployment instructions
- Scripts: Update cd commands or paths

**Validation**:
- All references functional after update
- No broken links in documentation

---

### Task 11: Final Verification - Test Existing AWS Deployment
**Action**: VERIFY

**Implementation**:
```bash
# Verify infrastructure is accessible
curl https://<app-runner-url>/health

# Or if URL not known, get from Terraform output
cd infra/tools/aws
tofu output app_runner_url
```

**Validation**:
- Application responds to health check
- No errors or downtime
- Infrastructure unchanged from pre-restructure state

---

### Task 12: Git Commit (Manual Step)
**Action**: COMMIT

**Staging**:
```bash
git add infra/tools/aws/
git add infra/tools/README.md
git add <any updated references>
git status  # Verify only intended files staged
```

**Commit Message**:
```
refactor(infra): restructure for multi-cloud support

Move AWS infrastructure to infra/tools/aws/ subdirectory to prepare
for Azure and GCP deployments. This is a pure directory restructure
with zero functional changes.

Changes:
- Move all AWS Terraform files to infra/tools/aws/
- Create root README.md documenting multi-cloud approach
- Update references to new paths (if any found)
- Verify Terraform state preserved and accessible
- Verify no infrastructure drift

Related: spec/active/multi-cloud-restructure/spec.md
```

**Validation**:
- Clean commit with clear message
- Only restructure changes included
- No accidental infrastructure modifications

---

## Risk Assessment

**Risk**: Terraform can't find existing state after file move
- **Likelihood**: Low (S3 backend uses absolute paths)
- **Mitigation**: Verified `backend.tf` key path unchanged
- **Recovery**: Restore files from git, use backup state if needed

**Risk**: `tofu plan` shows unexpected changes
- **Likelihood**: Very Low (no file content modified)
- **Mitigation**: Git diff verification before commit
- **Recovery**: Restore from git

**Risk**: References break (CI/CD, scripts)
- **Likelihood**: Low (thorough grep search)
- **Mitigation**: Comprehensive search and update in Task 8/10
- **Recovery**: Update missed references as discovered

**Risk**: Application downtime
- **Likelihood**: Zero (no infrastructure changes applied)
- **Mitigation**: This is a file move only, no `tofu apply` needed
- **Recovery**: N/A (infrastructure untouched)

## Integration Points
- **Terraform State**: S3 backend (unchanged)
- **AWS Resources**: No changes (App Runner, ECR, Secrets Manager continue running)
- **Future Work**: Enables Azure/GCP implementations

## VALIDATION GATES (MANDATORY)

This is a Terraform-only refactor with no application code changes, so validation is different:

**After Task 3 (File Move)**:
- Gate 1: All `.tf` files in correct location
- Gate 2: No `.tf` files remaining in `infra/tools/`

**After Task 7 (Terraform Verification)**:
- Gate 1: `tofu init -reconfigure` succeeds
- Gate 2: `tofu show` displays existing infrastructure
- Gate 3: `tofu plan` shows "No changes"

**After Task 10 (Reference Updates)**:
- Gate 1: All found references updated
- Gate 2: No broken links or paths

**Final Gate (Task 11)**:
- Gate 1: Application health check responds
- Gate 2: No infrastructure drift detected

**If ANY gate fails** → Stop and investigate before proceeding.

## Validation Sequence

Since this is infrastructure-only:
1. No lint/typecheck needed (no code changes)
2. No unit tests needed (pure file move)
3. Terraform validation gates (Tasks 5, 6, 7)
4. Application health check (Task 11)

## Plan Quality Assessment

**Complexity Score**: 2/10 (LOW)
- Only 12 tasks, mostly verification
- No code changes, pure file operations
- Well-understood Terraform behavior

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ Terraform state in S3 (unaffected by file moves)
- ✅ No application code changes
- ✅ Comprehensive verification steps
- ✅ Easy rollback (restore from git)
- ✅ Spec includes detailed testing strategy
- ⚠️ Minor risk: might find unexpected references

**Assessment**: This is a low-risk, well-understood refactor with comprehensive verification steps. Terraform's S3 backend makes file moves safe. The most likely issue is finding hardcoded path references, which Task 8 addresses proactively.

**Estimated one-pass success probability**: 95%

**Reasoning**: The only uncertainty is whether we'll find unexpected references to `infra/tools` in scripts or CI/CD. The grep search (Task 8) mitigates this, and any missed references are easy to fix post-restructure. The Terraform operations are deterministic and low-risk.

## Time Estimate

- Tasks 1-3 (Backup, Create, Move): 5 minutes
- Task 4 (Verify backend): 2 minutes
- Task 5-7 (Terraform verification): 10 minutes
- Task 8 (Search references): 5 minutes
- Task 9 (Create README): 5 minutes
- Task 10 (Update references): 5-10 minutes (depends on findings)
- Task 11 (Final verification): 3 minutes
- Task 12 (Git commit): 2 minutes

**Total: 30-40 minutes** (matches spec estimate)
