variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
  default     = "action-spec"
}

variable "budget_amount" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 10
}

variable "alert_email" {
  description = "Email address for budget alerts"
  type        = string
  sensitive   = true

  # No default - must be provided by user
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}
