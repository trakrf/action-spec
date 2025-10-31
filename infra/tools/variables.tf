variable "aws_region" {
  description = "AWS region for App Runner service"
  type        = string
  default     = "us-east-2"
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
  # No default - must be provided via environment
}

variable "cpu" {
  description = "App Runner CPU allocation (0.25 vCPU, 0.5 vCPU, 1 vCPU, 2 vCPU, 4 vCPU)"
  type        = string
  default     = "0.5 vCPU"
}

variable "memory" {
  description = "App Runner memory (0.5 GB, 1 GB, 2 GB, 3 GB, 4 GB)"
  type        = string
  default     = "1 GB"
}

variable "max_instances" {
  description = "Maximum auto-scaling instances"
  type        = number
  default     = 2
}
