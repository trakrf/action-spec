# Feature: GCP Cloud Run Deployment (Multi-Cloud Support)

## Origin
Expanding multi-cloud support alongside Azure to maximize market coverage. This specification emerged from analyzing the existing AWS App Runner deployment and identifying GCP equivalents.

**Context**: Complete cloud provider coverage (AWS, Azure, GCP) enables demos for any prospective client regardless of their cloud preference.

## Outcome
Multi-cloud deployment capability enabling action-spec to run on AWS, Azure, and GCP:
- Restructured `infra/tools/` to support three cloud providers
- Complete GCP infrastructure using Cloud Run
- Feature parity with AWS and Azure deployments
- Parallel documentation for GCP deployments
- Same Docker image runs on all three platforms

## User Story
As a **sales engineer**
I want **to deploy action-spec on GCP Cloud Run**
So that **I can demo the application to GCP-focused clients and have complete cloud coverage**

## Context

### Current State
- **AWS deployment** exists in `infra/tools/aws/`
- **Azure deployment** being added in parallel (`infra/tools/azure/`)
- Uses: ECR, App Runner, Secrets Manager, IAM roles
- Multi-stage Docker build (Vue frontend + Python/Flask backend)

### Desired State
- **Multi-cloud structure**: `infra/tools/{aws,azure,gcp}/`
- GCP deployment with equivalent functionality
- Same Docker image deploys to all three clouds
- Parallel quick-start experiences
- Documentation parity

### Why Cloud Run?
- **Closest equivalent** to AWS App Runner and Azure Container Apps
- **Fully managed** serverless container platform
- **Auto-scaling to zero** (even better cost efficiency)
- **Native Artifact Registry integration** (like ECR/ACR)
- **Simple ingress** with automatic HTTPS
- **Built-in health checks** and observability

## Technical Requirements

### Prerequisites

**IMPORTANT**: Before implementing GCP deployment, the infrastructure must be restructured for multi-cloud support.

**Prerequisite Spec**: `spec/active/multi-cloud-restructure/spec.md`

This restructure:
- Moves AWS files to `infra/tools/aws/`
- Creates root README at `infra/tools/README.md`
- Takes ~30-40 minutes
- Zero risk to existing AWS deployment
- **Shared with Azure** - only needs to be done once

**After restructure**, the directory structure will be:
```
infra/tools/
├── README.md          # Multi-cloud overview
├── aws/              # Existing AWS deployment (moved)
├── azure/            # Azure Container Apps (parallel)
└── gcp/              # Ready for GCP implementation
```

### Phase 1: GCP Infrastructure Implementation

#### 1.1 GCP Service Mappings

| AWS Service | GCP Equivalent | Purpose |
|------------|----------------|---------|
| ECR | Artifact Registry | Container image storage |
| App Runner | Cloud Run | Managed container hosting |
| Secrets Manager | Secret Manager | Secret management |
| IAM Roles | Service Accounts + IAM | Access control |
| CloudWatch Logs | Cloud Logging | Logging (built-in) |

#### 1.2 Required Files

```
infra/tools/gcp/
├── main.tf              # Cloud Run service
├── providers.tf         # GCP provider config
├── backend.tf           # Terraform state backend
├── variables.tf         # Input variables
├── artifact-registry.tf # Container registry
├── service-account.tf   # Service account + IAM
├── secrets.tf           # Secret Manager + secrets
├── outputs.tf           # Output values
└── README.md            # GCP deployment guide
```

#### 1.3 Core Infrastructure (main.tf)

**Resource: Cloud Run Service**
```hcl
resource "google_cloud_run_v2_service" "action_spec" {
  name     = "action-spec"
  location = var.gcp_region
  project  = var.gcp_project_id

  template {
    containers {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/action-spec/action-spec:latest"

      ports {
        container_port = 8080
      }

      env {
        name  = "GH_REPO"
        value = var.github_repo
      }

      env {
        name  = "SPECS_PATH"
        value = "infra"
      }

      env {
        name  = "WORKFLOW_BRANCH"
        value = var.github_branch
      }

      env {
        name = "GH_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.github_token.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds    = 30
        timeout_seconds   = 5
        failure_threshold = 3
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = var.max_instances
    }

    service_account = google_service_account.action_spec.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    application = "action-spec"
    managed-by  = "terraform"
  }
}

# Make service publicly accessible
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.action_spec.project
  location = google_cloud_run_v2_service.action_spec.location
  name     = google_cloud_run_v2_service.action_spec.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```

#### 1.4 Artifact Registry (artifact-registry.tf)

```hcl
resource "google_artifact_registry_repository" "action_spec" {
  project       = var.gcp_project_id
  location      = var.gcp_region
  repository_id = "action-spec"
  description   = "Docker repository for action-spec images"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-last-10"
    action = "DELETE"

    condition {
      tag_state  = "TAGGED"
      older_than = "2592000s"  # 30 days
    }

    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"

    condition {
      tag_state  = "UNTAGGED"
      older_than = "86400s"  # 1 day
    }
  }

  labels = {
    application = "action-spec"
    managed-by  = "terraform"
  }
}

# Grant service account permission to pull images
resource "google_artifact_registry_repository_iam_member" "action_spec_reader" {
  project    = google_artifact_registry_repository.action_spec.project
  location   = google_artifact_registry_repository.action_spec.location
  repository = google_artifact_registry_repository.action_spec.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.action_spec.email}"
}
```

#### 1.5 Service Account & IAM (service-account.tf)

```hcl
resource "google_service_account" "action_spec" {
  project      = var.gcp_project_id
  account_id   = "action-spec-sa"
  display_name = "Action-Spec Service Account"
  description  = "Service account for action-spec Cloud Run service"
}

# Grant Secret Manager access
resource "google_secret_manager_secret_iam_member" "action_spec_accessor" {
  project   = google_secret_manager_secret.github_token.project
  secret_id = google_secret_manager_secret.github_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.action_spec.email}"
}

# Grant Cloud Run service agent permission to access secrets
data "google_project" "project" {
  project_id = var.gcp_project_id
}

resource "google_project_iam_member" "cloudrun_secret_access" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}
```

#### 1.6 Secrets Management (secrets.tf)

```hcl
resource "google_secret_manager_secret" "github_token" {
  project   = var.gcp_project_id
  secret_id = "action-spec-github-token"

  replication {
    auto {}
  }

  labels = {
    application = "action-spec"
    managed-by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "github_token" {
  secret      = google_secret_manager_secret.github_token.id
  secret_data = var.github_token
}
```

#### 1.7 Provider Configuration (providers.tf)

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region

  # Credentials loaded from:
  # 1. GOOGLE_APPLICATION_CREDENTIALS environment variable
  # 2. gcloud auth application-default login
}
```

#### 1.8 Variables (variables.tf)

```hcl
variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  # No default - must be provided
}

variable "gcp_region" {
  description = "GCP region for Cloud Run service"
  type        = string
  default     = "us-central1"
}

variable "github_repo" {
  description = "GitHub repository (org/repo)"
  type        = string
  default     = "trakrf/action-spec"
}

variable "github_branch" {
  description = "Branch to deploy"
  type        = string
  default     = "main"
}

variable "github_token" {
  description = "GitHub token for API access (loaded from .env.local via TF_VAR_github_token)"
  type        = string
  sensitive   = true
}

variable "cpu" {
  description = "Cloud Run CPU allocation (1, 2, 4, 8)"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Cloud Run memory allocation (512Mi, 1Gi, 2Gi, 4Gi)"
  type        = string
  default     = "1Gi"
}

variable "max_instances" {
  description = "Maximum auto-scaling instances"
  type        = number
  default     = 2
}
```

#### 1.9 Outputs (outputs.tf)

```hcl
output "cloud_run_url" {
  description = "Public URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.action_spec.uri
}

output "cloud_run_service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.action_spec.name
}

output "artifact_registry_url" {
  description = "Artifact Registry URL for pushing Docker images"
  value       = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/action-spec"
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.action_spec.email
}

output "secret_name" {
  description = "Secret Manager secret name"
  value       = google_secret_manager_secret.github_token.secret_id
  sensitive   = true
}
```

#### 1.10 Backend Configuration (backend.tf)

```hcl
terraform {
  backend "gcs" {
    bucket = "action-spec-terraform-state"
    prefix = "gcp/action-spec"
  }
}
```

**Note**: User must create GCS bucket manually or use local backend:
```hcl
# Alternative: Local backend for demo
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
```

### Phase 2: Documentation

#### 2.1 GCP README (infra/tools/gcp/README.md)

**Structure** (mirror AWS/Azure README):

1. **Prerequisites**
   - GCP project created
   - gcloud CLI installed and authenticated
   - OpenTofu/Terraform installed (>= 1.5.0)
   - Docker installed
   - GitHub token with repo permissions
   - direnv (optional)
   - Required GCP APIs enabled:
     - Cloud Run API
     - Artifact Registry API
     - Secret Manager API

2. **Initial Setup**
   ```bash
   # Create GCP project (if needed)
   gcloud projects create action-spec-demo --name="Action Spec Demo"

   # Set project
   gcloud config set project action-spec-demo

   # Enable required APIs
   gcloud services enable \
     run.googleapis.com \
     artifactregistry.googleapis.com \
     secretmanager.googleapis.com

   # Authenticate
   gcloud auth application-default login
   ```

3. **Environment Setup**
   Add to `.env.local` (in repo root):
   ```bash
   TF_VAR_github_token=$GH_TOKEN
   TF_VAR_gcp_project_id=action-spec-demo
   ```

4. **Quick Start**
   ```bash
   cd infra/tools/gcp

   # Load environment
   direnv allow  # or: set -a; source ../../.env.local; set +a

   # Initialize
   tofu init

   # Review plan (~12 resources expected)
   tofu plan

   # Apply infrastructure
   tofu apply
   ```

5. **Build and Push to Artifact Registry**
   ```bash
   # Get Artifact Registry URL
   AR_URL=$(tofu output -raw artifact_registry_url)
   GCP_REGION=$(echo $AR_URL | cut -d. -f1 | cut -d/ -f1)

   # Configure Docker authentication
   gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev

   # Build image (from repo root)
   cd ../..
   docker build -t action-spec:latest .

   # Tag for Artifact Registry
   docker tag action-spec:latest ${AR_URL}/action-spec:latest

   # Push to Artifact Registry
   docker push ${AR_URL}/action-spec:latest
   ```

   Cloud Run will automatically deploy the new image (takes 1-2 minutes).

6. **Verify Deployment**
   ```bash
   cd infra/tools/gcp

   # Get service URL
   SERVICE_URL=$(tofu output -raw cloud_run_url)

   # Test health endpoint
   curl $SERVICE_URL/health
   # Expected: {"status": "healthy"}

   # Open in browser
   echo "Application URL: $SERVICE_URL"
   open $SERVICE_URL  # macOS
   # or: xdg-open $SERVICE_URL  # Linux
   ```

7. **Common Commands**
   ```bash
   # View Cloud Run logs
   gcloud run services logs read action-spec --region us-central1

   # Check service status
   gcloud run services describe action-spec --region us-central1

   # List revisions
   gcloud run revisions list --service action-spec --region us-central1
   ```

8. **Variables**

   | Variable | Default | Description |
   |----------|---------|-------------|
   | `gcp_project_id` | *required* | GCP project ID |
   | `gcp_region` | `us-central1` | GCP region |
   | `github_repo` | `trakrf/action-spec` | GitHub repository |
   | `github_branch` | `main` | Branch to deploy |
   | `github_token` | *required* | GitHub PAT |
   | `cpu` | `1` | CPU cores |
   | `memory` | `1Gi` | Memory allocation |
   | `max_instances` | `2` | Max auto-scaling instances |

9. **Troubleshooting**

   **`tofu init` fails**
   - Check GCP authentication: `gcloud auth application-default print-access-token`
   - Verify project exists: `gcloud projects describe $TF_VAR_gcp_project_id`

   **`tofu plan` fails with API not enabled**
   - Enable required APIs (see Initial Setup)
   - Wait 1-2 minutes for API enablement to propagate

   **Docker push to Artifact Registry fails**
   - Check authentication: `gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev`
   - Verify repository exists: `gcloud artifacts repositories list --location=$GCP_REGION`

   **Cloud Run service won't start**
   - Check if image exists: `gcloud artifacts docker images list ${AR_URL}`
   - View logs: `gcloud run services logs read action-spec`
   - Verify service account has secret access

   **Health check failing**
   - Check Cloud Run logs for application errors
   - Verify port 8080 is exposed
   - Test locally: `docker run -p 8080:8080 action-spec:latest`

10. **Continuous Deployment**

    Cloud Run supports **automatic deployment** from Artifact Registry. When you push a new image with `:latest` tag:
    1. Cloud Run detects the new image
    2. Creates a new revision
    3. Health checks the revision
    4. Routes traffic to the new revision (blue-green deployment)

    To deploy updates:
    ```bash
    # From repo root
    docker build -t action-spec:latest .
    docker tag action-spec:latest $(cd infra/tools/gcp && tofu output -raw artifact_registry_url)/action-spec:latest
    docker push $(cd infra/tools/gcp && tofu output -raw artifact_registry_url)/action-spec:latest
    ```

11. **Cleanup**
    ```bash
    tofu destroy
    # Confirm: yes

    # Optional: Delete GCS state bucket
    gsutil -m rm -r gs://action-spec-terraform-state
    ```

#### 2.2 Update Root README

**File**: `infra/tools/README.md`

Note: This will be created by the multi-cloud restructure prerequisite. If Azure is implemented first, just verify GCP section exists:
```markdown
### GCP (Cloud Run + Artifact Registry)
- **Path**: `infra/tools/gcp/`
- **Services**: Cloud Run, Artifact Registry, Secret Manager
- **Cost**: ~$5-15/month for demo (can scale to zero)
- **Docs**: [infra/tools/gcp/README.md](./gcp/README.md)
```

## Validation Criteria

Prerequisites:
- [ ] Multi-cloud restructure completed (see `spec/active/multi-cloud-restructure/spec.md`)
- [ ] AWS infrastructure working in `infra/tools/aws/`

Phase 1 (GCP Implementation):
- [ ] All GCP Terraform files created in `infra/tools/gcp/`
- [ ] GCP APIs enabled (Cloud Run, Artifact Registry, Secret Manager)
- [ ] `tofu init` succeeds in gcp directory
- [ ] `tofu plan` shows ~12 resources (Artifact Registry, Cloud Run service, Service Account, Secret Manager secret + version, IAM bindings)
- [ ] `tofu apply` successfully creates all resources
- [ ] Can authenticate to Artifact Registry with `gcloud auth configure-docker`
- [ ] Can push Docker image to Artifact Registry
- [ ] Cloud Run pulls image and starts successfully
- [ ] Health check passes: `curl $SERVICE_URL/health` returns `{"status": "healthy"}`
- [ ] Application UI accessible and functional
- [ ] Auto-scaling configuration applied (min 1, max 2 instances)
- [ ] Public access works (allUsers invoker role)

Phase 2 (Documentation):
- [ ] `infra/tools/gcp/README.md` comprehensive and tested
- [ ] Can deploy from scratch following README exactly
- [ ] Troubleshooting section covers common issues
- [ ] Commands are copy-pasteable and work
- [ ] Root `infra/tools/README.md` updated with GCP section

## Success Metrics

### Functional Parity
- [ ] Same Docker image runs on AWS, Azure, and GCP
- [ ] Same environment variables work on all platforms
- [ ] Health check endpoint works identically
- [ ] Auto-scaling behavior similar (1-2 instances)
- [ ] Secret injection works (GitHub token accessible)

### Deployment Experience
- [ ] Time to deploy: <15 minutes (after prerequisites)
- [ ] Number of manual steps: <12 (includes API enablement)
- [ ] Documentation clarity: Non-GCP expert can deploy

### Cost Efficiency
- [ ] Monthly cost: $5-15 for demo workload
- [ ] **Better than AWS/Azure**: Can scale to zero when idle
- [ ] No unexpected charges

### Demo Readiness
- [ ] Can deploy to fresh GCP project
- [ ] Can demo to client within 1 business day
- [ ] Stable enough for 1-hour sales presentation

## Time Estimate

**Prerequisites - Multi-Cloud Restructure**: 30-40 minutes (one-time, shared with Azure)
- See `spec/active/multi-cloud-restructure/spec.md`

**Phase 1 - GCP Infrastructure**: 4-6 hours
- Provider setup + API enablement: 30 min
- Artifact Registry with cleanup policies: 1 hour
- Cloud Run service configuration: 2-3 hours
- Service account + IAM bindings: 1 hour
- Secret Manager: 30 min
- Testing and debugging: 30-60 min

**Phase 2 - Documentation**: 2-3 hours
- GCP README: 1.5-2 hours
- Root README update: 15 min
- Testing documentation flow: 1 hour
- API enablement docs: 30 min

**Total GCP-specific: 6-9 hours** (approximately 1 day)
**Total including restructure: 7-10 hours**

**If done in parallel with Azure**:
- Shared restructure: 30-40 minutes (one-time)
- Parallel implementation: max(Azure 6-9 hours, GCP 6-9 hours) = 6-9 hours
- **Combined total: 7-10 hours** (same as doing one cloud)

**If done sequentially after Azure**: 6-9 hours additional (no restructure needed)

## Implementation Notes

### Key Advantages over AWS/Azure

1. **Scale to Zero**
   - Cloud Run can scale down to 0 instances when idle
   - Pay only for actual requests (not idle time)
   - Best cost efficiency for demo/low-traffic

2. **Simpler Authentication**
   - Service accounts simpler than IAM roles or Managed Identities
   - Built-in Docker authentication via gcloud
   - No token expiration issues

3. **Built-in Observability**
   - Cloud Logging integrated by default
   - No additional setup needed (unlike CloudWatch)
   - Cloud Trace for request tracing

4. **Fastest Cold Starts**
   - Cloud Run optimized for container startup
   - Typically <1 second cold start for this workload

5. **Revision Management**
   - Blue-green deployments built-in
   - Easy rollback to previous revisions
   - Traffic splitting for gradual rollout

### Key Differences from AWS/Azure

1. **Project-Based**
   - Must specify GCP project ID (not just region)
   - Projects provide billing isolation
   - Can create project per environment

2. **API Enablement**
   - Must explicitly enable GCP APIs
   - One-time setup per project
   - Can be automated via Terraform

3. **Service Accounts**
   - Simpler than IAM roles (AWS)
   - More intuitive than Managed Identities (Azure)
   - Direct attachment to Cloud Run service

4. **Artifact Registry**
   - Supports multiple formats (Docker, Maven, npm, etc.)
   - Regional replication available
   - More flexible than ECR/ACR

5. **Automatic HTTPS**
   - Cloud Run provides HTTPS by default
   - Custom domains easy to configure
   - No additional certificate management

### GCP-Specific Gotchas

1. **Project ID Requirements**
   - Must be globally unique
   - Cannot be changed after creation
   - Include in variable (no default)

2. **Service Account Email Format**
   - Must be <30 chars
   - Use short, descriptive names
   - Format: `<name>@<project>.iam.gserviceaccount.com`

3. **Region Naming**
   - Different from AWS/Azure regions
   - Use `us-central1`, `us-east1`, etc.
   - Check Cloud Run region availability

4. **Billing Account**
   - GCP project requires linked billing account
   - Free tier available (2M requests/month)
   - May require credit card for new accounts

5. **Quota Limits**
   - New projects have conservative limits
   - May need quota increase for production
   - Demo workload should be fine

### Future Enhancements (Out of Scope)

- Cloud Monitoring dashboards
- Cloud Trace integration
- Cloud Armor (WAF/DDoS protection)
- Custom domain with Cloud DNS
- Cloud CDN for static assets
- GitHub Actions deployment workflow
- VPC Connector for private resources
- Terraform modules for DRY code

## References

### Existing Implementation
- AWS deployment: `infra/tools/aws/`
- Azure deployment: `infra/tools/azure/` (parallel)
- App Runner spec: `spec/active/app-runner-phase1-deployment/spec.md`
- Dockerfile: `Dockerfile` (same for all clouds)

### GCP Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [GCP Terraform Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

### Conversation Context
- Azure spec created in parallel
- Same restructuring approach (`infra/tools/{aws,azure,gcp}/`)
- Orthogonal implementation (can be done simultaneously)
- Complete cloud coverage strategy
- Same Docker image across all platforms
