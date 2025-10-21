# SNS Topic for budget alerts
resource "aws_sns_topic" "budget_alerts" {
  name         = "${var.project_name}-budget-alerts"
  display_name = "${var.project_name} Budget Alerts"

  tags = {
    Name      = "${var.project_name}-budget-alerts"
    Project   = var.project_name
    ManagedBy = "terraform"
    Purpose   = "cost-monitoring"
  }
}

# Email subscription to SNS topic
resource "aws_sns_topic_subscription" "budget_email" {
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# AWS Budget with notification thresholds
resource "aws_budgets_budget" "monthly_cost" {
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_amount)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Warning notification at 80% (forecasted)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.warning_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }

  # Warning notification at 80% (actual)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.warning_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # Critical notification at 100% (actual, both email and SNS)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.critical_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }

  # Cost includes taxes, support charges, excludes credits
  cost_types {
    include_credit             = false
    include_discount           = true
    include_other_subscription = true
    include_recurring          = true
    include_refund             = false
    include_subscription       = true
    include_support            = true
    include_tax                = true
    include_upfront            = true
    use_blended                = false
  }

  tags = {
    Name      = "${var.project_name}-monthly-budget"
    Project   = var.project_name
    ManagedBy = "terraform"
    Purpose   = "cost-monitoring"
  }
}
