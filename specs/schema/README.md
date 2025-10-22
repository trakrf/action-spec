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
