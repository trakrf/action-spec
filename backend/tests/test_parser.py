"""
Unit tests for spec parser module.
Tests YAML parsing, schema validation, and error messages.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add parser module to path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "lambda", "functions", "spec-parser"),
)

from exceptions import ParseError, SecurityError, ValidationError
from parser import SpecParser, load_schema

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_schema():
    """Schema file loads successfully."""
    schema = load_schema()

    assert schema is not None
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["title"] == "ActionSpec v1 Schema"
    assert "properties" in schema


def test_parse_valid_minimal_spec():
    """Minimal valid spec parses successfully."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "valid" / "minimal.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is True
    assert spec["apiVersion"] == "actionspec/v1"
    assert spec["kind"] == "StaticSite"
    assert len(errors) == 0


def test_parse_valid_full_spec():
    """Full-featured spec parses successfully."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "valid" / "full-featured.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is True
    assert spec["kind"] == "WebApplication"
    assert spec["spec"]["compute"]["size"] == "demo"
    assert len(errors) == 0


def test_reject_missing_required_field():
    """Missing required field raises validation error."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "invalid" / "missing-apiversion.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any("apiVersion" in err for err in errors)


def test_reject_invalid_enum_value():
    """Invalid enum value rejected with helpful message."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "invalid" / "wrong-enum-value.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    # Check for helpful error message
    assert any("xlarge" in err and "demo" in err for err in errors)


def test_reject_type_mismatch():
    """Type mismatch (string vs integer) rejected."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "invalid" / "invalid-type.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any("min" in err.lower() or "type" in err.lower() for err in errors)


def test_reject_extra_properties():
    """Extra properties rejected when additionalProperties=false."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "invalid" / "extra-properties.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any("unknownField" in err for err in errors)


def test_conditional_validation_staticsite_no_compute():
    """StaticSite with compute field raises error."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "invalid" / "conditional-violation.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    # The conditional validation should prevent compute on StaticSite


def test_waf_enabled_requires_mode():
    """WAF enabled=true requires mode field."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "invalid" / "missing-waf-mode.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any("mode" in err for err in errors)


def test_user_friendly_error_messages():
    """Error messages include field path and expected values."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / "invalid" / "wrong-enum-value.yml").read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    error_msg = errors[0]

    # Should include:
    # - Field path (spec.compute.size or similar)
    # - Actual value (xlarge)
    # - Expected values (demo, small, medium, large)
    assert "size" in error_msg.lower()
    assert "xlarge" in error_msg
    assert any(size in error_msg for size in ["demo", "small", "medium", "large"])


def test_oversized_document_rejected():
    """Documents > 1MB raise security error."""
    parser = SpecParser()

    # Create 2MB document
    huge_yaml = "x: " + ("a" * (2 * 1024 * 1024))

    is_valid, spec, errors = parser.parse_and_validate(huge_yaml)

    assert is_valid is False
    assert len(errors) > 0
    assert any("too large" in err.lower() or "size" in err.lower() for err in errors)


def test_python_object_exploit_blocked():
    """!!python/object tags raise security error."""
    parser = SpecParser()

    malicious_yaml = """
apiVersion: actionspec/v1
kind: !!python/object:os.system
metadata:
  name: exploit
"""

    is_valid, spec, errors = parser.parse_and_validate(malicious_yaml)

    assert is_valid is False
    assert len(errors) > 0
    assert any(
        "security" in err.lower() or "dangerous" in err.lower() for err in errors
    )


def test_empty_document():
    """Empty YAML document raises parse error."""
    parser = SpecParser()

    is_valid, spec, errors = parser.parse_and_validate("")

    assert is_valid is False
    assert len(errors) > 0
    assert any("empty" in err.lower() for err in errors)


def test_invalid_yaml_syntax():
    """Invalid YAML syntax raises parse error."""
    parser = SpecParser()

    invalid_yaml = """
apiVersion: actionspec/v1
kind: WebApplication
metadata:
  name: test
  invalid indentation here
"""

    is_valid, spec, errors = parser.parse_and_validate(invalid_yaml)

    assert is_valid is False
    assert len(errors) > 0


# Integration tests with Lambda handler
class MockContext:
    request_id = "test-123"


def test_lambda_handler_valid_spec():
    """Lambda handler returns valid=true for good spec."""
    from handler import lambda_handler

    yaml_content = (FIXTURES_DIR / "valid" / "minimal.yml").read_text()

    event = {"body": {"spec": yaml_content, "source": "inline"}}

    response = lambda_handler(event, MockContext())

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["valid"] is True
    assert body["spec"]["kind"] == "StaticSite"
    assert len(body["errors"]) == 0
    assert "parse_time_ms" in body["metadata"]


def test_lambda_handler_invalid_spec():
    """Lambda handler returns valid=false with error details."""
    from handler import lambda_handler

    yaml_content = (FIXTURES_DIR / "invalid" / "missing-apiversion.yml").read_text()

    event = {"body": {"spec": yaml_content, "source": "inline"}}

    response = lambda_handler(event, MockContext())

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["valid"] is False
    assert len(body["errors"]) > 0
    assert any("apiVersion" in err for err in body["errors"])


def test_lambda_handler_missing_spec():
    """Lambda handler returns error when spec field missing."""
    from handler import lambda_handler

    event = {"body": {"source": "inline"}}

    response = lambda_handler(event, MockContext())

    assert response["statusCode"] == 400

    body = json.loads(response["body"])

    assert body["valid"] is False
    assert any("required field" in err.lower() for err in body["errors"])


def test_lambda_handler_invalid_json():
    """Lambda handler handles invalid JSON in request body."""
    from handler import lambda_handler

    event = {"body": "not valid json"}

    response = lambda_handler(event, MockContext())

    assert response["statusCode"] == 400

    body = json.loads(response["body"])

    assert body["valid"] is False
    assert any("json" in err.lower() for err in body["errors"])
