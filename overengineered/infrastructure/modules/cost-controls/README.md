# Cost Controls Module

AWS Budget monitoring with SNS alert notifications for cost overrun protection.

## Features

- Monthly budget tracking (default: $10 USD)
- Two-tier alerting:
  - **Warning**: 80% of budget (forecasted or actual)
  - **Critical**: 100% of budget (actual spend)
- Email notifications with spend details
- SNS topic integration for future automation

## Usage

```hcl
module "cost_controls" {
  source = "../../modules/cost-controls"

  project_name  = "action-spec"
  budget_amount = 10
  alert_email   = "alerts@example.com"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_name | Project name for resource naming | string | - | yes |
| budget_amount | Monthly budget limit in USD | number | 10 | no |
| alert_email | Email for budget alerts | string | - | yes |
| warning_threshold | Warning percentage | number | 80 | no |
| critical_threshold | Critical percentage | number | 100 | no |

## Outputs

| Name | Description |
|------|-------------|
| sns_topic_arn | ARN of budget alerts SNS topic |
| budget_id | ID of the AWS Budget resource |

## Testing

### Manual Testing (Recommended for MVP)

1. Deploy with low threshold for faster testing:
   ```hcl
   budget_amount = 1
   ```

2. Confirm SNS email subscription (check email inbox)

3. Trigger test notification via AWS Console:
   - Go to AWS Budgets → Select budget → Edit
   - Change threshold to current spend level
   - Save (triggers notification)

4. Verify email delivery (within 5 minutes)

5. Restore production threshold:
   ```hcl
   budget_amount = 10
   ```

### Automated Testing (Future Enhancement)

Consider using:
- `terraform-compliance` for policy testing
- AWS CLI to simulate budget events
- Integration tests with LocalStack

## Cost

- AWS Budgets: **Free** (first 2 budgets per account)
- SNS Email: **~$0.50/month** (negligible for email notifications)
- **Total: < $1/month**

## Security

- SNS topic restricted to AWS Budgets service principal
- Email variable marked `sensitive` (not logged)
- No secrets in Terraform state (email in variables only)

## Future Enhancements

- Lambda auto-remediation at 100% threshold
- Slack notifications via SNS → Lambda
- CloudWatch dashboard integration
- Per-service budget breakdowns
