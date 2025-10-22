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


### Security Change Tests ###


def test_waf_disabling_detected():
    """WAF disabling should generate warning."""
    old_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": True, "mode": "block"},
                "encryption": {"atRest": True, "inTransit": True},
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": True, "inTransit": True},
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
                "encryption": {"atRest": True, "inTransit": True},
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": True, "mode": "monitor"},
                "encryption": {"atRest": True, "inTransit": True},
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
                    "rulesets": [
                        "core-protection",
                        "rate-limiting",
                        "sql-injection",
                    ],
                },
                "encryption": {"atRest": True, "inTransit": True},
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {
                    "enabled": True,
                    "mode": "block",
                    "rulesets": ["core-protection"],
                },
                "encryption": {"atRest": True, "inTransit": True},
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
                "encryption": {"atRest": True, "inTransit": True},
            }
        }
    }
    new_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": False, "inTransit": False},
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 2
    messages = [w.message for w in warnings]
    assert any("at rest" in m.lower() for m in messages)
    assert any("in transit" in m.lower() for m in messages)


### Compute Change Tests ###


def test_compute_size_downgrade_detected():
    """Compute size reduction should generate warning."""
    old_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "small",
                "scaling": {"min": 2, "max": 10},
            }
        }
    }
    new_spec = {
        "spec": {
            "compute": {"tier": "web", "size": "demo", "scaling": {"min": 1, "max": 5}}
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
            "compute": {"tier": "web", "size": "demo", "scaling": {"min": 1, "max": 3}}
        }
    }
    new_spec = {
        "spec": {
            "compute": {"tier": "web", "size": "demo", "scaling": {"min": 1, "max": 3}}
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 0


def test_compute_scaling_reduction_detected():
    """Scaling min/max reduction should generate warnings."""
    old_spec = {
        "spec": {
            "compute": {"tier": "web", "size": "demo", "scaling": {"min": 2, "max": 10}}
        }
    }
    new_spec = {
        "spec": {
            "compute": {"tier": "web", "size": "demo", "scaling": {"min": 1, "max": 5}}
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 2  # min and max both reduced
    messages = [w.message for w in warnings]
    assert any("Maximum instance count" in m for m in messages)
    assert any("Minimum instance count" in m for m in messages)


### Data Change Tests ###


def test_data_engine_change_detected():
    """Data engine change should generate CRITICAL warning."""
    old_spec = {
        "spec": {
            "data": {"engine": "postgres", "size": "small", "highAvailability": False}
        }
    }
    new_spec = {
        "spec": {
            "data": {"engine": "mysql", "size": "small", "highAvailability": False}
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
    old_spec = {"spec": {"data": {"engine": "postgres", "size": "small"}}}
    new_spec = {"spec": {"data": {"engine": "none"}}}

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert warnings[0].severity == Severity.CRITICAL
    assert "DELETE" in warnings[0].message
    assert "irreversible" in warnings[0].message.lower()


def test_data_size_downgrade_detected():
    """Database size reduction should generate warning."""
    old_spec = {"spec": {"data": {"engine": "postgres", "size": "medium"}}}
    new_spec = {"spec": {"data": {"engine": "postgres", "size": "small"}}}

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "size reduction" in warnings[0].message.lower()
    assert "medium" in warnings[0].message
    assert "small" in warnings[0].message


def test_data_ha_disabling_detected():
    """Disabling HA should generate warning."""
    old_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "size": "medium",
                "highAvailability": True,
            }
        }
    }
    new_spec = {
        "spec": {
            "data": {
                "engine": "postgres",
                "size": "medium",
                "highAvailability": False,
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "high availability" in warnings[0].message.lower()
    assert "single point of failure" in warnings[0].message.lower()


def test_backup_retention_reduction_detected():
    """Backup retention reduction should generate warning."""
    old_spec = {"spec": {"data": {"engine": "postgres", "backupRetention": 30}}}
    new_spec = {"spec": {"data": {"engine": "postgres", "backupRetention": 7}}}

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert "30" in warnings[0].message
    assert "7" in warnings[0].message
    assert "days" in warnings[0].message.lower()


### Network Change Tests ###


def test_vpc_change_detected():
    """VPC change should generate warning."""
    old_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-old123",
                "subnets": ["subnet-a"],
                "securityGroups": ["sg-1"],
                "publicAccess": True,
            }
        }
    }
    new_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-new456",
                "subnets": ["subnet-b"],
                "securityGroups": ["sg-2"],
                "publicAccess": True,
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
                "publicAccess": True,
            }
        }
    }
    new_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-123",
                "subnets": ["subnet-a"],
                "securityGroups": ["sg-1"],
                "publicAccess": False,
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
                "securityGroups": ["sg-1"],
            }
        }
    }
    new_spec = {
        "spec": {
            "network": {
                "vpc": "vpc-123",
                "subnets": ["subnet-a"],
                "securityGroups": ["sg-1"],
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    subnet_warnings = [w for w in warnings if "subnet" in w.message.lower()]
    assert len(subnet_warnings) == 1
    assert "subnet-b" in subnet_warnings[0].message
    assert "subnet-c" in subnet_warnings[0].message


### Governance & Edge Case Tests ###


def test_auto_shutdown_enabling_detected():
    """Auto-shutdown enabling should generate INFO message."""
    old_spec = {
        "spec": {
            "governance": {
                "maxMonthlySpend": 10,
                "autoShutdown": {"enabled": False},
            }
        }
    }
    new_spec = {
        "spec": {
            "governance": {
                "maxMonthlySpend": 10,
                "autoShutdown": {"enabled": True, "afterHours": 48},
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
                "autoShutdown": {"enabled": False},
            }
        }
    }
    new_spec = {
        "spec": {
            "governance": {
                "maxMonthlySpend": 50,
                "autoShutdown": {"enabled": False},
            }
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 1
    assert warnings[0].severity == Severity.INFO
    assert "$100" in warnings[0].message
    assert "$50" in warnings[0].message


def test_no_warnings_for_identical_specs():
    """Identical specs should return empty warnings list."""
    spec = {
        "spec": {
            "security": {
                "waf": {"enabled": True},
                "encryption": {"atRest": True},
            },
            "governance": {
                "maxMonthlySpend": 10,
                "autoShutdown": {"enabled": False},
            },
        }
    }

    warnings = check_destructive_changes(spec, spec)

    assert len(warnings) == 0


def test_no_warnings_for_upgrades():
    """Upgrading resources should not generate warnings."""
    old_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "demo",
                "scaling": {"min": 1, "max": 3},
            },
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": True},
            },
        }
    }
    new_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "small",
                "scaling": {"min": 2, "max": 10},
            },
            "security": {
                "waf": {"enabled": True, "mode": "block"},
                "encryption": {"atRest": True},
            },
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    assert len(warnings) == 0


def test_missing_section_in_old_spec_no_warning():
    """Adding new sections (compute, data) should not generate warnings."""
    old_spec = {
        "spec": {
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": True},
            },
            "governance": {
                "maxMonthlySpend": 10,
                "autoShutdown": {"enabled": False},
            },
        }
    }
    new_spec = {
        "spec": {
            "compute": {
                "tier": "web",
                "size": "demo",
                "scaling": {"min": 1, "max": 3},
            },
            "data": {"engine": "postgres", "size": "demo"},
            "security": {
                "waf": {"enabled": False},
                "encryption": {"atRest": True},
            },
            "governance": {
                "maxMonthlySpend": 10,
                "autoShutdown": {"enabled": False},
            },
        }
    }

    warnings = check_destructive_changes(old_spec, new_spec)

    # Should not warn about adding compute/data
    assert len(warnings) == 0
