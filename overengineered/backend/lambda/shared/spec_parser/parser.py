"""
ActionSpec YAML parser with schema validation.
Safely parses YAML and validates against JSON Schema.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from jsonschema import Draft7Validator
from jsonschema import ValidationError as JsonSchemaValidationError

from spec_parser.exceptions import ParseError, SecurityError

# Maximum document size (1MB)
MAX_DOC_SIZE = 1 * 1024 * 1024

# Parsing timeout (5 seconds)
PARSE_TIMEOUT = 5

# Load schema once at module level (cached in Lambda container)
SCHEMA_PATH = Path(__file__).parent / "schema" / "actionspec-v1.schema.json"
_SCHEMA_CACHE = None


def load_schema() -> dict:
    """Load JSON Schema from file (cached)."""
    global _SCHEMA_CACHE

    if _SCHEMA_CACHE is None:
        # Try multiple locations (local dev vs Lambda)
        search_paths = [
            SCHEMA_PATH,
            # From backend/lambda/functions/spec-parser to project root (5 levels up)
            Path(__file__).parent.parent.parent.parent.parent
            / "specs"
            / "schema"
            / "actionspec-v1.schema.json",
            Path("/opt/shared/schemas/actionspec-v1.schema.json"),  # Lambda layer path
        ]

        for path in search_paths:
            if path.exists():
                with open(path) as f:
                    _SCHEMA_CACHE = json.load(f)
                break

        if _SCHEMA_CACHE is None:
            raise FileNotFoundError(
                f"Could not find schema file. Searched: {[str(p) for p in search_paths]}"
            )

    return _SCHEMA_CACHE


class SpecParser:
    """Parse and validate ActionSpec YAML files."""

    def __init__(self):
        self.schema = load_schema()
        self.validator = Draft7Validator(self.schema)

    def parse_yaml(self, yaml_content: str) -> dict:
        """
        Parse YAML with safety checks.

        Args:
            yaml_content: YAML string

        Returns:
            Parsed dict

        Raises:
            ParseError: YAML parsing failed
            SecurityError: Malicious YAML detected
        """
        # Size check (before parsing)
        if len(yaml_content) > MAX_DOC_SIZE:
            raise SecurityError(
                f"Document too large ({len(yaml_content)} bytes, max {MAX_DOC_SIZE})",
                pattern="oversized",
            )

        # Dangerous tag check
        dangerous_tags = ["!!python/object", "!!python/name", "!!python/module"]
        for tag in dangerous_tags:
            if tag in yaml_content:
                raise SecurityError("Dangerous YAML tag detected", pattern=tag)

        # Parse with timeout
        start_time = time.time()

        try:
            # CRITICAL: Use safe_load, NEVER load()
            parsed = yaml.safe_load(yaml_content)

            # Timeout check
            if time.time() - start_time > PARSE_TIMEOUT:
                raise SecurityError(
                    f"Parsing timeout ({PARSE_TIMEOUT}s exceeded)", pattern="timeout"
                )

            if parsed is None:
                raise ParseError("Empty document")

            if not isinstance(parsed, dict):
                raise ParseError(f"Root must be object, got {type(parsed).__name__}")

            return parsed

        except yaml.YAMLError as e:
            # Extract line number if available
            line = None
            if hasattr(e, "problem_mark"):
                line = e.problem_mark.line + 1

            raise ParseError(str(e), line=line)

    def validate_schema(self, spec_dict: dict) -> Tuple[bool, List[str]]:
        """
        Validate against JSON Schema.

        Args:
            spec_dict: Parsed spec

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        for error in self.validator.iter_errors(spec_dict):
            # Convert JSON Schema error to user-friendly message
            field_path = ".".join(str(p) for p in error.absolute_path)

            # Extract helpful info from error
            if error.validator == "required":
                missing_field = error.message.split("'")[1]
                full_path = (
                    f"{field_path}.{missing_field}" if field_path else missing_field
                )
                errors.append(f"Missing required field '{full_path}'")

            elif error.validator == "enum":
                allowed = error.validator_value
                actual = error.instance
                errors.append(
                    f"Invalid value for '{field_path}': got '{actual}', expected one of: {', '.join(allowed)}"
                )

            elif error.validator == "type":
                expected_type = error.validator_value
                actual_type = type(error.instance).__name__
                errors.append(
                    f"Wrong type for '{field_path}': got {actual_type}, expected {expected_type}"
                )

            elif error.validator == "additionalProperties":
                # Find which property is extra
                extra_props = set(error.instance.keys()) - set(
                    error.schema.get("properties", {}).keys()
                )
                # Filter out pattern properties (x-*)
                pattern_props = error.schema.get("patternProperties", {})
                for prop in extra_props:
                    # Check if it matches any pattern property
                    is_pattern_match = any(
                        import_re.match(pattern, prop)
                        for pattern in pattern_props.keys()
                        if (import_re := __import__("re"))
                    )
                    if not is_pattern_match:
                        errors.append(
                            f"Unknown field '{field_path}.{prop}' (not allowed by schema)"
                        )

            elif error.validator in ["minimum", "maximum"]:
                limit = error.validator_value
                actual = error.instance
                errors.append(
                    f"Value out of range for '{field_path}': got {actual}, {error.validator} is {limit}"
                )

            elif error.validator == "pattern":
                pattern = error.validator_value
                actual = error.instance
                errors.append(
                    f"Invalid format for '{field_path}': got '{actual}', must match pattern {pattern}"
                )

            else:
                # Generic error (fallback)
                errors.append(f"Validation error in '{field_path}': {error.message}")

        return (len(errors) == 0, errors)

    def parse_and_validate(self, yaml_content: str) -> Tuple[bool, dict, List[str]]:
        """
        Parse YAML and validate against schema (convenience method).

        Args:
            yaml_content: YAML string

        Returns:
            (is_valid, parsed_spec, error_messages)
        """
        try:
            spec = self.parse_yaml(yaml_content)
        except (ParseError, SecurityError) as e:
            return (False, {}, [str(e)])

        is_valid, errors = self.validate_schema(spec)
        return (is_valid, spec if is_valid else {}, errors)
