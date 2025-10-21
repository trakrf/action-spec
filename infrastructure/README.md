# Infrastructure

Terraform/OpenTofu infrastructure for ActionSpec demo environment.

## Prerequisites

- Terraform >= 1.5.0 or OpenTofu >= 1.6.0
- AWS CLI configured with credentials
- Valid email address for budget alerts

## Quick Start

### 1. Configure Variables

```bash
cd environments/demo
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set your alert email:
```hcl
alert_email = "your-email@example.com"
```

**Alternative**: Use environment variable (avoids file):
```bash
export TF_VAR_alert_email="your-email@example.com"
```

### 2. Initialize Terraform

```bash
terraform init
```

This configures the S3 backend for state storage.

### 3. Review Plan

```bash
terraform plan
```

Expected resources:
- 1 SNS topic
- 1 SNS email subscription
- 1 AWS Budget

### 4. Deploy

```bash
terraform apply
```

Type `yes` to confirm.

### 5. Confirm SNS Subscription

Check your email for "AWS Notification - Subscription Confirmation"
Click the confirmation link (expires in 3 days)

### 6. Verify Outputs

```bash
terraform output
```

You should see:
- SNS topic ARN
- Budget ID
- Next steps message

## Testing Budget Alerts

### Quick Test (Recommended)

1. Temporarily lower threshold:
   ```hcl
   budget_amount = 1
   ```

2. Apply changes:
   ```bash
   terraform apply
   ```

3. Wait for AWS forecast to trigger (usually within 24 hours)

4. Restore production threshold:
   ```hcl
   budget_amount = 10
   ```

### Manual Trigger (AWS Console)

1. Go to [AWS Budgets Console](https://console.aws.amazon.com/billing/home#/budgets)
2. Select your budget
3. Edit notification threshold to current spend
4. Save (triggers immediate alert)
5. Check email within 5 minutes

## Project Structure

```
infrastructure/
├── modules/
│   └── cost-controls/       # Reusable budget module
│       ├── main.tf          # SNS + Budget resources
│       ├── variables.tf     # Module inputs
│       ├── outputs.tf       # Module outputs
│       └── README.md        # Module documentation
└── environments/
    └── demo/                # Demo environment
        ├── main.tf          # Module instantiation
        ├── variables.tf     # Environment variables
        ├── outputs.tf       # Pass-through outputs
        ├── providers.tf     # AWS provider config
        ├── backend.tf       # S3 state backend
        └── terraform.tfvars.example
```

## Environment Variables

Terraform recognizes these environment variables:

```bash
# AWS Credentials (if not using ~/.aws/credentials)
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-west-2"

# Terraform Variables (alternative to terraform.tfvars)
export TF_VAR_alert_email="your-email@example.com"
export TF_VAR_budget_amount="10"
export TF_VAR_project_name="action-spec"
```

## Validation

### Syntax Check
```bash
terraform validate
```

### Formatting
```bash
terraform fmt -check -recursive
```

### Linting (Optional)
```bash
# Install tflint
brew install tflint  # macOS
# or: https://github.com/terraform-linters/tflint

tflint --init
tflint
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

Type `yes` to confirm.

**Note**: SNS subscriptions may remain active. Check AWS Console if needed.

## Cost

- AWS Budgets: **Free** (first 2 budgets)
- SNS: **~$0.50/month** (email notifications)
- **Total: < $1/month**

## Troubleshooting

### "Error: No valid credential sources"

Solution: Configure AWS credentials
```bash
aws configure
# or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

### "Error: Backend configuration changed"

Solution: Reinitialize backend
```bash
terraform init -reconfigure
```

### "Email not confirmed"

Check spam folder for AWS SNS confirmation email
Link expires in 3 days - request new subscription if expired

### "Budget not triggering alerts"

- Verify SNS subscription is confirmed (AWS Console → SNS → Subscriptions)
- Check current AWS spend (AWS Console → Billing)
- Wait 24 hours for forecast to calculate
- Try manual trigger via AWS Console

## Security

- ✅ Email variable marked `sensitive` (not logged)
- ✅ No secrets in Terraform state
- ✅ S3 backend uses encryption
- ✅ DynamoDB state locking enabled
- ⚠️ terraform.tfvars in .gitignore (never commit)

## Next Steps

After MVP deployment:
- [ ] Add Lambda auto-remediation at 100% threshold
- [ ] CloudWatch dashboard for cost visualization
- [ ] Slack notifications via SNS → Lambda
- [ ] Per-service budget breakdowns
