terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Module metadata
# This module creates a demo pod (EC2 instance) for the ActionSpec demo
# Phase D1: EC2 only (no ALB, no WAF)
# Phase D2: Will add ALB + conditional WAF
