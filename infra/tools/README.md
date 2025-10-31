# Action-Spec App Runner Deployment (ECR-based)

AWS App Runner deployment for action-spec using OpenTofu/Terraform with ECR container images.

## Prerequisites

- AWS account with credentials configured
- AWS CLI configured with appropriate permissions
- Docker installed and running
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

Expected output: ~13 resources to create (ECR repository, IAM roles, secrets, App Runner service)

### 4. Apply Infrastructure

```bash
tofu apply
```

Type `yes` to confirm. This creates the ECR repository and App Runner service (not yet running).

### 5. Build and Push Docker Image

```bash
# Get ECR repository URL
ECR_REPO=$(tofu output -raw ecr_repository_url)
AWS_REGION=$(tofu output -raw app_runner_service_arn | cut -d: -f4)

# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

# Build image (from repo root)
cd ../..
docker build -t action-spec:latest .

# Tag for ECR
docker tag action-spec:latest $ECR_REPO:latest

# Push to ECR
docker push $ECR_REPO:latest
```

App Runner will automatically detect the new image and deploy it (takes 3-5 minutes).

### 6. Verify Deployment

```bash
cd infra/tools

# Check service status
tofu output app_runner_service_status

# Wait until status is "RUNNING", then test health endpoint
SERVICE_URL=$(tofu output -raw app_runner_service_url)
curl $SERVICE_URL/health

# Expected: {"status": "healthy"}
```

### 7. Access Application

```bash
# Open in browser
SERVICE_URL=$(tofu output -raw app_runner_service_url)
echo "Application URL: $SERVICE_URL"
open $SERVICE_URL  # macOS
# or: xdg-open $SERVICE_URL  # Linux
```

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
| `cpu` | `0.5 vCPU` | vCPU allocation (must include units) |
| `memory` | `1 GB` | Memory (must include units) |
| `max_instances` | `2` | Max auto-scaling instances |

Override via environment variables (`TF_VAR_*`) or create `terraform.tfvars`.

## Troubleshooting

### `tofu init` fails
- Check AWS credentials: `aws sts get-caller-identity`
- Verify S3 bucket exists: `aws s3 ls s3://jxp-demo-terraform-backend-store`

### `tofu plan` fails with "github_token is required"
- Verify `.env.local` has `TF_VAR_github_token=$GH_TOKEN`
- Check environment: `echo $TF_VAR_github_token` (should show token)

### Docker login to ECR fails
- Check AWS credentials: `aws sts get-caller-identity`
- Verify you have ECR permissions: `aws ecr describe-repositories`
- Try re-authenticating: `aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $(tofu output -raw ecr_repository_url)`

### Docker push fails with "denied: Your authorization token has expired"
- ECR tokens expire after 12 hours
- Re-run the `aws ecr get-login-password` command to get a fresh token

### `tofu apply` succeeds but service won't start
- **Check if image exists in ECR**: `aws ecr describe-images --repository-name action-spec`
- If no images, you need to push one first (see step 5)
- Check App Runner console for deployment logs
- Verify GitHub token has correct permissions (for runtime API calls)

### Service status stuck on "OPERATION_IN_PROGRESS"
- Wait 3-5 minutes for image pull and deployment
- Check AWS App Runner console for detailed status
- Verify the Docker image exists in ECR with `:latest` tag

### App Runner can't pull image from ECR
- Verify IAM role has ECR permissions: Check `iam.tf` for `app_runner_ecr` policy
- Check ECR repository exists: `aws ecr describe-repositories --repository-name action-spec`
- Verify image exists: `aws ecr list-images --repository-name action-spec`

## Continuous Deployment

App Runner has **auto-deployment enabled** for ECR. When you push a new image with the `:latest` tag, App Runner automatically:
1. Detects the new image
2. Pulls it from ECR
3. Deploys the new version
4. Health checks the deployment
5. Routes traffic to the new version

To deploy updates:
```bash
# From repo root
docker build -t action-spec:latest .
docker tag action-spec:latest $(cd infra/tools && tofu output -raw ecr_repository_url):latest
docker push $(cd infra/tools && tofu output -raw ecr_repository_url):latest
```

You can also use semantic versioning:
```bash
docker tag action-spec:latest $ECR_REPO:v1.2.3
docker push $ECR_REPO:v1.2.3

# Update App Runner to use specific version
# (requires updating main.tf image_identifier from :latest to :v1.2.3)
```

## Next Steps

After Phase 1 is complete:
- Phase 2: Add CloudWatch monitoring and comprehensive documentation
- Configure custom domain (optional)
- Set up SNS alerts (optional)

## Cleanup

To remove all infrastructure:

```bash
# Stop App Runner service first (faster destroy)
aws apprunner pause-service --service-arn $(tofu output -raw app_runner_service_arn)

# Destroy all resources
tofu destroy
```

**Notes**:
- ECR images are automatically deleted when the repository is destroyed
- Lifecycle policy keeps last 10 tagged images and removes untagged after 1 day
- Secrets have a 7-day recovery window. To permanently delete:
  ```bash
  aws secretsmanager delete-secret --secret-id action-spec/github-token --force-delete-without-recovery
  ```
