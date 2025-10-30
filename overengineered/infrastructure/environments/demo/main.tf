# Demo environment - Cost controls deployment

module "cost_controls" {
  source = "../../modules/cost-controls"

  project_name  = var.project_name
  budget_amount = var.budget_amount
  alert_email   = var.alert_email

  # Use defaults for thresholds (80% warning, 100% critical)
}
