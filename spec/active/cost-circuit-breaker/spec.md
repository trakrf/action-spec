# Feature: AWS Cost Circuit Breaker

## Metadata
**Workspace**: infrastructure
**Type**: feature

## Outcome
Automated cost monitoring with budget alerts prevents unexpected AWS charges by notifying operators when spending thresholds are exceeded, enabling rapid response to cost overruns.

## User Story
As a DevOps engineer managing demo infrastructure
I want automated budget monitoring with immediate alerts
So that I can prevent runaway costs and respond quickly when spending exceeds safe thresholds

## Context
**Current**: No automated cost controls in place. Manual monitoring of AWS billing required.

**Desired**: AWS Budgets monitoring with SNS alerts at configurable thresholds. Email notifications enable rapid response. Foundation for future auto-remediation.

**Examples**:
- PRD.md lines 364-405 (Budget alarm design)
- PRD.md lines 494-502 (Emergency shutdown descoped, manual control for MVP)

## Technical Requirements

### Phase 1: Budget Monitoring & Alerts (MVP)
- AWS Budget resource with monthly spend limit (default: $10/month)
- SNS topic for budget notifications
- Email subscription for immediate alerts
- Two notification thresholds:
  - **Warning**: 80% of budget (forecast or actual)
  - **Critical**: 100% of budget (actual only)
- Budget configured to track all AWS services
- Alert email includes: service breakdown, current spend, threshold exceeded

### Infrastructure Components
- **Terraform/OpenTofu** for IaC (matching project standards)
- **AWS Budgets** for spend tracking
- **SNS** for notification delivery
- **CloudWatch** (optional) for additional metrics/dashboards

### Configuration Requirements
- Budget amount configurable via variable (default: 10 USD)
- Alert email configurable via variable (no hardcoded values)
- Time period: Monthly (calendar month)
- Cost type: Actual costs (not amortized)

### Security & Safety
- SNS topic access restricted to AWS Budgets service
- Email confirmation required for SNS subscription
- No secrets or sensitive data in Terraform state (email in variables only)
- Budget alerts should not trigger infrastructure destruction automatically (manual intervention required for MVP)

### Phase 2: Emergency Shutdown (Future Enhancement)
- Lambda function triggered by SNS at 100% threshold
- Automatic infrastructure teardown for resources tagged with project identifier
- Safety mechanisms: require specific tag, confirmation wait period
- **Status**: Descoped for MVP per PRD.md:494-502

## Validation Criteria
- [ ] AWS Budget successfully created with $10 monthly limit
- [ ] SNS topic created and email subscription confirmed
- [ ] Test alert triggers at 80% threshold (use AWS Budget forecast/simulation)
- [ ] Email notification received with correct spend information
- [ ] Terraform plan shows no sensitive data exposure
- [ ] Budget applies to all AWS services (not filtered to specific services)

## Success Metrics

Define measurable success criteria that will be tracked in SHIPPED.md:
- [ ] Budget resource created and active in target AWS account
- [ ] SNS topic ARN returned as Terraform output
- [ ] Email alert successfully delivered within 5 minutes of threshold breach
- [ ] Zero hardcoded secrets or email addresses in committed code
- [ ] Terraform apply completes in < 2 minutes
- [ ] All Terraform validation passes (`terraform validate`, `tflint`)

## References
- PRD.md lines 364-405: Cost Protection design
- PRD.md lines 494-502: Emergency Shutdown Lambda (descoped)
- PRD.md lines 596-604: Cost Safeguards requirements
- AWS Budgets Terraform: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/budgets_budget
- AWS SNS Terraform: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic

## Implementation Notes

### Directory Structure
```
infrastructure/
├── modules/
│   └── cost-controls/
│       ├── main.tf           # Budget + SNS resources
│       ├── variables.tf      # Configurable inputs
│       ├── outputs.tf        # SNS topic ARN, Budget ID
│       └── README.md         # Module documentation
└── environments/
    └── demo/
        └── cost-controls.tf  # Module instantiation
```

### Terraform Variables
```hcl
variable "budget_amount" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 10
}

variable "alert_email" {
  description = "Email address for budget alerts"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}
```

### AWS Budgets Configuration
- **Time Unit**: MONTHLY
- **Budget Type**: COST
- **Include**: All services, taxes, support charges
- **Exclude**: Credits, refunds
- **Notification Type**: ACTUAL and FORECASTED

### Testing Strategy
1. Create budget with very low threshold ($1) in test
2. Trigger notification using AWS CLI or console simulation
3. Verify email delivery
4. Restore production threshold ($10)
5. Monitor for false positives over 7 days

### Cost of Cost Controls
- AWS Budgets: **Free** (first 2 budgets per account)
- SNS: **~$0.50/month** (email notifications)
- Total: **< $1/month**

## Future Enhancements (Post-MVP)
- [ ] Lambda auto-remediation at 100% threshold
- [ ] CloudWatch dashboard for cost visualization
- [ ] Slack notifications (alternative to email)
- [ ] Per-service budget breakdowns
- [ ] Cost anomaly detection (AWS Cost Anomaly Detection service)
- [ ] Daily cost reports via SNS

## Dependencies
- AWS credentials configured (✅ verified)
- Terraform/OpenTofu installed
- Valid email address for alerts
- S3 backend for Terraform state (per Phase 1 requirements)
