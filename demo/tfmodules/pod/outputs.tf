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
