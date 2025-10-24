variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "ssh_key_name" {
  description = "SSH key pair name for EC2 instance access"
  type        = string
  default     = "msee2" # ED25519 key in us-east-2
}
