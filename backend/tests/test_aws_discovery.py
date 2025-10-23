import pytest
import json
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

# Import from handler (path added by pytest)
import sys
import os

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "lambda", "functions", "aws-discovery"
    ),
)
from handler import (
    lambda_handler,
    discover_vpcs,
    discover_subnets,
    discover_albs,
    discover_waf_webacls,
    _extract_name_tag,
    _log_discovery_error,
)


@pytest.fixture
def mock_ec2():
    """Mock EC2 client for VPC and subnet tests."""
    with patch("handler.ec2_client") as mock:
        yield mock


@pytest.fixture
def mock_elbv2():
    """Mock ELBv2 client for ALB tests."""
    with patch("handler.elbv2_client") as mock:
        yield mock


@pytest.fixture
def mock_wafv2():
    """Mock WAFv2 client for WebACL tests."""
    with patch("handler.wafv2_client") as mock:
        yield mock


# VPC Discovery Tests


def test_discover_vpcs_success(mock_ec2):
    """Test VPC discovery returns formatted results."""
    mock_ec2.describe_vpcs.return_value = {
        "Vpcs": [
            {
                "VpcId": "vpc-123",
                "CidrBlock": "10.0.0.0/16",
                "IsDefault": False,
                "Tags": [{"Key": "Name", "Value": "demo-vpc"}],
            },
            {
                "VpcId": "vpc-456",
                "CidrBlock": "10.1.0.0/16",
                "IsDefault": True,
                "Tags": [{"Key": "Name", "Value": "default-vpc"}],
            },
        ]
    }

    vpcs = discover_vpcs()

    assert len(vpcs) == 2
    # VPCs are sorted alphabetically: "default-vpc" comes before "demo-vpc"
    assert vpcs[0]["id"] == "vpc-456"
    assert vpcs[0]["name"] == "default-vpc"
    assert vpcs[0]["is_default"] is True
    assert vpcs[1]["id"] == "vpc-123"
    assert vpcs[1]["name"] == "demo-vpc"
    assert vpcs[1]["cidr"] == "10.0.0.0/16"
    assert vpcs[1]["is_default"] is False


def test_discover_vpcs_missing_permissions(mock_ec2):
    """Test VPC discovery with AccessDenied returns empty list."""
    mock_ec2.describe_vpcs.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}}, "DescribeVpcs"
    )

    vpcs = discover_vpcs()
    assert vpcs == []


def test_discover_vpcs_no_resources(mock_ec2):
    """Test VPC discovery with no VPCs returns empty list."""
    mock_ec2.describe_vpcs.return_value = {"Vpcs": []}

    vpcs = discover_vpcs()
    assert vpcs == []


def test_discover_vpcs_sorts_unnamed_to_bottom(mock_ec2):
    """Test unnamed VPCs sort after named VPCs."""
    mock_ec2.describe_vpcs.return_value = {
        "Vpcs": [
            {
                "VpcId": "vpc-unnamed",
                "CidrBlock": "10.0.0.0/16",
                "IsDefault": False,
                "Tags": [],
            },
            {
                "VpcId": "vpc-named",
                "CidrBlock": "10.1.0.0/16",
                "IsDefault": False,
                "Tags": [{"Key": "Name", "Value": "alpha-vpc"}],
            },
        ]
    }

    vpcs = discover_vpcs()

    assert len(vpcs) == 2
    assert vpcs[0]["name"] == "alpha-vpc"  # Named first
    assert vpcs[1]["name"] == "unnamed"  # Unnamed last


# Subnet Discovery Tests


def test_discover_subnets_success(mock_ec2):
    """Test subnet discovery returns formatted results."""
    mock_ec2.describe_subnets.return_value = {
        "Subnets": [
            {
                "SubnetId": "subnet-123",
                "VpcId": "vpc-123",
                "CidrBlock": "10.0.1.0/24",
                "AvailabilityZone": "us-west-2a",
                "Tags": [{"Key": "Name", "Value": "public-subnet-1"}],
            }
        ]
    }

    subnets = discover_subnets()

    assert len(subnets) == 1
    assert subnets[0]["id"] == "subnet-123"
    assert subnets[0]["vpc_id"] == "vpc-123"
    assert subnets[0]["cidr"] == "10.0.1.0/24"
    assert subnets[0]["availability_zone"] == "us-west-2a"
    assert subnets[0]["name"] == "public-subnet-1"


def test_discover_subnets_filtered_by_vpc(mock_ec2):
    """Test subnet discovery filters by VPC ID."""
    mock_ec2.describe_subnets.return_value = {
        "Subnets": [
            {
                "SubnetId": "subnet-123",
                "VpcId": "vpc-123",
                "CidrBlock": "10.0.1.0/24",
                "AvailabilityZone": "us-west-2a",
                "Tags": [{"Key": "Name", "Value": "subnet-1"}],
            }
        ]
    }

    subnets = discover_subnets(vpc_id="vpc-123")

    # Verify filter was applied
    mock_ec2.describe_subnets.assert_called_once()
    call_args = mock_ec2.describe_subnets.call_args
    assert call_args[1]["Filters"] == [{"Name": "vpc-id", "Values": ["vpc-123"]}]

    assert len(subnets) == 1
    assert subnets[0]["vpc_id"] == "vpc-123"


def test_discover_subnets_missing_permissions(mock_ec2):
    """Test subnet discovery with AccessDenied returns empty list."""
    mock_ec2.describe_subnets.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}}, "DescribeSubnets"
    )

    subnets = discover_subnets()
    assert subnets == []


def test_discover_subnets_no_resources(mock_ec2):
    """Test subnet discovery with no subnets returns empty list."""
    mock_ec2.describe_subnets.return_value = {"Subnets": []}

    subnets = discover_subnets()
    assert subnets == []


# ALB Discovery Tests


def test_discover_albs_success(mock_elbv2):
    """Test ALB discovery returns formatted results."""
    mock_elbv2.describe_load_balancers.return_value = {
        "LoadBalancers": [
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/demo-alb/1234567890abcdef",
                "LoadBalancerName": "demo-alb",
                "DNSName": "demo-alb-1234567890.us-west-2.elb.amazonaws.com",
                "VpcId": "vpc-123",
                "Type": "application",
                "State": {"Code": "active"},
            }
        ]
    }

    albs = discover_albs()

    assert len(albs) == 1
    assert albs[0]["name"] == "demo-alb"
    assert albs[0]["vpc_id"] == "vpc-123"
    assert albs[0]["state"] == "active"
    assert "arn" in albs[0]
    assert "dns_name" in albs[0]


def test_discover_albs_filters_application_only(mock_elbv2):
    """Test ALB discovery excludes NLBs and GLBs."""
    mock_elbv2.describe_load_balancers.return_value = {
        "LoadBalancers": [
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/alb/123",
                "LoadBalancerName": "app-lb",
                "DNSName": "app-lb.elb.amazonaws.com",
                "VpcId": "vpc-123",
                "Type": "application",
                "State": {"Code": "active"},
            },
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/nlb/456",
                "LoadBalancerName": "network-lb",
                "DNSName": "network-lb.elb.amazonaws.com",
                "VpcId": "vpc-123",
                "Type": "network",
                "State": {"Code": "active"},
            },
        ]
    }

    albs = discover_albs()

    # Should only return the application load balancer
    assert len(albs) == 1
    assert albs[0]["name"] == "app-lb"


def test_discover_albs_missing_permissions(mock_elbv2):
    """Test ALB discovery with AccessDenied returns empty list."""
    mock_elbv2.describe_load_balancers.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}}, "DescribeLoadBalancers"
    )

    albs = discover_albs()
    assert albs == []


def test_discover_albs_no_resources(mock_elbv2):
    """Test ALB discovery with no load balancers returns empty list."""
    mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}

    albs = discover_albs()
    assert albs == []


# WAF WebACL Discovery Tests


def test_discover_waf_regional_scope_only(mock_wafv2):
    """Test WAF discovery only returns REGIONAL scope WebACLs."""
    mock_wafv2.list_web_acls.return_value = {
        "WebACLs": [
            {
                "Id": "12345678-1234-1234-1234-123456789012",
                "Name": "demo-waf",
                "ARN": "arn:aws:wafv2:us-west-2:123456789012:regional/webacl/demo-waf/12345678-1234-1234-1234-123456789012",
            }
        ]
    }

    mock_wafv2.get_web_acl.return_value = {
        "WebACL": {
            "Id": "12345678-1234-1234-1234-123456789012",
            "Name": "demo-waf",
            "Rules": [
                {"Statement": {"ManagedRuleGroupStatement": {}}},
                {"Statement": {"ManagedRuleGroupStatement": {}}},
                {"Statement": {"RateBasedStatement": {}}},
            ],
        }
    }

    webacls = discover_waf_webacls()

    # Verify REGIONAL scope was used
    mock_wafv2.list_web_acls.assert_called_once_with(Scope="REGIONAL")

    assert len(webacls) == 1
    assert webacls[0]["name"] == "demo-waf"
    assert webacls[0]["scope"] == "REGIONAL"
    assert webacls[0]["managed_rule_count"] == 2  # Only managed rules counted


def test_discover_waf_missing_permissions(mock_wafv2):
    """Test WAF discovery with AccessDenied returns empty list."""
    mock_wafv2.list_web_acls.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}}, "ListWebACLs"
    )

    webacls = discover_waf_webacls()
    assert webacls == []


def test_discover_waf_no_resources(mock_wafv2):
    """Test WAF discovery with no WebACLs returns empty list."""
    mock_wafv2.list_web_acls.return_value = {"WebACLs": []}

    webacls = discover_waf_webacls()
    assert webacls == []


def test_discover_waf_get_web_acl_fails_gracefully(mock_wafv2):
    """Test WAF discovery continues if get_web_acl fails for individual WebACL."""
    mock_wafv2.list_web_acls.return_value = {
        "WebACLs": [
            {
                "Id": "webacl-1",
                "Name": "waf-1",
                "ARN": "arn:aws:wafv2:us-west-2:123456789012:regional/webacl/waf-1/1234",
            }
        ]
    }

    mock_wafv2.get_web_acl.side_effect = ClientError(
        {"Error": {"Code": "WAFNonexistentItemException"}}, "GetWebACL"
    )

    webacls = discover_waf_webacls()

    # Should still return the WebACL with 0 managed_rule_count
    assert len(webacls) == 1
    assert webacls[0]["managed_rule_count"] == 0


# Helper Function Tests


def test_extract_name_tag_present():
    """Test name extraction from tags."""
    tags = [
        {"Key": "Environment", "Value": "prod"},
        {"Key": "Name", "Value": "my-vpc"},
    ]

    assert _extract_name_tag(tags) == "my-vpc"


def test_extract_name_tag_missing():
    """Test name extraction with no Name tag."""
    tags = [{"Key": "Environment", "Value": "prod"}]

    assert _extract_name_tag(tags) == "unnamed"


def test_extract_name_tag_empty():
    """Test name extraction with empty tags list."""
    assert _extract_name_tag([]) == "unnamed"


def test_log_discovery_error_with_client_error():
    """Test error logging for boto3 ClientError."""
    error = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "DescribeVpcs",
    )

    with patch("handler.logging.getLogger") as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        _log_discovery_error("VPCs", error)

        mock_log.error.assert_called_once()
        assert "AccessDenied" in mock_log.error.call_args[0][0]


def test_log_discovery_error_with_generic_exception():
    """Test error logging for generic Exception."""
    error = ValueError("Invalid parameter")

    with patch("handler.logging.getLogger") as mock_logger:
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        _log_discovery_error("VPCs", error)

        mock_log.error.assert_called_once()
        assert "ValueError" in mock_log.error.call_args[0][0]


# Lambda Handler Integration Tests


def test_handler_all_resources(mock_ec2, mock_elbv2, mock_wafv2):
    """Test handler returns all resource types by default."""
    # Setup mocks
    mock_ec2.describe_vpcs.return_value = {"Vpcs": []}
    mock_ec2.describe_subnets.return_value = {"Subnets": []}
    mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
    mock_wafv2.list_web_acls.return_value = {"WebACLs": []}

    event = {"queryStringParameters": None}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])

    assert "vpcs" in body
    assert "subnets" in body
    assert "albs" in body
    assert "waf_webacls" in body


def test_handler_filters_by_resource_type_vpc(mock_ec2):
    """Test handler filters to VPC resource type only."""
    mock_ec2.describe_vpcs.return_value = {"Vpcs": []}

    event = {"queryStringParameters": {"resource_type": "vpc"}}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])

    assert "vpcs" in body
    assert "subnets" not in body
    assert "albs" not in body
    assert "waf_webacls" not in body


def test_handler_filters_by_resource_type_subnet(mock_ec2):
    """Test handler filters to subnet resource type only."""
    mock_ec2.describe_subnets.return_value = {"Subnets": []}

    event = {"queryStringParameters": {"resource_type": "subnet"}}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])

    assert "subnets" in body
    assert "vpcs" not in body


def test_handler_subnet_with_vpc_filter(mock_ec2):
    """Test handler passes vpc_id filter to discover_subnets."""
    mock_ec2.describe_subnets.return_value = {"Subnets": []}

    event = {"queryStringParameters": {"resource_type": "subnet", "vpc_id": "vpc-123"}}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 200

    # Verify vpc_id filter was used
    call_args = mock_ec2.describe_subnets.call_args
    assert call_args[1]["Filters"] == [{"Name": "vpc-id", "Values": ["vpc-123"]}]


def test_handler_empty_query_params(mock_ec2, mock_elbv2, mock_wafv2):
    """Test handler with empty query parameters returns all resources."""
    mock_ec2.describe_vpcs.return_value = {"Vpcs": []}
    mock_ec2.describe_subnets.return_value = {"Subnets": []}
    mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
    mock_wafv2.list_web_acls.return_value = {"WebACLs": []}

    event = {"queryStringParameters": {}}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])

    # Default to 'all'
    assert "vpcs" in body
    assert "subnets" in body
    assert "albs" in body
    assert "waf_webacls" in body
