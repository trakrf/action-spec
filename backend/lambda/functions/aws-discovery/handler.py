"""
AWS Discovery Lambda Function
Phase 3.3.5: Full implementation - Discovers AWS resources for frontend dropdowns
"""

import boto3
import json
import logging
import os
import sys
from typing import List, Dict, Any, Optional

# Add shared layer to path
sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from security_wrapper import secure_handler

# Initialize AWS clients outside handler for reuse (AWS best practice)
ec2_client = boto3.client("ec2")
elbv2_client = boto3.client("elbv2")
wafv2_client = boto3.client("wafv2")


def discover_vpcs() -> List[Dict[str, Any]]:
    """
    Discover all VPCs in the current region.

    Returns empty list on errors (graceful degradation).
    Logs errors at ERROR level for visibility.
    """
    try:
        response = ec2_client.describe_vpcs()
        vpcs = []

        for vpc in response.get("Vpcs", []):
            name = _extract_name_tag(vpc.get("Tags", []))
            vpcs.append(
                {
                    "id": vpc["VpcId"],
                    "cidr": vpc["CidrBlock"],
                    "name": name,
                    "is_default": vpc.get("IsDefault", False),
                }
            )

        # Sort named resources first, then unnamed
        return sorted(vpcs, key=lambda v: (v["name"] == "unnamed", v["name"]))

    except Exception as e:
        _log_discovery_error("VPCs", e)
        return []


def discover_subnets(vpc_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Discover subnets in current region, optionally filtered by VPC.

    Args:
        vpc_id: Optional VPC ID filter

    Returns empty list on errors (graceful degradation).
    """
    try:
        filters = []
        if vpc_id:
            filters.append({"Name": "vpc-id", "Values": [vpc_id]})

        response = (
            ec2_client.describe_subnets(Filters=filters)
            if filters
            else ec2_client.describe_subnets()
        )
        subnets = []

        for subnet in response.get("Subnets", []):
            name = _extract_name_tag(subnet.get("Tags", []))
            subnets.append(
                {
                    "id": subnet["SubnetId"],
                    "vpc_id": subnet["VpcId"],
                    "cidr": subnet["CidrBlock"],
                    "availability_zone": subnet["AvailabilityZone"],
                    "name": name,
                }
            )

        return sorted(subnets, key=lambda s: (s["name"] == "unnamed", s["name"]))

    except Exception as e:
        _log_discovery_error("Subnets", e)
        return []


def discover_albs() -> List[Dict[str, Any]]:
    """
    Discover Application Load Balancers in current region.

    Filters to only ALBs (excludes NLBs, GLBs).
    Returns empty list on errors (graceful degradation).
    """
    try:
        response = elbv2_client.describe_load_balancers()
        albs = []

        for lb in response.get("LoadBalancers", []):
            # Filter to only Application Load Balancers
            if lb.get("Type") == "application":
                albs.append(
                    {
                        "arn": lb["LoadBalancerArn"],
                        "name": lb["LoadBalancerName"],
                        "dns_name": lb["DNSName"],
                        "vpc_id": lb["VpcId"],
                        "state": lb["State"]["Code"],
                    }
                )

        return sorted(albs, key=lambda a: a["name"])

    except Exception as e:
        _log_discovery_error("ALBs", e)
        return []


def discover_waf_webacls() -> List[Dict[str, Any]]:
    """
    Discover WAF WebACLs in current region (REGIONAL scope only).

    Returns empty list on errors (graceful degradation).
    Note: CLOUDFRONT scope requires us-east-1 global endpoint (future enhancement).
    """
    try:
        response = wafv2_client.list_web_acls(Scope="REGIONAL")
        webacls = []

        for webacl in response.get("WebACLs", []):
            # Get detailed info for rule count
            try:
                details = wafv2_client.get_web_acl(
                    Scope="REGIONAL", Id=webacl["Id"], Name=webacl["Name"]
                )

                managed_rule_count = len(
                    [
                        rule
                        for rule in details["WebACL"].get("Rules", [])
                        if "ManagedRuleGroupStatement" in rule.get("Statement", {})
                    ]
                )
            except Exception:
                # If get_web_acl fails, continue with 0 count
                managed_rule_count = 0

            webacls.append(
                {
                    "id": webacl["Id"],
                    "name": webacl["Name"],
                    "arn": webacl["ARN"],
                    "scope": "REGIONAL",
                    "managed_rule_count": managed_rule_count,
                }
            )

        return sorted(webacls, key=lambda w: w["name"])

    except Exception as e:
        _log_discovery_error("WAF WebACLs", e)
        return []


def _extract_name_tag(tags: List[Dict[str, str]]) -> str:
    """
    Extract 'Name' tag from AWS resource tags.

    Args:
        tags: List of tag dicts with 'Key' and 'Value'

    Returns:
        Name tag value or "unnamed" if not found
    """
    for tag in tags:
        if tag.get("Key") == "Name":
            return tag.get("Value", "unnamed")
    return "unnamed"


def _log_discovery_error(resource_type: str, error: Exception):
    """
    Log discovery errors at ERROR level without failing request.

    Args:
        resource_type: Type of resource being discovered
        error: Exception that occurred

    Note: Logs at ERROR level for visibility (not WARNING).
    """
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"Failed to discover {resource_type}: {error_code}")
    else:
        logger.error(f"Failed to discover {resource_type}: {type(error).__name__}")


@secure_handler
def lambda_handler(event, context):
    """
    GET /api/discover

    Query Parameters:
    - resource_type: Optional filter (vpc|subnet|alb|waf|all)
    - vpc_id: Optional VPC filter for subnets

    Returns JSON with discovered AWS resources.
    Missing permissions or errors return empty arrays (graceful degradation).
    """
    # Parse query parameters
    params = event.get("queryStringParameters") or {}
    resource_type = params.get("resource_type", "all")
    vpc_id = params.get("vpc_id")

    # Discover resources based on filter
    results = {}

    if resource_type in ["vpc", "all"]:
        results["vpcs"] = discover_vpcs()

    if resource_type in ["subnet", "all"]:
        results["subnets"] = discover_subnets(vpc_id)

    if resource_type in ["alb", "all"]:
        results["albs"] = discover_albs()

    if resource_type in ["waf", "all"]:
        results["waf_webacls"] = discover_waf_webacls()

    return {"statusCode": 200, "body": json.dumps(results)}
