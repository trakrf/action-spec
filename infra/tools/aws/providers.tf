terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Credentials loaded from:
  # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  # 2. ~/.aws/credentials (AWS_PROFILE)
  # 3. ~/.aws/config

  default_tags {
    tags = {
      Project     = "action-spec"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}
