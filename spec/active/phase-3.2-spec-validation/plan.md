# Implementation Plan: Phase 3.2a - Schema + Basic Parser
Generated: 2025-10-21
Specification: spec.md

## Understanding

Phase 3.2a implements the foundation of ActionSpec's validation engine:
- **Complete JSON Schema** defining all ActionSpec v1 fields with conditional validation
- **Parser module** that safely parses YAML and validates against schema
- **User-friendly error messages** that help developers fix issues quickly
- **Three example specs** demonstrating minimal, typical, and full configurations
- **Comprehensive test coverage** ensuring reliability

This phase provides the critical validation layer that all downstream components (form generation, GitHub integration, Terraform deployment) depend on. The focus is on **correctness and safety** - getting the schema right now prevents architectural pivots later.

**Key Design Decisions from Clarifying Questions**:
- Accept any string for VPC/subnet IDs (allows "create-new" placeholder)
- Detailed error messages with field path, expected/actual values, and hints
- Extend stack.md to include Python validation (pytest, black, mypy)
- Use authentic-looking AWS resource ID patterns in examples
- Defer Lambda layer to Phase 3.2c (simpler testing)
- Moderate test fixture coverage (7-8 invalid spec scenarios)

## Relevant Files

**Reference Patterns** (existing code to follow):
- `backend/lambda/shared/security_wrapper.py` (lines 43-76) - Pattern for recursive dict sanitization (apply to schema error formatting)
- `backend/lambda/functions/spec-parser/handler.py` (lines 18-45) - Existing stub handler structure to enhance
- `backend/tests/test_security_wrapper.py` (lines 24-29) - MockContext pattern for Lambda testing
- `backend/tests/test_security_wrapper.py` (lines 32-44) - pytest assertion patterns

**Files to Create**:
- `specs/schema/actionspec-v1.schema.json` - Complete JSON Schema definition (~250 lines)
- `backend/lambda/functions/spec-parser/parser.py` - Core parsing module (~200 lines)
- `backend/lambda/functions/spec-parser/exceptions.py` - Custom exception classes (~50 lines)
- `backend/lambda/functions/spec-parser/requirements.txt` - Python dependencies
- `specs/examples/minimal-static-site.spec.yml` - Minimal example (~20 lines)
- `specs/examples/secure-web-waf.spec.yml` - WAF demo example (~45 lines)
- `specs/examples/full-api-service.spec.yml` - Complete example (~60 lines)
- `backend/tests/fixtures/valid/minimal.yml` - Valid minimal fixture
- `backend/tests/fixtures/valid/full-featured.yml` - Valid complex fixture
- `backend/tests/fixtures/invalid/missing-apiversion.yml` - Test: missing required field
- `backend/tests/fixtures/invalid/wrong-enum-value.yml` - Test: invalid enum
- `backend/tests/fixtures/invalid/invalid-type.yml` - Test: type mismatch
- `backend/tests/fixtures/invalid/extra-properties.yml` - Test: additionalProperties=false
- `backend/tests/fixtures/invalid/conditional-violation.yml` - Test: StaticSite with compute
- `backend/tests/fixtures/invalid/missing-waf-mode.yml` - Test: waf.enabled=true but no mode
- `backend/tests/fixtures/invalid/scaling-max-lt-min.yml` - Test: scaling.max < scaling.min
- `backend/tests/test_parser.py` - Parser unit tests (~250 lines)
- `specs/schema/README.md` - Schema documentation (~100 lines)

**Files to Modify**:
- `backend/lambda/functions/spec-parser/handler.py` (lines ~20-45) - Replace stub with real parser logic
- `spec/stack.md` (add Python section) - Add pytest, black, mypy commands

## Architecture Impact
- **Subsystems affected**: Backend (spec-parser Lambda), Schema definition, Testing infrastructure
- **New dependencies**: PyYAML==6.0.1, jsonschema==4.21.1, jsonschema[format], pytest-cov, black, mypy
- **Breaking changes**: None (Phase 3.1 was stubs only)
- **Integration points**:
  - Schema will be consumed by Phase 3.3 (GitHub integration)
  - Parser output format consumed by Phase 3.4 (form generator)
  - Example specs used for end-to-end testing in all future phases

## Task Breakdown

### Task 1: Extend stack.md with Python Validation Commands
**File**: `spec/stack.md`
**Action**: MODIFY (add Python section)
**Pattern**: Follow existing npm section structure

**Implementation**:
Add after existing npm commands:
```markdown
## Python Backend (Lambda)

### Lint
```bash
cd backend
black --check lambda/ tests/
```

### Format
```bash
cd backend
black lambda/ tests/
```

### Typecheck
```bash
cd backend
mypy lambda/ --ignore-missing-imports
```

### Test
```bash
cd backend
pytest tests/ -v --cov=lambda --cov-report=term-missing
```

### Test (specific file)
```bash
cd backend
pytest tests/test_parser.py -v
```
```

**Validation**:
- File syntax is valid markdown
- Commands follow existing pattern (npm run X → direct tool invocation)

---

### Task 2: Create JSON Schema Definition
**File**: `specs/schema/actionspec-v1.schema.json`
**Action**: CREATE
**Pattern**: JSON Schema Draft 7 specification

**Implementation**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://actionspec.dev/schemas/v1",
  "title": "ActionSpec v1 Schema",
  "description": "Infrastructure specification for GitHub Actions automation",
  "type": "object",
  "required": ["apiVersion", "kind", "metadata", "spec"],
  "additionalProperties": false,
  "properties": {
    "apiVersion": {
      "type": "string",
      "enum": ["actionspec/v1"],
      "description": "Schema version"
    },
    "kind": {
      "type": "string",
      "enum": ["WebApplication", "APIService", "StaticSite"],
      "description": "Type of infrastructure to deploy"
    },
    "metadata": {
      "type": "object",
      "required": ["name"],
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-z0-9-]+$",
          "minLength": 3,
          "maxLength": 63,
          "description": "Resource name (lowercase, alphanumeric, hyphens)"
        },
        "labels": {
          "type": "object",
          "additionalProperties": {"type": "string"},
          "description": "Arbitrary key-value labels"
        }
      },
      "additionalProperties": false
    },
    "spec": {
      "type": "object",
      "properties": {
        "compute": { "$ref": "#/definitions/compute" },
        "network": { "$ref": "#/definitions/network" },
        "data": { "$ref": "#/definitions/data" },
        "security": { "$ref": "#/definitions/security" },
        "governance": { "$ref": "#/definitions/governance" }
      },
      "required": ["security", "governance"],
      "additionalProperties": false,
      "patternProperties": {
        "^x-[a-zA-Z0-9-]+$": {
          "description": "Vendor extensions allowed"
        }
      }
    }
  },
  "definitions": {
    "compute": {
      "type": "object",
      "properties": {
        "tier": {
          "type": "string",
          "enum": ["web", "api", "worker"]
        },
        "size": {
          "type": "string",
          "enum": ["demo", "small", "medium", "large"]
        },
        "scaling": {
          "type": "object",
          "properties": {
            "min": {"type": "integer", "minimum": 1, "maximum": 10},
            "max": {"type": "integer", "minimum": 1, "maximum": 100}
          },
          "required": ["min", "max"]
        }
      },
      "required": ["tier", "size", "scaling"]
    },
    "network": {
      "type": "object",
      "properties": {
        "vpc": {"type": "string"},
        "subnets": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 0
        },
        "securityGroups": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 0
        },
        "publicAccess": {"type": "boolean", "default": false}
      },
      "required": ["vpc", "subnets", "securityGroups"]
    },
    "data": {
      "type": "object",
      "properties": {
        "engine": {
          "type": "string",
          "enum": ["postgres", "mysql", "dynamodb", "none"]
        },
        "size": {
          "type": "string",
          "enum": ["demo", "small", "medium", "large"]
        },
        "highAvailability": {"type": "boolean"},
        "backupRetention": {
          "type": "integer",
          "minimum": 0,
          "maximum": 35
        }
      },
      "required": ["engine"]
    },
    "security": {
      "type": "object",
      "properties": {
        "waf": {
          "type": "object",
          "properties": {
            "enabled": {"type": "boolean"},
            "mode": {
              "type": "string",
              "enum": ["monitor", "block"]
            },
            "rulesets": {
              "type": "array",
              "items": {
                "type": "string",
                "enum": ["core-protection", "rate-limiting", "geo-blocking", "sql-injection", "xss"]
              },
              "uniqueItems": true
            }
          },
          "required": ["enabled"]
        },
        "encryption": {
          "type": "object",
          "properties": {
            "atRest": {"type": "boolean", "default": true},
            "inTransit": {"type": "boolean", "default": true}
          }
        }
      },
      "required": ["waf", "encryption"]
    },
    "governance": {
      "type": "object",
      "properties": {
        "maxMonthlySpend": {
          "type": "number",
          "minimum": 1,
          "maximum": 1000
        },
        "autoShutdown": {
          "type": "object",
          "properties": {
            "enabled": {"type": "boolean"},
            "afterHours": {
              "type": "integer",
              "minimum": 1,
              "maximum": 168
            }
          },
          "required": ["enabled"]
        }
      },
      "required": ["maxMonthlySpend", "autoShutdown"]
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {"kind": {"const": "WebApplication"}}
      },
      "then": {
        "properties": {
          "spec": {"required": ["compute", "network"]}
        }
      }
    },
    {
      "if": {
        "properties": {"kind": {"const": "APIService"}}
      },
      "then": {
        "properties": {
          "spec": {
            "required": ["compute", "network"],
            "properties": {
              "data": {
                "properties": {
                  "engine": {"not": {"const": "none"}}
                }
              }
            }
          }
        }
      }
    },
    {
      "if": {
        "properties": {"kind": {"const": "StaticSite"}}
      },
      "then": {
        "properties": {
          "spec": {
            "not": {
              "required": ["compute"]
            }
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "spec": {
            "properties": {
              "security": {
                "properties": {
                  "waf": {
                    "properties": {"enabled": {"const": true}}
                  }
                }
              }
            }
          }
        }
      },
      "then": {
        "properties": {
          "spec": {
            "properties": {
              "security": {
                "properties": {
                  "waf": {"required": ["mode"]}
                }
              }
            }
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "spec": {
            "properties": {
              "compute": {
                "properties": {
                  "scaling": {
                    "properties": {"max": {"minimum": 11}}
                  }
                }
              }
            }
          }
        }
      },
      "then": {
        "properties": {
          "spec": {
            "properties": {
              "governance": {
                "properties": {
                  "maxMonthlySpend": {"minimum": 50}
                }
              }
            }
          }
        }
      }
    }
  ]
}
```

**Key Features**:
- Conditional validation using `allOf` + `if/then` (WebApplication requires compute, StaticSite forbids it)
- Vendor extensions via `patternProperties` (x-*)
- Nested definitions for clean organization
- Comprehensive validation rules (min/max, patterns, enums)

**Validation**:
- JSON syntax is valid (use `jq . specs/schema/actionspec-v1.schema.json`)
- Schema validates against JSON Schema Draft 7 meta-schema
- Load schema with Python jsonschema library without errors

---

### Task 3: Create Custom Exception Classes
**File**: `backend/lambda/functions/spec-parser/exceptions.py`
**Action**: CREATE
**Pattern**: Python exception hierarchy

**Implementation**:
```python
"""
Custom exceptions for spec parsing and validation.
Provides context for user-friendly error messages.
"""


class SpecParserError(Exception):
    """Base exception for all spec parsing errors."""
    pass


class ParseError(SpecParserError):
    """YAML parsing failed."""

    def __init__(self, message: str, line: int = None, column: int = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.line:
            return f"Parse error at line {self.line}: {self.message}"
        return f"Parse error: {self.message}"


class ValidationError(SpecParserError):
    """Schema validation failed."""

    def __init__(
        self,
        message: str,
        field: str = None,
        expected: any = None,
        actual: any = None
    ):
        self.message = message
        self.field = field
        self.expected = expected
        self.actual = actual
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = []

        if self.field:
            parts.append(f"Validation error in '{self.field}'")
        else:
            parts.append("Validation error")

        parts.append(self.message)

        if self.expected is not None and self.actual is not None:
            parts.append(f"Expected: {self.expected}, Got: {self.actual}")
        elif self.expected is not None:
            parts.append(f"Expected: {self.expected}")

        return " - ".join(parts)


class SecurityError(SpecParserError):
    """Potentially malicious YAML detected."""

    def __init__(self, message: str, pattern: str = None):
        self.message = message
        self.pattern = pattern
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.pattern:
            return f"Security violation: {self.message} (detected: {self.pattern})"
        return f"Security violation: {self.message}"
```

**Validation**:
- Python syntax is valid (`python -m py_compile exceptions.py`)
- Can import exceptions in other modules
- Exception messages are user-friendly

---

### Task 4: Implement Parser Module
**File**: `backend/lambda/functions/spec-parser/parser.py`
**Action**: CREATE
**Pattern**: Class-based parser with method chaining

**Implementation**:
```python
"""
ActionSpec YAML parser with schema validation.
Safely parses YAML and validates against JSON Schema.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

import yaml
from jsonschema import validate as jsonschema_validate
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import Draft7Validator

from exceptions import ParseError, ValidationError, SecurityError


# Maximum document size (1MB)
MAX_DOC_SIZE = 1 * 1024 * 1024

# Parsing timeout (5 seconds)
PARSE_TIMEOUT = 5

# Load schema once at module level (cached in Lambda container)
SCHEMA_PATH = Path(__file__).parent / 'schema' / 'actionspec-v1.schema.json'
_SCHEMA_CACHE = None


def load_schema() -> dict:
    """Load JSON Schema from file (cached)."""
    global _SCHEMA_CACHE

    if _SCHEMA_CACHE is None:
        # Try multiple locations (local dev vs Lambda)
        search_paths = [
            SCHEMA_PATH,
            Path(__file__).parent.parent.parent.parent.parent / 'specs' / 'schema' / 'actionspec-v1.schema.json',
            Path('/opt/shared/schemas/actionspec-v1.schema.json')  # Lambda layer path
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
                pattern="oversized"
            )

        # Dangerous tag check
        dangerous_tags = ['!!python/object', '!!python/name', '!!python/module']
        for tag in dangerous_tags:
            if tag in yaml_content:
                raise SecurityError(
                    "Dangerous YAML tag detected",
                    pattern=tag
                )

        # Parse with timeout
        start_time = time.time()

        try:
            # CRITICAL: Use safe_load, NEVER load()
            parsed = yaml.safe_load(yaml_content)

            # Timeout check
            if time.time() - start_time > PARSE_TIMEOUT:
                raise SecurityError(
                    f"Parsing timeout ({PARSE_TIMEOUT}s exceeded)",
                    pattern="timeout"
                )

            if parsed is None:
                raise ParseError("Empty document")

            if not isinstance(parsed, dict):
                raise ParseError(
                    f"Root must be object, got {type(parsed).__name__}"
                )

            return parsed

        except yaml.YAMLError as e:
            # Extract line number if available
            line = None
            if hasattr(e, 'problem_mark'):
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
            if error.validator == 'required':
                missing_field = error.message.split("'")[1]
                full_path = f"{field_path}.{missing_field}" if field_path else missing_field
                errors.append(
                    f"Missing required field '{full_path}'"
                )

            elif error.validator == 'enum':
                allowed = error.validator_value
                actual = error.instance
                errors.append(
                    f"Invalid value for '{field_path}': got '{actual}', expected one of: {', '.join(allowed)}"
                )

            elif error.validator == 'type':
                expected_type = error.validator_value
                actual_type = type(error.instance).__name__
                errors.append(
                    f"Wrong type for '{field_path}': got {actual_type}, expected {expected_type}"
                )

            elif error.validator == 'additionalProperties':
                # Find which property is extra
                extra_props = set(error.instance.keys()) - set(error.schema.get('properties', {}).keys())
                for prop in extra_props:
                    errors.append(
                        f"Unknown field '{field_path}.{prop}' (not allowed by schema)"
                    )

            elif error.validator in ['minimum', 'maximum']:
                limit = error.validator_value
                actual = error.instance
                errors.append(
                    f"Value out of range for '{field_path}': got {actual}, {error.validator} is {limit}"
                )

            elif error.validator == 'pattern':
                pattern = error.validator_value
                actual = error.instance
                errors.append(
                    f"Invalid format for '{field_path}': got '{actual}', must match pattern {pattern}"
                )

            else:
                # Generic error (fallback)
                errors.append(
                    f"Validation error in '{field_path}': {error.message}"
                )

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
```

**Validation**:
Use pytest:
```bash
cd backend
python -m pytest tests/test_parser.py::test_parse_valid_minimal -v
```

---

### Task 5: Update Spec Parser Handler
**File**: `backend/lambda/functions/spec-parser/handler.py`
**Action**: MODIFY (replace stub with real implementation)
**Pattern**: Reference `backend/lambda/shared/security_wrapper.py` for error handling structure

**Implementation**:
Replace lines 18-45 with:
```python
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
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'valid': False,
                'errors': ['Invalid JSON in request body']
            })
        }

    # Extract YAML content
    yaml_content = body.get('spec')
    if not yaml_content:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'valid': False,
                'errors': ['Missing required field: spec']
            })
        }

    # Parse and validate
    parser = SpecParser()
    start_time = time.time()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    parse_time = time.time() - start_time

    # Return result
    return {
        'statusCode': 200,
        'body': json.dumps({
            'valid': is_valid,
            'spec': spec,
            'errors': errors,
            'metadata': {
                'parse_time_ms': round(parse_time * 1000, 2),
                'spec_size_bytes': len(yaml_content),
                'version': 'phase-3.2a'
            }
        })
    }
```

Also add imports at top:
```python
import json
import time
```

**Validation**:
Run integration test:
```bash
cd backend
pytest tests/test_parser.py::test_lambda_handler_valid_spec -v
```

---

### Task 6: Create Example Specs
**Files**:
- `specs/examples/minimal-static-site.spec.yml`
- `specs/examples/secure-web-waf.spec.yml`
- `specs/examples/full-api-service.spec.yml`

**Action**: CREATE
**Pattern**: YAML best practices (comments, indentation)

**minimal-static-site.spec.yml**:
```yaml
# Minimal ActionSpec - Static website
# Demonstrates: Simplest valid spec with minimal fields

apiVersion: actionspec/v1
kind: StaticSite
metadata:
  name: my-static-site
  labels:
    purpose: documentation
    environment: prod

spec:
  # StaticSite does not require compute or network

  security:
    waf:
      enabled: false  # Optional for static content
    encryption:
      atRest: true
      inTransit: true

  governance:
    maxMonthlySpend: 5
    autoShutdown:
      enabled: false  # Always available
```

**secure-web-waf.spec.yml** (see spec.md lines 312-363 for full content):
```yaml
# ActionSpec Demo - WAF Protection
# Demonstrates: Toggle WAF from disabled → enabled

apiVersion: actionspec/v1
kind: WebApplication
metadata:
  name: demo-secure-app
  labels:
    purpose: portfolio-demonstration
    environment: demo

spec:
  compute:
    tier: web
    size: demo
    scaling:
      min: 1
      max: 3

  network:
    vpc: vpc-0a1b2c3d4e5f6g7h8  # Real-looking AWS VPC ID
    subnets:
      - subnet-0a1b2c3d
      - subnet-4e5f6g7h
    securityGroups:
      - sg-0a1b2c3d4e5f
    publicAccess: true

  data:
    engine: postgres
    size: demo
    highAvailability: false
    backupRetention: 7

  # The star feature - toggle to enable WAF
  security:
    waf:
      enabled: false  # ← Change to true!
      mode: monitor   # monitor or block
      rulesets:
        - core-protection
        - rate-limiting
    encryption:
      atRest: true
      inTransit: true

  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: true
      afterHours: 24
```

**full-api-service.spec.yml** (see spec.md lines 365-421):
```yaml
# ActionSpec Complete Example - Production API
# Demonstrates: All features enabled

apiVersion: actionspec/v1
kind: APIService
metadata:
  name: production-api
  labels:
    environment: production
    team: platform
    cost-center: engineering

spec:
  compute:
    tier: api
    size: medium
    scaling:
      min: 3
      max: 20

  network:
    vpc: create-new  # Auto-create VPC
    subnets: []
    securityGroups: []
    publicAccess: false

  data:
    engine: postgres
    size: large
    highAvailability: true
    backupRetention: 30

  security:
    waf:
      enabled: true
      mode: block
      rulesets:
        - core-protection
        - rate-limiting
        - geo-blocking
        - sql-injection
        - xss
    encryption:
      atRest: true
      inTransit: true

  governance:
    maxMonthlySpend: 500
    autoShutdown:
      enabled: false

  # Vendor extension example
  x-monitoring:
    datadog:
      enabled: true
      api_key_ssm: /prod/datadog/api-key
```

**Validation**:
```bash
# Test that examples parse successfully
cd backend
python -c "
from lambda.functions.spec_parser.parser import SpecParser
from pathlib import Path

parser = SpecParser()
examples = Path('specs/examples').glob('*.spec.yml')

for ex in examples:
    is_valid, spec, errors = parser.parse_and_validate(ex.read_text())
    print(f'{ex.name}: {'✅ Valid' if is_valid else '❌ Invalid'}')
    if errors:
        for err in errors:
            print(f'  - {err}')
"
```

---

### Task 7: Create Test Fixtures (Valid)
**Files**:
- `backend/tests/fixtures/valid/minimal.yml`
- `backend/tests/fixtures/valid/full-featured.yml`

**Action**: CREATE
**Pattern**: Copy from examples with slight variations

**minimal.yml**:
```yaml
apiVersion: actionspec/v1
kind: StaticSite
metadata:
  name: test-minimal
spec:
  security:
    waf:
      enabled: false
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 5
    autoShutdown:
      enabled: false
```

**full-featured.yml**:
```yaml
apiVersion: actionspec/v1
kind: WebApplication
metadata:
  name: test-full-featured
  labels:
    env: test
spec:
  compute:
    tier: web
    size: demo
    scaling:
      min: 1
      max: 3
  network:
    vpc: vpc-test123
    subnets:
      - subnet-a
      - subnet-b
    securityGroups:
      - sg-test
    publicAccess: true
  data:
    engine: postgres
    size: demo
    highAvailability: false
    backupRetention: 7
  security:
    waf:
      enabled: true
      mode: monitor
      rulesets:
        - core-protection
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: true
      afterHours: 24
```

**Validation**:
- Files are valid YAML
- Parse successfully with parser

---

### Task 8: Create Test Fixtures (Invalid - Part 1)
**Files**:
- `backend/tests/fixtures/invalid/missing-apiversion.yml`
- `backend/tests/fixtures/invalid/wrong-enum-value.yml`
- `backend/tests/fixtures/invalid/invalid-type.yml`
- `backend/tests/fixtures/invalid/extra-properties.yml`

**Action**: CREATE
**Pattern**: Intentional violations for testing

**missing-apiversion.yml**:
```yaml
# Missing required field: apiVersion
kind: WebApplication
metadata:
  name: test-invalid
spec:
  security:
    waf:
      enabled: false
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: false
```

**wrong-enum-value.yml**:
```yaml
apiVersion: actionspec/v1
kind: WebApplication
metadata:
  name: test-invalid-enum
spec:
  compute:
    tier: web
    size: xlarge  # ← Invalid! Must be: demo, small, medium, large
    scaling:
      min: 1
      max: 3
  network:
    vpc: vpc-test
    subnets: []
    securityGroups: []
  security:
    waf:
      enabled: false
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: false
```

**invalid-type.yml**:
```yaml
apiVersion: actionspec/v1
kind: WebApplication
metadata:
  name: test-type-error
spec:
  compute:
    tier: web
    size: demo
    scaling:
      min: "one"  # ← Invalid! Should be integer
      max: 3
  network:
    vpc: vpc-test
    subnets: []
    securityGroups: []
  security:
    waf:
      enabled: false
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: false
```

**extra-properties.yml**:
```yaml
apiVersion: actionspec/v1
kind: StaticSite
metadata:
  name: test-extra-prop
  unknownField: "not allowed"  # ← Invalid! additionalProperties: false
spec:
  security:
    waf:
      enabled: false
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 5
    autoShutdown:
      enabled: false
```

**Validation**:
- Files are valid YAML
- Parser correctly rejects them with appropriate error messages

---

### Task 9: Create Test Fixtures (Invalid - Part 2)
**Files**:
- `backend/tests/fixtures/invalid/conditional-violation.yml`
- `backend/tests/fixtures/invalid/missing-waf-mode.yml`
- `backend/tests/fixtures/invalid/scaling-max-lt-min.yml`

**Action**: CREATE
**Pattern**: Test conditional validation rules

**conditional-violation.yml**:
```yaml
# Violation: StaticSite cannot have compute field
apiVersion: actionspec/v1
kind: StaticSite
metadata:
  name: test-conditional-error
spec:
  compute:  # ← Invalid for StaticSite!
    tier: web
    size: demo
    scaling:
      min: 1
      max: 3
  security:
    waf:
      enabled: false
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: false
```

**missing-waf-mode.yml**:
```yaml
# Violation: waf.enabled=true requires waf.mode
apiVersion: actionspec/v1
kind: StaticSite
metadata:
  name: test-missing-mode
spec:
  security:
    waf:
      enabled: true  # ← Requires mode field!
      # mode: missing!
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: false
```

**scaling-max-lt-min.yml**:
```yaml
# Violation: scaling.max >= scaling.min
apiVersion: actionspec/v1
kind: WebApplication
metadata:
  name: test-scaling-error
spec:
  compute:
    tier: web
    size: demo
    scaling:
      min: 5
      max: 3  # ← Invalid! max < min
  network:
    vpc: vpc-test
    subnets: []
    securityGroups: []
  security:
    waf:
      enabled: false
    encryption:
      atRest: true
      inTransit: true
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: false
```

**Note**: The scaling.max >= min validation requires custom validation logic beyond JSON Schema. This will be addressed in Phase 3.2b when we implement the validator.py module. For now, document this as a known limitation.

**Validation**:
- Files parse as YAML
- Parser detects violations (except scaling, which needs custom validation)

---

### Task 10: Create Parser Unit Tests
**File**: `backend/tests/test_parser.py`
**Action**: CREATE
**Pattern**: Follow `backend/tests/test_security_wrapper.py` pytest structure

**Implementation**:
```python
"""
Unit tests for spec parser module.
Tests YAML parsing, schema validation, and error messages.
"""

import sys
import os
from pathlib import Path

import pytest

# Add parser module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'functions', 'spec-parser'))

from parser import SpecParser, load_schema
from exceptions import ParseError, ValidationError, SecurityError


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


def test_load_schema():
    """Schema file loads successfully."""
    schema = load_schema()

    assert schema is not None
    assert schema['$schema'] == 'http://json-schema.org/draft-07/schema#'
    assert schema['title'] == 'ActionSpec v1 Schema'
    assert 'properties' in schema


def test_parse_valid_minimal_spec():
    """Minimal valid spec parses successfully."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'valid' / 'minimal.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is True
    assert spec['apiVersion'] == 'actionspec/v1'
    assert spec['kind'] == 'StaticSite'
    assert len(errors) == 0


def test_parse_valid_full_spec():
    """Full-featured spec parses successfully."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'valid' / 'full-featured.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is True
    assert spec['kind'] == 'WebApplication'
    assert spec['spec']['compute']['size'] == 'demo'
    assert len(errors) == 0


def test_reject_missing_required_field():
    """Missing required field raises validation error."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'invalid' / 'missing-apiversion.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any('apiVersion' in err for err in errors)


def test_reject_invalid_enum_value():
    """Invalid enum value rejected with helpful message."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'invalid' / 'wrong-enum-value.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    # Check for helpful error message
    assert any('xlarge' in err and 'demo, small, medium, large' in err for err in errors)


def test_reject_type_mismatch():
    """Type mismatch (string vs integer) rejected."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'invalid' / 'invalid-type.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any('scaling.min' in err or 'type' in err.lower() for err in errors)


def test_reject_extra_properties():
    """Extra properties rejected when additionalProperties=false."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'invalid' / 'extra-properties.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any('unknownField' in err for err in errors)


def test_conditional_validation_staticsite_no_compute():
    """StaticSite with compute field raises error."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'invalid' / 'conditional-violation.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    # Note: JSON Schema conditional validation may be complex
    # This test validates the conditional logic works


def test_waf_enabled_requires_mode():
    """WAF enabled=true requires mode field."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'invalid' / 'missing-waf-mode.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    assert len(errors) > 0
    assert any('mode' in err for err in errors)


def test_user_friendly_error_messages():
    """Error messages include field path and expected values."""
    parser = SpecParser()

    yaml_content = (FIXTURES_DIR / 'invalid' / 'wrong-enum-value.yml').read_text()

    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    assert is_valid is False
    error_msg = errors[0]

    # Should include:
    # - Field path (spec.compute.size or similar)
    # - Actual value (xlarge)
    # - Expected values (demo, small, medium, large)
    assert 'size' in error_msg.lower()
    assert 'xlarge' in error_msg
    assert any(size in error_msg for size in ['demo', 'small', 'medium', 'large'])


def test_oversized_document_rejected():
    """Documents > 1MB raise security error."""
    parser = SpecParser()

    # Create 2MB document
    huge_yaml = "x: " + ("a" * (2 * 1024 * 1024))

    is_valid, spec, errors = parser.parse_and_validate(huge_yaml)

    assert is_valid is False
    assert len(errors) > 0
    assert any('too large' in err.lower() or 'size' in err.lower() for err in errors)


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
    assert any('security' in err.lower() or 'dangerous' in err.lower() for err in errors)


def test_empty_document():
    """Empty YAML document raises parse error."""
    parser = SpecParser()

    is_valid, spec, errors = parser.parse_and_validate("")

    assert is_valid is False
    assert len(errors) > 0
    assert any('empty' in err.lower() for err in errors)


def test_invalid_yaml_syntax():
    """Invalid YAML syntax raises parse error with line number."""
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
    # Should include line number or helpful error
    error_msg = errors[0]
    assert 'line' in error_msg.lower() or 'indent' in error_msg.lower()


# Integration test with Lambda handler
def test_lambda_handler_valid_spec():
    """Lambda handler returns valid=true for good spec."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'functions', 'spec-parser'))
    from handler import lambda_handler

    class MockContext:
        request_id = 'test-123'

    yaml_content = (FIXTURES_DIR / 'valid' / 'minimal.yml').read_text()

    event = {
        'body': {
            'spec': yaml_content,
            'source': 'inline'
        }
    }

    response = lambda_handler(event, MockContext())

    assert response['statusCode'] == 200

    import json
    body = json.loads(response['body'])

    assert body['valid'] is True
    assert body['spec']['kind'] == 'StaticSite'
    assert len(body['errors']) == 0
    assert 'parse_time_ms' in body['metadata']


def test_lambda_handler_invalid_spec():
    """Lambda handler returns valid=false with error details."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'functions', 'spec-parser'))
    from handler import lambda_handler

    class MockContext:
        request_id = 'test-456'

    yaml_content = (FIXTURES_DIR / 'invalid' / 'missing-apiversion.yml').read_text()

    event = {
        'body': {
            'spec': yaml_content,
            'source': 'inline'
        }
    }

    response = lambda_handler(event, MockContext())

    assert response['statusCode'] == 200

    import json
    body = json.loads(response['body'])

    assert body['valid'] is False
    assert len(body['errors']) > 0
    assert any('apiVersion' in err for err in body['errors'])
```

**Validation**:
```bash
cd backend
pytest tests/test_parser.py -v --cov=lambda/functions/spec-parser --cov-report=term-missing
```

Expected: 90%+ coverage

---

### Task 11: Create Schema Documentation
**File**: `specs/schema/README.md`
**Action**: CREATE
**Pattern**: Developer-friendly documentation with examples

**Implementation**:
```markdown
# ActionSpec v1 Schema

This directory contains the JSON Schema definition for ActionSpec v1.

## Schema File

- **actionspec-v1.schema.json** - Complete schema definition

## Quick Reference

### Top-Level Structure

```yaml
apiVersion: actionspec/v1  # Required
kind: WebApplication | APIService | StaticSite  # Required
metadata:  # Required
  name: my-app  # Required: lowercase, alphanumeric, hyphens
  labels:  # Optional: arbitrary key-value pairs
    env: prod
spec:  # Required: kind-specific fields
  compute: { }
  network: { }
  data: { }
  security: { }  # Required
  governance: { }  # Required
```

### Kinds and Required Fields

| Kind | Requires compute? | Requires network? | Requires data? |
|------|-------------------|-------------------|----------------|
| **WebApplication** | Yes | Yes | Optional |
| **APIService** | Yes | Yes | Required (not "none") |
| **StaticSite** | **No** (forbidden) | No | No |

### Field Reference

#### compute (required for WebApplication, APIService)
```yaml
compute:
  tier: web | api | worker
  size: demo | small | medium | large
  scaling:
    min: 1-10
    max: 1-100  # Must be >= min
```

#### network (required for WebApplication, APIService)
```yaml
network:
  vpc: "vpc-abc123" | "create-new"  # Any string
  subnets:
    - subnet-abc123
    - subnet-def456
  securityGroups:
    - sg-abc123
  publicAccess: true | false
```

#### data (optional, but required for APIService)
```yaml
data:
  engine: postgres | mysql | dynamodb | none
  size: demo | small | medium | large
  highAvailability: true | false
  backupRetention: 0-35  # days
```

#### security (required)
```yaml
security:
  waf:
    enabled: true | false
    mode: monitor | block  # Required if enabled=true
    rulesets:
      - core-protection
      - rate-limiting
      - geo-blocking
      - sql-injection
      - xss
  encryption:
    atRest: true | false  # Default: true
    inTransit: true | false  # Default: true
```

#### governance (required)
```yaml
governance:
  maxMonthlySpend: 1-1000  # USD
  autoShutdown:
    enabled: true | false
    afterHours: 1-168  # hours (1 week max)
```

### Conditional Validation Rules

1. **StaticSite cannot have compute**
   - If `kind: StaticSite`, then `spec.compute` is forbidden

2. **APIService requires database**
   - If `kind: APIService`, then `spec.data.engine` cannot be "none"

3. **WAF enabled requires mode**
   - If `spec.security.waf.enabled: true`, then `spec.security.waf.mode` is required

4. **High scaling requires higher budget**
   - If `spec.compute.scaling.max > 10`, then `spec.governance.maxMonthlySpend >= 50`

### Vendor Extensions

You can add custom fields prefixed with `x-`:

```yaml
spec:
  # ... standard fields ...
  x-monitoring:
    datadog:
      enabled: true
  x-custom-feature:
    setting: value
```

Vendor extensions are not validated by the schema.

## Validation Tools

### Python

```python
from parser import SpecParser

parser = SpecParser()
is_valid, spec, errors = parser.parse_and_validate(yaml_content)

if is_valid:
    print("✅ Valid spec")
else:
    for error in errors:
        print(f"❌ {error}")
```

### Command Line

```bash
# Validate single file
python -m parser --validate path/to/spec.yml

# Validate all examples
./scripts/validate-specs.sh
```

## Error Messages

The parser provides helpful error messages:

```
❌ Invalid value for 'spec.compute.size': got 'xlarge', expected one of: demo, small, medium, large
✅ Missing required field 'spec.security'
⚠️ Wrong type for 'spec.governance.maxMonthlySpend': got string, expected number
```

## Schema Versioning

- Current version: **v1**
- Schema ID: `https://actionspec.dev/schemas/v1`
- Specs declare version with `apiVersion: actionspec/v1`

Future versions (v2, v3) will use semantic versioning for breaking changes.

## Examples

See `specs/examples/` for complete working examples:
- `minimal-static-site.spec.yml` - Simplest valid spec
- `secure-web-waf.spec.yml` - WAF demo spec
- `full-api-service.spec.yml` - All features enabled
```

**Validation**:
- Markdown renders correctly
- Links are accurate
- Examples match actual schema

---

### Task 12: Create requirements.txt
**File**: `backend/lambda/functions/spec-parser/requirements.txt`
**Action**: CREATE
**Pattern**: Pin versions for reproducibility

**Implementation**:
```
PyYAML==6.0.1
jsonschema==4.21.1
jsonschema[format]==4.21.1
```

**Validation**:
```bash
cd backend/lambda/functions/spec-parser
pip install -r requirements.txt
python -c "import yaml, jsonschema; print('✅ Dependencies installed')"
```

---

## VALIDATION GATES (MANDATORY)

**After EVERY task**, run validation commands from `spec/stack.md`:

### Python Backend Validation

```bash
cd backend

# Gate 1: Formatting (run black)
black lambda/ tests/

# Gate 2: Type checking
mypy lambda/ --ignore-missing-imports

# Gate 3: Unit tests
pytest tests/test_parser.py -v --cov=lambda/functions/spec-parser --cov-report=term-missing
```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

---

## Validation Sequence

**After each task**:
1. Black format check (auto-fix)
2. Mypy type check
3. Pytest unit tests

**Final validation** (after all tasks):
```bash
cd backend

# Full test suite
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-report=html

# Coverage gate: Must be >= 80%
coverage report --fail-under=80

# Test all example specs parse
python -c "
from pathlib import Path
import sys
sys.path.insert(0, 'lambda/functions/spec-parser')
from parser import SpecParser

parser = SpecParser()
examples = Path('specs/examples').glob('*.spec.yml')
failed = []

for ex in examples:
    is_valid, spec, errors = parser.parse_and_validate(ex.read_text())
    status = '✅' if is_valid else '❌'
    print(f'{status} {ex.name}')
    if not is_valid:
        failed.append(ex.name)
        for err in errors:
            print(f'    {err}')

if failed:
    print(f'\n❌ {len(failed)} examples failed')
    sys.exit(1)
else:
    print(f'\n✅ All {len(list(Path(\"specs/examples\").glob(\"*.spec.yml\")))} examples valid')
"
```

---

## Risk Assessment

**Risk: JSON Schema conditionals complex**
- **Mitigation**: Test conditional rules extensively (Tasks 9-10). Reference JSON Schema docs for `if/then` syntax.

**Risk: User-friendly error messages difficult**
- **Mitigation**: Parser wraps jsonschema errors (Task 4, lines 150-200). Test error messages manually (Task 10, test_user_friendly_error_messages).

**Risk: Schema incomplete or incorrect**
- **Mitigation**: Task 2 based on comprehensive spec. Validate against all 3 examples + 8 invalid fixtures.

**Risk: Test coverage < 90%**
- **Mitigation**: Task 10 includes 15+ test cases. Run pytest with --cov to verify.

---

## Integration Points

**Phase 3.1 (Backend Foundation)**:
- Uses existing security_wrapper (no changes needed)
- Extends spec-parser handler (Task 5)
- Follows existing test patterns (Task 10)

**Phase 3.2b (Change Detection)**:
- Validator module will consume parser output
- Parser.parse_and_validate() returns (bool, dict, errors) tuple for validator

**Phase 3.2c (Lambda Layer)**:
- Schema will move to Lambda layer: `/opt/shared/schemas/`
- Parser load_schema() already handles multiple search paths (Task 4, lines 25-30)

**Phase 3.3 (GitHub Integration)**:
- spec-applier will call parser to validate before creating PR
- Parser output format enables PR description generation

**Phase 3.4 (Form Generator)**:
- Schema consumed to generate form fields
- Example specs used for form defaults

---

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM-LOW)
**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec.md (comprehensive)
✅ Similar patterns found in codebase:
  - security_wrapper.py (dict recursion pattern)
  - test_security_wrapper.py (pytest structure)
  - handler.py (Lambda response format)
✅ All clarifying questions answered (user preferences clear)
✅ JSON Schema is well-documented standard (minimal unknowns)
✅ PyYAML and jsonschema are mature libraries
⚠️ JSON Schema conditional validation may require iteration
⚠️ Error message formatting needs manual testing

**Assessment**: High confidence in successful implementation. JSON Schema conditional rules may require 1-2 iteration cycles, but overall approach is sound and follows established patterns.

**Estimated one-pass success probability**: 75%

**Reasoning**:
- Core parsing logic is straightforward (PyYAML + jsonschema)
- Example specs provide clear validation targets
- Existing test patterns reduce test writing uncertainty
- Main risk is JSON Schema `if/then` conditionals, but these are testable
- User clarifications eliminated ambiguity about error messages and validation approach

---

## Post-Phase 3.2a: Roadmap Overview

### Phase 3.2b: Change Detection & Validation (Complexity: 5/10)

**Goal**: Detect destructive changes between spec versions and provide severity-based warnings

**Key Deliverables**:
1. **validator.py module** (`backend/lambda/shared/validator.py`)
   - ChangeAnalyzer class with detect_changes() method
   - Deep diff algorithm (handles nested objects, arrays, type changes)
   - Severity classification (ERROR/WARNING/INFO)
   - Warning aggregation and summary generation

2. **Destructive Change Taxonomy**:
   - **ERROR**: Data loss (DB downsize), Security downgrade (WAF disable)
   - **WARNING**: Availability impact (HA disable), Cost explosion (instance upsize)
   - **INFO**: Security enhancement, Cost reduction, Feature toggle

3. **Change Detection Logic**:
   - First deployment handling (no old_spec → all INFO)
   - Null → Value transitions (enabling features)
   - Value → Null transitions (disabling features)
   - Boolean flips with context-dependent severity
   - Array order-independence (security groups, subnets)

4. **Test Suite**:
   - Unit tests for all severity levels
   - Deep nested change detection
   - Array comparison (order-independent)
   - Edge cases (missing keys, type changes)
   - Integration tests with spec-parser

5. **API Integration**:
   - Extend spec-parser handler to accept old_spec parameter
   - Return change analysis in response
   - Update response format: `{valid, spec, errors, warnings, changes: {errors: [], warnings: [], info: []}}`

**Task Breakdown** (7 subtasks):
1. Create validator.py with ChangeAnalyzer skeleton
2. Implement deep_diff algorithm
3. Implement severity classification logic
4. Create test fixtures (old/new spec pairs)
5. Write unit tests for validator
6. Integrate with spec-parser handler
7. Write integration tests

**Estimated**: 3-4 days

**Dependencies**:
- Phase 3.2a parser (provides spec dict format)
- Spec examples (used for change detection testing)

**Success Criteria**:
- WAF disable flagged as ERROR
- DB downsize flagged as ERROR
- HA disable flagged as WARNING
- Instance upsize flagged as WARNING
- Array order changes not flagged (subnets, security groups)
- Test coverage >= 85%

---

### Phase 3.2c: Lambda Layer + Hardening (Complexity: 4/10)

**Goal**: Productionize validation system with Lambda layer, security hardening, and performance optimization

**Key Deliverables**:
1. **Lambda Layer Structure** (`backend/lambda/layers/spec-validation/`)
   - Move parser.py and validator.py to layer
   - Move schema to layer: `/opt/shared/schemas/`
   - requirements.txt (PyYAML, jsonschema)
   - build-layer.sh script

2. **SAM Template Updates** (`template.yaml`)
   - Add SpecValidationLayer resource
   - Update all Lambda functions to use layer
   - Remove parser/validator from function deployment packages

3. **Security Hardening**:
   - YAML bomb protection tests (recursive references)
   - Billion laughs attack tests (entity expansion)
   - Python code execution tests (!!python/object)
   - Oversized document tests (> 1MB)
   - Timeout enforcement tests (> 5s parse time)

4. **Performance Benchmarks**:
   - Parse time SLA: < 500ms for typical spec (< 100 lines)
   - Parse time SLA: < 2s for complex spec (< 1000 lines)
   - Memory usage: < 256MB (Lambda default)
   - Benchmark script with 100 spec variations

5. **CLI Validator Tool** (Optional):
   - `scripts/validate-spec.py` - Standalone validator
   - Supports single file and glob patterns
   - Compares with git history (--compare-with branch)
   - Pre-commit hook integration
   - Colored terminal output (✅/❌/⚠️)

6. **Production Documentation**:
   - Update specs/schema/README.md with layer info
   - Add LOCAL_DEVELOPMENT.md for parser/validator
   - Document layer build process
   - Performance tuning guide

**Task Breakdown** (6 subtasks):
1. Create Lambda layer directory structure
2. Write build-layer.sh and test locally
3. Update SAM template with layer resource
4. Write security test suite (malicious YAML)
5. Write performance benchmarks
6. Create CLI validator tool (optional)

**Estimated**: 2-3 days

**Dependencies**:
- Phase 3.2b validator module
- SAM local environment (for layer testing)

**Success Criteria**:
- Layer builds successfully (< 10MB uncompressed)
- Layer imports work from all Lambda functions
- YAML bomb test completes without crash (timeout or reject)
- Performance benchmarks pass (500ms typical, 2s complex)
- CLI validator works on all example specs
- Deploy to AWS succeeds with layer

**Integration with Future Phases**:
- Phase 3.3 (GitHub): Uses parser/validator from layer
- Phase 3.4 (Form Generator): Uses schema from layer
- All future Lambdas: Can import parser/validator from layer

---

## Summary

Phase 3.2a establishes the foundation:
- ✅ Complete JSON Schema (250 lines)
- ✅ Safe YAML parser (200 lines)
- ✅ User-friendly errors (detailed messages)
- ✅ 3 example specs (minimal, WAF demo, full)
- ✅ 10 test fixtures (2 valid, 8 invalid)
- ✅ 15+ unit tests (90%+ coverage target)

**Next**: Phase 3.2b adds change detection, Phase 3.2c hardens for production.

**Ready to build**: Yes - All tasks are atomic, testable, and follow existing patterns.
