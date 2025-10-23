# AWS IAM Policies for ActionSpec Lambda Functions

## AWS Discovery Lambda Permissions

The `aws-discovery` Lambda requires read-only permissions to query AWS resources.

### Minimal IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DiscoverVPCResources",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DiscoverLoadBalancers",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancers"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DiscoverWAFResources",
      "Effect": "Allow",
      "Action": [
        "wafv2:ListWebACLs",
        "wafv2:GetWebACL"
      ],
      "Resource": "*"
    }
  ]
}
```

### Why These Permissions?

- **ec2:DescribeVpcs**: List VPCs for network configuration
- **ec2:DescribeSubnets**: List subnets for compute placement
- **elasticloadbalancing:DescribeLoadBalancers**: List ALBs for WAF attachment
- **wafv2:ListWebACLs**: List existing WAF configurations
- **wafv2:GetWebACL**: Get WAF details (rule counts, etc.)

### Permission Scope

All permissions use `"Resource": "*"` because:
- Describe operations don't support resource-level permissions
- Read-only operations have minimal security risk
- Simplifies deployment (no resource ARNs needed)

### Testing Permissions

Validate Lambda has correct permissions:

```bash
# Invoke discovery Lambda
aws lambda invoke \
  --function-name actionspec-aws-discovery \
  --payload '{}' \
  response.json

# Check response
cat response.json | jq .

# Expected: JSON with vpcs, subnets, albs, waf_webacls arrays
# If empty arrays: Either no resources exist OR missing permissions
```

### Troubleshooting

**Empty arrays in response:**
1. Check CloudWatch logs for permission errors
2. Verify Lambda execution role has policy attached
3. Confirm resources exist in same region as Lambda
4. Test with AWS CLI using same role

**Permission errors in logs:**
```
Failed to discover VPCs: AccessDenied
```
- Add missing permission to Lambda execution role
- Verify IAM policy is attached (not just created)
- Check for SCPs or permission boundaries blocking access
