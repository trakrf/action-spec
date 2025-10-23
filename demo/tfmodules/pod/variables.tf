variable "customer" {
  description = "Customer name for resource naming and tagging"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.customer))
    error_message = "Customer must be lowercase alphanumeric with hyphens only"
  }
}

variable "environment" {
  description = "Environment name (dev, stg, prd)"
  type        = string

  validation {
    condition     = contains(["dev", "stg", "prd"], var.environment)
    error_message = "Environment must be dev, stg, or prd"
  }
}

variable "instance_name" {
  description = "User-friendly instance name (e.g., web1, app1)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.nano"
}

variable "demo_message" {
  description = "Message displayed by http-echo service"
  type        = string
  default     = "Hello from ActionSpec Demo"
}

variable "waf_enabled" {
  description = "Enable WAF protection (Phase D2)"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "security_group_id" {
  description = "Optional: Override default security group"
  type        = string
  default     = null
}
