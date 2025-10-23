# Phase 3.3.5: AWS Discovery Lambda

## Origin
This specification implements the third sub-phase of Phase 3.3 (GitHub Integration & AWS Discovery) from PRD.md. This phase is **independent** and can be developed in parallel with Phase 3.3.2. It enables the React frontend (Phase 3.4) to pre-populate form dropdowns with existing AWS resources.

## Outcome
ActionSpec can query existing AWS infrastructure (VPCs, Subnets, ALBs, WAF) and return structured JSON suitable for form dropdown population. This improves user experience by showing available resources instead of requiring manual entry.

**What will change:**
- Complete `aws-discovery` Lambda implementation (replaces stub from Phase 3.1)
- Resource query functions for VPCs, Subnets, ALBs, and WAF WebACLs
- Structured JSON response format for frontend consumption
- IAM policy documentation (`docs/IAM_POLICIES.md`)
- Error handling for missing permissions and empty results
- Comprehensive unit tests with mocked boto3 responses

## User Story
As a **user configuring infrastructure via ActionSpec**
I want **dropdowns populated with my existing AWS resources**
So that **I can select resources without memorizing IDs or ARNs**

## Context

**Discovery**: Phase 3.4 will build a React form for editing specs. Instead of requiring users to type VPC IDs or ALB ARNs manually, we can query AWS and populate dropdowns. This reduces errors and improves UX.

**Current State**:
- aws-discovery Lambda is a stub returning hardcoded JSON
- No AWS resource queries implemented
- No IAM policies defined for resource discovery
- Frontend will require manual resource ID entry

**Desired State**:
- aws-discovery Lambda queries real AWS resources
- Returns structured JSON with resource IDs, names, and metadata
- Handles missing permissions gracefully (empty arrays, not errors)
- Handles AWS accounts with no resources (new accounts)
- Frontend receives ready-to-use dropdown data

**Why This Matters**:
- **User Experience**: Dropdowns > manual ID entry
- **Error Reduction**: Can't select non-existent resources
- **Discovery**: Shows users what infrastructure exists
- **Validation**: Can verify references before creating PR

**Why Independent**:
- Doesn't depend on GitHub integration (3.3.1, 3.3.2)
- Doesn't block PR creation (3.3.2)
- Can be developed and tested in parallel
- Nice-to-have for Phase 3.4 (not blocking)

## Technical Requirements

### 1. AWS Discovery Lambda Implementation (`backend/lambda/functions/aws-discovery/handler.py`)

Replace stub with full implementation:

```python
import boto3
import json
from typing import List, Dict, Any
from shared.security_wrapper import secure_handler

# Initialize AWS clients (outside handler for reuse)
ec2_client = boto3.client('ec2')
elbv2_client = boto3.client('elbv2')
wafv2_client = boto3.client('wafv2')

@secure_handler
def handler(event, context):
    """
    GET /aws/discover

    Query Parameters:
    - resource_type: Optional filter (vpc|subnet|alb|waf|all)
    - vpc_id: Optional VPC filter for subnets

    Response:
    {
      "vpcs": [
        {
          "id": "vpc-0123456789abcdef0",
          "cidr": "10.0.0.0/16",
          "name": "demo-vpc",
          "is_default": false
        }
      ],
      "subnets": [
        {
          "id": "subnet-0123456789abcdef0",
          "vpc_id": "vpc-0123456789abcdef0",
          "cidr": "10.0.1.0/24",
          "availability_zone": "us-west-2a",
          "name": "demo-subnet-public-1"
        }
      ],
      "albs": [
        {
          "arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/demo-alb/1234567890abcdef",
          "name": "demo-alb",
          "dns_name": "demo-alb-1234567890.us-west-2.elb.amazonaws.com",
          "vpc_id": "vpc-0123456789abcdef0",
          "state": "active"
        }
      ],
      "waf_webacls": [
        {
          "id": "12345678-1234-1234-1234-123456789012",
          "name": "demo-waf",
          "arn": "arn:aws:wafv2:us-west-2:123456789012:regional/webacl/demo-waf/12345678-1234-1234-1234-123456789012",
          "scope": "REGIONAL",
          "managed_rule_count": 3
        }
      ]
    }
    """

    # Parse query parameters
    params = event.get('queryStringParameters') or {}
    resource_type = params.get('resource_type', 'all')
    vpc_id = params.get('vpc_id')

    # Discover resources
    results = {}

    if resource_type in ['vpc', 'all']:
        results['vpcs'] = discover_vpcs()

    if resource_type in ['subnet', 'all']:
        results['subnets'] = discover_subnets(vpc_id)

    if resource_type in ['alb', 'all']:
        results['albs'] = discover_albs()

    if resource_type in ['waf', 'all']:
        results['waf_webacls'] = discover_waf_webacls()

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
```

### 2. Resource Discovery Functions

```python
def discover_vpcs() -> List[Dict[str, Any]]:
    """
    Discover all VPCs in the current region.

    Returns:
        List of VPC dictionaries with keys:
        - id: VPC ID (e.g., "vpc-0123...")
        - cidr: CIDR block (e.g., "10.0.0.0/16")
        - name: VPC name from tags (or "unnamed")
        - is_default: Boolean indicating default VPC

    Error Handling:
        - Missing permissions: Returns empty list (no exception)
        - No VPCs: Returns empty list
        - API errors: Logs error, returns empty list
    """
    try:
        response = ec2_client.describe_vpcs()
        vpcs = []

        for vpc in response.get('Vpcs', []):
            # Extract name from tags
            name = _extract_name_tag(vpc.get('Tags', []))

            vpcs.append({
                'id': vpc['VpcId'],
                'cidr': vpc['CidrBlock'],
                'name': name,
                'is_default': vpc.get('IsDefault', False)
            })

        return sorted(vpcs, key=lambda v: v['name'])

    except ec2_client.exceptions.ClientError as e:
        _log_discovery_error('VPCs', e)
        return []
    except Exception as e:
        _log_discovery_error('VPCs', e)
        return []

def discover_subnets(vpc_id: str = None) -> List[Dict[str, Any]]:
    """
    Discover subnets in current region, optionally filtered by VPC.

    Args:
        vpc_id: Optional VPC ID filter

    Returns:
        List of subnet dictionaries with keys:
        - id: Subnet ID
        - vpc_id: Parent VPC ID
        - cidr: CIDR block
        - availability_zone: AZ name
        - name: Subnet name from tags

    Error Handling:
        - Missing permissions: Returns empty list
        - Invalid vpc_id: Returns empty list (no exception)
        - No subnets: Returns empty list
    """
    try:
        filters = []
        if vpc_id:
            filters.append({'Name': 'vpc-id', 'Values': [vpc_id]})

        response = ec2_client.describe_subnets(Filters=filters)
        subnets = []

        for subnet in response.get('Subnets', []):
            name = _extract_name_tag(subnet.get('Tags', []))

            subnets.append({
                'id': subnet['SubnetId'],
                'vpc_id': subnet['VpcId'],
                'cidr': subnet['CidrBlock'],
                'availability_zone': subnet['AvailabilityZone'],
                'name': name
            })

        return sorted(subnets, key=lambda s: s['name'])

    except ec2_client.exceptions.ClientError as e:
        _log_discovery_error('Subnets', e)
        return []
    except Exception as e:
        _log_discovery_error('Subnets', e)
        return []

def discover_albs() -> List[Dict[str, Any]]:
    """
    Discover Application Load Balancers in current region.

    Returns:
        List of ALB dictionaries with keys:
        - arn: Full ALB ARN
        - name: ALB name
        - dns_name: DNS name for ALB
        - vpc_id: VPC where ALB is deployed
        - state: ALB state (active, provisioning, failed)

    Error Handling:
        - Missing permissions: Returns empty list
        - No ALBs: Returns empty list
    """
    try:
        response = elbv2_client.describe_load_balancers()
        albs = []

        for lb in response.get('LoadBalancers', []):
            # Filter to only Application Load Balancers (not NLB, GLB)
            if lb.get('Type') == 'application':
                albs.append({
                    'arn': lb['LoadBalancerArn'],
                    'name': lb['LoadBalancerName'],
                    'dns_name': lb['DNSName'],
                    'vpc_id': lb['VpcId'],
                    'state': lb['State']['Code']
                })

        return sorted(albs, key=lambda a: a['name'])

    except elbv2_client.exceptions.ClientError as e:
        _log_discovery_error('ALBs', e)
        return []
    except Exception as e:
        _log_discovery_error('ALBs', e)
        return []

def discover_waf_webacls() -> List[Dict[str, Any]]:
    """
    Discover WAF WebACLs in current region (REGIONAL scope).

    Returns:
        List of WebACL dictionaries with keys:
        - id: WebACL ID
        - name: WebACL name
        - arn: Full WebACL ARN
        - scope: REGIONAL (CloudFront WebACLs not included)
        - managed_rule_count: Number of managed rule groups

    Error Handling:
        - Missing permissions: Returns empty list
        - No WebACLs: Returns empty list

    Note:
        - Only discovers REGIONAL scope (for API Gateway, ALB)
        - CLOUDFRONT scope WebACLs require global endpoint (future)
    """
    try:
        response = wafv2_client.list_web_acls(Scope='REGIONAL')
        webacls = []

        for webacl in response.get('WebACLs', []):
            # Get detailed info for rule count
            details = wafv2_client.get_web_acl(
                Scope='REGIONAL',
                Id=webacl['Id'],
                Name=webacl['Name']
            )

            managed_rule_count = len([
                rule for rule in details['WebACL'].get('Rules', [])
                if 'ManagedRuleGroupStatement' in rule.get('Statement', {})
            ])

            webacls.append({
                'id': webacl['Id'],
                'name': webacl['Name'],
                'arn': webacl['ARN'],
                'scope': 'REGIONAL',
                'managed_rule_count': managed_rule_count
            })

        return sorted(webacls, key=lambda w: w['name'])

    except wafv2_client.exceptions.ClientError as e:
        _log_discovery_error('WAF WebACLs', e)
        return []
    except Exception as e:
        _log_discovery_error('WAF WebACLs', e)
        return []

# Helper functions

def _extract_name_tag(tags: List[Dict[str, str]]) -> str:
    """
    Extract 'Name' tag from AWS resource tags.

    Args:
        tags: List of tag dicts with 'Key' and 'Value'

    Returns:
        str: Name tag value or "unnamed" if not found
    """
    for tag in tags:
        if tag.get('Key') == 'Name':
            return tag.get('Value', 'unnamed')
    return 'unnamed'

def _log_discovery_error(resource_type: str, error: Exception):
    """
    Log discovery errors without failing the request.

    Args:
        resource_type: Type of resource being discovered
        error: Exception that occurred

    Note:
        - Logs at WARNING level (not ERROR)
        - Helps debug permission issues
        - Doesn't expose sensitive info
    """
    import logging
    logger = logging.getLogger()

    if hasattr(error, 'response'):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        logger.warning(f"Failed to discover {resource_type}: {error_code}")
    else:
        logger.warning(f"Failed to discover {resource_type}: {type(error).__name__}")
```

### 3. IAM Permissions Required

Document in `docs/IAM_POLICIES.md`:

```markdown
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
```

### 4. API Gateway Integration

Update SAM template:

```yaml
AwsDiscoveryFunction:
  Type: AWS::Serverless::Function
  Properties:
    Handler: handler.handler
    Events:
      DiscoverResources:
        Type: Api
        Properties:
          RestApiId: !Ref ActionSpecApi
          Path: /aws/discover
          Method: GET
    Policies:
      - Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - ec2:DescribeVpcs
              - ec2:DescribeSubnets
              - elasticloadbalancing:DescribeLoadBalancers
              - wafv2:ListWebACLs
              - wafv2:GetWebACL
            Resource: '*'
```

### 5. Testing Requirements

**Unit Tests (pytest):**

```python
# test_aws_discovery.py

def test_discover_vpcs_success(mock_ec2):
    """Test VPC discovery returns formatted results"""
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [
            {
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'Tags': [{'Key': 'Name', 'Value': 'demo-vpc'}]
            }
        ]
    }

    vpcs = discover_vpcs()

    assert len(vpcs) == 1
    assert vpcs[0]['id'] == 'vpc-123'
    assert vpcs[0]['name'] == 'demo-vpc'

def test_discover_vpcs_missing_permissions(mock_ec2):
    """Test VPC discovery with AccessDenied returns empty list (not error)"""
    from botocore.exceptions import ClientError

    mock_ec2.describe_vpcs.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied'}},
        'DescribeVpcs'
    )

    vpcs = discover_vpcs()
    assert vpcs == []  # Graceful degradation

def test_discover_vpcs_no_resources(mock_ec2):
    """Test VPC discovery with no VPCs returns empty list"""
    mock_ec2.describe_vpcs.return_value = {'Vpcs': []}
    vpcs = discover_vpcs()
    assert vpcs == []

def test_discover_subnets_filtered_by_vpc(mock_ec2):
    """Test subnet discovery filters by VPC ID"""
    pass

def test_discover_albs_filters_application_only(mock_elbv2):
    """Test ALB discovery excludes NLBs and GLBs"""
    pass

def test_discover_waf_regional_scope_only(mock_wafv2):
    """Test WAF discovery only returns REGIONAL scope"""
    pass

def test_handler_all_resources(mock_ec2, mock_elbv2, mock_wafv2):
    """Test handler returns all resource types"""
    event = {'queryStringParameters': None}
    response = handler(event, None)

    body = json.loads(response['body'])
    assert 'vpcs' in body
    assert 'subnets' in body
    assert 'albs' in body
    assert 'waf_webacls' in body

def test_handler_filters_by_resource_type(mock_ec2):
    """Test handler filters to specific resource type"""
    event = {'queryStringParameters': {'resource_type': 'vpc'}}
    response = handler(event, None)

    body = json.loads(response['body'])
    assert 'vpcs' in body
    assert 'subnets' not in body

def test_extract_name_tag_present():
    """Test name extraction from tags"""
    tags = [{'Key': 'Name', 'Value': 'my-vpc'}]
    assert _extract_name_tag(tags) == 'my-vpc'

def test_extract_name_tag_missing():
    """Test name extraction with no Name tag"""
    tags = [{'Key': 'Environment', 'Value': 'prod'}]
    assert _extract_name_tag(tags) == 'unnamed'
```

**Integration Tests (Manual):**
- [ ] Deploy to AWS and test against real account
- [ ] Verify response with resources present
- [ ] Verify response with no resources (new account)
- [ ] Test with read-only IAM role (confirm no write operations)

## Validation Criteria

### Immediate (Measured at PR Merge):
- [ ] discover_vpcs() returns list of VPCs with name, CIDR, ID
- [ ] discover_subnets() filters by VPC ID correctly
- [ ] discover_albs() only returns Application Load Balancers
- [ ] discover_waf_webacls() returns REGIONAL scope WebACLs
- [ ] Missing permissions return empty arrays (no exceptions)
- [ ] No resources return empty arrays (not errors)
- [ ] Unit tests cover all error scenarios (8+ tests)
- [ ] Test coverage > 85% for aws-discovery handler
- [ ] IAM policy documented in docs/IAM_POLICIES.md

### Integration Tests (Manual):
- [ ] Test against AWS account with resources → Returns populated arrays
- [ ] Test against new AWS account → Returns empty arrays (no errors)
- [ ] Test with missing permissions → Returns empty arrays, logs warning
- [ ] Response JSON structure matches frontend expectations

### Post-Merge (Phase 3.4 Validation):
- [ ] React frontend calls /aws/discover successfully
- [ ] Dropdowns populated with real AWS resources
- [ ] Empty arrays don't break UI (graceful handling)

## Success Metrics

**Technical:**
- < 2s response time for full discovery (all resource types)
- < 500ms response time for single resource type
- 100% test pass rate
- Zero exceptions for missing permissions

**User Experience:**
- Users see existing resources in dropdowns
- No manual ID entry required
- Clear messaging when no resources exist

## Dependencies
- **Requires**: Phase 3.1 (SAM template with Lambda stub)
- **Independent**: Can run parallel with 3.3.1 and 3.3.2
- **Nice-to-have for**: Phase 3.4 (frontend dropdowns)

## Edge Cases to Handle

1. **No Resources Exist** (New AWS Account):
   - Scenario: User just created AWS account
   - Response: Return empty arrays for all resource types
   - UI Handling: Show "No resources found" message

2. **Missing IAM Permissions**:
   - Scenario: Lambda role missing ec2:DescribeVpcs
   - Response: Log warning, return empty array for VPCs
   - Other Resources: Continue querying (partial results OK)

3. **Large Number of Resources** (1000+ VPCs):
   - Scenario: Enterprise account with many resources
   - Response: Paginate through results (boto3 handles automatically)
   - Performance: May exceed 2s SLA (document limitation)

4. **Resources in Different Region**:
   - Scenario: Resources exist but in us-east-1, Lambda in us-west-2
   - Response: Return empty arrays (region-specific)
   - Documentation: Note Lambda discovers same-region resources only

5. **Unnamed Resources** (No Name Tag):
   - Scenario: Resources created without Name tag
   - Response: Use "unnamed" as name, include ID
   - Sorting: Unnamed resources sort to top

6. **Network Load Balancers Mixed with ALBs**:
   - Scenario: describe_load_balancers returns NLBs too
   - Response: Filter to Type == 'application' only
   - Why: WAF only attaches to ALBs, not NLBs

## Implementation Notes

### Why Graceful Degradation (Empty Arrays)?
- User Experience: Partial results > complete failure
- Error Recovery: UI can handle empty arrays
- Debugging: Logs indicate permission issues
- Resilience: One API failure doesn't break entire response

### Why REGIONAL Scope Only for WAF?
- API Gateway: Uses REGIONAL WebACLs
- ALB: Uses REGIONAL WebACLs
- CloudFront: Uses CLOUDFRONT WebACLs (different endpoint)
- Simplification: Phase 1 focuses on regional resources

### Why Sort by Name?
- User Experience: Alphabetical order easier to scan
- Predictability: Consistent ordering across requests
- Unnamed First: Easy to spot resources needing tags

### Why Cache boto3 Clients Outside Handler?
- Performance: Reuse connections across invocations
- Best Practice: AWS Lambda recommends global client initialization
- Cost: Reduces SDK overhead

## Future Enhancements (Post-Phase 3.3.3)

Not in scope for this phase but documented for future work:

1. **Response Caching** (ElastiCache/DynamoDB):
   - Benefit: Reduce AWS API calls, faster responses
   - TTL: 5-minute cache (resources don't change often)
   - Effort: 4-6 hours

2. **Cross-Region Discovery**:
   - Benefit: Show resources from all regions
   - Implementation: Query multiple regions in parallel
   - Effort: 3-4 hours

3. **CloudFront WAF WebACLs**:
   - Benefit: Discover global WAF configurations
   - Implementation: Query us-east-1 CLOUDFRONT scope
   - Effort: 2-3 hours

4. **Target Group Discovery**:
   - Benefit: Show ALB target groups for compute selection
   - Implementation: Add describe_target_groups()
   - Effort: 2 hours

5. **Security Group Discovery**:
   - Benefit: Show security groups for network configuration
   - Implementation: Add describe_security_groups()
   - Effort: 2 hours

6. **Resource Filtering by Tags**:
   - Benefit: Only show resources tagged for ActionSpec
   - Implementation: Add tag filter to describe calls
   - Effort: 1-2 hours

## Conversation References

**Key Insights:**
- "Phase 3.3.3 is independent - can run parallel to 3.3.2" - Execution strategy
- "Nice-to-have for Phase 3.4 (not blocking)" - Priority clarification
- "Dropdowns populated with existing resources" - User experience goal

**Decisions Made:**
- Graceful degradation (empty arrays) for missing permissions
- REGIONAL scope only (CloudFront deferred)
- Name tag extraction with "unnamed" fallback
- Sort by name for better UX

**Concerns Addressed:**
- New AWS accounts: Empty arrays, not errors
- Missing permissions: Log warning, continue with other resources
- Large result sets: Document pagination (handled by boto3)
- Cross-region: Document limitation (same-region only)
