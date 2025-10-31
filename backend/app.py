"""
Spec Editor Flask App - Demo Phase D4A
Read-only UI for viewing infrastructure pod specifications.
"""

from flask import Flask, render_template, jsonify, abort, request, redirect
from github import Github
from github.GithubException import (
    BadCredentialsException,
    RateLimitExceededException,
    GithubException,
)
import yaml
import os
import sys
import time
import logging
import re
from github_helpers import get_github_client, check_repo_access

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__, static_folder="static", static_url_path="")
# Flask secret key for sessions (CSRF protection during OAuth)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
if not os.environ.get("FLASK_SECRET_KEY"):
    logger.warning(
        "FLASK_SECRET_KEY not set - using random key (sessions will not persist across restarts)"
    )

# Configuration from environment
GH_TOKEN = os.environ.get("GH_TOKEN")
GH_REPO = os.environ.get("GH_REPO", "trakrf/action-spec")
SPECS_PATH = os.environ.get("SPECS_PATH", "infra")
WORKFLOW_BRANCH = os.environ.get("WORKFLOW_BRANCH", "main")

# GH_TOKEN is now optional (fallback for operations without user context)
if not GH_TOKEN:
    logger.warning(
        "GH_TOKEN not set - application will require user authentication for all GitHub operations"
    )
    logger.warning(
        "For local development, set GH_TOKEN in .env.local, or log in via /auth/login"
    )

logger.info(f"Initializing Spec Editor")
logger.info(f"GitHub Repo: {GH_REPO}")
logger.info(f"Specs Path: {SPECS_PATH}")
logger.info(f"Workflow Branch: {WORKFLOW_BRANCH}")

# Initialize GitHub client (with GH_TOKEN if available, for startup checks)
github = None
repo = None

if GH_TOKEN:
    try:
        github = Github(GH_TOKEN)
        repo = github.get_repo(GH_REPO)
        # Test connectivity
        repo.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)
        logger.info(
            f"✓ Successfully connected to GitHub repo: {GH_REPO} (branch: {WORKFLOW_BRANCH}) using GH_TOKEN"
        )
    except BadCredentialsException:
        logger.error("GitHub authentication failed: Invalid or expired GH_TOKEN")
        logger.error("Check that GH_TOKEN has 'repo' scope")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        logger.error(f"Repository: {GH_REPO}, Path: {SPECS_PATH}")
        sys.exit(1)
else:
    logger.info(
        "Starting without GH_TOKEN - user authentication required for GitHub operations"
    )

# Simple cache with 30-second TTL (demo usage has plenty of API quota)
_cache = {}
CACHE_TTL = 30  # 30 seconds


def get_cached(key):
    """Get cached value if not expired"""
    if key in _cache:
        content, timestamp = _cache[key]
        age = time.time() - timestamp
        if age < CACHE_TTL:
            logger.debug(f"Cache hit: {key} (age: {age:.1f}s)")
            return content
        else:
            logger.debug(f"Cache expired: {key} (age: {age:.1f}s)")
            del _cache[key]
    return None


def set_cached(key, content):
    """Store value in cache with current timestamp"""
    _cache[key] = (content, time.time())
    logger.debug(f"Cached: {key}")


def validate_path_component(value, param_name):
    """
    Validate URL path components to prevent path traversal and injection.

    Args:
        value: The path component to validate (customer or env)
        param_name: Name for error messages ("customer" or "environment")

    Returns:
        str: The validated value

    Raises:
        ValueError: If validation fails
    """
    if not value or len(value) > 50:
        raise ValueError(f"{param_name} must be 1-50 characters")

    # Alphanumeric, hyphen, underscore only
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise ValueError(
            f"{param_name} contains invalid characters (use a-z, A-Z, 0-9, -, _ only)"
        )

    # Prevent path traversal
    if ".." in value or "/" in value or "\\" in value:
        logger.warning(f"Path traversal attempt detected: {param_name}={value}")
        raise ValueError(f"{param_name} contains path traversal attempt")

    return value


def validate_instance_name(value):
    """
    Validate instance_name (stricter than customer/env).

    Must be:
    - Lowercase letters, numbers, hyphens only
    - 1-30 characters
    - Cannot start or end with hyphen

    Args:
        value: The instance name to validate

    Returns:
        str: The validated value

    Raises:
        ValueError: If validation fails
    """
    if not value or len(value) > 30:
        raise ValueError("instance_name must be 1-30 characters")

    if not re.match(r"^[a-z0-9-]+$", value):
        raise ValueError(
            "instance_name must be lowercase letters, numbers, and hyphens only (no uppercase, no underscores, no spaces)"
        )

    if value.startswith("-") or value.endswith("-"):
        raise ValueError("instance_name cannot start or end with hyphen")

    return value


def generate_spec_yaml(customer, env, instance_name, waf_enabled):
    """
    Generate spec.yml content from form inputs.

    Args:
        customer: Customer name (validated)
        env: Environment name (validated)
        instance_name: EC2 instance name (validated)
        waf_enabled: Boolean - whether WAF is enabled

    Returns:
        str: YAML content for spec.yml
    """
    spec = {
        "metadata": {"customer": customer, "environment": env, "version": "1.0"},
        "spec": {
            "compute": {"instance_name": instance_name, "instance_type": "t4g.nano"},
            "security": {"waf": {"enabled": waf_enabled}},
        },
    }

    return yaml.dump(spec, default_flow_style=False, sort_keys=False)


def fetch_spec(customer, env):
    """
    Fetch and parse spec.yml from GitHub for a specific pod.
    Uses user token from cookie, falls back to GH_TOKEN if available.

    Args:
        customer: Customer name (validated)
        env: Environment name (validated)

    Returns:
        dict: Parsed spec.yml content

    Raises:
        Exception: If spec not found or YAML parse fails
    """
    path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"

    try:
        logger.info(f"Fetching spec: {path}")

        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)

        content = repo_obj.get_contents(path, ref=WORKFLOW_BRANCH)
        spec_yaml = content.decoded_content.decode("utf-8")
        spec = yaml.safe_load(spec_yaml)
        logger.info(f"✓ Successfully parsed spec for {customer}/{env}")
        return spec

    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in {path}: {e}")
        raise ValueError(f"Invalid YAML in spec.yml: {e}")

    except Exception as e:
        logger.error(f"Failed to fetch spec {path}: {e}")
        raise


def list_all_pods():
    """
    Dynamically discover pods by walking GitHub repo structure.
    Uses user token from cookie, falls back to GH_TOKEN if available.
    Returns list of {"customer": str, "env": str} dicts.
    Sorted: alphabetically by customer, lifecycle order by env (dev, stg, prd).
    """
    cache_key = f"pods:{SPECS_PATH}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    logger.info(f"Discovering pods in {SPECS_PATH}...")
    pods = []

    try:
        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)

        customers = repo_obj.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)

        for customer in customers:
            if customer.type != "dir":
                continue

            try:
                envs = repo_obj.get_contents(
                    f"{SPECS_PATH}/{customer.name}", ref=WORKFLOW_BRANCH
                )
                for env in envs:
                    if env.type != "dir":
                        continue

                    # Check if spec.yml exists
                    try:
                        repo_obj.get_contents(
                            f"{SPECS_PATH}/{customer.name}/{env.name}/spec.yml",
                            ref=WORKFLOW_BRANCH,
                        )
                        pods.append({"customer": customer.name, "env": env.name})
                        logger.debug(f"  Found pod: {customer.name}/{env.name}")
                    except:
                        # spec.yml doesn't exist in this env, skip
                        pass
            except Exception as e:
                logger.warning(f"Error listing envs for {customer.name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error discovering pods: {e}")
        raise

    # Sort: customer alphabetically, then env in lifecycle order
    env_order = {"dev": 0, "stg": 1, "prd": 2}
    pods.sort(key=lambda p: (p["customer"], env_order.get(p["env"], 99)))

    logger.info(f"✓ Discovered {len(pods)} pods")
    set_cached(cache_key, pods)
    return pods


# Register API blueprint
from api import api_blueprint

app.register_blueprint(api_blueprint)

# Register auth blueprint
from auth import auth_blueprint

app.register_blueprint(auth_blueprint)


# OLD ROUTE REMOVED: The "/" route now handled by serve_spa() at line ~736
# This was leftover from pre-Vue migration and conflicted with SPA serving


@app.route("/refresh")
def refresh():
    """Clear cache and redirect to home page"""
    global _cache
    _cache = {}
    logger.info("Cache cleared by user refresh")
    return redirect("/")


@app.route("/pod/<customer>/<env>")
def view_pod(customer, env):
    """Pod detail page: show spec.yml configuration in read-only form"""
    try:
        # Validate input parameters
        customer = validate_path_component(customer, "customer")
        env = validate_path_component(env, "environment")

        # Fetch and parse spec
        spec = fetch_spec(customer, env)

        # D5A: Render form with mode=edit, inputs enabled
        return render_template(
            "form.html.j2", mode="edit", customer=customer, env=env, spec=spec
        )

    except ValueError as e:
        # Validation error - show error page with details
        logger.warning(f"Validation error for /pod/{customer}/{env}: {e}")
        return (
            render_template(
                "error.html.j2",
                error_type="validation",
                error_title="Invalid Request",
                error_message=str(e),
                show_pods=True,
                pods=list_all_pods(),
            ),
            400,
        )

    except Exception as e:
        # Spec not found or other error
        logger.error(f"Error viewing pod {customer}/{env}: {e}")
        return (
            render_template(
                "error.html.j2",
                error_type="not_found",
                error_title="Pod Not Found",
                error_message=f"Could not find spec for {customer}/{env}",
                show_pods=True,
                pods=list_all_pods(),
            ),
            404,
        )


@app.route("/pod/new")
def new_pod():
    """Create new pod form"""
    if not repo:
        logger.error("GitHub client not initialized")
        abort(500)

    # Empty spec structure for template
    empty_spec = {
        "metadata": {"customer": "", "environment": ""},
        "spec": {
            "compute": {"instance_name": "", "instance_type": "t4g.nano"},
            "security": {"waf": {"enabled": False}},
        },
    }

    return render_template(
        "form.html.j2", mode="new", customer="", env="", spec=empty_spec
    )


@app.route("/deploy", methods=["POST"])
def deploy():
    """Handle form submission - validate and preview (D5A: no actual deployment)"""
    if not repo and not os.environ.get("GH_TOKEN"):
        logger.error("GitHub client not initialized and no GH_TOKEN available")
        abort(500)

    try:
        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)

        # Extract and validate form data
        customer = validate_path_component(request.form["customer"], "customer")
        env = validate_path_component(request.form["environment"], "environment")
        instance_name = validate_instance_name(request.form["instance_name"])
        waf_enabled = request.form.get("waf_enabled") == "on"
        mode = request.form.get("mode", "edit")

        # CRITICAL: For new pods, check if spec already exists
        if mode == "new":
            path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"
            try:
                repo_obj.get_contents(path, ref=WORKFLOW_BRANCH)
                # File exists - reject with 409 Conflict
                logger.warning(f"Attempted to create existing pod: {customer}/{env}")
                pods = list_all_pods()
                return (
                    render_template(
                        "error.html.j2",
                        error_type="conflict",
                        error_title="Pod Already Exists",
                        error_message=f"Pod {customer}/{env} already exists. Choose a different customer/environment combination or edit the existing pod.",
                        show_pods=True,
                        pods=pods,
                    ),
                    409,
                )
            except:
                # File doesn't exist - good to proceed
                logger.info(f"Creating new pod: {customer}/{env}")
                pass
        else:
            logger.info(f"Updating existing pod: {customer}/{env}")

        # D8: GitOps PR Workflow - Create branch, update spec.yml, create PR
        timestamp = int(time.time())
        branch_name = f"deploy-{customer}-{env}-{timestamp}"
        spec_path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"

        logger.info(f"Creating deployment branch: {branch_name}")

        try:
            # Get base branch (main) commit SHA
            base = repo_obj.get_branch("main")
            base_sha = base.commit.sha

            # Create new branch from main
            repo_obj.create_git_ref(f"refs/heads/{branch_name}", base_sha)
            logger.info(f"✓ Branch created: {branch_name}")

        except GithubException as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return (
                render_template(
                    "error.html.j2",
                    error_type="api_error",
                    error_title="Branch Creation Failed",
                    error_message=f"Could not create deployment branch: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}",
                    show_pods=False,
                    pods=[],
                ),
                503,
            )

        # Generate spec.yml content
        spec_content = generate_spec_yaml(customer, env, instance_name, waf_enabled)
        logger.debug(f"Generated spec.yml:\n{spec_content}")

        # Update or create spec.yml on the new branch
        try:
            # Try to get existing file (for updates)
            try:
                file = repo_obj.get_contents(spec_path, ref="main")
                # File exists - update it
                commit_message = f"deploy: Update {customer}/{env} infrastructure\n\nInstance: {instance_name}\nWAF: {'enabled' if waf_enabled else 'disabled'}"
                repo_obj.update_file(
                    path=spec_path,
                    message=commit_message,
                    content=spec_content,
                    sha=file.sha,
                    branch=branch_name,
                )
                logger.info(f"✓ Updated spec.yml on {branch_name}")

            except GithubException as e:
                if e.status == 404:
                    # File doesn't exist - create it (new pod)
                    commit_message = f"deploy: Create {customer}/{env} infrastructure\n\nInstance: {instance_name}\nWAF: {'enabled' if waf_enabled else 'disabled'}"
                    repo_obj.create_file(
                        path=spec_path,
                        message=commit_message,
                        content=spec_content,
                        branch=branch_name,
                    )
                    logger.info(f"✓ Created spec.yml on {branch_name}")
                else:
                    raise  # Re-raise other GitHub errors

        except GithubException as e:
            logger.error(f"Failed to write spec.yml: {e}")
            return (
                render_template(
                    "error.html.j2",
                    error_type="api_error",
                    error_title="Spec Update Failed",
                    error_message=f"Could not write spec.yml: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}",
                    show_pods=False,
                    pods=[],
                ),
                503,
            )

        # Create Pull Request
        pr_title = f"Deploy: {customer}/{env}"
        pr_body = f"""## 🚀 Infrastructure Deployment

**Customer**: {customer}
**Environment**: {env}
**Instance Name**: {instance_name}
**WAF**: {'✅ Enabled' if waf_enabled else '❌ Disabled'}

---

### Changes
This PR updates the infrastructure specification for `{customer}/{env}`.

### Automation
- ✅ Terraform plan will run automatically (see comments below)
- ✅ Merge this PR to apply changes to AWS infrastructure
- ✅ Terraform apply runs automatically on merge

### Validation
Review the terraform plan output below before merging.

---

🤖 Generated via ActionSpec spec-editor
"""

        try:
            pr = repo_obj.create_pull(
                title=pr_title, body=pr_body, head=branch_name, base="main"
            )
            logger.info(f"✓ PR created: {pr.html_url} (#{pr.number})")

        except GithubException as e:
            logger.error(f"Failed to create PR: {e}")
            return (
                render_template(
                    "error.html.j2",
                    error_type="api_error",
                    error_title="Pull Request Failed",
                    error_message=f"Could not create pull request: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}",
                    show_pods=False,
                    pods=[],
                ),
                503,
            )

        # Success - return PR details
        deployment_details = {
            "customer": customer,
            "environment": env,
            "instance_name": instance_name,
            "waf_enabled": waf_enabled,
        }

        return render_template(
            "success.html.j2",
            mode=mode,
            customer=customer,
            env=env,
            deployment_inputs=deployment_details,
            preview_mode=False,
            pr_url=pr.html_url,
            pr_number=pr.number,
        )

    except ValueError as e:
        # Validation error
        logger.warning(f"Validation error in /deploy: {e}")
        return (
            render_template(
                "error.html.j2",
                error_type="validation",
                error_title="Invalid Input",
                error_message=str(e),
                show_pods=True,
                pods=list_all_pods(),
            ),
            400,
        )

    except KeyError as e:
        # Missing form field
        logger.error(f"Missing form field: {e}")
        return (
            render_template(
                "error.html.j2",
                error_type="validation",
                error_title="Missing Required Field",
                error_message=f"Required field missing: {e}",
                show_pods=False,
                pods=[],
            ),
            400,
        )

    except GithubException as e:
        # GitHub API error (not caught by specific handlers above)
        logger.error(f"GitHub API error: {e}")
        return (
            render_template(
                "error.html.j2",
                error_type="api_error",
                error_title="GitHub API Error",
                error_message=f"Failed to trigger deployment: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}",
                show_pods=False,
                pods=[],
            ),
            503,
        )

    except Exception as e:
        # Generic error
        logger.error(f"Deployment failed: {e}")
        return (
            render_template(
                "error.html.j2",
                error_type="server_error",
                error_title="Server Error",
                error_message=f"Failed to process form: {e}",
                show_pods=False,
                pods=[],
            ),
            500,
        )


@app.route("/health")
def health():
    """Health check: validate GitHub connectivity and show rate limit"""
    try:
        # Get authenticated GitHub client (user token or GH_TOKEN fallback)
        github_client = get_github_client(require_user=False)
        repo_obj = github_client.get_repo(GH_REPO)

        # Test connectivity
        repo_obj.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)

        # Get rate limit info
        rate_limit = github_client.get_rate_limit()
        remaining = rate_limit.core.remaining
        limit = rate_limit.core.limit
        reset_timestamp = rate_limit.core.reset.timestamp()

        # D5B: Check workflow scope (best-effort)
        has_workflow_scope = False
        try:
            # Try to list workflows (requires workflow scope)
            workflows = repo_obj.get_workflows()
            has_workflow_scope = workflows.totalCount > 0
        except:
            pass

        return jsonify(
            {
                "status": "healthy",
                "github": "connected",
                "repo": GH_REPO,
                "scopes": {
                    "repo": True,  # If we got here, we have repo scope
                    "workflow": has_workflow_scope,
                },
                "rate_limit": {
                    "remaining": remaining,
                    "limit": limit,
                    "reset_at": int(reset_timestamp),
                },
            }
        )

    except RateLimitExceededException as e:
        reset_time = github.get_rate_limit().core.reset
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": "Rate limit exceeded",
                    "reset_at": int(reset_time.timestamp()),
                }
            ),
            503,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Don't expose exception details to external users
        return jsonify({"status": "unhealthy", "error": "Service unavailable"}), 503


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors - removed template rendering for Vue SPA compatibility"""
    # For Vue SPA, 404 errors should pass through to SPA routing
    # Don't handle 404s here - let serve_spa() handle them
    pass


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors globally - return JSON for API compatibility"""
    logger.error(f"Internal server error: {error}")
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "message": "Something went wrong. Please try again later.",
                "status": 500,
            }
        ),
        500,
    )


@app.errorhandler(503)
def service_unavailable_error(error):
    """Handle 503 errors (GitHub API issues) - return JSON for API compatibility"""
    return (
        jsonify(
            {
                "error": "Service Unavailable",
                "message": "GitHub API is temporarily unavailable. Please try again later.",
                "status": 503,
            }
        ),
        503,
    )


@app.context_processor
def utility_processor():
    """Add utility functions to all templates"""

    def env_badge_color(env):
        """Return Tailwind color classes for environment badges"""
        colors = {"dev": "green", "stg": "yellow", "prd": "red"}
        return colors.get(env, "gray")

    return dict(env_badge_color=env_badge_color)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    """
    Serve Vue SPA for all non-API routes.

    If path is a file (e.g., .js, .css), serve it.
    Otherwise, serve index.html (SPA fallback).
    """
    # API routes are handled by blueprint, don't catch them here
    if path.startswith("api/"):
        abort(404)

    # Security: Validate path to prevent directory traversal
    if ".." in path or path.startswith("/"):
        abort(404)

    # If path points to a static file, serve it
    # send_static_file safely handles path resolution within static_folder
    try:
        static_file = os.path.join(app.static_folder, path)
        # Ensure resolved path is within static folder (prevent traversal)
        static_folder_abs = os.path.abspath(app.static_folder)
        static_file_abs = os.path.abspath(static_file)
        if not static_file_abs.startswith(static_folder_abs):
            abort(404)

        if os.path.exists(static_file) and os.path.isfile(static_file):
            return app.send_static_file(path)
    except (ValueError, OSError):
        # Invalid path, fall through to SPA fallback
        pass

    # Otherwise, serve index.html (SPA fallback)
    return app.send_static_file("index.html")


if __name__ == "__main__":
    # Only enable debug mode if explicitly set via environment variable
    # Never enable in production
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")  # 0.0.0.0 = all interfaces
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(debug=debug_mode, host=host, port=port)
