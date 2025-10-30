# Read configuration from spec.yml
locals {
  spec = yamldecode(file("${path.module}/spec.yml"))
}

# Call pod module with spec-driven configuration
module "pod" {
  source = "../../modules/pod"

  customer      = local.spec.metadata.customer
  environment   = local.spec.metadata.environment
  instance_name = local.spec.spec.compute.instance_name
  instance_type = local.spec.spec.compute.instance_type
  waf_enabled   = local.spec.spec.security.waf.enabled
  aws_region    = var.aws_region
  ssh_key_name  = var.ssh_key_name
}

# Outputs for easy access
output "instance_id" {
  description = "EC2 instance ID"
  value       = module.pod.instance_id
}

output "demo_url" {
  description = "Test the app at this URL (wait ~2 min after apply)"
  value       = module.pod.demo_url
}

output "instance_name" {
  description = "Full instance name"
  value       = module.pod.instance_name
}

output "alb_url" {
  description = "Access the app via ALB at this URL (wait ~60s for health checks)"
  value       = module.pod.alb_url
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.pod.alb_dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = module.pod.alb_arn
}

output "waf_enabled" {
  description = "Whether WAF is enabled"
  value       = module.pod.waf_enabled
}

output "waf_web_acl_id" {
  description = "WAF Web ACL ID (empty if disabled)"
  value       = module.pod.waf_web_acl_id
}

output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN (empty if disabled)"
  value       = module.pod.waf_web_acl_arn
}
