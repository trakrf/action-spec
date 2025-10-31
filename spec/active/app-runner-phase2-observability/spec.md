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

**Memory Utilization Alarm**:
```hcl
resource "aws_cloudwatch_metric_alarm" "app_runner_high_memory" {
  alarm_name          = "action-spec-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/AppRunner"
  period              = 300  # 5 minutes
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when memory exceeds 80% for 10 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = aws_apprunner_service.action_spec.service_name
  }

  # Optional: Add SNS topic ARN here for notifications
  # alarm_actions = [aws_sns_topic.alerts.arn]
}
```

**Health Check Failures Alarm**:
```hcl
resource "aws_cloudwatch_metric_alarm" "app_runner_health_check_failures" {
  alarm_name          = "action-spec-health-check-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HealthCheckFailed"
  namespace           = "AWS/AppRunner"
  period              = 300  # 5 minutes
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Alert when health checks fail more than 3 times in 5 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = aws_apprunner_service.action_spec.service_name
  }

  # Optional: Add SNS topic ARN here for notifications
  # alarm_actions = [aws_sns_topic.alerts.arn]
}
```

#### 3. CloudWatch Log Insights Queries

Create saved queries for common debugging scenarios:

**Application Errors**:
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 50
```

**5xx Errors**:
```
fields @timestamp, @message
| filter @message like /5\d{2}/
| stats count() by bin(5m)
```

**Slow Requests**:
```
fields @timestamp, @message
| filter @message like /duration/
| parse @message /duration: (?<duration>\d+)ms/
| filter duration > 1000
| sort duration desc
```

**Health Check Status**:
```
fields @timestamp, @message
| filter @message like /health/
| sort @timestamp desc
| limit 20
```

#### 4. Outputs (add to outputs.tf)
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

output "alarm_memory_arn" {
  description = "ARN of memory utilization alarm"
  value       = aws_cloudwatch_metric_alarm.app_runner_high_memory.arn
}

output "alarm_health_check_arn" {
  description = "ARN of health check failures alarm"
  value       = aws_cloudwatch_metric_alarm.app_runner_health_check_failures.arn
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

### Testing & Validation

After Phase 2 deployment, perform end-to-end validation:

#### Test Cases

**1. Load Blueprint from GitHub**:
```bash
# Access the deployed app
curl https://<app-runner-url>/

# Verify UI loads
# Navigate to blueprint selector
# Select a blueprint from the configured GitHub repo
# Expected: Blueprint loads successfully, displays infrastructure parameters
```

**2. Edit Values in UI**:
- Modify infrastructure parameter values (e.g., instance_type, region)
- Expected: UI reflects changes immediately
- Expected: No errors in browser console

**3. Validate Against AWS**:
- Click "Validate" button
- Expected: Validation runs against AWS API
- Expected: Returns success/failure with clear messages
- Expected: Check CloudWatch logs for validation API calls

**4. Trigger workflow_dispatch**:
```bash
# From UI, trigger GitHub Actions workflow
# Expected: Workflow dispatch event sent to GitHub API
# Expected: Success message displayed in UI
```

**5. Verify Workflow Execution**:
```bash
# Check GitHub Actions tab in repo
gh run list --limit 5

# Expected: New workflow run appears
# Expected: Run completes successfully
# Expected: Infrastructure changes applied (if validation passed)
```

#### Monitoring Validation

**6. Verify CloudWatch Logs**:
```bash
# Tail logs in real-time
aws logs tail /aws/apprunner/action-spec-service --follow

# Expected: Application logs appear within 1 minute
# Expected: Request/response logs visible
# Expected: No ERROR level messages during normal operation
```

**7. Check Alarm Status**:
```bash
# List all alarms
aws cloudwatch describe-alarms --alarm-names \
  action-spec-high-5xx-errors \
  action-spec-high-cpu \
  action-spec-high-memory \
  action-spec-health-check-failures

# Expected: All alarms in "OK" state
# Expected: No "ALARM" state unless intentionally triggered
```

**8. Test CloudWatch Insights Queries**:
- Navigate to CloudWatch > Logs Insights
- Select log group: `/aws/apprunner/action-spec-service`
- Run each saved query from section "CloudWatch Log Insights Queries"
- Expected: Queries execute successfully
- Expected: Results show application activity

#### Optional: Trigger Test Alarm

**9. Intentionally Trigger 5xx Alarm** (for validation):
```python
# Add temporary route to backend for testing
@app.route('/test/trigger-500')
def trigger_500():
    abort(500)

# Make 6 requests within 5 minutes
for i in range(6):
    curl https://<app-runner-url>/test/trigger-500
```
- Expected: 5xx alarm triggers within 5 minutes
- Expected: Alarm state changes to "ALARM"
- Remove test route after validation

### Handoff Requirements

Phase 2 includes handoff to MediaCo team:

#### Pre-Handoff Checklist
- [ ] All monitoring resources deployed and verified
- [ ] All documentation complete and tested
- [ ] End-to-end testing passed (all 9 test cases above)
- [ ] Application healthy and responding
- [ ] No active alarms

#### Handoff Session
**Demo Walkthrough** (30-45 minutes):
1. Show deployed application in action
2. Walk through loading a blueprint
3. Demonstrate editing and validation
4. Show workflow dispatch triggering
5. Verify workflow execution in GitHub
6. Show CloudWatch logs in real-time
7. Explain alarm setup and monitoring

**Documentation Review** (15 minutes):
- Walk through DEPLOYMENT.md
- Explain OPERATIONS.md runbook
- Answer questions about troubleshooting

**Access Handoff**:
- Confirm MediaCo team has AWS console access
- Verify they can access:
  - App Runner service
  - CloudWatch logs
  - CloudWatch alarms
  - Secrets Manager (for token updates)
- Provide credentials if needed

**Confirmation** (get explicit sign-off):
- [ ] Team can access and use the tool successfully
- [ ] Team understands how to check logs and alarms
- [ ] Team knows how to update secrets if needed
- [ ] Team has contact for escalation (if issues arise)
- [ ] All questions answered

#### Post-Handoff
- Document any issues raised during handoff
- Address blockers immediately
- Schedule follow-up check-in (1 week later)
- Mark D2A-30 complete only after confirmation received

## Validation Criteria

Phase 2 is complete when:

**Infrastructure**:
- [ ] `monitoring.tf` created with log group and 4 alarms (5xx, CPU, Memory, Health Check)
- [ ] `tofu plan` shows 5 new resources (log group + 4 alarms)
- [ ] `tofu apply` successfully creates monitoring resources
- [ ] CloudWatch log group exists and receives logs
- [ ] All 4 alarms are in "OK" state (or "INSUFFICIENT_DATA" initially)
- [ ] All alarm outputs added to `outputs.tf`

**CloudWatch Insights**:
- [ ] All 4 saved queries created and tested
- [ ] Queries return expected results with application data

**Documentation**:
- [ ] `docs/DEPLOYMENT.md` is comprehensive and accurate
- [ ] `docs/OPERATIONS.md` is comprehensive and accurate
- [ ] `infra/tools/README.md` enhanced with troubleshooting
- [ ] All documentation tested by following steps exactly

**Testing & Validation**:
- [ ] Test Case 1: Load blueprint from GitHub (✓ passes)
- [ ] Test Case 2: Edit values in UI (✓ passes)
- [ ] Test Case 3: Validate against AWS (✓ passes)
- [ ] Test Case 4: Trigger workflow_dispatch (✓ passes)
- [ ] Test Case 5: Verify workflow execution (✓ passes)
- [ ] Test Case 6: Verify CloudWatch logs (✓ passes)
- [ ] Test Case 7: Check alarm status (✓ passes)
- [ ] Test Case 8: Test CloudWatch Insights queries (✓ passes)
- [ ] Test Case 9: Trigger test alarm (optional, ✓ if attempted)

**Handoff**:
- [ ] Pre-handoff checklist complete (all items ✓)
- [ ] Demo walkthrough completed with MediaCo team
- [ ] Documentation review completed
- [ ] Access handoff completed (team has AWS access)
- [ ] Team confirmation received (explicit sign-off)
- [ ] All team questions answered
- [ ] Follow-up scheduled (1 week post-handoff)

## Success Metrics

- Documentation quality: Team member can deploy from scratch using docs
- Alarm response time: Alerts trigger within 5 minutes of threshold breach
- Log availability: Application logs visible in CloudWatch within 1 minute
- Operations clarity: Common tasks documented with exact commands

## Implementation Notes

- **Minimal code changes**: Only Terraform, documentation, and optional test route
- **Idempotent**: Can run `tofu apply` multiple times safely
- **Non-breaking**: Adding monitoring doesn't affect running service
- **Future-proof**: Document SNS setup but don't implement (out of scope)
- **Handoff required**: Phase 2 not complete until MediaCo team sign-off

## References

- Phase 1 spec: `spec/active/app-runner-phase1-deployment/spec.md`
- Parent spec: `spec/active/app-runner-deployment/spec.md`
- Linear issue: [D2A-30](https://linear.app/trakrf/issue/D2A-30)
- AWS CloudWatch Logs docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/
- AWS CloudWatch Alarms docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
