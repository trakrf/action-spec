# Feature: Multi-Cloud Infrastructure Restructure

## Metadata
**Workspace**: infrastructure
**Type**: refactor

## Origin
Prerequisite for Azure and GCP deployment support. This emerged from the need to support multiple cloud providers while keeping the existing AWS deployment intact.

**Context**: Azure and GCP clients require platform-specific deployments, but we want to maintain AWS as well. Need clean directory structure to support all three.

## Outcome
Infrastructure directory restructured to support multiple cloud providers:
- AWS infrastructure moved to `infra/tools/aws/`
- Root README created at `infra/tools/README.md` documenting multi-cloud approach
- Existing AWS deployment continues working without interruption
- Foundation ready for Azure and GCP implementations

## User Story
As a **platform engineer**
I want **a clean multi-cloud directory structure**
So that **we can support AWS, Azure, and GCP deployments without conflicts**

## Context

### Current State
```
infra/tools/
├── main.tf
├── providers.tf
├── backend.tf
├── variables.tf
├── ecr.tf
├── iam.tf
├── secrets.tf
├── outputs.tf
└── README.md
```

All files are AWS-specific (App Runner, ECR, etc.) but the directory name doesn't indicate this.

### Desired State
```
infra/tools/
├── README.md          # Multi-cloud overview
└── aws/              # AWS-specific files
    ├── main.tf
    ├── providers.tf
    ├── backend.tf
    ├── variables.tf
    ├── ecr.tf
    ├── iam.tf
    ├── secrets.tf
    ├── outputs.tf
    └── README.md
```

Ready to add `azure/` and `gcp/` directories alongside `aws/`.

### Why This Matters
- **Clarity**: Directory name indicates cloud provider
- **Scalability**: Easy to add more providers
- **Isolation**: No risk of cross-cloud conflicts
- **Documentation**: Clear entry point for multi-cloud docs
- **Standards**: Follows common multi-cloud repository patterns

## Technical Requirements

### Step 1: Create AWS Subdirectory
```bash
mkdir -p infra/tools/aws
```

### Step 2: Move All Existing Files
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

### Step 3: Verify No Broken References

**Check for relative path references:**
- Backend configuration (S3 bucket paths should be fine)
- Any file references in Terraform
- Any scripts that reference these paths

**Files to check:**
- `backend.tf` - S3 bucket path (should be absolute, no changes needed)
- `main.tf` - No relative file paths expected
- Any `.envrc` files that might reference paths

### Step 4: Test AWS Deployment Still Works

```bash
cd infra/tools/aws

# Initialize (may need to reconfigure backend)
tofu init -reconfigure

# Verify state is intact
tofu show

# Verify no changes needed
tofu plan
# Expected: "No changes. Your infrastructure matches the configuration."
```

**Important**: The `-reconfigure` flag tells Terraform to migrate the state location if needed, but since we're using S3 backend with absolute paths, it should find the existing state.

### Step 5: Create Root Multi-Cloud README

**File**: `infra/tools/README.md`

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

### Step 6: Update References in Project

**Files that might reference `infra/tools`:**

1. **GitHub Actions workflows** (if any)
   - Update paths to `infra/tools/aws/`

2. **Documentation** (README, docs/)
   - Update references to point to `infra/tools/aws/`
   - Or update to point to `infra/tools/` (root README)

3. **Scripts** (if any)
   - Update any deployment scripts

4. **.envrc files**
   - Update paths if they reference `infra/tools`

**Search for references:**
```bash
# Find files referencing infra/tools
grep -r "infra/tools" --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=venv --exclude="*.tfstate*" .
```

### Step 7: Verify Terraform Backend

**Important consideration**: When you move Terraform files, the state file location doesn't change (it's in S3), but Terraform needs to know it's the same project.

**Check `backend.tf`:**
```hcl
terraform {
  backend "s3" {
    bucket = "jxp-demo-terraform-backend-store"
    key    = "action-spec/terraform.tfstate"  # This path should stay the same
    region = "us-east-2"
  }
}
```

The `key` should remain the same so Terraform finds the existing state.

## Validation Criteria

- [ ] AWS infrastructure files moved to `infra/tools/aws/`
- [ ] Root README created at `infra/tools/README.md`
- [ ] `tofu init -reconfigure` succeeds in `infra/tools/aws/`
- [ ] `tofu show` displays existing infrastructure (state intact)
- [ ] `tofu plan` shows "No changes" (infrastructure matches config)
- [ ] Existing AWS deployment still accessible and working
- [ ] No broken references found in codebase (`grep -r "infra/tools"`)
- [ ] GitHub Actions workflows updated (if applicable)
- [ ] Documentation updated with new paths
- [ ] `.envrc` files updated (if applicable)

## Success Metrics

- [ ] Zero downtime during restructure
- [ ] Terraform state preserved and accessible
- [ ] All existing functionality works identically
- [ ] Time to restructure: <30 minutes
- [ ] Clear foundation for Azure/GCP additions

## Implementation Notes

### Why This is Low-Risk

1. **State in S3**: Terraform state is remote, not affected by file moves
2. **No code changes**: Only moving files, not changing content
3. **Backend config unchanged**: S3 bucket and key stay the same
4. **Reversible**: Can easily move files back if issues arise

### Potential Issues

**Issue**: `tofu init` can't find state
- **Cause**: Backend configuration changed unexpectedly
- **Fix**: Verify `backend.tf` has correct S3 bucket and key
- **Recovery**: Run `tofu init -reconfigure`

**Issue**: `tofu plan` shows unexpected changes
- **Cause**: File content changed during move
- **Fix**: Verify files with `git diff`
- **Recovery**: Restore from git

**Issue**: Scripts or workflows fail
- **Cause**: Hardcoded paths to `infra/tools/*.tf`
- **Fix**: Update paths to `infra/tools/aws/*.tf`
- **Prevention**: Search for references beforehand

### Testing Strategy

1. **Backup current state** (optional but recommended):
   ```bash
   cd infra/tools
   tofu state pull > backup-$(date +%Y%m%d).tfstate
   ```

2. **Make changes** (move files, create README)

3. **Verify state access**:
   ```bash
   cd infra/tools/aws
   tofu init -reconfigure
   tofu show  # Should show existing infrastructure
   ```

4. **Verify no drift**:
   ```bash
   tofu plan  # Should show "No changes"
   ```

5. **Test deployment** (optional):
   ```bash
   # Make a trivial change
   tofu apply
   ```

## Dependencies

### Prerequisite
- [ ] Existing AWS deployment working
- [ ] Terraform state accessible in S3
- [ ] No pending Terraform changes (`tofu plan` shows no changes)

### Enables
- [ ] Azure deployment implementation (spec: `spec/active/azure-deployment/spec.md`)
- [ ] GCP deployment implementation (spec: `spec/active/gcp-deployment/spec.md`)
- [ ] Future cloud providers (DigitalOcean, etc.)

### Unrelated To
- App Runner Phase 2 Observability (can be done before or after)
- Application code changes
- Docker image changes

## Time Estimate

- **File operations**: 5 minutes
- **Creating root README**: 10 minutes
- **Testing Terraform**: 10 minutes
- **Searching for references**: 5 minutes
- **Updating references**: 5 minutes (if any found)
- **Buffer**: 5 minutes

**Total: 30-40 minutes**

## References

### Related Specs
- Azure deployment: `spec/active/azure-deployment/spec.md`
- GCP deployment: `spec/active/gcp-deployment/spec.md`
- App Runner Phase 2: `spec/active/app-runner-phase2-observability/spec.md` (independent)

### Current Implementation
- AWS infrastructure: `infra/tools/` (to be moved to `infra/tools/aws/`)
- Terraform backend: S3 (`jxp-demo-terraform-backend-store`)

### Documentation Updates Needed
- Main README.md (if it references infra/tools)
- Any deployment docs
- GitHub Actions workflows
