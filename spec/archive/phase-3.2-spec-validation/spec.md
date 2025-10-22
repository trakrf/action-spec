# Feature: Phase 3.2 - Spec Validation & Parsing Engine

## Metadata
**Workspace**: backend
**Type**: feature
**Phase**: 3.2
**Estimated Effort**: 4-6 days
**Dependencies**: Phase 3.1 (Backend Foundation) ✅ Completed

## Outcome
ActionSpec can parse, validate, and analyze infrastructure specification files with comprehensive error reporting, destructive change detection, and safe handling of untrusted YAML input.

## User Story
As a **platform engineer**
I want **robust validation of infrastructure specifications**
So that **I can confidently deploy changes knowing dangerous configurations will be caught before they reach AWS**

## Context

**Origin**: This specification implements Phase 3.2 from PRD.md (lines 503-530), building on the Lambda foundation established in Phase 3.1.

**Current**: Phase 3.1 provides stub Lambda functions with security wrappers. The spec-parser Lambda currently returns mock data. There is no schema definition or validation logic.

**Desired**: A complete validation framework that:
- Defines the ActionSpec v1 schema (JSON Schema format)
- Parses YAML specs safely and efficiently
- Validates against schema with helpful error messages
- Detects potentially destructive changes (data loss, security downgrades)
- Provides example specs demonstrating best practices
- Achieves 90%+ test coverage with comprehensive test suite

**Why This Matters**: This is the "brain" of ActionSpec. Every downstream component (form generation, GitHub integration, Terraform deployment) relies on correctly validated specs. Weak validation = production disasters.

## Technical Requirements

### 1. JSON Schema Definition (`specs/schema/actionspec-v1.schema.json`)

**Core Structure**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://actionspec.dev/schemas/v1",
  "title": "ActionSpec v1 Schema",
  "description": "Infrastructure specification for GitHub Actions automation",
  "type": "object",
  "required": ["apiVersion", "kind", "metadata", "spec"],
  "additionalProperties": false
}
```

**Top-Level Fields**:
- `apiVersion`: enum `["actionspec/v1"]` (enables future versioning)
- `kind`: enum `["WebApplication", "APIService", "StaticSite"]`
- `metadata`: object with `name` (required), `labels` (optional)
- `spec`: object (kind-specific schema via `if/then` conditionals)

**Spec Fields (kind: WebApplication)**:
- `compute`: object (required for WebApplication)
  - `tier`: enum `["web", "api", "worker"]`
  - `size`: enum `["demo", "small", "medium", "large"]`
  - `scaling`: object
    - `min`: integer (1-10)
    - `max`: integer (1-100)
    - Validation: `max >= min`

- `network`: object (NEW - missing from PRD, critical for VPC config)
  - `vpc`: string (VPC ID or "create-new")
  - `subnets`: array of strings (subnet IDs)
  - `securityGroups`: array of strings (SG IDs)
  - `publicAccess`: boolean (default: false)

- `data`: object (optional)
  - `engine`: enum `["postgres", "mysql", "dynamodb", "none"]`
  - `size`: enum `["demo", "small", "medium", "large"]`
  - `highAvailability`: boolean
  - `backupRetention`: integer (0-35 days)

- `security`: object (required)
  - `waf`: object
    - `enabled`: boolean
    - `mode`: enum `["monitor", "block"]` (required if enabled=true)
    - `rulesets`: array of enum `["core-protection", "rate-limiting", "geo-blocking", "sql-injection", "xss"]`
  - `encryption`: object
    - `atRest`: boolean (default: true)
    - `inTransit`: boolean (default: true)

- `governance`: object (required for cost protection)
  - `maxMonthlySpend`: number (1-1000 USD)
  - `autoShutdown`: object
    - `enabled`: boolean
    - `afterHours`: integer (1-168 hours)

**Conditional Validation** (using JSON Schema `if/then`):
- If `kind = "StaticSite"`, then `compute` is NOT allowed
- If `kind = "APIService"`, then `data.engine` cannot be "none"
- If `security.waf.enabled = true`, then `security.waf.mode` is required
- If `compute.scaling.max > 10`, then `governance.maxMonthlySpend` must be >= 50

**Extensibility**:
- Support `x-*` vendor extensions (not validated, passed through)
- `metadata.labels` allows arbitrary key-value pairs
- Pattern: `"^x-[a-zA-Z0-9-]+$"` for extension fields

### 2. Spec Parser Lambda Implementation

**Location**: `backend/lambda/functions/spec-parser/`

**Core Module** (`parser.py`):
```python
class SpecParser:
    """Parse and validate ActionSpec YAML files"""

    def parse_yaml(self, yaml_content: str) -> dict:
        """
        Parse YAML with safety checks
        - Prevent YAML bombs (!!python/object exploits)
        - Limit document size (max 1MB)
        - Timeout after 5 seconds
        - Return parsed dict or raise ParseError
        """

    def validate_schema(self, spec_dict: dict) -> ValidationResult:
        """
        Validate against JSON Schema
        - Load schema from embedded file
        - Use jsonschema.validate()
        - Return user-friendly error messages (not raw schema errors)
        - Include context: field path, expected type, actual value
        """

    def transform_for_terraform(self, spec_dict: dict) -> dict:
        """
        Transform spec → Terraform variables
        - Map size enums to instance types ("demo" → "t4g.nano")
        - Generate resource names from metadata
        - Flatten nested structures for tfvars
        """

    def transform_for_form(self, spec_dict: dict) -> dict:
        """
        Transform spec → frontend form structure
        - Separate fields by section (compute, network, security, etc.)
        - Include current values and allowed values
        - Add UI hints (field order, help text, dependencies)
        """
```

**Handler** (`handler.py`):
```python
from shared.security_wrapper import secure_handler
from parser import SpecParser

@secure_handler
def lambda_handler(event, context):
    """
    Parse and validate a spec file

    POST /parse
    Body: {
        "source": "github|s3|inline",
        "spec": "<yaml content or S3 key>",
        "validate_only": false
    }

    Response: {
        "valid": true/false,
        "spec": { parsed dict },
        "errors": [ array of validation errors ],
        "warnings": [ array of warnings ],
        "metadata": { parsing stats }
    }
    """
```

**Input Sources** (Phase 3.2 scope):
- ✅ Inline YAML string (for testing, CLI usage)
- ✅ S3 key (for stored specs)
- ⏸️ GitHub repository (deferred to Phase 3.3)

**Performance Requirements**:
- Parse time: < 500ms for typical spec (< 100 lines)
- Parse time: < 2s for complex spec (< 1000 lines)
- Memory usage: < 256MB (Lambda default)
- Timeout: 10s Lambda timeout (fail fast)

**Error Handling**:
```python
class ParseError(Exception):
    """YAML parsing failed"""
    field: str  # e.g., "spec.compute.size"
    message: str  # Human-readable
    line: int  # YAML line number (if available)

class ValidationError(Exception):
    """Schema validation failed"""
    field: str
    message: str
    expected: Any
    actual: Any
```

**User-Friendly Error Messages**:
```
❌ Bad: "Failed validating 'enum' in schema['properties']['spec']['properties']['compute']['properties']['size']"

✅ Good: "Invalid value for 'spec.compute.size': got 'xlarge', expected one of: demo, small, medium, large"
```

### 3. Configuration Validator Module

**Location**: `backend/lambda/shared/validator.py`

**Destructive Change Detection**:

```python
class ChangeAnalyzer:
    """Analyze differences between old and new specs"""

    SEVERITY_LEVELS = ["error", "warning", "info"]

    def detect_changes(self, old_spec: dict, new_spec: dict) -> List[Change]:
        """
        Deep comparison with semantic understanding

        Returns: List of Change objects with:
        - field: str (dot-notation path)
        - old_value: Any
        - new_value: Any
        - severity: "error" | "warning" | "info"
        - message: str (user-facing description)
        - category: str (e.g., "security", "cost", "availability")
        """
```

**Destructive Change Taxonomy**:

| Change Type | Severity | Example | Message |
|-------------|----------|---------|---------|
| **Data Loss Risk** | ERROR | data.size: medium → demo | "⛔ Database downsize may cause data loss. Backup required before proceeding." |
| **Security Downgrade** | ERROR | security.waf.enabled: true → false | "⛔ Disabling WAF removes critical protection. Requires explicit approval." |
| **Availability Impact** | WARNING | data.highAvailability: true → false | "⚠️ Disabling HA may cause downtime during failures." |
| **Cost Explosion** | WARNING | compute.size: demo → large | "⚠️ Instance upsize increases costs ~10x. Estimated +$150/month." |
| **Security Enhancement** | INFO | security.waf.enabled: false → true | "✅ Enabling WAF adds protection against common attacks." |
| **Cost Reduction** | INFO | compute.size: large → medium | "✅ Instance downsize reduces costs ~50%. Estimated -$75/month." |

**Special Cases**:
- **First deployment** (no old_spec): All changes are INFO severity, warn about cost estimates
- **Null → Value**: INFO (enabling new feature)
- **Value → Null**: WARNING (disabling feature)
- **Boolean flips**: Context-dependent severity

**Diff Algorithm**:
```python
def deep_diff(old: dict, new: dict, path: str = "") -> List[Difference]:
    """
    Recursive comparison with semantic understanding

    Handles:
    - Nested objects (recurse with path tracking)
    - Arrays (order-independent for lists like securityGroups)
    - Type changes (string → number = validation error)
    - Missing keys (deletion vs never set)
    """
```

**Warning Aggregation**:
```python
def aggregate_warnings(changes: List[Change]) -> ChangeReport:
    """
    Group changes by severity and category

    Returns:
    - has_errors: bool (any ERROR severity)
    - has_warnings: bool (any WARNING severity)
    - errors: List[Change]
    - warnings: List[Change]
    - info: List[Change]
    - summary: str (e.g., "3 errors, 2 warnings, 5 changes")
    """
```

### 4. Example Spec Files

**Location**: `specs/examples/`

Create three reference specs demonstrating progressive complexity:

#### 4.1 `minimal-static-site.spec.yml`
```yaml
# Simplest possible spec - static website only
apiVersion: actionspec/v1
kind: StaticSite
metadata:
  name: my-static-site
  labels:
    purpose: documentation

spec:
  # StaticSite doesn't require compute or data
  security:
    waf:
      enabled: false  # Optional for static content
    encryption:
      atRest: true

  governance:
    maxMonthlySpend: 5
    autoShutdown:
      enabled: false  # Always-on for docs
```

#### 4.2 `secure-web-waf.spec.yml`
```yaml
# The "star of the show" - demonstrates WAF enablement
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
    vpc: vpc-demo123  # Discovered from AWS or "create-new"
    subnets:
      - subnet-public-a
      - subnet-public-b
    securityGroups:
      - sg-web-tier
    publicAccess: true

  data:
    engine: postgres
    size: demo
    highAvailability: false
    backupRetention: 7

  # The key feature - toggle enabled: true to deploy WAF
  security:
    waf:
      enabled: false  # ← Change this to true!
      mode: monitor    # Start in monitor mode (block later)
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
      afterHours: 24  # Auto-destroy after 24h of demo
```

#### 4.3 `full-api-service.spec.yml`
```yaml
# Complete example with all features
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
      min: 3  # HA requires min 3
      max: 20

  network:
    vpc: create-new  # Auto-create VPC
    subnets: []  # Auto-create across 3 AZs
    securityGroups: []  # Auto-create
    publicAccess: false  # Internal API

  data:
    engine: postgres
    size: large
    highAvailability: true
    backupRetention: 30

  security:
    waf:
      enabled: true
      mode: block  # Production = block mode
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
      enabled: false  # Production stays up

  # Vendor extension example
  x-monitoring:
    datadog:
      enabled: true
      api_key_ssm: /prod/datadog/api-key
```

### 5. Lambda Layer for Shared Dependencies

**Location**: `backend/lambda/layers/spec-validation/`

**Purpose**: Share PyYAML and jsonschema across all Lambda functions without duplicating in each deployment package.

**Structure**:
```
layers/spec-validation/
├── python/
│   ├── yaml/          # PyYAML
│   ├── jsonschema/    # jsonschema + dependencies
│   └── shared/        # Our custom modules
│       ├── validator.py
│       ├── parser.py
│       └── schemas/
│           └── actionspec-v1.schema.json
├── requirements.txt
└── build-layer.sh
```

**requirements.txt**:
```
PyYAML==6.0.1
jsonschema==4.21.1
jsonschema[format]  # For format validation (email, uri, etc.)
```

**build-layer.sh**:
```bash
#!/bin/bash
# Build Lambda layer with dependencies
set -e

LAYER_DIR="python"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR"

pip install -r requirements.txt -t "$LAYER_DIR" --upgrade

# Copy schema
mkdir -p "$LAYER_DIR/shared/schemas"
cp ../../../specs/schema/actionspec-v1.schema.json "$LAYER_DIR/shared/schemas/"

echo "✅ Layer built: $(du -sh $LAYER_DIR)"
```

**SAM Template Integration**:
```yaml
SpecValidationLayer:
  Type: AWS::Serverless::LayerVersion
  Properties:
    LayerName: actionspec-spec-validation
    Description: YAML parsing and JSON schema validation
    ContentUri: layers/spec-validation/
    CompatibleRuntimes:
      - python3.12
  Metadata:
    BuildMethod: python3.12
```

### 6. Testing Strategy

**Test Coverage Goal**: 90%+ for validation logic

#### 6.1 Unit Tests (`backend/lambda/functions/spec-parser/tests/`)

**Test Fixtures** (`tests/fixtures/`):
```
fixtures/
├── valid/
│   ├── minimal.yml
│   ├── typical-webapp.yml
│   ├── full-featured.yml
│   └── with-extensions.yml
├── invalid/
│   ├── missing-apiversion.yml
│   ├── wrong-enum-value.yml
│   ├── invalid-type.yml
│   ├── extra-properties.yml
│   └── conditional-violation.yml  # e.g., StaticSite with compute
└── malicious/
    ├── yaml-bomb.yml
    ├── recursive-reference.yml
    ├── oversized-doc.yml (> 1MB)
    └── python-object-exploit.yml
```

**Test Cases** (`test_parser.py`):
```python
class TestSpecParser:
    def test_parse_valid_minimal_spec(self):
        """Minimal valid spec parses successfully"""

    def test_parse_valid_full_spec(self):
        """Full-featured spec with all fields parses"""

    def test_reject_missing_required_field(self):
        """Missing 'apiVersion' raises ValidationError"""

    def test_reject_invalid_enum_value(self):
        """Invalid compute.size enum value rejected"""

    def test_reject_type_mismatch(self):
        """String where number expected raises error"""

    def test_conditional_validation_staticsite_no_compute(self):
        """StaticSite with compute field raises error"""

    def test_user_friendly_error_messages(self):
        """Error messages include field path and expected values"""

    def test_yaml_bomb_protection(self):
        """Malicious YAML with recursive references times out"""

    def test_oversized_document_rejected(self):
        """Documents > 1MB raise error"""

    def test_python_object_exploit_blocked(self):
        """!!python/object tags raise security error"""
```

**Test Cases** (`test_validator.py`):
```python
class TestChangeAnalyzer:
    def test_detect_data_loss_risk(self):
        """Database downsize flagged as ERROR"""

    def test_detect_security_downgrade(self):
        """WAF disable flagged as ERROR"""

    def test_detect_cost_explosion(self):
        """Large instance upsize flagged as WARNING"""

    def test_first_deployment_all_info(self):
        """No old spec = all changes are INFO severity"""

    def test_deep_nested_change_detection(self):
        """Changes in spec.security.waf.rulesets detected"""

    def test_array_order_independence(self):
        """securityGroups order change is not flagged"""

    def test_warning_aggregation(self):
        """ChangeReport correctly counts errors/warnings"""
```

#### 6.2 Integration Tests (`backend/lambda/tests/integration/`)

**Test Cases** (`test_spec_parser_lambda.py`):
```python
class TestSpecParserLambdaIntegration:
    def test_lambda_handler_valid_spec(self):
        """Handler returns valid=true for good spec"""

    def test_lambda_handler_invalid_spec(self):
        """Handler returns valid=false with error details"""

    def test_security_headers_present(self):
        """All responses include security headers from wrapper"""

    def test_parse_from_s3(self):
        """Can fetch and parse spec from S3 bucket"""

    def test_timeout_on_malicious_yaml(self):
        """Lambda times out gracefully on YAML bomb"""
```

#### 6.3 Performance Tests

**Benchmarks** (`tests/performance/benchmark.py`):
```python
def test_parse_performance():
    """Parsing typical spec completes in < 500ms"""
    specs = load_fixtures("valid/*.yml")

    for spec_path in specs:
        start = time.time()
        result = parser.parse_yaml(spec_path.read_text())
        duration = time.time() - start

        assert duration < 0.5, f"{spec_path.name} took {duration}s"
```

#### 6.4 Security Tests

**Test Cases** (`tests/security/test_malicious_input.py`):
```python
def test_yaml_bomb_timeout():
    """Recursive YAML reference handled safely"""

def test_large_document_rejected():
    """Documents > 1MB rejected before parsing"""

def test_billion_laughs_attack():
    """Entity expansion attack prevented"""

def test_code_execution_blocked():
    """!!python/object tags raise SecurityError"""
```

### 7. CLI Validator Tool (Optional Enhancement)

**Location**: `scripts/validate-spec.py`

**Purpose**: Allow developers to validate specs locally before committing (pre-commit hook integration).

**Usage**:
```bash
# Validate single file
./scripts/validate-spec.py specs/examples/my-app.spec.yml

# Validate all specs in directory
./scripts/validate-spec.py specs/examples/*.yml

# Check for destructive changes
./scripts/validate-spec.py --compare-with main specs/examples/my-app.spec.yml
```

**Output**:
```
✅ specs/examples/minimal-static-site.spec.yml
   Valid ActionSpec v1

✅ specs/examples/secure-web-waf.spec.yml
   Valid ActionSpec v1
   ⚠️  1 warning:
   - security.waf.enabled: false → true (Cost impact: +$5/month)

❌ specs/examples/invalid.spec.yml
   Invalid ActionSpec v1
   Errors:
   - spec.compute.size: Invalid value 'xlarge', expected one of: demo, small, medium, large
   - spec.governance.maxMonthlySpend: Required field missing
```

**Implementation**: Reuse parser.py and validator.py modules (Python script, not Lambda).

## Validation Criteria

- [ ] **JSON Schema Complete**: Schema validates all fields from PRD examples plus network configuration
- [ ] **Parser Handles Valid Specs**: All 3 example specs (minimal, secure-waf, full) parse successfully
- [ ] **Parser Rejects Invalid Specs**: Schema violations produce clear, actionable error messages
- [ ] **Destructive Change Detection**: WAF disable and data downsize flagged as ERROR severity
- [ ] **Security Hardening**: YAML bomb and recursive reference attacks handled safely
- [ ] **Performance SLA**: Typical spec parses in < 500ms
- [ ] **Test Coverage**: 90%+ coverage on parser.py and validator.py
- [ ] **Lambda Integration**: spec-parser Lambda function works with test fixtures
- [ ] **Lambda Layer**: Shared dependencies deployed and importable
- [ ] **Documentation**: README explains schema fields and validation rules

## Success Metrics

**Technical Quality**:
- [ ] **90%+ test coverage** on validation logic (pytest-cov report)
- [ ] **All 3 example specs parse successfully** (minimal, secure-waf, full)
- [ ] **Invalid specs produce helpful errors** (manual review of error messages)
- [ ] **Destructive changes detected** (WAF disable = ERROR, HA disable = WARNING)
- [ ] **YAML bomb handled safely** (test completes without crashing)
- [ ] **Parse performance < 500ms** for typical spec (benchmark test passes)

**Functional Completeness**:
- [ ] **Schema includes network configuration** (vpc, subnets, securityGroups)
- [ ] **Conditional validation works** (StaticSite cannot have compute)
- [ ] **Diff algorithm handles nested changes** (spec.security.waf.rulesets changes detected)
- [ ] **First deployment handled** (no old spec = all INFO severity)
- [ ] **Lambda layer builds** (build-layer.sh succeeds, layer < 10MB)
- [ ] **CLI validator works** (optional: can validate specs from command line)

**Integration Readiness**:
- [ ] **Parser output ready for form generation** (Phase 3.4 can consume transform_for_form())
- [ ] **Parser output ready for Terraform** (transform_for_terraform() produces valid tfvars)
- [ ] **S3 integration works** (can read specs from S3 bucket)
- [ ] **Security headers present** (secure_handler wrapper applied)

**Expected Results**:
- Parsing minimal.yml: ✅ Valid, 0 errors, 0 warnings
- Parsing secure-waf.yml: ✅ Valid, 0 errors, 0 warnings
- Parsing full.yml: ✅ Valid, 0 errors, 0 warnings
- Parsing invalid-enum.yml: ❌ Invalid, 1 error ("spec.compute.size: got 'xlarge', expected one of...")
- Destructive change (WAF disable): ⛔ ERROR severity with message
- Performance: Parse 100 typical specs in < 50 seconds (avg 500ms each)

## References

**PRD.md**:
- Phase 3.2 definition: lines 503-530
- JSON Schema examples: lines 906-947
- Validation logic: lines 950-980
- Destructive change examples: lines 968-980

**Dependencies**:
- Phase 3.1 (Backend Foundation): ✅ Completed (PR #7)
- Integrates with Phase 3.3 (GitHub Integration): Parser output format
- Enables Phase 3.4 (Form Generator): transform_for_form() output

**Technical References**:
- JSON Schema spec: https://json-schema.org/draft-07/schema
- PyYAML safe loading: https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
- jsonschema library: https://python-jsonschema.readthedocs.io/

## Implementation Notes

**Schema Versioning Strategy**:
- Use `$id` field for schema URL: `https://actionspec.dev/schemas/v1`
- Future versions: `v2`, `v3` (semver for breaking changes)
- Specs declare version with `apiVersion: actionspec/v1`
- Parser loads schema based on spec's apiVersion
- Migration: Build converter tool when releasing v2

**Error Context Strategy**:
- Wrap jsonschema errors with custom exception class
- Extract field path from JSON Schema error (e.g., `$.spec.compute.size`)
- Convert to dot notation for clarity (`spec.compute.size`)
- Add context: expected values, actual value, helpful hint

**Performance Optimization**:
- Cache schema in memory (loaded once per Lambda container)
- Use `yaml.safe_load()` not `yaml.load()` (faster, safer)
- Set reasonable limits: 1MB doc size, 5s timeout
- Minimize dict traversals (single-pass diff where possible)

**Security Considerations**:
- NEVER use `yaml.load()` - always `yaml.safe_load()`
- Reject `!!python/object` and other dangerous tags
- Limit document size BEFORE parsing (prevents memory exhaustion)
- Timeout parsing operations (prevents infinite loops)
- Sanitize error messages (don't leak AWS account IDs from discovered resources)

## Out of Scope (Phase 3.2)

Explicitly NOT included in this phase:
- ❌ GitHub integration (fetching specs from repos) → Phase 3.3
- ❌ Form generation logic → Phase 3.4
- ❌ Terraform deployment → Phase 4
- ❌ Frontend UI → Phase 3.4
- ❌ Multi-region support → Future
- ❌ Custom resource types beyond WebApplication/APIService/StaticSite → Future
- ❌ Auto-migration between schema versions → Future (build when releasing v2)

## Conversation References

**Key Insights**:
- "This is the brain of ActionSpec" - User emphasized criticality of validation layer
- "We just finished phase 3.1" - Dependencies satisfied, ready to start
- "Ultrathink what do we need" - Requested deep analysis of requirements
- PRD has partial schema examples but missing networking config - Need to fill gaps

**Decisions**:
- Follow PRD structure but expand where PRD is incomplete (network config)
- Build CLI validator as optional enhancement (good DX, low cost)
- Use JSON Schema (standard, tooling, docs) over custom validation
- Three-tier severity (ERROR/WARNING/INFO) for destructive changes

**Concerns**:
- Security: Malicious YAML can DOS the system (addressed with safe_load + timeouts)
- Performance: Slow parsing = high Lambda costs (addressed with benchmarks)
- UX: Cryptic errors frustrate developers (addressed with user-friendly error wrapper)
- Future-proofing: Schema will evolve (addressed with versioning strategy)
