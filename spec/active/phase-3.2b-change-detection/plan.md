# Implementation Plan: Phase 3.2b - Destructive Change Detection
Generated: 2025-10-22
Specification: spec.md

## Understanding

This phase implements change detection logic to identify potentially destructive infrastructure changes between old and new ActionSpec configurations. The module will be consumed by the Spec Applier Lambda (Phase 3.3) to warn users before creating PRs that could cause downtime, data loss, or security degradation.

**Key Design Decisions**:
1. **Standalone module**: Self-contained, importable module with no integration code (Phase 3.3 will handle integration)
2. **Asymmetric logic**: Adding fields is safe (no warning), removing critical fields triggers warnings
3. **Dual-format warnings**: Emoji for human readability + structured severity field for programmatic use
4. **Hardcoded constants**: SIZE_ORDER dict in module for simplicity (YAGNI - no shared constants file yet)
5. **Unit tests only**: 15+ test cases prove detection logic; real integration test comes in Phase 3.3

**Success Criteria**:
- Detect all security downgrades (WAF, encryption, rulesets)
- Detect compute/data size reductions using ordered comparison
- Detect data engine changes and network reconfigurations
- Return user-friendly warnings with emoji + severity
- 80%+ test coverage
- All validation gates pass (black, mypy, pytest)

## Relevant Files

### Reference Patterns (existing code to follow)

**Parser module structure**:
- `backend/lambda/functions/spec-parser/parser.py` (lines 1-215) - Module organization, type hints, docstrings
  - Pattern: Type hints with `Dict`, `List`, `Tuple`, `Optional`
  - Pattern: Module-level constants (MAX_DOC_SIZE, PARSE_TIMEOUT)
  - Pattern: Comprehensive docstrings with Args/Returns/Raises

**Exception handling**:
- `backend/lambda/functions/spec-parser/exceptions.py` (lines 1-78) - Custom exception classes
  - Pattern: Inherit from base `SpecParserError`
  - Pattern: `_format_message()` method for user-friendly output
  - Pattern: Store context (field, pattern, line) in exception attributes

**Test structure**:
- `backend/tests/test_parser.py` (lines 1-249) - pytest patterns
  - Pattern: Fixture-based testing (valid/invalid directories)
  - Pattern: Descriptive test names (`test_reject_invalid_enum_value`)
  - Pattern: Assert on error message content for user-friendliness
  - Pattern: Path manipulation: `sys.path.insert(0, ...)` to import Lambda code

**Test fixtures**:
- `backend/tests/fixtures/valid/minimal.yml` - Minimal valid spec
- `backend/tests/fixtures/valid/full-featured.yml` - Full spec with all fields
  - Pattern: Reuse existing valid fixtures for old_spec in tests
  - Pattern: Create modified copies for new_spec scenarios

### Files to Create

**Core module**:
- `backend/lambda/functions/spec-parser/change_detector.py` (~250 lines)
  - Purpose: Detect destructive changes between two validated specs
  - Exports: `check_destructive_changes()`, `ChangeWarning` dataclass
  - Dependencies: typing (stdlib), dataclasses (stdlib)

**Test file**:
- `backend/tests/test_change_detector.py` (~400 lines)
  - Purpose: Unit tests for all detection categories + edge cases
  - Test count: 18 tests (5 categories × 3 tests + 3 edge cases)
  - Dependencies: pytest, sys path manipulation

**Test fixtures** (optional - can use inline YAML):
- `backend/tests/fixtures/changes/waf-disable.yml` (if using file-based fixtures)
- Alternative: Use inline YAML in test file for simplicity

### Files to Modify

None - this is a standalone module addition.

## Architecture Impact

- **Subsystems affected**: spec-parser only (self-contained)
- **New dependencies**: None (uses Python stdlib only)
- **Breaking changes**: None (additive functionality)
- **Integration point**: Phase 3.3 will import and call `check_destructive_changes()`

## Task Breakdown

### Task 1: Create change_detector.py skeleton
**File**: `backend/lambda/functions/spec-parser/change_detector.py`
**Action**: CREATE
**Pattern**: Follow parser.py structure (lines 1-30) for imports, constants, docstring

**Implementation**:
```python
"""
Detect destructive changes between ActionSpec versions.
Compares two validated specs and returns warnings for potentially dangerous changes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional

# Size ordering for comparison (demo < small < medium < large)
SIZE_ORDER = {"demo": 0, "small": 1, "medium": 2, "large": 3}


class Severity(str, Enum):
    """Warning severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ChangeWarning:
    """Structured warning with severity and display message."""
    severity: Severity
    message: str
    field_path: str

    def __str__(self) -> str:
        """Return emoji + message for display."""
        return self.message


def check_destructive_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """
    Identify potentially destructive changes between specs.

    Args:
        old_spec: Previously validated spec dict
        new_spec: New validated spec dict to compare

    Returns:
        List of ChangeWarning objects (empty if no warnings)

    Examples:
        >>> old = {"spec": {"security": {"waf": {"enabled": True}}}}
        >>> new = {"spec": {"security": {"waf": {"enabled": False}}}}
        >>> warnings = check_destructive_changes(old, new)
        >>> len(warnings)
        1
        >>> warnings[0].severity
        <Severity.WARNING: 'warning'>
    """
    warnings = []

    # Detect changes across all categories
    warnings.extend(_check_security_changes(old_spec, new_spec))
    warnings.extend(_check_compute_changes(old_spec, new_spec))
    warnings.extend(_check_data_changes(old_spec, new_spec))
    warnings.extend(_check_network_changes(old_spec, new_spec))
    warnings.extend(_check_governance_changes(old_spec, new_spec))

    return warnings
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
```

---

### Task 2: Implement _check_security_changes()
**File**: `backend/lambda/functions/spec-parser/change_detector.py`
**Action**: MODIFY (add function)
**Pattern**: Follow parser.py validation logic (lines 121-196) for nested dict access

**Implementation**:
```python
def _check_security_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect security downgrades."""
    warnings = []
    old_sec = old_spec.get("spec", {}).get("security", {})
    new_sec = new_spec.get("spec", {}).get("security", {})

    # WAF disabling
    old_waf = old_sec.get("waf", {})
    new_waf = new_sec.get("waf", {})

    if old_waf.get("enabled") and not new_waf.get("enabled"):
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message="⚠️ Disabling WAF will remove security protection",
            field_path="spec.security.waf.enabled"
        ))

    # WAF mode downgrade
    if old_waf.get("mode") == "block" and new_waf.get("mode") == "monitor":
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message="⚠️ WAF mode downgrade from 'block' to 'monitor' - attacks will be logged but not blocked",
            field_path="spec.security.waf.mode"
        ))

    # Ruleset reduction
    old_rules = set(old_waf.get("rulesets", []))
    new_rules = set(new_waf.get("rulesets", []))
    removed_rules = old_rules - new_rules
    if removed_rules:
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message=f"⚠️ Removing WAF rulesets: {', '.join(sorted(removed_rules))}",
            field_path="spec.security.waf.rulesets"
        ))

    # Encryption disabling
    old_enc = old_sec.get("encryption", {})
    new_enc = new_sec.get("encryption", {})

    if old_enc.get("atRest", True) and not new_enc.get("atRest", True):
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message="⚠️ Disabling encryption at rest",
            field_path="spec.security.encryption.atRest"
        ))

    if old_enc.get("inTransit", True) and not new_enc.get("inTransit", True):
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message="⚠️ Disabling encryption in transit",
            field_path="spec.security.encryption.inTransit"
        ))

    return warnings
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
python3 -c "from lambda.functions.spec_parser.change_detector import _check_security_changes; print('Import OK')"
```

---

### Task 3: Implement _check_compute_changes()
**File**: `backend/lambda/functions/spec-parser/change_detector.py`
**Action**: MODIFY (add function)
**Pattern**: Use SIZE_ORDER for comparisons

**Implementation**:
```python
def _check_compute_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect compute downsizing."""
    warnings = []
    old_comp = old_spec.get("spec", {}).get("compute", {})
    new_comp = new_spec.get("spec", {}).get("compute", {})

    # Early return if no compute in one or both specs
    if not old_comp or not new_comp:
        return warnings

    # Size downgrade (demo < small < medium < large)
    old_size = old_comp.get("size")
    new_size = new_comp.get("size")
    if old_size and new_size:
        old_order = SIZE_ORDER.get(old_size, 0)
        new_order = SIZE_ORDER.get(new_size, 0)
        if new_order < old_order:
            warnings.append(ChangeWarning(
                severity=Severity.WARNING,
                message=f"⚠️ Compute size reduction from '{old_size}' to '{new_size}' may cause downtime",
                field_path="spec.compute.size"
            ))

    # Scaling reduction
    old_scaling = old_comp.get("scaling", {})
    new_scaling = new_comp.get("scaling", {})

    old_max = old_scaling.get("max")
    new_max = new_scaling.get("max")
    if old_max and new_max and new_max < old_max:
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message=f"⚠️ Maximum instance count reduced from {old_max} to {new_max}",
            field_path="spec.compute.scaling.max"
        ))

    old_min = old_scaling.get("min")
    new_min = new_scaling.get("min")
    if old_min and new_min and new_min < old_min:
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message=f"⚠️ Minimum instance count reduced from {old_min} to {new_min}",
            field_path="spec.compute.scaling.min"
        ))

    return warnings
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
```

---

### Task 4: Implement _check_data_changes()
**File**: `backend/lambda/functions/spec-parser/change_detector.py`
**Action**: MODIFY (add function)
**Pattern**: Use CRITICAL severity for data loss scenarios

**Implementation**:
```python
def _check_data_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect data layer changes (high risk)."""
    warnings = []
    old_data = old_spec.get("spec", {}).get("data", {})
    new_data = new_spec.get("spec", {}).get("data", {})

    # Early return if no data layer previously
    if not old_data:
        return warnings

    # Engine change or removal (CRITICAL)
    old_engine = old_data.get("engine")
    new_engine = new_data.get("engine")

    if old_engine and old_engine != "none":
        if new_engine == "none":
            warnings.append(ChangeWarning(
                severity=Severity.CRITICAL,
                message="🔴 Setting data.engine to 'none' will DELETE all data (irreversible!)",
                field_path="spec.data.engine"
            ))
        elif new_engine and new_engine != old_engine:
            warnings.append(ChangeWarning(
                severity=Severity.CRITICAL,
                message=f"🔴 Changing data.engine from '{old_engine}' to '{new_engine}' requires manual data migration",
                field_path="spec.data.engine"
            ))

    # Size downgrade
    old_size = old_data.get("size")
    new_size = new_data.get("size")
    if old_size and new_size:
        old_order = SIZE_ORDER.get(old_size, 0)
        new_order = SIZE_ORDER.get(new_size, 0)
        if new_order < old_order:
            warnings.append(ChangeWarning(
                severity=Severity.WARNING,
                message=f"⚠️ Database size reduction from '{old_size}' to '{new_size}' may require data cleanup",
                field_path="spec.data.size"
            ))

    # HA disabling
    if old_data.get("highAvailability") and not new_data.get("highAvailability"):
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message="⚠️ Disabling high availability - single point of failure introduced",
            field_path="spec.data.highAvailability"
        ))

    # Backup retention reduction
    old_retention = old_data.get("backupRetention")
    new_retention = new_data.get("backupRetention")
    if old_retention and new_retention and new_retention < old_retention:
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message=f"⚠️ Backup retention reduced from {old_retention} to {new_retention} days",
            field_path="spec.data.backupRetention"
        ))

    return warnings
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
```

---

### Task 5: Implement _check_network_changes()
**File**: `backend/lambda/functions/spec-parser/change_detector.py`
**Action**: MODIFY (add function)

**Implementation**:
```python
def _check_network_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect network configuration changes."""
    warnings = []
    old_net = old_spec.get("spec", {}).get("network", {})
    new_net = new_spec.get("spec", {}).get("network", {})

    # Early return if no network previously
    if not old_net:
        return warnings

    # VPC change (requires complete reconfiguration)
    old_vpc = old_net.get("vpc")
    new_vpc = new_net.get("vpc")
    if old_vpc and new_vpc and old_vpc != new_vpc:
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message="⚠️ VPC change requires complete network reconfiguration",
            field_path="spec.network.vpc"
        ))

    # Public access removal
    if old_net.get("publicAccess") and not new_net.get("publicAccess"):
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message="⚠️ Disabling public access - external connectivity will be lost",
            field_path="spec.network.publicAccess"
        ))

    # Subnet removals
    old_subnets = set(old_net.get("subnets", []))
    new_subnets = set(new_net.get("subnets", []))
    removed_subnets = old_subnets - new_subnets
    if removed_subnets:
        warnings.append(ChangeWarning(
            severity=Severity.WARNING,
            message=f"⚠️ Removing subnets: {', '.join(sorted(removed_subnets))}",
            field_path="spec.network.subnets"
        ))

    return warnings
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
```

---

### Task 6: Implement _check_governance_changes()
**File**: `backend/lambda/functions/spec-parser/change_detector.py`
**Action**: MODIFY (add function)
**Pattern**: Use INFO severity for non-critical changes

**Implementation**:
```python
def _check_governance_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect governance changes (informational)."""
    warnings = []
    old_gov = old_spec.get("spec", {}).get("governance", {})
    new_gov = new_spec.get("spec", {}).get("governance", {})

    # Auto-shutdown enabling
    old_shutdown = old_gov.get("autoShutdown", {})
    new_shutdown = new_gov.get("autoShutdown", {})

    if not old_shutdown.get("enabled") and new_shutdown.get("enabled"):
        hours = new_shutdown.get("afterHours", 24)
        warnings.append(ChangeWarning(
            severity=Severity.INFO,
            message=f"ℹ️ Auto-shutdown enabled: infrastructure will stop after {hours} hours of inactivity",
            field_path="spec.governance.autoShutdown.enabled"
        ))

    # Budget reduction (informational)
    old_budget = old_gov.get("maxMonthlySpend")
    new_budget = new_gov.get("maxMonthlySpend")
    if old_budget and new_budget and new_budget < old_budget:
        warnings.append(ChangeWarning(
            severity=Severity.INFO,
            message=f"ℹ️ Monthly budget reduced from ${old_budget} to ${new_budget}",
            field_path="spec.governance.maxMonthlySpend"
        ))

    return warnings
```

**Validation**:
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
python3 -c "from lambda.functions.spec_parser.change_detector import check_destructive_changes; print('Import OK')"
```

---

### Task 7: Create test_change_detector.py setup
**File**: `backend/tests/test_change_detector.py`
**Action**: CREATE
**Pattern**: Follow test_parser.py structure (lines 1-25) for imports and path setup

**Implementation**:
```python
"""
Unit tests for change_detector module.
Tests detection of destructive changes across all spec categories.
"""

import os
import sys
from pathlib import Path

import pytest

# Add change_detector module to path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "lambda", "functions", "spec-parser"),
)

from change_detector import (
    check_destructive_changes,
    ChangeWarning,
    Severity,
    SIZE_ORDER,
)

# Test fixtures (inline YAML specs)
# Using minimal.yml and full-featured.yml patterns from existing fixtures
```

**Validation**:
```bash
cd backend
black tests/test_change_detector.py
pytest tests/test_change_detector.py::test_import -v
```

---

### Task 8: Add security change tests
**File**: `backend/tests/test_change_detector.py`
**Action**: MODIFY (add tests)
**Pattern**: Follow test_parser.py assertion patterns (lines 42-47)

**Implementation**:
```python
def test_waf_disabling_detected():
    """WAF disabling should generate warning."""
    old_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": True, "mode": "block"},
                "encryption": {"atRest": True, "inTransit": True}
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": True, "inTransit": True}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) >= 1
    waf_warnings = [w for w in warnings if "WAF" in w.message]
    assert len(waf_warnings) == 1
    assert waf_warnings[0].severity == Severity.WARNING
    assert waf_warnings[0].field_path == "spec.security.waf.enabled"


def test_waf_mode_downgrade_detected():
    """WAF mode downgrade from block to monitor should warn."""
    old_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": True, "mode": "block"},
                "encryption": {"atRest": True, "inTransit": True}
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": True, "mode": "monitor"},
                "encryption": {"atRest": True, "inTransit": True}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "block" in warnings[0].message and "monitor" in warnings[0].message
    assert warnings[0].severity == Severity.WARNING


def test_waf_ruleset_reduction_detected():
    """Removing WAF rulesets should generate warning."""
    old_spec = {
        "spec": {
            "security": {
                "waf": {
                    "enabled": True,
                    "mode": "block",
                    "rulesets": ["core-protection", "rate-limiting", "sql-injection"]
                },
                "encryption": {"atRest": True, "inTransit": True}
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {
                    "enabled": True,
                    "mode": "block",
                    "rulesets": ["core-protection"]
                },
                "encryption": {"atRest": True, "inTransit": True}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "rate-limiting" in warnings[0].message
    assert "sql-injection" in warnings[0].message


def test_encryption_disabling_detected():
    """Disabling encryption should generate warnings."""
    old_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": True, "inTransit": True}
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": False, "inTransit": False}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 2
    messages = [w.message for w in warnings]
    assert any("at rest" in m.lower() for m in messages)
    assert any("in transit" in m.lower() for m in messages)
```

**Validation**:
```bash
cd backend
pytest tests/test_change_detector.py::test_waf_disabling_detected -v
pytest tests/test_change_detector.py::test_waf_mode_downgrade_detected -v
pytest tests/test_change_detector.py::test_waf_ruleset_reduction_detected -v
pytest tests/test_change_detector.py::test_encryption_disabling_detected -v
```

---

### Task 9: Add compute change tests
**File**: `backend/tests/test_change_detector.py`
**Action**: MODIFY (add tests)

**Implementation**:
```python
def test_compute_size_downgrade_detected():
    """Compute size reduction should generate warning."""
    old_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "small",
                "scaling": {"min": 2, "max": 10}
            }
        }
    }
    new_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "demo",
                "scaling": {"min": 1, "max": 5}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    size_warnings = [w for w in warnings if "size reduction" in w.message.lower()]
    assert len(size_warnings) == 1
    assert "small" in size_warnings[0].message
    assert "demo" in size_warnings[0].message


def test_compute_same_size_no_warning():
    """Same compute size should not generate warning."""
    old_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "demo",
                "scaling": {"min": 1, "max": 3}
            }
        }
    }
    new_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "demo",
                "scaling": {"min": 1, "max": 3}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 0


def test_compute_scaling_reduction_detected():
    """Scaling min/max reduction should generate warnings."""
    old_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "demo",
                "scaling": {"min": 2, "max": 10}
            }
        }
    }
    new_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "demo",
                "scaling": {"min": 1, "max": 5}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 2  # min and max both reduced
    messages = [w.message for w in warnings]
    assert any("Maximum instance count" in m for m in messages)
    assert any("Minimum instance count" in m for m in messages)
```

**Validation**:
```bash
cd backend
pytest tests/test_change_detector.py::test_compute_size_downgrade_detected -v
pytest tests/test_change_detector.py::test_compute_same_size_no_warning -v
pytest tests/test_change_detector.py::test_compute_scaling_reduction_detected -v
```

---

### Task 10: Add data change tests
**File**: `backend/tests/test_change_detector.py`
**Action**: MODIFY (add tests)

**Implementation**:
```python
def test_data_engine_change_detected():
    """Data engine change should generate CRITICAL warning."""
    old_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "size": "small",
                "highAvailability": False
            }
        }
    }
    new_spec = {
        "spec": {
            "data": {
                "engine": "mysql",
                "size": "small",
                "highAvailability": False
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert warnings[0].severity == Severity.CRITICAL
    assert "🔴" in warnings[0].message
    assert "migration" in warnings[0].message.lower()
    assert "postgres" in warnings[0].message
    assert "mysql" in warnings[0].message


def test_data_engine_removal_detected():
    """Setting engine to 'none' should generate CRITICAL warning."""
    old_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "size": "small"
            }
        }
    }
    new_spec = {
        "spec": {
            "data": {
                "engine": "none"
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert warnings[0].severity == Severity.CRITICAL
    assert "DELETE" in warnings[0].message
    assert "irreversible" in warnings[0].message.lower()


def test_data_ha_disabling_detected():
    """Disabling HA should generate warning."""
    old_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "size": "medium",
                "highAvailability": True
            }
        }
    }
    new_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "size": "medium",
                "highAvailability": False
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "high availability" in warnings[0].message.lower()
    assert "single point of failure" in warnings[0].message.lower()


def test_backup_retention_reduction_detected():
    """Backup retention reduction should generate warning."""
    old_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "backupRetention": 30
            }
        }
    }
    new_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "backupRetention": 7
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "30" in warnings[0].message
    assert "7" in warnings[0].message
    assert "days" in warnings[0].message.lower()
```

**Validation**:
```bash
cd backend
pytest tests/test_change_detector.py -k "test_data" -v
```

---

### Task 11: Add network change tests
**File**: `backend/tests/test_change_detector.py`
**Action**: MODIFY (add tests)

**Implementation**:
```python
def test_vpc_change_detected():
    """VPC change should generate warning."""
    old_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-old123",
                "subnets": ["subnet-a"],
                "securityGroups": ["sg-1"],
                "publicAccess": True
            }
        }
    }
    new_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-new456",
                "subnets": ["subnet-b"],
                "securityGroups": ["sg-2"],
                "publicAccess": True
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    vpc_warnings = [w for w in warnings if "VPC" in w.message]
    assert len(vpc_warnings) == 1
    assert "reconfiguration" in vpc_warnings[0].message.lower()


def test_public_access_removal_detected():
    """Disabling public access should generate warning."""
    old_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-123",
                "subnets": ["subnet-a"],
                "securityGroups": ["sg-1"],
                "publicAccess": True
            }
        }
    }
    new_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-123",
                "subnets": ["subnet-a"],
                "securityGroups": ["sg-1"],
                "publicAccess": False
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "public access" in warnings[0].message.lower()
    assert "connectivity" in warnings[0].message.lower()


def test_subnet_removal_detected():
    """Removing subnets should generate warning."""
    old_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-123",
                "subnets": ["subnet-a", "subnet-b", "subnet-c"],
                "securityGroups": ["sg-1"]
            }
        }
    }
    new_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-123",
                "subnets": ["subnet-a"],
                "securityGroups": ["sg-1"]
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    subnet_warnings = [w for w in warnings if "subnet" in w.message.lower()]
    assert len(subnet_warnings) == 1
    assert "subnet-b" in subnet_warnings[0].message
    assert "subnet-c" in subnet_warnings[0].message
```

**Validation**:
```bash
cd backend
pytest tests/test_change_detector.py -k "test_vpc or test_public or test_subnet" -v
```

---

### Task 12: Add governance and edge case tests
**File**: `backend/tests/test_change_detector.py`
**Action**: MODIFY (add tests)

**Implementation**:
```python
def test_auto_shutdown_enabling_detected():
    """Auto-shutdown enabling should generate INFO message."""
    old_spec = {
        "spec": {
            "governance": {
                "maxMonthlySpend": 10,
                "autoShutdown": {"enabled": False}
            }
        }
    }
    new_spec = {
        "spec": {
            "governance": {
                "maxMonthlySpend": 10,
                "autoShutdown": {"enabled": True, "afterHours": 48}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert warnings[0].severity == Severity.INFO
    assert "ℹ️" in warnings[0].message
    assert "48 hours" in warnings[0].message


def test_budget_reduction_detected():
    """Budget reduction should generate INFO message."""
    old_spec = {
        "spec": {
            "governance": {
                "maxMonthlySpend": 100,
                "autoShutdown": {"enabled": False}
            }
        }
    }
    new_spec = {
        "spec": {
            "governance": {
                "maxMonthlySpend": 50,
                "autoShutdown": {"enabled": False}
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert warnings[0].severity == Severity.INFO
    assert "$100" in warnings[0].message
    assert "$50" in warnings[0].message


# Edge cases
def test_no_warnings_for_identical_specs():
    """Identical specs should return empty warnings list."""
    spec = {
        "spec": {
            "security": {"waf": {"enabled": True}, "encryption": {"atRest": True}},
            "governance": {"maxMonthlySpend": 10, "autoShutdown": {"enabled": False}}
        }
    }

    warnings = check_destructive_changes(spec, spec)

    assert len(warnings) == 0


def test_no_warnings_for_upgrades():
    """Upgrading resources should not generate warnings."""
    old_spec = {
        "spec": {
            "compute": {"tier": "web", "size": "demo", "scaling": {"min": 1, "max": 3}},
            "security": {"waf": {"enabled": False}, "encryption": {"atRest": True}}
        }
    }
    new_spec = {
        "spec": {
            "compute": {"tier": "web", "size": "small", "scaling": {"min": 2, "max": 10}},
            "security": {"waf": {"enabled": True, "mode": "block"}, "encryption": {"atRest": True}}
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 0


def test_missing_section_in_old_spec_no_warning():
    """Adding new sections (compute, data) should not generate warnings."""
    old_spec = {
        "spec": {
            "security": {"waf": {"enabled": False}, "encryption": {"atRest": True}},
            "governance": {"maxMonthlySpend": 10, "autoShutdown": {"enabled": False}}
        }
    }
    new_spec = {
        "spec": {
            "compute": {"tier": "web", "size": "demo", "scaling": {"min": 1, "max": 3}},
            "data": {"engine": "postgres", "size": "demo"},
            "security": {"waf": {"enabled": False}, "encryption": {"atRest": True}},
            "governance": {"maxMonthlySpend": 10, "autoShutdown": {"enabled": False}}
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    # Should not warn about adding compute/data
    assert len(warnings) == 0
```

**Validation**:
```bash
cd backend
pytest tests/test_change_detector.py -k "test_auto_shutdown or test_budget or test_no_warnings or test_missing" -v
```

---

### Task 13: Run full test suite with coverage
**File**: N/A (validation step)
**Action**: RUN TESTS
**Pattern**: Follow spec/stack.md test commands

**Implementation**:
```bash
cd backend

# Run all change_detector tests
pytest tests/test_change_detector.py -v

# Run with coverage
pytest tests/test_change_detector.py -v \
  --cov=lambda/functions/spec-parser/change_detector \
  --cov-report=term-missing \
  --cov-fail-under=80

# Verify no regressions in existing tests
pytest tests/ -v
```

**Expected Output**:
- 18 tests passing (4 security + 3 compute + 4 data + 3 network + 2 governance + 2 edge cases)
- Coverage >= 80% on change_detector.py
- All existing tests still passing

**Validation**:
- All tests green
- Coverage threshold met
- No mypy errors
- Black formatting clean

---

### Task 14: Final validation gates
**File**: N/A (validation step)
**Action**: RUN ALL GATES
**Pattern**: spec/stack.md commands

**Implementation**:
```bash
cd backend

# Gate 1: Lint & Format
black --check lambda/functions/spec-parser/change_detector.py
black --check tests/test_change_detector.py

# Gate 2: Type Safety
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports

# Gate 3: Full Test Suite
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=80

# Verify module importable
python3 -c "
from lambda.functions.spec_parser.change_detector import check_destructive_changes, ChangeWarning, Severity
print('✅ Module imports successfully')
print(f'✅ SIZE_ORDER defined: {len(Severity)} severity levels')
"
```

**Expected Output**:
- ✅ Black formatting: All checks passed
- ✅ Mypy: Success: no issues found
- ✅ Pytest: 18/18 tests passed, coverage 84%+
- ✅ Import check: Module loads successfully

**Validation**:
All gates must pass before proceeding to commit.

---

## Risk Assessment

### Risk: Size ordering comparison might not match actual infrastructure sizes
**Mitigation**: SIZE_ORDER is hardcoded based on JSON Schema enum order. If AWS instance sizes change, this is a simple dict update. Alternative: Could validate against schema enum order in tests.

### Risk: Asymmetric logic (adding vs removing) could miss edge cases
**Mitigation**: Comprehensive edge case tests cover missing sections in old_spec. Phase 3.3 integration will reveal any gaps through real-world usage.

### Risk: Warning messages might not be clear enough for users
**Mitigation**: Each message follows pattern: emoji + action + consequence. Test assertions verify message content includes relevant field names and values.

### Risk: Future spec schema changes might break detection logic
**Mitigation**: Detection logic mirrors schema structure (spec.security.waf.*). Schema changes will require corresponding updates here. Unit tests will catch breakage immediately.

## Integration Points

**Phase 3.3 (Spec Applier Lambda)**:
```python
# How spec-applier will use this module
from spec_parser.change_detector import check_destructive_changes

warnings = check_destructive_changes(old_spec, new_spec)

# Group by severity for PR description
critical = [w for w in warnings if w.severity == Severity.CRITICAL]
warnings = [w for w in warnings if w.severity == Severity.WARNING]
info = [w for w in warnings if w.severity == Severity.INFO]

# Build PR body with warnings section
pr_body = build_pr_description(critical, warnings, info)
```

**No changes required in**:
- `parser.py` (change_detector is standalone)
- `handler.py` (integration happens in Phase 3.3)
- `exceptions.py` (using dataclass, not exception-based)

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY code change, run commands from `spec/stack.md`:

### Gate 1: Lint & Format
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py
black tests/test_change_detector.py
```
**Pass criteria**: No changes made by black (or auto-formatted successfully)

### Gate 2: Type Safety
```bash
cd backend
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
```
**Pass criteria**: "Success: no issues found"

### Gate 3: Unit Tests
```bash
cd backend
pytest tests/test_change_detector.py -v --cov=lambda/functions/spec-parser/change_detector --cov-report=term-missing
```
**Pass criteria**: All tests pass, coverage >= 80%

### Gate 4: No Regressions
```bash
cd backend
pytest tests/ -v
```
**Pass criteria**: All existing tests still pass (test_parser.py, test_security_wrapper.py, test_smoke.py)

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

### After Each Task (1-6, 8-12):
```bash
cd backend
black lambda/functions/spec-parser/change_detector.py tests/test_change_detector.py
mypy lambda/functions/spec-parser/change_detector.py --ignore-missing-imports
pytest tests/test_change_detector.py -v -k "test_<relevant>"
```

### After Task 13 (Full Test Suite):
```bash
cd backend
pytest tests/test_change_detector.py -v --cov=lambda/functions/spec-parser/change_detector --cov-report=term-missing --cov-fail-under=80
```

### Final Validation (Task 14):
```bash
cd backend
black --check lambda/ tests/
mypy lambda/functions/spec-parser/ --ignore-missing-imports
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=80
```

**Success Criteria**:
- ✅ All 18 tests passing
- ✅ Coverage >= 80% on change_detector.py
- ✅ No type errors
- ✅ Black formatting clean
- ✅ No regressions in existing tests

## Plan Quality Assessment

**Complexity Score**: 4/10 (MEDIUM-LOW)
- File impact: 2 files created, 0 modified (1pt)
- Subsystem coupling: 1 subsystem (0pts)
- Task count: 14 subtasks (3pts)
- Dependencies: 0 new packages (0pts)
- Pattern novelty: Existing patterns (0pts)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from detailed spec
✅ Similar patterns found in codebase at:
   - `backend/lambda/functions/spec-parser/parser.py` (module structure)
   - `backend/tests/test_parser.py` (test patterns)
   - `backend/lambda/functions/spec-parser/exceptions.py` (error handling)
✅ All clarifying questions answered
✅ Existing test patterns to follow in test_parser.py
✅ No external dependencies (Python stdlib only)
✅ Self-contained module (no integration complexity)
✅ Comprehensive test fixtures available

**Assessment**: High confidence implementation. Module is well-defined, self-contained, and follows existing codebase patterns. The 14 subtasks are small, focused, and independently validatable. Test-driven approach with 18 test cases provides strong validation.

**Estimated one-pass success probability**: 85%

**Reasoning**:
- Clear spec with detailed examples reduces ambiguity
- Existing parser.py provides strong pattern reference
- No external API calls or complex dependencies
- Comprehensive test strategy (18 tests) catches issues early
- Only risk is minor edge cases in nested dict access (mitigated by asymmetric logic design)
- Phase 3.3 integration is deferred, removing integration complexity from this phase
