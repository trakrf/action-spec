variable "budget_amount" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 10

  validation {
    condition     = var.budget_amount > 0
    error_message = "Budget amount must be greater than 0"
  }
}

variable "alert_email" {
  description = "Email address for budget alert notifications"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "Must be a valid email address"
  }
}

variable "project_name" {
  description = "Project name for resource tagging and naming"
  type        = string

  validation {
    condition     = length(var.project_name) > 0
    error_message = "Project name cannot be empty"
  }
}

variable "warning_threshold" {
  description = "Percentage of budget for warning notification"
  type        = number
  default     = 80

  validation {
    condition     = var.warning_threshold > 0 && var.warning_threshold <= 100
    error_message = "Warning threshold must be between 0 and 100"
  }
}

variable "critical_threshold" {
  description = "Percentage of budget for critical notification"
  type        = number
  default     = 100

  validation {
    condition     = var.critical_threshold > 0 && var.critical_threshold <= 100
    error_message = "Critical threshold must be between 0 and 100"
  }
}
