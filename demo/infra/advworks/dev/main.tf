# Read configuration from spec.yml
locals {
  spec = yamldecode(file("${path.module}/spec.yml"))
}

# Call pod module with spec-driven configuration
module "pod" {
  source = "../../../tfmodules/pod"

  customer      = local.spec.metadata.customer
  environment   = local.spec.metadata.environment
  instance_name = local.spec.spec.compute.instance_name
  instance_type = local.spec.spec.compute.instance_type
  demo_message  = local.spec.spec.compute.demo_message
  waf_enabled   = local.spec.spec.security.waf.enabled
  aws_region    = var.aws_region
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
