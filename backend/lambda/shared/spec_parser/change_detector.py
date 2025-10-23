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


def _check_security_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect security downgrades."""
    warnings: List[ChangeWarning] = []
    old_sec = old_spec.get("spec", {}).get("security", {})
    new_sec = new_spec.get("spec", {}).get("security", {})

    # WAF disabling
    old_waf = old_sec.get("waf", {})
    new_waf = new_sec.get("waf", {})

    if old_waf.get("enabled") and not new_waf.get("enabled"):
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message="⚠️ Disabling WAF will remove security protection",
                field_path="spec.security.waf.enabled",
            )
        )

    # WAF mode downgrade
    if old_waf.get("mode") == "block" and new_waf.get("mode") == "monitor":
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message="⚠️ WAF mode downgrade from 'block' to 'monitor' - attacks will be logged but not blocked",
                field_path="spec.security.waf.mode",
            )
        )

    # Ruleset reduction
    old_rules = set(old_waf.get("rulesets", []))
    new_rules = set(new_waf.get("rulesets", []))
    removed_rules = old_rules - new_rules
    if removed_rules:
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message=f"⚠️ Removing WAF rulesets: {', '.join(sorted(removed_rules))}",
                field_path="spec.security.waf.rulesets",
            )
        )

    # Encryption disabling
    old_enc = old_sec.get("encryption", {})
    new_enc = new_sec.get("encryption", {})

    if old_enc.get("atRest", True) and not new_enc.get("atRest", True):
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message="⚠️ Disabling encryption at rest",
                field_path="spec.security.encryption.atRest",
            )
        )

    if old_enc.get("inTransit", True) and not new_enc.get("inTransit", True):
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message="⚠️ Disabling encryption in transit",
                field_path="spec.security.encryption.inTransit",
            )
        )

    return warnings


def _check_compute_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect compute downsizing."""
    warnings: List[ChangeWarning] = []
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
            warnings.append(
                ChangeWarning(
                    severity=Severity.WARNING,
                    message=f"⚠️ Compute size reduction from '{old_size}' to '{new_size}' may cause downtime",
                    field_path="spec.compute.size",
                )
            )

    # Scaling reduction
    old_scaling = old_comp.get("scaling", {})
    new_scaling = new_comp.get("scaling", {})

    old_max = old_scaling.get("max")
    new_max = new_scaling.get("max")
    if old_max and new_max and new_max < old_max:
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message=f"⚠️ Maximum instance count reduced from {old_max} to {new_max}",
                field_path="spec.compute.scaling.max",
            )
        )

    old_min = old_scaling.get("min")
    new_min = new_scaling.get("min")
    if old_min and new_min and new_min < old_min:
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message=f"⚠️ Minimum instance count reduced from {old_min} to {new_min}",
                field_path="spec.compute.scaling.min",
            )
        )

    return warnings


def _check_data_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect data layer changes (high risk)."""
    warnings: List[ChangeWarning] = []
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
            warnings.append(
                ChangeWarning(
                    severity=Severity.CRITICAL,
                    message="🔴 Setting data.engine to 'none' will DELETE all data (irreversible!)",
                    field_path="spec.data.engine",
                )
            )
        elif new_engine and new_engine != old_engine:
            warnings.append(
                ChangeWarning(
                    severity=Severity.CRITICAL,
                    message=f"🔴 Changing data.engine from '{old_engine}' to '{new_engine}' requires manual data migration",
                    field_path="spec.data.engine",
                )
            )

    # Size downgrade
    old_size = old_data.get("size")
    new_size = new_data.get("size")
    if old_size and new_size:
        old_order = SIZE_ORDER.get(old_size, 0)
        new_order = SIZE_ORDER.get(new_size, 0)
        if new_order < old_order:
            warnings.append(
                ChangeWarning(
                    severity=Severity.WARNING,
                    message=f"⚠️ Database size reduction from '{old_size}' to '{new_size}' may require data cleanup",
                    field_path="spec.data.size",
                )
            )

    # HA disabling
    if old_data.get("highAvailability") and not new_data.get("highAvailability"):
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message="⚠️ Disabling high availability - single point of failure introduced",
                field_path="spec.data.highAvailability",
            )
        )

    # Backup retention reduction
    old_retention = old_data.get("backupRetention")
    new_retention = new_data.get("backupRetention")
    if old_retention and new_retention and new_retention < old_retention:
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message=f"⚠️ Backup retention reduced from {old_retention} to {new_retention} days",
                field_path="spec.data.backupRetention",
            )
        )

    return warnings


def _check_network_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect network configuration changes."""
    warnings: List[ChangeWarning] = []
    old_net = old_spec.get("spec", {}).get("network", {})
    new_net = new_spec.get("spec", {}).get("network", {})

    # Early return if no network previously
    if not old_net:
        return warnings

    # VPC change (requires complete reconfiguration)
    old_vpc = old_net.get("vpc")
    new_vpc = new_net.get("vpc")
    if old_vpc and new_vpc and old_vpc != new_vpc:
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message="⚠️ VPC change requires complete network reconfiguration",
                field_path="spec.network.vpc",
            )
        )

    # Public access removal
    if old_net.get("publicAccess") and not new_net.get("publicAccess"):
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message="⚠️ Disabling public access - external connectivity will be lost",
                field_path="spec.network.publicAccess",
            )
        )

    # Subnet removals
    old_subnets = set(old_net.get("subnets", []))
    new_subnets = set(new_net.get("subnets", []))
    removed_subnets = old_subnets - new_subnets
    if removed_subnets:
        warnings.append(
            ChangeWarning(
                severity=Severity.WARNING,
                message=f"⚠️ Removing subnets: {', '.join(sorted(removed_subnets))}",
                field_path="spec.network.subnets",
            )
        )

    return warnings


def _check_governance_changes(old_spec: dict, new_spec: dict) -> List[ChangeWarning]:
    """Detect governance changes (informational)."""
    warnings: List[ChangeWarning] = []
    old_gov = old_spec.get("spec", {}).get("governance", {})
    new_gov = new_spec.get("spec", {}).get("governance", {})

    # Auto-shutdown enabling
    old_shutdown = old_gov.get("autoShutdown", {})
    new_shutdown = new_gov.get("autoShutdown", {})

    if not old_shutdown.get("enabled") and new_shutdown.get("enabled"):
        hours = new_shutdown.get("afterHours", 24)
        warnings.append(
            ChangeWarning(
                severity=Severity.INFO,
                message=f"ℹ️ Auto-shutdown enabled: infrastructure will stop after {hours} hours of inactivity",
                field_path="spec.governance.autoShutdown.enabled",
            )
        )

    # Budget reduction (informational)
    old_budget = old_gov.get("maxMonthlySpend")
    new_budget = new_gov.get("maxMonthlySpend")
    if old_budget and new_budget and new_budget < old_budget:
        warnings.append(
            ChangeWarning(
                severity=Severity.INFO,
                message=f"ℹ️ Monthly budget reduced from ${old_budget} to ${new_budget}",
                field_path="spec.governance.maxMonthlySpend",
            )
        )

    return warnings
