output "sns_topic_arn" {
  description = "ARN of the SNS topic for budget alerts"
  value       = aws_sns_topic.budget_alerts.arn
}

output "sns_topic_name" {
  description = "Name of the SNS topic"
  value       = aws_sns_topic.budget_alerts.name
}

output "budget_id" {
  description = "ID of the AWS Budget"
  value       = aws_budgets_budget.monthly_cost.id
}

output "budget_name" {
  description = "Name of the AWS Budget"
  value       = aws_budgets_budget.monthly_cost.name
}
