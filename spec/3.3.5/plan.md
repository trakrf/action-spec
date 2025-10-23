# Implementation Plan: AWS Discovery Lambda
Generated: 2025-10-23
Specification: spec.md

## Understanding

This phase replaces the aws-discovery Lambda stub with a full implementation that queries AWS resources (VPCs, Subnets, ALBs, WAF WebACLs) and returns structured JSON for frontend dropdown population. The implementation follows established patterns from the codebase and emphasizes graceful degradation - missing permissions or empty results return empty arrays, not errors.

**Key Requirements:**
- Query AWS resources using boto3 clients (EC2, ELBv2, WAFv2)
- Return structured JSON with resource IDs, names, and metadata
- Handle missing permissions gracefully (empty arrays, log at ERROR level)
- Handle AWS accounts with no resources (new accounts)
- Comprehensive unit tests with mocked boto3 responses (90%+ coverage)
- IAM policy documentation

**User Value:**
- Dropdowns populated with existing AWS resources
- No manual ID/ARN entry required
- Reduced errors from invalid resource references

## Relevant Files

**Reference Patterns** (existing code to follow):

- `backend/lambda/functions/spec-parser/handler.py` (lines 18-87) - Lambda handler structure with @secure_handler
- `backend/lambda/shared/security_wrapper.py` (lines 112-242) - @secure_handler decorator implementation
- `backend/lambda/shared/github_client.py` (lines 135-147) - boto3 client usage and ClientError handling
- `backend/tests/test_github_client.py` (lines 31-82) - Mock fixtures setup pattern for boto3
- `backend/tests/test_security_wrapper.py` (lines 129-142) - Security headers verification pattern
- `backend/lambda/functions/spec-applier/handler.py` (lines 111-116) - Error response formatting

**Files to Create**:

- `backend/tests/test_aws_discovery.py` - Comprehensive unit tests for all discovery functions
- `docs/IAM_POLICIES.md` - IAM permissions documentation for Lambda functions

**Files to Modify**:

- `backend/lambda/functions/aws-discovery/handler.py` (lines 1-49) - Replace stub with full AWS resource discovery implementation
- `template.yaml` (lines 145-189) - Verify/update IAM policies and API Gateway path (currently `/api/discover`, spec shows `/aws/discover`)

## Architecture Impact

- **Subsystems affected**: Backend API (Lambda functions only)
- **New dependencies**: None (boto3 included in Lambda runtime)
- **Breaking changes**: API path may change from `/api/discover` to `/aws/discover` (verify with user during build)

## Task Breakdown

### Task 1: Initialize boto3 clients at module level
**File**: `backend/lambda/functions/aws-discovery/handler.py`
**Action**: MODIFY (lines 1-17)
**Pattern**: AWS best practice - initialize outside handler for connection reuse

**Implementation**:
```python
import boto3
import json
from typing import List, Dict, Any
import sys
import os

# Add shared module to path
sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from security_wrapper import secure_handler

# Initialize AWS clients outside handler for reuse (AWS best practice)
ec2_client = boto3.client('ec2')
elbv2_client = boto3.client('elbv2')
wafv2_client = boto3.client('wafv2')
```

**Validation**:
```bash
cd backend
black --check lambda/functions/aws-discovery/handler.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

### Task 2: Implement discover_vpcs() function
**File**: `backend/lambda/functions/aws-discovery/handler.py`
**Action**: MODIFY (add after client initialization)
**Pattern**: Reference github_client.py:135-147 for boto3 error handling

**Implementation**:
```python
def discover_vpcs() -> List[Dict[str, Any]]:
    """
    Discover all VPCs in the current region.

    Returns empty list on errors (graceful degradation).
    Logs errors at ERROR level for visibility.
    """
    try:
        response = ec2_client.describe_vpcs()
        vpcs = []

        for vpc in response.get('Vpcs', []):
            name = _extract_name_tag(vpc.get('Tags', []))
            vpcs.append({
                'id': vpc['VpcId'],
                'cidr': vpc['CidrBlock'],
                'name': name,
                'is_default': vpc.get('IsDefault', False)
            })

        # Sort named resources first, then unnamed
        return sorted(vpcs, key=lambda v: (v['name'] == 'unnamed', v['name']))

    except Exception as e:
        _log_discovery_error('VPCs', e)
        return []
```

**Validation**:
```bash
cd backend
black --check lambda/functions/aws-discovery/handler.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

### Task 3: Implement discover_subnets() function
**File**: `backend/lambda/functions/aws-discovery/handler.py`
**Action**: MODIFY (add after discover_vpcs)
**Pattern**: Similar to discover_vpcs with optional filtering

**Implementation**:
```python
def discover_subnets(vpc_id: str = None) -> List[Dict[str, Any]]:
    """
    Discover subnets in current region, optionally filtered by VPC.

    Args:
        vpc_id: Optional VPC ID filter

    Returns empty list on errors (graceful degradation).
    """
    try:
        filters = []
        if vpc_id:
            filters.append({'Name': 'vpc-id', 'Values': [vpc_id]})

        response = ec2_client.describe_subnets(Filters=filters) if filters else ec2_client.describe_subnets()
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

        return sorted(subnets, key=lambda s: (s['name'] == 'unnamed', s['name']))

    except Exception as e:
        _log_discovery_error('Subnets', e)
        return []
```

**Validation**:
```bash
cd backend
black --check lambda/functions/aws-discovery/handler.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

### Task 4: Implement discover_albs() function
**File**: `backend/lambda/functions/aws-discovery/handler.py`
**Action**: MODIFY (add after discover_subnets)
**Pattern**: Filter by Type == 'application' to exclude NLBs and GLBs

**Implementation**:
```python
def discover_albs() -> List[Dict[str, Any]]:
    """
    Discover Application Load Balancers in current region.

    Filters to only ALBs (excludes NLBs, GLBs).
    Returns empty list on errors (graceful degradation).
    """
    try:
        response = elbv2_client.describe_load_balancers()
        albs = []

        for lb in response.get('LoadBalancers', []):
            # Filter to only Application Load Balancers
            if lb.get('Type') == 'application':
                albs.append({
                    'arn': lb['LoadBalancerArn'],
                    'name': lb['LoadBalancerName'],
                    'dns_name': lb['DNSName'],
                    'vpc_id': lb['VpcId'],
                    'state': lb['State']['Code']
                })

        return sorted(albs, key=lambda a: a['name'])

    except Exception as e:
        _log_discovery_error('ALBs', e)
        return []
```

**Validation**:
```bash
cd backend
black --check lambda/functions/aws-discovery/handler.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

### Task 5: Implement discover_waf_webacls() function
**File**: `backend/lambda/functions/aws-discovery/handler.py`
**Action**: MODIFY (add after discover_albs)
**Pattern**: Query REGIONAL scope only, get detailed info for rule count

**Implementation**:
```python
def discover_waf_webacls() -> List[Dict[str, Any]]:
    """
    Discover WAF WebACLs in current region (REGIONAL scope only).

    Returns empty list on errors (graceful degradation).
    Note: CLOUDFRONT scope requires us-east-1 global endpoint (future enhancement).
    """
    try:
        response = wafv2_client.list_web_acls(Scope='REGIONAL')
        webacls = []

        for webacl in response.get('WebACLs', []):
            # Get detailed info for rule count
            try:
                details = wafv2_client.get_web_acl(
                    Scope='REGIONAL',
                    Id=webacl['Id'],
                    Name=webacl['Name']
                )

                managed_rule_count = len([
                    rule for rule in details['WebACL'].get('Rules', [])
                    if 'ManagedRuleGroupStatement' in rule.get('Statement', {})
                ])
            except Exception:
                # If get_web_acl fails, continue with 0 count
                managed_rule_count = 0

            webacls.append({
                'id': webacl['Id'],
                'name': webacl['Name'],
                'arn': webacl['ARN'],
                'scope': 'REGIONAL',
                'managed_rule_count': managed_rule_count
            })

        return sorted(webacls, key=lambda w: w['name'])

    except Exception as e:
        _log_discovery_error('WAF WebACLs', e)
        return []
```

**Validation**:
```bash
cd backend
black --check lambda/functions/aws-discovery/handler.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

### Task 6: Implement helper functions
**File**: `backend/lambda/functions/aws-discovery/handler.py`
**Action**: MODIFY (add after discovery functions)
**Pattern**: Simple utility functions for name extraction and error logging

**Implementation**:
```python
def _extract_name_tag(tags: List[Dict[str, str]]) -> str:
    """
    Extract 'Name' tag from AWS resource tags.

    Args:
        tags: List of tag dicts with 'Key' and 'Value'

    Returns:
        Name tag value or "unnamed" if not found
    """
    for tag in tags:
        if tag.get('Key') == 'Name':
            return tag.get('Value', 'unnamed')
    return 'unnamed'


def _log_discovery_error(resource_type: str, error: Exception):
    """
    Log discovery errors at ERROR level without failing request.

    Args:
        resource_type: Type of resource being discovered
        error: Exception that occurred

    Note: Logs at ERROR level for visibility (not WARNING).
    """
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    if hasattr(error, 'response'):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"Failed to discover {resource_type}: {error_code}")
    else:
        logger.error(f"Failed to discover {resource_type}: {type(error).__name__}")
```

**Validation**:
```bash
cd backend
black --check lambda/functions/aws-discovery/handler.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

### Task 7: Update main handler function
**File**: `backend/lambda/functions/aws-discovery/handler.py`
**Action**: MODIFY (replace lines 18-49 stub handler)
**Pattern**: Reference spec-parser/handler.py:18-87 for handler structure

**Implementation**:
```python
@secure_handler
def lambda_handler(event, context):
    """
    GET /aws/discover

    Query Parameters:
    - resource_type: Optional filter (vpc|subnet|alb|waf|all)
    - vpc_id: Optional VPC filter for subnets

    Returns JSON with discovered AWS resources.
    Missing permissions or errors return empty arrays (graceful degradation).
    """
    # Parse query parameters
    params = event.get('queryStringParameters') or {}
    resource_type = params.get('resource_type', 'all')
    vpc_id = params.get('vpc_id')

    # Discover resources based on filter
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

**Validation**:
```bash
cd backend
black --check lambda/functions/aws-discovery/handler.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

### Task 8: Create comprehensive unit tests
**File**: `backend/tests/test_aws_discovery.py`
**Action**: CREATE
**Pattern**: Reference test_github_client.py:31-82 for mock fixture setup

**Implementation**:
```python
import pytest
import json
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

# Import from handler (path added by pytest)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'functions', 'aws-discovery'))
from handler import (
    lambda_handler,
    discover_vpcs,
    discover_subnets,
    discover_albs,
    discover_waf_webacls,
    _extract_name_tag,
    _log_discovery_error
)


@pytest.fixture
def mock_ec2():
    """Mock EC2 client for VPC and subnet tests."""
    with patch('handler.ec2_client') as mock:
        yield mock


@pytest.fixture
def mock_elbv2():
    """Mock ELBv2 client for ALB tests."""
    with patch('handler.elbv2_client') as mock:
        yield mock


@pytest.fixture
def mock_wafv2():
    """Mock WAFv2 client for WebACL tests."""
    with patch('handler.wafv2_client') as mock:
        yield mock


# VPC Discovery Tests

def test_discover_vpcs_success(mock_ec2):
    """Test VPC discovery returns formatted results."""
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [
            {
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'Tags': [{'Key': 'Name', 'Value': 'demo-vpc'}]
            },
            {
                'VpcId': 'vpc-456',
                'CidrBlock': '10.1.0.0/16',
                'IsDefault': True,
                'Tags': [{'Key': 'Name', 'Value': 'default-vpc'}]
            }
        ]
    }

    vpcs = discover_vpcs()

    assert len(vpcs) == 2
    assert vpcs[0]['id'] == 'vpc-123'
    assert vpcs[0]['name'] == 'demo-vpc'
    assert vpcs[0]['cidr'] == '10.0.0.0/16'
    assert vpcs[0]['is_default'] is False
    assert vpcs[1]['id'] == 'vpc-456'
    assert vpcs[1]['is_default'] is True


def test_discover_vpcs_missing_permissions(mock_ec2):
    """Test VPC discovery with AccessDenied returns empty list."""
    mock_ec2.describe_vpcs.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied'}},
        'DescribeVpcs'
    )

    vpcs = discover_vpcs()
    assert vpcs == []


def test_discover_vpcs_no_resources(mock_ec2):
    """Test VPC discovery with no VPCs returns empty list."""
    mock_ec2.describe_vpcs.return_value = {'Vpcs': []}

    vpcs = discover_vpcs()
    assert vpcs == []


def test_discover_vpcs_sorts_unnamed_to_bottom(mock_ec2):
    """Test unnamed VPCs sort after named VPCs."""
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [
            {
                'VpcId': 'vpc-unnamed',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'Tags': []
            },
            {
                'VpcId': 'vpc-named',
                'CidrBlock': '10.1.0.0/16',
                'IsDefault': False,
                'Tags': [{'Key': 'Name', 'Value': 'alpha-vpc'}]
            }
        ]
    }

    vpcs = discover_vpcs()

    assert len(vpcs) == 2
    assert vpcs[0]['name'] == 'alpha-vpc'  # Named first
    assert vpcs[1]['name'] == 'unnamed'     # Unnamed last


# Subnet Discovery Tests

def test_discover_subnets_success(mock_ec2):
    """Test subnet discovery returns formatted results."""
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'SubnetId': 'subnet-123',
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.1.0/24',
                'AvailabilityZone': 'us-west-2a',
                'Tags': [{'Key': 'Name', 'Value': 'public-subnet-1'}]
            }
        ]
    }

    subnets = discover_subnets()

    assert len(subnets) == 1
    assert subnets[0]['id'] == 'subnet-123'
    assert subnets[0]['vpc_id'] == 'vpc-123'
    assert subnets[0]['cidr'] == '10.0.1.0/24'
    assert subnets[0]['availability_zone'] == 'us-west-2a'
    assert subnets[0]['name'] == 'public-subnet-1'


def test_discover_subnets_filtered_by_vpc(mock_ec2):
    """Test subnet discovery filters by VPC ID."""
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'SubnetId': 'subnet-123',
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.1.0/24',
                'AvailabilityZone': 'us-west-2a',
                'Tags': [{'Key': 'Name', 'Value': 'subnet-1'}]
            }
        ]
    }

    subnets = discover_subnets(vpc_id='vpc-123')

    # Verify filter was applied
    mock_ec2.describe_subnets.assert_called_once()
    call_args = mock_ec2.describe_subnets.call_args
    assert call_args[1]['Filters'] == [{'Name': 'vpc-id', 'Values': ['vpc-123']}]

    assert len(subnets) == 1
    assert subnets[0]['vpc_id'] == 'vpc-123'


def test_discover_subnets_missing_permissions(mock_ec2):
    """Test subnet discovery with AccessDenied returns empty list."""
    mock_ec2.describe_subnets.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied'}},
        'DescribeSubnets'
    )

    subnets = discover_subnets()
    assert subnets == []


def test_discover_subnets_no_resources(mock_ec2):
    """Test subnet discovery with no subnets returns empty list."""
    mock_ec2.describe_subnets.return_value = {'Subnets': []}

    subnets = discover_subnets()
    assert subnets == []


# ALB Discovery Tests

def test_discover_albs_success(mock_elbv2):
    """Test ALB discovery returns formatted results."""
    mock_elbv2.describe_load_balancers.return_value = {
        'LoadBalancers': [
            {
                'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/demo-alb/1234567890abcdef',
                'LoadBalancerName': 'demo-alb',
                'DNSName': 'demo-alb-1234567890.us-west-2.elb.amazonaws.com',
                'VpcId': 'vpc-123',
                'Type': 'application',
                'State': {'Code': 'active'}
            }
        ]
    }

    albs = discover_albs()

    assert len(albs) == 1
    assert albs[0]['name'] == 'demo-alb'
    assert albs[0]['vpc_id'] == 'vpc-123'
    assert albs[0]['state'] == 'active'
    assert 'arn' in albs[0]
    assert 'dns_name' in albs[0]


def test_discover_albs_filters_application_only(mock_elbv2):
    """Test ALB discovery excludes NLBs and GLBs."""
    mock_elbv2.describe_load_balancers.return_value = {
        'LoadBalancers': [
            {
                'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/alb/123',
                'LoadBalancerName': 'app-lb',
                'DNSName': 'app-lb.elb.amazonaws.com',
                'VpcId': 'vpc-123',
                'Type': 'application',
                'State': {'Code': 'active'}
            },
            {
                'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/nlb/456',
                'LoadBalancerName': 'network-lb',
                'DNSName': 'network-lb.elb.amazonaws.com',
                'VpcId': 'vpc-123',
                'Type': 'network',
                'State': {'Code': 'active'}
            }
        ]
    }

    albs = discover_albs()

    # Should only return the application load balancer
    assert len(albs) == 1
    assert albs[0]['name'] == 'app-lb'


def test_discover_albs_missing_permissions(mock_elbv2):
    """Test ALB discovery with AccessDenied returns empty list."""
    mock_elbv2.describe_load_balancers.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied'}},
        'DescribeLoadBalancers'
    )

    albs = discover_albs()
    assert albs == []


def test_discover_albs_no_resources(mock_elbv2):
    """Test ALB discovery with no load balancers returns empty list."""
    mock_elbv2.describe_load_balancers.return_value = {'LoadBalancers': []}

    albs = discover_albs()
    assert albs == []


# WAF WebACL Discovery Tests

def test_discover_waf_regional_scope_only(mock_wafv2):
    """Test WAF discovery only returns REGIONAL scope WebACLs."""
    mock_wafv2.list_web_acls.return_value = {
        'WebACLs': [
            {
                'Id': '12345678-1234-1234-1234-123456789012',
                'Name': 'demo-waf',
                'ARN': 'arn:aws:wafv2:us-west-2:123456789012:regional/webacl/demo-waf/12345678-1234-1234-1234-123456789012'
            }
        ]
    }

    mock_wafv2.get_web_acl.return_value = {
        'WebACL': {
            'Id': '12345678-1234-1234-1234-123456789012',
            'Name': 'demo-waf',
            'Rules': [
                {'Statement': {'ManagedRuleGroupStatement': {}}},
                {'Statement': {'ManagedRuleGroupStatement': {}}},
                {'Statement': {'RateBasedStatement': {}}}
            ]
        }
    }

    webacls = discover_waf_webacls()

    # Verify REGIONAL scope was used
    mock_wafv2.list_web_acls.assert_called_once_with(Scope='REGIONAL')

    assert len(webacls) == 1
    assert webacls[0]['name'] == 'demo-waf'
    assert webacls[0]['scope'] == 'REGIONAL'
    assert webacls[0]['managed_rule_count'] == 2  # Only managed rules counted


def test_discover_waf_missing_permissions(mock_wafv2):
    """Test WAF discovery with AccessDenied returns empty list."""
    mock_wafv2.list_web_acls.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied'}},
        'ListWebACLs'
    )

    webacls = discover_waf_webacls()
    assert webacls == []


def test_discover_waf_no_resources(mock_wafv2):
    """Test WAF discovery with no WebACLs returns empty list."""
    mock_wafv2.list_web_acls.return_value = {'WebACLs': []}

    webacls = discover_waf_webacls()
    assert webacls == []


def test_discover_waf_get_web_acl_fails_gracefully(mock_wafv2):
    """Test WAF discovery continues if get_web_acl fails for individual WebACL."""
    mock_wafv2.list_web_acls.return_value = {
        'WebACLs': [
            {
                'Id': 'webacl-1',
                'Name': 'waf-1',
                'ARN': 'arn:aws:wafv2:us-west-2:123456789012:regional/webacl/waf-1/1234'
            }
        ]
    }

    mock_wafv2.get_web_acl.side_effect = ClientError(
        {'Error': {'Code': 'WAFNonexistentItemException'}},
        'GetWebACL'
    )

    webacls = discover_waf_webacls()

    # Should still return the WebACL with 0 managed_rule_count
    assert len(webacls) == 1
    assert webacls[0]['managed_rule_count'] == 0


# Helper Function Tests

def test_extract_name_tag_present():
    """Test name extraction from tags."""
    tags = [
        {'Key': 'Environment', 'Value': 'prod'},
        {'Key': 'Name', 'Value': 'my-vpc'}
    ]

    assert _extract_name_tag(tags) == 'my-vpc'


def test_extract_name_tag_missing():
    """Test name extraction with no Name tag."""
    tags = [{'Key': 'Environment', 'Value': 'prod'}]

    assert _extract_name_tag(tags) == 'unnamed'


def test_extract_name_tag_empty():
    """Test name extraction with empty tags list."""
    assert _extract_name_tag([]) == 'unnamed'


def test_log_discovery_error_with_client_error():
    """Test error logging for boto3 ClientError."""
    error = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        'DescribeVpcs'
    )

    with patch('handler.logging.getLogger') as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        _log_discovery_error('VPCs', error)

        mock_log.error.assert_called_once()
        assert 'AccessDenied' in mock_log.error.call_args[0][0]


def test_log_discovery_error_with_generic_exception():
    """Test error logging for generic Exception."""
    error = ValueError("Invalid parameter")

    with patch('handler.logging.getLogger') as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        _log_discovery_error('VPCs', error)

        mock_log.error.assert_called_once()
        assert 'ValueError' in mock_log.error.call_args[0][0]


# Lambda Handler Integration Tests

def test_handler_all_resources(mock_ec2, mock_elbv2, mock_wafv2):
    """Test handler returns all resource types by default."""
    # Setup mocks
    mock_ec2.describe_vpcs.return_value = {'Vpcs': []}
    mock_ec2.describe_subnets.return_value = {'Subnets': []}
    mock_elbv2.describe_load_balancers.return_value = {'LoadBalancers': []}
    mock_wafv2.list_web_acls.return_value = {'WebACLs': []}

    event = {'queryStringParameters': None}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])

    assert 'vpcs' in body
    assert 'subnets' in body
    assert 'albs' in body
    assert 'waf_webacls' in body


def test_handler_filters_by_resource_type_vpc(mock_ec2):
    """Test handler filters to VPC resource type only."""
    mock_ec2.describe_vpcs.return_value = {'Vpcs': []}

    event = {'queryStringParameters': {'resource_type': 'vpc'}}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])

    assert 'vpcs' in body
    assert 'subnets' not in body
    assert 'albs' not in body
    assert 'waf_webacls' not in body


def test_handler_filters_by_resource_type_subnet(mock_ec2):
    """Test handler filters to subnet resource type only."""
    mock_ec2.describe_subnets.return_value = {'Subnets': []}

    event = {'queryStringParameters': {'resource_type': 'subnet'}}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])

    assert 'subnets' in body
    assert 'vpcs' not in body


def test_handler_subnet_with_vpc_filter(mock_ec2):
    """Test handler passes vpc_id filter to discover_subnets."""
    mock_ec2.describe_subnets.return_value = {'Subnets': []}

    event = {
        'queryStringParameters': {
            'resource_type': 'subnet',
            'vpc_id': 'vpc-123'
        }
    }
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200

    # Verify vpc_id filter was used
    call_args = mock_ec2.describe_subnets.call_args
    assert call_args[1]['Filters'] == [{'Name': 'vpc-id', 'Values': ['vpc-123']}]


def test_handler_empty_query_params(mock_ec2, mock_elbv2, mock_wafv2):
    """Test handler with empty query parameters returns all resources."""
    mock_ec2.describe_vpcs.return_value = {'Vpcs': []}
    mock_ec2.describe_subnets.return_value = {'Subnets': []}
    mock_elbv2.describe_load_balancers.return_value = {'LoadBalancers': []}
    mock_wafv2.list_web_acls.return_value = {'WebACLs': []}

    event = {'queryStringParameters': {}}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])

    # Default to 'all'
    assert 'vpcs' in body
    assert 'subnets' in body
    assert 'albs' in body
    assert 'waf_webacls' in body
```

**Validation**:
```bash
cd backend
black --check tests/test_aws_discovery.py
pytest tests/test_aws_discovery.py -v --cov=lambda/functions/aws-discovery --cov-report=term-missing --cov-fail-under=90
```

### Task 9: Create IAM policies documentation
**File**: `docs/IAM_POLICIES.md`
**Action**: CREATE
**Pattern**: Standard markdown documentation with code blocks

**Implementation**:
Use content from spec.md lines 370-463, formatted as documentation.

**Validation**:
```bash
# Verify file created
test -f docs/IAM_POLICIES.md && echo "✓ Documentation created"
```

### Task 10: Verify SAM template IAM policies
**File**: `template.yaml`
**Action**: MODIFY (lines 145-189 if needed)
**Pattern**: Compare existing policies with spec requirements

**Analysis**:
Existing SAM template (lines 152-173) already has:
- ✅ ec2:DescribeVpcs
- ✅ ec2:DescribeSubnets
- ✅ elasticloadbalancing:DescribeLoadBalancers
- ✅ wafv2:ListWebACLs
- ✅ wafv2:GetWebACL
- ⚠️ Extra: ec2:DescribeSecurityGroups (future enhancement)
- ⚠️ Extra: elasticloadbalancing:DescribeTargetGroups (future enhancement)
- ⚠️ Extra: elasticloadbalancing:DescribeListeners (future enhancement)

**Action Required**:
No changes needed - existing policies cover all requirements plus future enhancements.

**Validation**:
```bash
# Verify template syntax
sam validate --template template.yaml
```

### Task 11: Verify API Gateway path
**File**: `template.yaml`
**Action**: VERIFY (lines 181-189)
**Pattern**: Check if path matches spec requirement

**Analysis**:
- **Current path**: `/api/discover` (line 186)
- **Spec shows**: `/aws/discover` (spec.md line 71)

**Decision**: Document discrepancy - ASK USER during /build which path to use, or keep current path as it's already defined.

**Validation**:
```bash
# No changes needed unless user confirms path change
sam validate --template template.yaml
```

### Task 12: Run full validation suite
**File**: All modified files
**Action**: Validate all gates pass
**Pattern**: Use commands from spec/stack.md

**Implementation**:
```bash
cd backend

# Gate 1: Lint & Format
black --check lambda/functions/aws-discovery/ tests/test_aws_discovery.py

# Gate 2: Type Safety
mypy lambda/functions/aws-discovery/ --ignore-missing-imports

# Gate 3: Unit Tests (90%+ coverage)
pytest tests/test_aws_discovery.py -v --cov=lambda/functions/aws-discovery --cov-report=term-missing --cov-fail-under=90

# Final: Full test suite
pytest tests/ -v --cov=lambda --cov-report=term-missing
```

**Validation Criteria**:
- ✅ Black passes (no formatting errors)
- ✅ Mypy passes (no type errors)
- ✅ All tests pass (30+ test cases)
- ✅ Coverage ≥ 90% for aws-discovery module
- ✅ No regressions in other modules

## Risk Assessment

- **Risk**: boto3 automatic pagination may timeout for accounts with 1000+ resources
  **Mitigation**: Document performance limitation in IAM_POLICIES.md; defer explicit pagination to future phase if needed

- **Risk**: API path mismatch between spec (`/aws/discover`) and SAM template (`/api/discover`)
  **Mitigation**: Verify with user during /build; update SAM template if needed (1 line change)

- **Risk**: WAF get_web_acl calls may increase response time (additional API call per WebACL)
  **Mitigation**: Implemented graceful fallback (0 count if fails); document < 2s SLA may not be met with many WebACLs

- **Risk**: ERROR level logging may be too noisy in production
  **Mitigation**: User explicitly requested ERROR level; can adjust to WARNING post-deployment if needed

## Integration Points

- **API Gateway**: `/api/discover` endpoint with GET method (API key required)
- **IAM Policies**: Lambda execution role has read-only permissions for EC2, ELBv2, WAFv2
- **Frontend Integration** (Phase 3.4): React form will call this endpoint to populate dropdowns
- **CloudWatch Logs**: ERROR level logs for permission failures

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY code change, use commands from `spec/stack.md`:

**Gate 1: Syntax & Style**
```bash
cd backend
black --check lambda/functions/aws-discovery/ tests/test_aws_discovery.py
```

**Gate 2: Type Safety**
```bash
cd backend
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
```

**Gate 3: Unit Tests**
```bash
cd backend
pytest tests/test_aws_discovery.py -v --cov=lambda/functions/aws-discovery --cov-report=term-missing --cov-fail-under=90
```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

**After each task (1-11)**:
```bash
cd backend
black --check lambda/functions/aws-discovery/ tests/test_aws_discovery.py
mypy lambda/functions/aws-discovery/ --ignore-missing-imports
pytest tests/test_aws_discovery.py -v
```

**Final validation (Task 12)**:
```bash
cd backend
black --check lambda/ tests/
mypy lambda/ --ignore-missing-imports
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=80
```

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM-LOW)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec - all discovery functions well-defined
✅ Similar patterns found in codebase at:
  - `backend/lambda/shared/github_client.py:135-147` (boto3 error handling)
  - `backend/tests/test_github_client.py:31-82` (mock fixture patterns)
  - `backend/lambda/functions/spec-parser/handler.py:18-87` (handler structure)
✅ All clarifying questions answered (boto3 initialization, error logging level, coverage target, etc.)
✅ Existing test patterns to follow at `backend/tests/test_github_client.py`
✅ SAM template already has IAM policies defined (minimal changes needed)
✅ boto3 included in Lambda runtime (no dependency installation required)
⚠️ API path discrepancy between spec and SAM template (minor - easy to verify)
⚠️ WAF WebACL managed rule counting adds complexity (mitigated with try/except)

**Assessment**: High confidence implementation. Well-established patterns, comprehensive spec, all discovery functions follow same structure. Only minor risk is API path clarification.

**Estimated one-pass success probability**: 85%

**Reasoning**: Strong patterns, clear requirements, comprehensive test coverage target (90%+), and graceful error handling design. The 15% risk accounts for potential API path decision and minor edge cases in WAF WebACL rule counting logic. All core functionality is straightforward boto3 describe operations following established error handling patterns from github_client.py.
