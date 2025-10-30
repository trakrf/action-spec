output "sns_topic_arn" {
  description = "ARN of the budget alerts SNS topic"
  value       = module.cost_controls.sns_topic_arn
}

output "budget_id" {
  description = "ID of the AWS Budget"
  value       = module.cost_controls.budget_id
}

output "budget_name" {
  description = "Name of the AWS Budget"
  value       = module.cost_controls.budget_name
}

output "next_steps" {
  description = "Next steps after deployment"
  sensitive   = true
  value       = <<-EOT
    ✅ Budget deployed successfully!

    Next steps:
    1. Check email (${var.alert_email}) for SNS subscription confirmation
    2. Click confirmation link in email
    3. Monitor AWS Budgets console for alerts
    4. Budget will alert at ${var.budget_amount * 0.8} USD (80%) and ${var.budget_amount} USD (100%)

    To test alerts, temporarily lower budget_amount to $1 and wait for forecast.
  EOT
}
