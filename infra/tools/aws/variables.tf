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

variable "github_oauth_client_id" {
  description = "GitHub OAuth App Client ID (public identifier)"
  type        = string
}

variable "github_oauth_client_secret" {
  description = "GitHub OAuth App Client Secret (sensitive)"
  type        = string
  sensitive   = true
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
