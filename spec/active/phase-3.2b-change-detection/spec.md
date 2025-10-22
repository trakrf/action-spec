# Feature: Phase 3.2b - Destructive Change Detection

## Origin
This specification emerged from Phase 3 implementation planning (PRD.md:504-540). Phase 3.2a (Spec Validation & Parsing) completed successfully with PR #8, but change detection logic was consciously deferred to Phase 3.2b to maintain focused scope.

## Outcome
The system will detect and warn users about potentially destructive infrastructure changes before they create PRs, preventing accidental downtime, data loss, or security degradation.

## User Story
As a **platform engineer using ActionSpec**
I want **clear warnings when my spec changes could cause infrastructure damage**
So that **I can make informed decisions before deploying changes**

## Context

### Discovery
- **Phase 3.2a Status**: ✅ Complete (PR #8, merged 2025-10-22)
  - YAML parsing with PyYAML ✅
  - JSON Schema validation with jsonschema ✅
  - 18 unit tests, 100% passing, 84% coverage ✅
  - Security hardening (YAML bombs, oversized docs) ✅

- **What's Missing**: Destructive change detection (PRD.md:529)

### Current State
- The `SpecParser` class can validate individual specs against the JSON Schema
- No ability to compare old vs new specs
- No mechanism to detect semantic changes (like WAF disabling or compute downsizing)
- PR creation happens without change impact analysis

### Desired State
A `check_destructive_changes(old_spec, new_spec)` function that:
1. Compares two validated specs
2. Identifies potentially destructive changes across all spec domains
3. Returns user-friendly warning messages
4. Integrates with Spec Applier Lambda for PR descriptions

## Technical Requirements

### Core Functionality

#### 1. Change Detection Module
- **Location**: `backend/lambda/functions/spec-parser/change_detector.py`
- **Primary Function**: `check_destructive_changes(old_spec: dict, new_spec: dict) -> List[str]`
- **Input**: Two validated spec dicts (already passed JSON Schema validation)
- **Output**: List of warning messages (empty list = no warnings)

#### 2. Detection Categories

**Security Changes** (CRITICAL):
- ✅ WAF disabling: `security.waf.enabled: true → false`
- ✅ WAF mode downgrade: `security.waf.mode: "block" → "monitor"`
- ✅ WAF ruleset reduction: removing protection rules
- ✅ Encryption disabling: `security.encryption.atRest/inTransit: true → false`

**Compute Changes** (HIGH):
- ✅ Size downgrade: `compute.size: "small" → "demo"` (order: demo < small < medium < large)
- ✅ Scaling reduction: `compute.scaling.max` decrease
- ✅ Minimum instance reduction: `compute.scaling.min` decrease
- ⚠️ Same-size changes: `compute.size: "demo" → "demo"` (no warning)

**Data Changes** (CRITICAL):
- ✅ Engine change: `data.engine: "postgres" → "mysql"` (migration required)
- ✅ Engine removal: `data.engine: "postgres" → "none"` (data loss!)
- ✅ Size downgrade: `data.size: "small" → "demo"`
- ✅ HA disabling: `data.highAvailability: true → false`
- ✅ Backup retention reduction: `data.backupRetention: 30 → 7`

**Network Changes** (HIGH):
- ✅ Public access removal: `network.publicAccess: true → false` (connectivity loss)
- ✅ VPC change: `network.vpc` change (complete network reconfig)
- ⚠️ Subnet changes: detect subnet removals (partial network change)
- ⚠️ Security group changes: detect removals (firewall changes)

**Governance Changes** (INFO):
- ℹ️ Budget reduction: `governance.maxMonthlySpend` decrease (informational)
- ℹ️ Auto-shutdown enabling: `governance.autoShutdown.enabled: false → true` (warn about downtime)

#### 3. Warning Message Format
```python
# User-friendly messages with emoji indicators
"⚠️ Disabling WAF will remove security protection"
"🔴 Changing data.engine from 'postgres' to 'mysql' requires manual data migration"
"⚠️ Compute size reduction from 'small' to 'demo' may cause downtime"
"🔴 Setting data.engine to 'none' will DELETE all data (irreversible!)"
"ℹ️ Auto-shutdown enabled: infrastructure will stop after 24 hours of inactivity"
```

#### 4. Integration Points

**Spec Applier Lambda** (PRD.md:837-856):
```python
# In backend/lambda/functions/spec-applier/handler.py
from spec_parser.change_detector import check_destructive_changes

def create_pr_with_warnings(old_spec, new_spec):
    # Validate both specs first
    warnings = check_destructive_changes(old_spec, new_spec)

    # Build PR description with warnings
    pr_body = generate_pr_description(old_spec, new_spec, warnings)

    # Create PR with warning section
    return github_client.create_pull_request(pr_body)
```

**PR Description Template**:
```markdown
## ActionSpec Update

### 🚨 Warnings
- ⚠️ Disabling WAF will remove security protection
- ⚠️ Compute size reduction from 'small' to 'demo' may cause downtime

### Changes
- `security.waf.enabled`: true → false
- `compute.size`: small → demo

### Review Checklist
- [ ] Confirmed WAF removal is intentional
- [ ] Verified compute capacity sufficient for load
- [ ] Notified stakeholders of changes

🤖 Automated by ActionSpec
```

### Error Handling

#### Edge Cases
1. **Missing fields in old spec**: Treat as "adding" not "removing" (no warning)
2. **Missing fields in new spec**: Treat as "removing" (warn if destructive)
3. **Invalid specs**: Should never reach change detection (validation happens first)
4. **Identical specs**: Return empty warning list
5. **Null/None values**: Treat as field removal

#### Graceful Degradation
- If comparison fails: return generic warning rather than crashing
- Log errors but don't block PR creation
- Fall back to schema validation if change detection unavailable

### Performance Constraints
- **Execution time**: < 500ms for typical spec comparison
- **Memory**: < 10MB (specs are small YAML files)
- **Lambda timeout**: Part of overall 30s Lambda timeout budget

### Security Considerations
- Change detection happens AFTER validation (inputs are trusted)
- No external API calls required (pure comparison logic)
- Warning messages must not leak sensitive data
- Sanitize field paths in messages (no raw dict keys)

## Code Examples

### Core Change Detector
```python
# backend/lambda/functions/spec-parser/change_detector.py
"""
Detect destructive changes between ActionSpec versions.
"""

from typing import List, Dict, Any, Optional

# Size ordering for comparisons
SIZE_ORDER = {"demo": 0, "small": 1, "medium": 2, "large": 3}


def check_destructive_changes(old_spec: dict, new_spec: dict) -> List[str]:
    """
    Identify potentially destructive changes between specs.

    Args:
        old_spec: Previously validated spec
        new_spec: New validated spec to compare

    Returns:
        List of warning messages (empty if no warnings)
    """
    warnings = []

    # Security changes (CRITICAL)
    warnings.extend(_check_security_changes(old_spec, new_spec))

    # Compute changes (HIGH)
    warnings.extend(_check_compute_changes(old_spec, new_spec))

    # Data changes (CRITICAL)
    warnings.extend(_check_data_changes(old_spec, new_spec))

    # Network changes (HIGH)
    warnings.extend(_check_network_changes(old_spec, new_spec))

    # Governance changes (INFO)
    warnings.extend(_check_governance_changes(old_spec, new_spec))

    return warnings


def _check_security_changes(old_spec: dict, new_spec: dict) -> List[str]:
    """Detect security downgrades."""
    warnings = []
    old_sec = old_spec.get("spec", {}).get("security", {})
    new_sec = new_spec.get("spec", {}).get("security", {})

    # WAF disabling
    old_waf = old_sec.get("waf", {})
    new_waf = new_sec.get("waf", {})

    if old_waf.get("enabled") and not new_waf.get("enabled"):
        warnings.append("⚠️ Disabling WAF will remove security protection")

    # WAF mode downgrade
    if old_waf.get("mode") == "block" and new_waf.get("mode") == "monitor":
        warnings.append("⚠️ WAF mode downgrade from 'block' to 'monitor' - attacks will be logged but not blocked")

    # Ruleset reduction
    old_rules = set(old_waf.get("rulesets", []))
    new_rules = set(new_waf.get("rulesets", []))
    removed_rules = old_rules - new_rules
    if removed_rules:
        warnings.append(f"⚠️ Removing WAF rulesets: {', '.join(removed_rules)}")

    # Encryption disabling
    old_enc = old_sec.get("encryption", {})
    new_enc = new_sec.get("encryption", {})

    if old_enc.get("atRest", True) and not new_enc.get("atRest", True):
        warnings.append("⚠️ Disabling encryption at rest")

    if old_enc.get("inTransit", True) and not new_enc.get("inTransit", True):
        warnings.append("⚠️ Disabling encryption in transit")

    return warnings


def _check_compute_changes(old_spec: dict, new_spec: dict) -> List[str]:
    """Detect compute downsizing."""
    warnings = []
    old_comp = old_spec.get("spec", {}).get("compute", {})
    new_comp = new_spec.get("spec", {}).get("compute", {})

    if not old_comp or not new_comp:
        return warnings  # No compute in one or both specs

    # Size downgrade
    old_size = old_comp.get("size")
    new_size = new_comp.get("size")
    if old_size and new_size and SIZE_ORDER.get(old_size, 0) > SIZE_ORDER.get(new_size, 0):
        warnings.append(f"⚠️ Compute size reduction from '{old_size}' to '{new_size}' may cause downtime")

    # Scaling reduction
    old_scaling = old_comp.get("scaling", {})
    new_scaling = new_comp.get("scaling", {})

    old_max = old_scaling.get("max")
    new_max = new_scaling.get("max")
    if old_max and new_max and new_max < old_max:
        warnings.append(f"⚠️ Maximum instance count reduced from {old_max} to {new_max}")

    old_min = old_scaling.get("min")
    new_min = new_scaling.get("min")
    if old_min and new_min and new_min < old_min:
        warnings.append(f"⚠️ Minimum instance count reduced from {old_min} to {new_min}")

    return warnings


def _check_data_changes(old_spec: dict, new_spec: dict) -> List[str]:
    """Detect data layer changes."""
    warnings = []
    old_data = old_spec.get("spec", {}).get("data", {})
    new_data = new_spec.get("spec", {}).get("data", {})

    if not old_data:
        return warnings  # No data layer previously

    # Engine change or removal
    old_engine = old_data.get("engine")
    new_engine = new_data.get("engine")

    if old_engine and old_engine != "none":
        if new_engine == "none":
            warnings.append("🔴 Setting data.engine to 'none' will DELETE all data (irreversible!)")
        elif new_engine and new_engine != old_engine:
            warnings.append(f"🔴 Changing data.engine from '{old_engine}' to '{new_engine}' requires manual data migration")

    # Size downgrade
    old_size = old_data.get("size")
    new_size = new_data.get("size")
    if old_size and new_size and SIZE_ORDER.get(old_size, 0) > SIZE_ORDER.get(new_size, 0):
        warnings.append(f"⚠️ Database size reduction from '{old_size}' to '{new_size}' may require data cleanup")

    # HA disabling
    if old_data.get("highAvailability") and not new_data.get("highAvailability"):
        warnings.append("⚠️ Disabling high availability - single point of failure introduced")

    # Backup retention reduction
    old_retention = old_data.get("backupRetention")
    new_retention = new_data.get("backupRetention")
    if old_retention and new_retention and new_retention < old_retention:
        warnings.append(f"⚠️ Backup retention reduced from {old_retention} to {new_retention} days")

    return warnings


def _check_network_changes(old_spec: dict, new_spec: dict) -> List[str]:
    """Detect network configuration changes."""
    warnings = []
    old_net = old_spec.get("spec", {}).get("network", {})
    new_net = new_spec.get("spec", {}).get("network", {})

    if not old_net:
        return warnings

    # VPC change
    old_vpc = old_net.get("vpc")
    new_vpc = new_net.get("vpc")
    if old_vpc and new_vpc and old_vpc != new_vpc:
        warnings.append("⚠️ VPC change requires complete network reconfiguration")

    # Public access removal
    if old_net.get("publicAccess") and not new_net.get("publicAccess"):
        warnings.append("⚠️ Disabling public access - external connectivity will be lost")

    # Subnet removals
    old_subnets = set(old_net.get("subnets", []))
    new_subnets = set(new_net.get("subnets", []))
    removed_subnets = old_subnets - new_subnets
    if removed_subnets:
        warnings.append(f"⚠️ Removing subnets: {', '.join(removed_subnets)}")

    return warnings


def _check_governance_changes(old_spec: dict, new_spec: dict) -> List[str]:
    """Detect governance changes (informational)."""
    warnings = []
    old_gov = old_spec.get("spec", {}).get("governance", {})
    new_gov = new_spec.get("spec", {}).get("governance", {})

    # Auto-shutdown enabling
    old_shutdown = old_gov.get("autoShutdown", {})
    new_shutdown = new_gov.get("autoShutdown", {})

    if not old_shutdown.get("enabled") and new_shutdown.get("enabled"):
        hours = new_shutdown.get("afterHours", 24)
        warnings.append(f"ℹ️ Auto-shutdown enabled: infrastructure will stop after {hours} hours of inactivity")

    # Budget reduction (informational)
    old_budget = old_gov.get("maxMonthlySpend")
    new_budget = new_gov.get("maxMonthlySpend")
    if old_budget and new_budget and new_budget < old_budget:
        warnings.append(f"ℹ️ Monthly budget reduced from ${old_budget} to ${new_budget}")

    return warnings
```

### Unit Test Structure
```python
# backend/lambda/functions/spec-parser/tests/test_change_detector.py
import pytest
from change_detector import check_destructive_changes


def test_waf_disabling_detected():
    """WAF disabling should generate warning."""
    old_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": True, "mode": "block"}
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": False}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) > 0
    assert any("WAF" in w for w in warnings)


def test_compute_downsize_detected():
    """Compute size reduction should generate warning."""
    old_spec = {
        "spec": {
            "compute": {"size": "small", "scaling": {"min": 2, "max": 10}}
        }
    }
    new_spec = {
        "spec": {
            "compute": {"size": "demo", "scaling": {"min": 1, "max": 5}}
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) >= 2  # Size + scaling warnings
    assert any("Compute size reduction" in w for w in warnings)


def test_data_engine_change_detected():
    """Data engine change should generate critical warning."""
    old_spec = {
        "spec": {
            "data": {"engine": "postgres", "size": "small"}
        }
    }
    new_spec = {
        "spec": {
            "data": {"engine": "mysql", "size": "small"}
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) > 0
    assert any("🔴" in w and "migration" in w.lower() for w in warnings)


def test_no_warnings_for_safe_changes():
    """Safe changes should not generate warnings."""
    old_spec = {
        "spec": {
            "security": {"waf": {"enabled": True}},
            "compute": {"size": "demo"}
        }
    }
    new_spec = {
        "spec": {
            "security": {"waf": {"enabled": True, "mode": "block"}},  # Adding mode
            "compute": {"size": "small"}  # Upgrading size
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 0
```

### Integration with Spec Applier Lambda
```python
# backend/lambda/functions/spec-applier/handler.py (excerpt)
from spec_parser.parser import SpecParser
from spec_parser.change_detector import check_destructive_changes

def lambda_handler(event, context):
    """Handle spec submission and create PR."""
    # Parse submitted spec
    parser = SpecParser()
    new_spec_yaml = event["body"]["spec_content"]
    is_valid, new_spec, errors = parser.parse_and_validate(new_spec_yaml)

    if not is_valid:
        return {"statusCode": 400, "body": {"errors": errors}}

    # Fetch current spec from GitHub
    old_spec_yaml = github_client.fetch_spec(repo, spec_path)
    _, old_spec, _ = parser.parse_and_validate(old_spec_yaml)

    # Detect destructive changes
    warnings = check_destructive_changes(old_spec, new_spec)

    # Create PR with warnings in description
    pr_url = create_pull_request_with_warnings(
        repo, spec_path, new_spec_yaml, warnings
    )

    return {
        "statusCode": 200,
        "body": {
            "pr_url": pr_url,
            "warnings": warnings
        }
    }
```

## Validation Criteria

### Functional Tests
- [ ] WAF disabling detected (enabled: true → false)
- [ ] WAF mode downgrade detected (block → monitor)
- [ ] Compute size downgrade detected (small → demo)
- [ ] Compute size same-tier change ignored (demo → demo)
- [ ] Scaling max reduction detected (10 → 5)
- [ ] Scaling min reduction detected (2 → 1)
- [ ] Data engine change detected (postgres → mysql)
- [ ] Data engine removal detected (postgres → none)
- [ ] Data size downgrade detected (medium → small)
- [ ] HA disabling detected (true → false)
- [ ] Backup retention reduction detected (30 → 7)
- [ ] VPC change detected (vpc-123 → vpc-456)
- [ ] Public access removal detected (true → false)
- [ ] Subnet removal detected (subnet in old, not in new)
- [ ] Auto-shutdown enabling detected (false → true)
- [ ] Budget reduction detected (100 → 50)

### Edge Case Tests
- [ ] Missing compute in old spec (no warning)
- [ ] Missing compute in new spec (field removal handled)
- [ ] Identical specs return empty warnings list
- [ ] Adding new fields doesn't trigger warnings
- [ ] Upgrading (demo → small) doesn't warn
- [ ] Invalid specs never reach change detection (validation first)

### Integration Tests
- [ ] Warnings appear in PR descriptions correctly formatted
- [ ] Multiple warnings listed clearly in PR body
- [ ] Empty warnings list produces clean PR description
- [ ] PR creation succeeds even if change detection fails (graceful)

### Performance Tests
- [ ] Comparison completes in < 500ms for typical specs
- [ ] Memory usage < 10MB
- [ ] No external API calls during comparison

### Security Tests
- [ ] Warning messages don't leak sensitive data
- [ ] Field paths sanitized in error messages
- [ ] Comparison function doesn't modify input specs

## Dependencies
- **Phase 3.1**: ✅ Complete (Lambda runtime environment, SAM template)
- **Phase 3.2a**: ✅ Complete (SpecParser, JSON Schema validation)
- **Phase 3.3**: ⏳ Pending (GitHub integration, Spec Applier Lambda)

## Conversation References

**Key Insight from User**:
> "tell me about what we are working on next. Phase 3.2b: Change detection, I believe"

**PRD Context** (PRD.md:529):
> "⏳ Detect destructive changes (WAF disable, compute downsize) - deferred to Phase 3.2b"

**Design Reference** (PRD.md:976-990):
```python
def check_destructive_changes(old_spec, new_spec):
    """Identify potentially destructive changes"""
    warnings = []

    # Check for compute downsizing
    if old_spec.get('compute', {}).get('size') > new_spec.get('compute', {}).get('size'):
        warnings.append("⚠️ Compute size reduction may cause downtime")

    # Check for security downgrades
    if old_spec.get('security', {}).get('waf', {}).get('enabled') and \
       not new_spec.get('security', {}).get('waf', {}).get('enabled'):
        warnings.append("⚠️ Disabling WAF will remove security protection")

    return warnings
```

**Success Criteria** (PRD.md:527-530):
- Detect WAF disable operations
- Detect compute downsizing (demo→demo OK, small→demo warns)
- Return user-friendly warning messages
- Integration with existing spec-parser Lambda

## Effort Estimate
**Time**: 1-2 days (4-8 hours focused work)
- Core change detector: 2-3 hours
- Unit tests (15+ test cases): 2-3 hours
- Integration with spec-applier: 1 hour
- Documentation and PR: 1 hour

**Complexity**: LOW-MEDIUM
- Pure Python logic (no external dependencies)
- Clear requirements from PRD
- Well-defined input/output
- Existing test infrastructure in place

## Notes
- This is a **deferred** component from Phase 3.2a, consciously split for scope management
- Implementation should follow existing patterns in `parser.py` (error handling, typing)
- Warning messages use emoji for visual clarity (⚠️ = warning, 🔴 = critical, ℹ️ = info)
- Change detection happens AFTER validation (inputs are always valid specs)
- Future enhancement: Severity levels (info, warning, critical) for frontend display
