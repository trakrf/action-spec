output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.pod.id
}

output "public_ip" {
  description = "Public IP address of the instance"
  value       = aws_instance.pod.public_ip
}

output "instance_name" {
  description = "Full instance name tag"
  value       = aws_instance.pod.tags["Name"]
}

output "demo_url" {
  description = "HTTP URL to test the demo app (wait ~2 min after apply)"
  value       = "http://${aws_instance.pod.public_ip}/"
}

output "security_group_id" {
  description = "Security group ID used by the instance"
  value       = local.security_group_id
}

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "alb_url" {
  description = "HTTP URL to access via ALB (wait ~60s for health checks)"
  value       = "http://${aws_lb.main.dns_name}/"
}

output "waf_enabled" {
  description = "Whether WAF is enabled"
  value       = var.waf_enabled
}

output "waf_web_acl_id" {
  description = "ID of WAF Web ACL (empty if disabled)"
  value       = var.waf_enabled ? aws_wafv2_web_acl.main[0].id : ""
}

output "waf_web_acl_arn" {
  description = "ARN of WAF Web ACL (empty if disabled)"
  value       = var.waf_enabled ? aws_wafv2_web_acl.main[0].arn : ""
}
