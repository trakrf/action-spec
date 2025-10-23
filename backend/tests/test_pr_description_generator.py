"""Tests for PR description generator (Phase 3.3.3)"""

import os
import sys

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "shared"))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "lambda", "functions", "spec-applier"
    ),
)

from handler import generate_pr_description
from spec_parser.change_detector import ChangeWarning, Severity


def test_generate_pr_description_with_warnings():
    """Test PR description includes warnings from change_detector"""
    old_spec = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    new_spec = {"metadata": {"name": "test"}, "kind": "WebApplication"}

    warnings = [
        ChangeWarning(
            Severity.WARNING, "⚠️ WARNING: WAF disabled", "spec.security.waf.enabled"
        ),
        ChangeWarning(
            Severity.CRITICAL, "🔴 CRITICAL: Engine changed", "spec.data.engine"
        ),
    ]

    description = generate_pr_description(old_spec, new_spec, warnings)

    assert "⚠️ WARNING: WAF disabled" in description
    assert "🔴 CRITICAL: Engine changed" in description
    assert "Review Checklist" in description
    assert "ActionSpec Update" in description


def test_generate_pr_description_no_warnings():
    """Test PR description when no warnings (safe changes)"""
    old_spec = {"metadata": {"name": "test"}, "kind": "StaticSite"}
    new_spec = {"metadata": {"name": "test"}, "kind": "StaticSite"}

    description = generate_pr_description(old_spec, new_spec, [])

    assert "No warnings - changes appear safe ✅" in description
    assert "Review Checklist" in description


def test_generate_pr_description_includes_spec_metadata():
    """Test PR description includes spec name and kind"""
    old_spec = {"metadata": {"name": "my-app"}, "kind": "APIService"}
    new_spec = {"metadata": {"name": "my-app"}, "kind": "APIService"}

    description = generate_pr_description(old_spec, new_spec, [])

    assert "`my-app`" in description
    assert "`APIService`" in description


def test_generate_pr_description_with_all_severity_levels():
    """Test PR description includes correct emojis for all severity levels"""
    old_spec = {"metadata": {"name": "test"}, "kind": "WebApplication"}
    new_spec = {"metadata": {"name": "test"}, "kind": "WebApplication"}

    warnings = [
        ChangeWarning(Severity.INFO, "Info message", "spec.info"),
        ChangeWarning(Severity.WARNING, "Warning message", "spec.warning"),
        ChangeWarning(Severity.CRITICAL, "Critical message", "spec.critical"),
    ]

    description = generate_pr_description(old_spec, new_spec, warnings)

    # Check emojis are present for each severity
    assert "ℹ️" in description  # INFO emoji
    assert "⚠️" in description  # WARNING emoji
    assert "🔴" in description  # CRITICAL emoji
    assert "INFO: Info message" in description
    assert "WARNING: Warning message" in description
    assert "CRITICAL: Critical message" in description
