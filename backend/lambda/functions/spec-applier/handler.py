"""
Spec Applier Lambda Function
Phase 3.3.3: Create GitHub PRs with spec changes and destructive change warnings
"""

import json
import os
import sys
import time
import logging

# Add shared layer to path (matches Phase 3.1 pattern)
sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from github_client import (
    create_branch,
    commit_file_change,
    create_pull_request,
    add_pr_labels,
    fetch_spec_file,
    GitHubError,
    BranchExistsError,
    PullRequestExistsError,
)
from spec_parser.change_detector import check_destructive_changes, Severity
from spec_parser.parser import SpecParser
from spec_parser.exceptions import ValidationError, ParseError
from security_wrapper import secure_handler


def parse_spec(yaml_content: str) -> dict:
    """
    Parse and validate spec YAML.

    Args:
        yaml_content: YAML string

    Returns:
        Parsed and validated spec dict

    Raises:
        ValidationError: If spec is invalid
        ParseError: If YAML parsing fails
    """
    parser = SpecParser()
    is_valid, spec, errors = parser.parse_and_validate(yaml_content)

    if not is_valid:
        raise ValidationError("; ".join(errors))

    return spec


logger = logging.getLogger()
logger.setLevel(logging.INFO)


@secure_handler
def lambda_handler(event, context):
    """
    POST /spec/apply

    Creates GitHub PR with spec changes and destructive change warnings.

    Request Body:
    {
      "repo": "trakrf/action-spec",
      "spec_path": "specs/examples/secure-web-waf.spec.yml",
      "new_spec_yaml": "apiVersion: actionspec/v1\n...",
      "commit_message": "Enable WAF protection"
    }

    Response (Success):
    {
      "success": true,
      "pr_url": "https://github.com/trakrf/action-spec/pull/123",
      "pr_number": 123,
      "branch_name": "action-spec-update-1234567890",
      "warnings": [
        {
          "severity": "warning",
          "message": "⚠️ WARNING: Disabling WAF will remove security protection",
          "field_path": "spec.security.waf.enabled"
        }
      ]
    }

    Response (Validation Error):
    {
      "success": false,
      "error": "Validation failed",
      "details": "..."
    }
    """
    try:
        # 1. Parse request body
        body = json.loads(event["body"])
        repo_name = body["repo"]
        spec_path = body["spec_path"]
        new_spec_yaml = body["new_spec_yaml"]
        commit_message = body.get("commit_message", "Update ActionSpec configuration")

        logger.info(f"Processing spec update for {repo_name}:{spec_path}")

        # 2. Validate new spec (will raise ValidationError if invalid)
        try:
            new_spec = parse_spec(new_spec_yaml)
        except (ValidationError, ParseError) as e:
            logger.warning(f"Spec validation failed: {e}")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"success": False, "error": "Validation failed", "details": str(e)}
                ),
            }

        # 3. Fetch old spec from GitHub
        try:
            old_spec_yaml = fetch_spec_file(repo_name, spec_path)
            old_spec = parse_spec(old_spec_yaml)
        except FileNotFoundError as e:
            logger.error(f"Old spec not found: {e}")
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {
                        "success": False,
                        "error": "Spec file not found",
                        "details": f"File '{spec_path}' not found in {repo_name}",
                    }
                ),
            }

        # 4. Run change detection (KEY INTEGRATION with Phase 3.2b!)
        warnings = check_destructive_changes(old_spec, new_spec)
        logger.info(f"Change detection found {len(warnings)} warning(s)")

        # 5. Create feature branch with timestamp for uniqueness
        timestamp = int(time.time())
        branch_name = f"action-spec-update-{timestamp}"

        try:
            branch_sha = create_branch(repo_name, branch_name, base_ref="main")
            logger.info(f"Created branch {branch_name} (SHA: {branch_sha})")
        except BranchExistsError:
            # Retry ONCE with random suffix if timestamp collision
            import random

            suffix = random.randint(1000, 9999)
            branch_name = f"action-spec-update-{timestamp}-{suffix}"
            branch_sha = create_branch(repo_name, branch_name, base_ref="main")
            logger.info(
                f"Created branch {branch_name} with random suffix (SHA: {branch_sha})"
            )

        # 6. Commit spec changes to branch
        commit_sha = commit_file_change(
            repo_name, branch_name, spec_path, new_spec_yaml, commit_message
        )
        logger.info(f"Committed changes (SHA: {commit_sha})")

        # 7. Generate PR description with warnings
        pr_body = generate_pr_description(old_spec, new_spec, warnings)
        pr_title = f"ActionSpec Update: {commit_message}"

        # 8. Create pull request
        try:
            pr_info = create_pull_request(
                repo_name,
                pr_title,
                pr_body,
                head_branch=branch_name,
                base_branch="main",
            )
            logger.info(f"Created PR #{pr_info['number']}: {pr_info['url']}")
        except PullRequestExistsError:
            # PR already exists for this branch (edge case)
            logger.warning(f"PR already exists for branch {branch_name}")
            return {
                "statusCode": 409,
                "body": json.dumps(
                    {
                        "success": False,
                        "error": "Pull request already exists",
                        "details": f"A PR already exists for branch '{branch_name}'",
                    }
                ),
            }

        # 9. Add labels for filtering and automation (non-critical)
        try:
            add_pr_labels(
                repo_name, pr_info["number"], ["infrastructure-change", "automated"]
            )
            logger.info(f"Added labels to PR #{pr_info['number']}")
        except Exception as e:
            # Label addition is non-critical - log but don't fail
            logger.warning(f"Failed to add labels: {e}")

        # 10. Return response with PR URL and warnings
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": True,
                    "pr_url": pr_info["url"],
                    "pr_number": pr_info["number"],
                    "branch_name": branch_name,
                    "warnings": [
                        {
                            "severity": w.severity.value,
                            "message": w.message,
                            "field_path": w.field_path,
                        }
                        for w in warnings
                    ],
                }
            ),
        }

    except GitHubError as e:
        logger.error(f"GitHub error: {e}")
        return {
            "statusCode": 502,
            "body": json.dumps(
                {
                    "success": False,
                    "error": "GitHub API error",
                    "details": str(e),
                }
            ),
        }
    except KeyError as e:
        logger.error(f"Missing required field in request: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "success": False,
                    "error": "Missing required field",
                    "details": f"Required field {e} not found in request body",
                }
            ),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "success": False,
                    "error": "Internal server error",
                    "details": str(e),
                }
            ),
        }


def _severity_emoji(severity) -> str:
    """Map Severity enum to emoji indicator"""
    emoji_map = {
        Severity.INFO: "ℹ️",
        Severity.WARNING: "⚠️",
        Severity.CRITICAL: "🔴",
    }
    return emoji_map.get(severity, "•")


def generate_pr_description(old_spec: dict, new_spec: dict, warnings: list) -> str:
    """
    Generate formatted PR description with warnings from change_detector.

    Args:
        old_spec: Previous spec dict
        new_spec: Updated spec dict
        warnings: List of ChangeWarning objects from check_destructive_changes()

    Returns:
        Markdown-formatted PR description
    """
    # Build warnings section
    if warnings:
        warnings_md = "\n".join(
            [
                f"{_severity_emoji(w.severity)} {w.severity.value.upper()}: {w.message}"
                for w in warnings
            ]
        )
    else:
        warnings_md = "No warnings - changes appear safe ✅"

    # Extract spec metadata (use 'kind' not 'spec.type')
    spec_kind = new_spec.get("kind", "unknown")
    spec_name = new_spec.get("metadata", {}).get("name", "unnamed")

    # Build template
    template = f"""## ActionSpec Update

**Spec**: `{spec_name}` (kind: `{spec_kind}`)

### Warnings
{warnings_md}

### Review Checklist
- [ ] Reviewed all warnings above
- [ ] Confirmed changes are intentional
- [ ] Tested in staging environment (if applicable)

---
🤖 Automated by [ActionSpec](https://github.com/trakrf/action-spec)
"""

    return template
