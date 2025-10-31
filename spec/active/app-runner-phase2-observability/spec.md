# Feature: AWS App Runner Deployment - Phase 2 (Observability & Documentation)

## Origin
This is **Phase 2 of 2** for the App Runner deployment from Linear issue **D2A-30**.

**Parent Spec**: `spec/active/app-runner-deployment/spec.md`
**Prerequisite**: Phase 1 must be completed and deployed

**Phase Strategy**:
- **Phase 1** (completed): Core infrastructure + working deployment
- **Phase 2** (this): Monitoring, alarms, and comprehensive documentation

## Outcome
Production-grade observability and documentation for the App Runner deployment:
- CloudWatch Logs with retention policy
- CloudWatch Alarms for critical metrics
- Comprehensive deployment documentation
- Operations runbook
- Enhanced README with troubleshooting

## User Story
As a **DevOps engineer**
I want **comprehensive monitoring and documentation for the App Runner deployment**
So that **I can operate it reliably and hand it off to a team**

## Context

### Why Phase 2 After Phase 1?
- **Build on working foundation**: Phase 1 proved the deployment works
- **Add observability**: Now that it's working, add visibility
- **Enable operations**: Documentation enables self-service operations
- **Reduce cognitive load**: Monitoring split keeps Phase 1 focused

### What Phase 1 Delivered
✅ Complete Terraform infrastructure
✅ Working App Runner service
✅ Secrets Manager integration
✅ Basic README

### What Phase 2 Adds
🎯 CloudWatch log group with retention
🎯 CloudWatch alarms (5xx errors, CPU)
🎯 Comprehensive DEPLOYMENT.md
🎯 Comprehensive OPERATIONS.md
🎯 Enhanced README with troubleshooting
🎯 Cost monitoring guidance

## Technical Requirements

### Files to Create

```
infra/tools/
└── monitoring.tf        # CloudWatch logs + alarms

docs/
├── DEPLOYMENT.md        # Comprehensive deployment guide
└── OPERATIONS.md        # Operations runbook

infra/tools/README.md    # MODIFY - enhance with troubleshooting
```

### CloudWatch Resources (monitoring.tf)

#### 1. Log Group
```hcl
resource "aws_cloudwatch_log_group" "app_runner" {
  name              = "/aws/apprunner/action-spec-service"
  retention_in_days = 7  # Cost-effective for demo

  tags = {
    Application = "action-spec"
    ManagedBy   = "terraform"
  }
}
```

**Note**: App Runner automatically sends logs to this group if it exists.

#### 2. CloudWatch Alarms

**5xx Error Rate Alarm**:
```hcl
resource "aws_cloudwatch_metric_alarm" "app_runner_5xx_errors" {
  alarm_name          = "action-spec-high-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/AppRunner"
  period              = 300  # 5 minutes
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when 5xx errors exceed 5 in 5 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = aws_apprunner_service.action_spec.service_name
  }

  # Optional: Add SNS topic ARN here for notifications
  # alarm_actions = [aws_sns_topic.alerts.arn]
}
```

**CPU Utilization Alarm**:
```hcl
resource "aws_cloudwatch_metric_alarm" "app_runner_high_cpu" {
  alarm_name          = "action-spec-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/AppRunner"
  period              = 300  # 5 minutes
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when CPU exceeds 80% for 10 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = aws_apprunner_service.action_spec.service_name
  }

  # Optional: Add SNS topic ARN here for notifications
  # alarm_actions = [aws_sns_topic.alerts.arn]
}
```

#### 3. Outputs (add to outputs.tf)
```hcl
output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.app_runner.name
}

output "alarm_5xx_arn" {
  description = "ARN of 5xx error alarm"
  value       = aws_cloudwatch_metric_alarm.app_runner_5xx_errors.arn
}

output "alarm_cpu_arn" {
  description = "ARN of CPU utilization alarm"
  value       = aws_cloudwatch_metric_alarm.app_runner_high_cpu.arn
}
```

### Documentation Requirements

#### docs/DEPLOYMENT.md

**Table of Contents**:
1. Prerequisites
2. Initial Setup
3. Environment Configuration
4. Deployment Steps
5. Verification
6. Troubleshooting
7. Updating the Deployment
8. Destroying Resources

**Key Sections**:

**Prerequisites**:
- AWS account and credentials configured
- OpenTofu installed (>= 1.5.0)
- direnv installed (optional but recommended)
- GitHub token with repo and workflow permissions

**Environment Configuration**:
- How to add `TF_VAR_github_token=$GH_TOKEN` to `.env.local`
- How to set up `.envrc` in `infra/tools/`
- How to verify environment variables

**Deployment Steps** (detailed walkthrough):
```bash
# 1. Navigate to infra/tools
cd infra/tools

# 2. Load environment (with direnv)
direnv allow

# Or manually
set -a; source ../../.env.local; set +a

# 3. Initialize Terraform
tofu init

# 4. Review plan
tofu plan

# 5. Apply infrastructure
tofu apply

# 6. Verify deployment
curl https://<output-url>/health
```

**Troubleshooting Common Issues**:
- `Error: No valid credential sources found` → AWS credentials not configured
- `Error: github_token is required` → TF_VAR_github_token not set
- `Service stuck in "OPERATION_IN_PROGRESS"` → Wait 5-10 minutes, check logs
- `Health check failing` → Check application logs in CloudWatch

**Updating**:
- Code changes: Push to GitHub (auto-deploys)
- Infrastructure changes: `tofu apply`
- Secret rotation: Update Secrets Manager value

**Destroying**:
```bash
tofu destroy
# Confirm: yes
# Note: 7-day recovery window for secrets
```

#### docs/OPERATIONS.md

**Table of Contents**:
1. Viewing Logs
2. Monitoring Alarms
3. Updating Secrets
4. Scaling the Service
5. Debugging Deployments
6. Cost Monitoring

**Key Sections**:

**Viewing Logs**:
```bash
# AWS Console
1. Navigate to CloudWatch > Log groups
2. Find /aws/apprunner/action-spec-service
3. Select log stream

# AWS CLI
aws logs tail /aws/apprunner/action-spec-service --follow
```

**Monitoring Alarms**:
- Where to find alarms in CloudWatch console
- What each alarm means
- How to interpret alarm states (OK, ALARM, INSUFFICIENT_DATA)
- Future: How to configure SNS notifications

**Updating GitHub Token Secret**:
```bash
# Via AWS Console
1. Secrets Manager > action-spec/github-token
2. Retrieve secret value > Edit
3. Update value > Save

# Via AWS CLI
aws secretsmanager put-secret-value \
  --secret-id action-spec/github-token \
  --secret-string "ghp_newtoken"

# Via Terraform (update .env.local, then)
tofu apply
```

**Scaling the Service**:
- How to modify `max_instances` in variables.tf
- How to update CPU/memory if needed
- When to consider scaling up

**Debugging Deployment Failures**:
- Check App Runner service status
- View deployment logs in CloudWatch
- Common failure modes:
  - Docker build failed → Check Dockerfile syntax
  - Health check timeout → Verify /health endpoint
  - Permission denied → Check IAM role policies

**Cost Monitoring**:
- Expected monthly cost: ~$5-10 for demo
- How to view costs in AWS Cost Explorer
- Cost factors: Instance hours, data transfer
- How to reduce costs: Decrease max_instances, reduce retention

#### infra/tools/README.md (enhance)

**Add sections**:

**Troubleshooting**:
- `tofu init` fails → Check AWS credentials
- `tofu plan` fails → Check TF_VAR_github_token
- `tofu apply` fails → Read error message, check AWS limits
- Service not responding → Check CloudWatch logs

**Monitoring**:
- Link to CloudWatch Logs: `/aws/apprunner/action-spec-service`
- Link to CloudWatch Alarms dashboard
- How to check service health

**Common Operations**:
- Force redeployment: Update environment variable
- View current infrastructure: `tofu show`
- Check drift: `tofu plan` (should show no changes)

## Validation Criteria

Phase 2 is complete when:

- [ ] `monitoring.tf` created with log group and 2 alarms
- [ ] `tofu plan` shows 3 new resources (log group + 2 alarms)
- [ ] `tofu apply` successfully creates monitoring resources
- [ ] CloudWatch log group exists and receives logs
- [ ] Both alarms are in "OK" state (or "INSUFFICIENT_DATA" initially)
- [ ] `docs/DEPLOYMENT.md` is comprehensive and accurate
- [ ] `docs/OPERATIONS.md` is comprehensive and accurate
- [ ] `infra/tools/README.md` enhanced with troubleshooting
- [ ] All documentation tested by following steps exactly
- [ ] Can trigger a 5xx alarm by intentional error (optional validation)

## Success Metrics

- Documentation quality: Team member can deploy from scratch using docs
- Alarm response time: Alerts trigger within 5 minutes of threshold breach
- Log availability: Application logs visible in CloudWatch within 1 minute
- Operations clarity: Common tasks documented with exact commands

## Implementation Notes

- **No code changes**: Only Terraform and documentation
- **Idempotent**: Can run `tofu apply` multiple times safely
- **Non-breaking**: Adding monitoring doesn't affect running service
- **Future-proof**: Document SNS setup but don't implement (out of scope)

## References

- Phase 1 spec: `spec/active/app-runner-phase1-deployment/spec.md`
- Parent spec: `spec/active/app-runner-deployment/spec.md`
- Linear issue: [D2A-30](https://linear.app/trakrf/issue/D2A-30)
- AWS CloudWatch Logs docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/
- AWS CloudWatch Alarms docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
