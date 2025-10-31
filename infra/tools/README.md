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
