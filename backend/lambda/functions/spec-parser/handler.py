"""
Spec Parser Lambda Function
Phase 3.2: Parse and validate ActionSpec YAML
"""

import json
import os
import sys
import time

# Add shared layer to path
sys.path.insert(0, "/opt/python")  # Lambda layer path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from security_wrapper import secure_handler


@secure_handler
def lambda_handler(event, context):
    """
    Parse and validate ActionSpec YAML.

    POST /api/parse
    Body: {
        "spec": "<yaml content>",
        "source": "inline"  # Phase 3.2a only supports inline
    }

    Returns:
        {
            "valid": true/false,
            "spec": { parsed dict } or {},
            "errors": [ array of error messages ],
            "metadata": { parsing stats }
        }
    """
    from parser import SpecParser

    # Parse request body
    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"valid": False, "errors": ["Invalid JSON in request body"]}
            ),
        }

    # Extract YAML content
    yaml_content = body.get("spec")
    if not yaml_content:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"valid": False, "errors": ["Missing required field: spec"]}
            ),
        }

    # Parse and validate
    parser = SpecParser()
    start_time = time.time()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    parse_time = time.time() - start_time

    # Return result
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "valid": is_valid,
                "spec": spec,
                "errors": errors,
                "metadata": {
                    "parse_time_ms": round(parse_time * 1000, 2),
                    "spec_size_bytes": len(yaml_content),
                    "version": "phase-3.2a",
                },
            }
        ),
    }
