output "app_runner_service_url" {
  description = "Public URL of the App Runner service"
  value       = "https://${aws_apprunner_service.action_spec.service_url}"
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.action_spec.arn
}

output "app_runner_service_id" {
  description = "ID of the App Runner service"
  value       = aws_apprunner_service.action_spec.service_id
}

output "app_runner_service_status" {
  description = "Status of the App Runner service"
  value       = aws_apprunner_service.action_spec.status
}

output "oauth_secret_arn" {
  description = "ARN of the GitHub OAuth client secret"
  value       = aws_secretsmanager_secret.github_oauth_client_secret.arn
  sensitive   = true
}

output "custom_domain" {
  description = "Custom domain for App Runner service"
  value       = "https://${aws_apprunner_custom_domain_association.action_spec.domain_name}"
}

output "custom_domain_status" {
  description = "Status of custom domain association"
  value       = aws_apprunner_custom_domain_association.action_spec.status
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing Docker images"
  value       = aws_ecr_repository.action_spec.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.action_spec.arn
}
