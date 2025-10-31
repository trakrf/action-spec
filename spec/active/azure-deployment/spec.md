# Feature: Azure Container Apps Deployment (Multi-Cloud Support)

## Origin
Prospective client is an Azure shop and needs a demo deployment on Azure infrastructure. This specification emerged 
from analyzing the existing AWS App Runner deployment and identifying Azure equivalents.

**Context**: Sales opportunity requires demonstrating action-spec on Azure to win Azure-focused clients.

## Outcome
Multi-cloud deployment capability enabling action-spec to run on both AWS and Azure:
- Restructured `infra/tools/` to support multiple cloud providers
- Complete Azure infrastructure using Container Apps
- Feature parity with existing AWS deployment
- Parallel documentation for Azure deployments
- Same Docker image runs on both platforms

## User Story
As a **sales engineer**
I want **to deploy action-spec on Azure Container Apps**
So that **I can demo the application to Azure-focused clients and win deals**

## Context

### Current State
- **AWS deployment** exists in `infra/tools/`
- Uses: ECR, App Runner, Secrets Manager, IAM roles
- ~13 Terraform resources
- Multi-stage Docker build (Vue frontend + Python/Flask backend)
- Working deployment with auto-scaling and health checks
- Comprehensive documentation

### Desired State
- **Multi-cloud structure**: `infra/tools/aws/` and `infra/tools/azure/`
- Azure deployment with equivalent functionality
- Same Docker image deploys to both clouds
- Parallel quick-start experiences
- Documentation parity

### Why Azure Container Apps?
- **Closest equivalent** to AWS App Runner (managed container service)
- **Consumption-based pricing** similar to App Runner
- **Built-in auto-scaling** and health checks
- **Native ACR integration** (like App Runner + ECR)
- **Simplified networking** (ingress configuration)

## Technical Requirements

### Prerequisites

**IMPORTANT**: Before implementing Azure deployment, the infrastructure must be restructured for multi-cloud support.

**Prerequisite Spec**: `spec/active/multi-cloud-restructure/spec.md`

This restructure:
- Moves AWS files to `infra/tools/aws/`
- Creates root README at `infra/tools/README.md`
- Takes ~30-40 minutes
- Zero risk to existing AWS deployment

**After restructure**, the directory structure will be:
```
infra/tools/
├── README.md          # Multi-cloud overview
├── aws/              # Existing AWS deployment (moved)
└── azure/            # Ready for Azure implementation
```

### Phase 1: Azure Infrastructure Implementation

#### 1.1 Azure Service Mappings

| AWS Service | Azure Equivalent | Purpose |
|------------|------------------|---------|
| ECR | Azure Container Registry (ACR) | Container image storage |
| App Runner | Azure Container Apps | Managed container hosting |
| Secrets Manager | Azure Key Vault | Secret management |
| IAM Roles | Managed Identities + RBAC | Access control |
| CloudWatch Logs | Azure Monitor / Log Analytics | Logging (future) |

#### 1.2 Required Files

```
infra/tools/azure/
├── main.tf              # Container Apps environment + app
├── providers.tf         # Azure provider config
├── backend.tf           # Terraform state backend
├── variables.tf         # Input variables
├── acr.tf              # Container registry
├── identity.tf         # Managed identity + RBAC
├── keyvault.tf         # Key Vault + secrets
├── outputs.tf          # Output values
└── README.md           # Azure deployment guide
```

#### 1.3 Core Infrastructure (main.tf)

**Resource: Container Apps Environment**
```hcl
resource "azurerm_container_app_environment" "action_spec" {
  name                = "action-spec-env"
  location            = azurerm_resource_group.action_spec.location
  resource_group_name = azurerm_resource_group.action_spec.name

  tags = {
    Application = "action-spec"
    ManagedBy   = "terraform"
  }
}

resource "azurerm_resource_group" "action_spec" {
  name     = "action-spec-rg"
  location = var.azure_region
}
```

**Resource: Container App**
```hcl
resource "azurerm_container_app" "action_spec" {
  name                         = "action-spec"
  container_app_environment_id = azurerm_container_app_environment.action_spec.id
  resource_group_name          = azurerm_resource_group.action_spec.name
  revision_mode                = "Single"

  template {
    container {
      name   = "action-spec"
      image  = "${azurerm_container_registry.action_spec.login_server}/action-spec:latest"
      cpu    = var.cpu
      memory = var.memory

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
        name        = "GH_TOKEN"
        secret_name = "github-token"
      }
    }

    min_replicas = 1
    max_replicas = var.max_instances
  }

  ingress {
    external_enabled = true
    target_port      = 8080

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  secret {
    name  = "github-token"
    value = var.github_token
  }

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.action_spec.id
    ]
  }

  registry {
    server   = azurerm_container_registry.action_spec.login_server
    identity = azurerm_user_assigned_identity.action_spec.id
  }

  tags = {
    Application = "action-spec"
  }
}
```

#### 1.4 Container Registry (acr.tf)

```hcl
resource "azurerm_container_registry" "action_spec" {
  name                = "actionspecacr${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.action_spec.name
  location            = azurerm_resource_group.action_spec.location
  sku                 = "Basic"
  admin_enabled       = false  # Use managed identity

  tags = {
    Application = "action-spec"
  }
}

# Random suffix for globally unique ACR name
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Retention policy - keep last 10 tagged images
resource "azurerm_container_registry_task" "cleanup" {
  name                  = "cleanup-old-images"
  container_registry_id = azurerm_container_registry.action_spec.id

  platform {
    os = "Linux"
  }

  encoded_step {
    task_content = base64encode(<<-EOT
      version: v1.1.0
      steps:
        - cmd: acr purge --filter 'action-spec:.*' --keep 10 --untagged
    EOT
    )
  }

  timer_trigger {
    name     = "daily"
    schedule = "0 0 * * *"  # Daily at midnight
    enabled  = true
  }
}
```

#### 1.5 Identity & Access (identity.tf)

```hcl
resource "azurerm_user_assigned_identity" "action_spec" {
  name                = "action-spec-identity"
  location            = azurerm_resource_group.action_spec.location
  resource_group_name = azurerm_resource_group.action_spec.name

  tags = {
    Application = "action-spec"
  }
}

# Grant ACR pull permission to managed identity
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.action_spec.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.action_spec.principal_id
}

# Grant Key Vault secrets access
resource "azurerm_role_assignment" "keyvault_secrets" {
  scope                = azurerm_key_vault.action_spec.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.action_spec.principal_id
}
```

#### 1.6 Secrets Management (keyvault.tf)

```hcl
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "action_spec" {
  name                       = "action-spec-kv-${random_string.suffix.result}"
  location                   = azurerm_resource_group.action_spec.location
  resource_group_name        = azurerm_resource_group.action_spec.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  tags = {
    Application = "action-spec"
  }
}

# Grant current user access to manage secrets during deployment
resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.action_spec.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge"
  ]
}

resource "azurerm_key_vault_secret" "github_token" {
  name         = "github-token"
  value        = var.github_token
  key_vault_id = azurerm_key_vault.action_spec.id

  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]

  tags = {
    Application = "action-spec"
  }
}
```

#### 1.7 Provider Configuration (providers.tf)

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}
```

#### 1.8 Variables (variables.tf)

```hcl
variable "azure_region" {
  description = "Azure region for deployment"
  type        = string
  default     = "eastus"
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
  description = "Container CPU allocation (0.25, 0.5, 1.0, 2.0)"
  type        = number
  default     = 0.5
}

variable "memory" {
  description = "Container memory in Gi (0.5, 1.0, 2.0, 4.0)"
  type        = string
  default     = "1.0Gi"
}

variable "max_instances" {
  description = "Maximum auto-scaling instances"
  type        = number
  default     = 2
}
```

#### 1.9 Outputs (outputs.tf)

```hcl
output "container_app_url" {
  description = "Public URL of the Container App"
  value       = "https://${azurerm_container_app.action_spec.ingress[0].fqdn}"
}

output "container_app_fqdn" {
  description = "FQDN of the Container App"
  value       = azurerm_container_app.action_spec.ingress[0].fqdn
}

output "acr_login_server" {
  description = "ACR login server for pushing Docker images"
  value       = azurerm_container_registry.action_spec.login_server
}

output "acr_name" {
  description = "Name of the ACR registry"
  value       = azurerm_container_registry.action_spec.name
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.action_spec.name
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.action_spec.name
  sensitive   = true
}
```

#### 1.10 Backend Configuration (backend.tf)

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "actionspectfstate"
    container_name       = "tfstate"
    key                  = "azure/action-spec.tfstate"
  }
}
```

**Note**: User must create storage account manually or use local backend:
```hcl
# Alternative: Local backend for demo
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
```

### Phase 2: Documentation

#### 2.1 Azure README (infra/tools/azure/README.md)

**Structure** (mirror AWS README):
1. **Prerequisites**
   - Azure CLI installed and authenticated
   - OpenTofu/Terraform installed (>= 1.5.0)
   - Docker installed
   - GitHub token with repo permissions
   - direnv (optional)

2. **Quick Start**
   - Environment setup (.env.local)
   - Initialize Terraform
   - Review plan (~15 resources expected)
   - Apply infrastructure
   - Build and push Docker image
   - Verify deployment
   - Access application

3. **Build and Push to ACR**
   ```bash
   # Get ACR details
   ACR_NAME=$(tofu output -raw acr_name)

   # Login to ACR
   az acr login --name $ACR_NAME

   # Build image (from repo root)
   cd ../..
   docker build -t action-spec:latest .

   # Tag for ACR
   ACR_SERVER=$(cd infra/tools/azure && tofu output -raw acr_login_server)
   docker tag action-spec:latest $ACR_SERVER/action-spec:latest

   # Push to ACR
   docker push $ACR_SERVER/action-spec:latest
   ```

4. **Common Commands**
   - `tofu plan`, `tofu apply`, `tofu destroy`
   - Viewing logs: `az containerapp logs show`
   - Checking status: `az containerapp show`

5. **Variables**
   - All configurable variables with defaults
   - Override via TF_VAR_* or terraform.tfvars

6. **Troubleshooting**
   - Azure CLI authentication issues
   - ACR push failures
   - Container App not starting
   - Health check failures
   - Secret access denied

7. **Continuous Deployment**
   - Container Apps support continuous deployment from ACR
   - Push new image with :latest tag triggers automatic deployment
   - Can use semantic versioning like AWS

8. **Cleanup**
   ```bash
   tofu destroy
   # Purge soft-deleted Key Vault if needed
   az keyvault purge --name <vault-name>
   ```

#### 2.2 Cross-Reference Documentation

**Update main README.md** to mention multi-cloud support:
- Link to `infra/tools/README.md`
- Brief mention of AWS and Azure options

## Validation Criteria

Prerequisites:
- [ ] Multi-cloud restructure completed (see `spec/active/multi-cloud-restructure/spec.md`)
- [ ] AWS infrastructure working in `infra/tools/aws/`

Phase 1 (Azure Implementation):
- [ ] All Azure Terraform files created in `infra/tools/azure/`
- [ ] `tofu init` succeeds in azure directory
- [ ] `tofu plan` shows ~15 resources (Resource Group, Container App Environment, Container App, ACR, Key Vault, Managed Identity, Role Assignments)
- [ ] `tofu apply` successfully creates all resources
- [ ] Can authenticate to ACR with `az acr login`
- [ ] Can push Docker image to ACR
- [ ] Container App pulls image and starts successfully
- [ ] Health check passes: `curl https://<fqdn>/health` returns `{"status": "healthy"}`
- [ ] Application UI accessible and functional
- [ ] Auto-scaling configuration applied (min 1, max 2 replicas)

Phase 2 (Documentation):
- [ ] `infra/tools/azure/README.md` comprehensive and tested
- [ ] Can deploy from scratch following README exactly
- [ ] Troubleshooting section covers common issues
- [ ] Commands are copy-pasteable and work

## Success Metrics

### Functional Parity
- [ ] Same Docker image runs on both AWS and Azure
- [ ] Same environment variables work on both platforms
- [ ] Health check endpoint works identically
- [ ] Auto-scaling behavior similar (1-2 instances)
- [ ] Secret injection works (GitHub token accessible)

### Deployment Experience
- [ ] Time to deploy: <15 minutes (after prerequisites)
- [ ] Number of manual steps: <10
- [ ] Documentation clarity: Non-Azure expert can deploy

### Cost Efficiency
- [ ] Monthly cost: $10-20 for demo workload
- [ ] Similar to AWS App Runner cost profile
- [ ] No unexpected charges

### Demo Readiness
- [ ] Can deploy to fresh Azure subscription
- [ ] Can demo to client within 1 business day
- [ ] Stable enough for 1-hour sales presentation

## Time Estimate

Based on AWS implementation analysis:

**Prerequisites - Multi-Cloud Restructure**: 30-40 minutes (one-time)
- See `spec/active/multi-cloud-restructure/spec.md`

**Phase 1 - Azure Infrastructure**: 4-6 hours
- Provider setup: 30 min
- ACR with lifecycle: 1 hour
- Container Apps environment + app: 2-3 hours
- Managed identity + RBAC: 1 hour
- Key Vault + secrets: 1 hour
- Testing and debugging: 30-60 min

**Phase 2 - Documentation**: 2-3 hours
- Azure README: 1.5-2 hours
- Root README: 30 min
- Testing documentation flow: 1 hour

**Total Azure-specific: 6-9 hours** (approximately 1 day)
**Total including restructure: 7-10 hours**

**Quick Demo Version**: 4-6 hours (minimal docs, defaults only)

## Implementation Notes

### Key Differences from AWS

1. **Naming Constraints**
   - ACR names must be globally unique (hence random suffix)
   - Container App names must be unique within region
   - Key Vault names must be globally unique

2. **Authentication**
   - Managed Identity simpler than IAM roles
   - RBAC more granular than IAM policies
   - Azure CLI authentication for deployment

3. **Container Registry**
   - ACR admin account disabled (use managed identity)
   - Different lifecycle policy syntax (ACR tasks vs. ECR lifecycle)
   - `az acr login` instead of AWS ECR token

4. **Auto-Scaling**
   - Container Apps uses rules vs. App Runner config
   - Simpler min/max replica model
   - Consumption-based billing

5. **Secrets**
   - Key Vault has soft-delete (7-day recovery)
   - Different secret reference syntax
   - Access policy vs. IAM policy

### Future Enhancements (Out of Scope)

- Azure Monitor integration (equivalent to CloudWatch Phase 2)
- Application Insights for APM
- Custom domain with Azure DNS
- Azure Front Door for CDN
- GitHub Actions deployment workflow
- Terraform modules for DRY code

## References

### Existing Implementation
- AWS deployment: `infra/tools/aws/`
- App Runner spec: `spec/active/app-runner-phase1-deployment/spec.md`
- Dockerfile: `Dockerfile` (same for both clouds)

### Azure Documentation
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Managed Identities](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
- [Azure Terraform Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

### Conversation Context
- Time estimate discussion: 8-12 hours total
- Cost comparison: $10-20/month similar to AWS
- Client requirement: Azure shop needs demo
- Architectural decision: Multi-cloud structure with `infra/tools/{aws,azure}/`
