"""
Spec Editor Flask App - Demo Phase D4A
Read-only UI for viewing infrastructure pod specifications.
"""

from flask import Flask, render_template, jsonify, abort, request, redirect
from github import Github
from github.GithubException import BadCredentialsException, RateLimitExceededException, GithubException
import yaml
import os
import sys
import time
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Configuration from environment
GH_TOKEN = os.environ.get('GH_TOKEN')
GH_REPO = os.environ.get('GH_REPO', 'trakrf/action-spec')
SPECS_PATH = os.environ.get('SPECS_PATH', 'demo/infra')
WORKFLOW_BRANCH = os.environ.get('WORKFLOW_BRANCH', 'main')

# Fail fast if GH_TOKEN missing
if not GH_TOKEN:
    logger.error("GH_TOKEN environment variable is required")
    logger.error("Set GH_TOKEN in your environment or .env.local file")
    sys.exit(1)

logger.info(f"Initializing Spec Editor")
logger.info(f"GitHub Repo: {GH_REPO}")
logger.info(f"Specs Path: {SPECS_PATH}")
logger.info(f"Workflow Branch: {WORKFLOW_BRANCH}")

# Initialize GitHub client (fail fast on auth errors)
try:
    github = Github(GH_TOKEN)
    repo = github.get_repo(GH_REPO)
    # Test connectivity
    repo.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)
    logger.info(f"✓ Successfully connected to GitHub repo: {GH_REPO} (branch: {WORKFLOW_BRANCH})")
except BadCredentialsException:
    logger.error("GitHub authentication failed: Invalid or expired token")
    logger.error("Check that GH_TOKEN has 'repo' scope")
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to initialize GitHub client: {e}")
    logger.error(f"Repository: {GH_REPO}, Path: {SPECS_PATH}")
    sys.exit(1)

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
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValueError(f"{param_name} contains invalid characters (use a-z, A-Z, 0-9, -, _ only)")

    # Prevent path traversal
    if '..' in value or '/' in value or '\\' in value:
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

    if not re.match(r'^[a-z0-9-]+$', value):
        raise ValueError("instance_name must be lowercase letters, numbers, and hyphens only (no uppercase, no underscores, no spaces)")

    if value.startswith('-') or value.endswith('-'):
        raise ValueError("instance_name cannot start or end with hyphen")

    return value

def fetch_spec(customer, env):
    """
    Fetch and parse spec.yml from GitHub for a specific pod.

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
        content = repo.get_contents(path, ref=WORKFLOW_BRANCH)
        spec_yaml = content.decoded_content.decode('utf-8')
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
        customers = repo.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)

        for customer in customers:
            if customer.type != "dir":
                continue

            try:
                envs = repo.get_contents(f"{SPECS_PATH}/{customer.name}", ref=WORKFLOW_BRANCH)
                for env in envs:
                    if env.type != "dir":
                        continue

                    # Check if spec.yml exists
                    try:
                        repo.get_contents(f"{SPECS_PATH}/{customer.name}/{env.name}/spec.yml", ref=WORKFLOW_BRANCH)
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

@app.route('/')
def index():
    """Home page: list all pods grouped by customer"""
    try:
        pods = list_all_pods()

        # Group by customer for template
        customers = {}
        for pod in pods:
            cust = pod["customer"]
            if cust not in customers:
                customers[cust] = []
            customers[cust].append(pod["env"])

        return render_template('index.html.j2',
                               pods=pods,
                               customers=customers)

    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        abort(500)

@app.route('/refresh')
def refresh():
    """Clear cache and redirect to home page"""
    global _cache
    _cache = {}
    logger.info("Cache cleared by user refresh")
    return redirect('/')

@app.route('/pod/<customer>/<env>')
def view_pod(customer, env):
    """Pod detail page: show spec.yml configuration in read-only form"""
    try:
        # Validate input parameters
        customer = validate_path_component(customer, "customer")
        env = validate_path_component(env, "environment")

        # Fetch and parse spec
        spec = fetch_spec(customer, env)

        # D5A: Render form with mode=edit, inputs enabled
        return render_template('form.html.j2',
                               mode='edit',
                               customer=customer,
                               env=env,
                               spec=spec)

    except ValueError as e:
        # Validation error - show error page with details
        logger.warning(f"Validation error for /pod/{customer}/{env}: {e}")
        return render_template('error.html.j2',
                               error_type="validation",
                               error_title="Invalid Request",
                               error_message=str(e),
                               show_pods=True,
                               pods=list_all_pods()), 400

    except Exception as e:
        # Spec not found or other error
        logger.error(f"Error viewing pod {customer}/{env}: {e}")
        return render_template('error.html.j2',
                               error_type="not_found",
                               error_title="Pod Not Found",
                               error_message=f"Could not find spec for {customer}/{env}",
                               show_pods=True,
                               pods=list_all_pods()), 404

@app.route('/pod/new')
def new_pod():
    """Create new pod form"""
    if not repo:
        logger.error("GitHub client not initialized")
        abort(500)

    # Empty spec structure for template
    empty_spec = {
        'metadata': {
            'customer': '',
            'environment': ''
        },
        'spec': {
            'compute': {
                'instance_name': '',
                'instance_type': 't4g.nano'
            },
            'security': {
                'waf': {
                    'enabled': False
                }
            }
        }
    }

    return render_template('form.html.j2',
                           mode='new',
                           customer='',
                           env='',
                           spec=empty_spec)

@app.route('/deploy', methods=['POST'])
def deploy():
    """Handle form submission - validate and preview (D5A: no actual deployment)"""
    if not repo:
        logger.error("GitHub client not initialized")
        abort(500)

    try:
        # Extract and validate form data
        customer = validate_path_component(request.form['customer'], 'customer')
        env = validate_path_component(request.form['environment'], 'environment')
        instance_name = validate_instance_name(request.form['instance_name'])
        waf_enabled = request.form.get('waf_enabled') == 'on'
        mode = request.form.get('mode', 'edit')

        # CRITICAL: For new pods, check if spec already exists
        if mode == 'new':
            path = f"{SPECS_PATH}/{customer}/{env}/spec.yml"
            try:
                repo.get_contents(path, ref=WORKFLOW_BRANCH)
                # File exists - reject with 409 Conflict
                logger.warning(f"Attempted to create existing pod: {customer}/{env}")
                pods = list_all_pods()
                return render_template('error.html.j2',
                    error_type="conflict",
                    error_title="Pod Already Exists",
                    error_message=f"Pod {customer}/{env} already exists. Choose a different customer/environment combination or edit the existing pod.",
                    show_pods=True,
                    pods=pods), 409
            except:
                # File doesn't exist - good to proceed
                logger.info(f"Creating new pod: {customer}/{env}")
                pass
        else:
            logger.info(f"Updating existing pod: {customer}/{env}")

        # D5B: Trigger workflow_dispatch
        workflow_file = 'deploy-pod.yml'

        # Get workflow object
        try:
            workflow = repo.get_workflow(workflow_file)
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_file}: {e}")
            return render_template('error.html.j2',
                error_type="not_found",
                error_title="Workflow Not Found",
                error_message=f"GitHub workflow '{workflow_file}' not found. Check .github/workflows/ directory.",
                show_pods=False,
                pods=[]), 404

        # Prepare workflow inputs (must match workflow_dispatch inputs in deploy-pod.yml)
        workflow_inputs = {
            'customer': customer,
            'environment': env,
            'instance_name': instance_name,
            'waf_enabled': waf_enabled  # Boolean, not string
        }

        logger.info(f"Triggering workflow_dispatch for {customer}/{env} with inputs: {workflow_inputs}")

        # Trigger workflow dispatch on configured branch
        try:
            workflow.create_dispatch(
                ref=WORKFLOW_BRANCH,
                inputs=workflow_inputs
            )
        except GithubException as e:
            logger.error(f"workflow_dispatch failed: {e.status} - {e.data}")

            # Handle specific GitHub API errors
            if e.status == 403:
                return render_template('error.html.j2',
                    error_type="forbidden",
                    error_title="Permission Denied",
                    error_message="GitHub token lacks 'workflow' scope. Update GH_TOKEN with workflow permissions.",
                    show_pods=False,
                    pods=[]), 403
            elif e.status == 404:
                return render_template('error.html.j2',
                    error_type="not_found",
                    error_title="Workflow Not Found",
                    error_message=f"Workflow '{workflow_file}' or branch '{WORKFLOW_BRANCH}' not found.",
                    show_pods=False,
                    pods=[]), 404
            elif e.status == 422:
                return render_template('error.html.j2',
                    error_type="validation",
                    error_title="Invalid Workflow Inputs",
                    error_message=f"Workflow rejected inputs: {e.data.get('message', 'Unknown error')}",
                    show_pods=False,
                    pods=[]), 422
            else:
                raise  # Re-raise for generic handler

        # If we got here, dispatch succeeded (no exception raised)
        logger.info(f"workflow_dispatch succeeded for {customer}/{env}")

        # D5B: Get latest workflow run URL (best-effort)
        action_url = None
        try:
            # Wait briefly for GitHub to create the run
            time.sleep(2)

            runs = workflow.get_runs(branch=WORKFLOW_BRANCH)
            logger.info(f"Retrieved {runs.totalCount} workflow runs")
            if runs.totalCount > 0:
                latest_run = runs[0]
                action_url = latest_run.html_url
                logger.info(f"Latest workflow run: {action_url}")
            else:
                logger.warning("No workflow runs found after 2 second delay - using fallback link")
        except Exception as e:
            logger.warning(f"Could not retrieve workflow run URL: {e}")
            # Non-fatal - continue without URL

        # Success
        return render_template('success.html.j2',
            mode=mode,
            customer=customer,
            env=env,
            deployment_inputs=workflow_inputs,
            preview_mode=False,  # D5B: actual deployment
            action_url=action_url)

    except ValueError as e:
        # Validation error
        logger.warning(f"Validation error in /deploy: {e}")
        return render_template('error.html.j2',
            error_type="validation",
            error_title="Invalid Input",
            error_message=str(e),
            show_pods=True,
            pods=list_all_pods()), 400

    except KeyError as e:
        # Missing form field
        logger.error(f"Missing form field: {e}")
        return render_template('error.html.j2',
            error_type="validation",
            error_title="Missing Required Field",
            error_message=f"Required field missing: {e}",
            show_pods=False,
            pods=[]), 400

    except GithubException as e:
        # GitHub API error (not caught by specific handlers above)
        logger.error(f"GitHub API error: {e}")
        return render_template('error.html.j2',
            error_type="api_error",
            error_title="GitHub API Error",
            error_message=f"Failed to trigger deployment: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}",
            show_pods=False,
            pods=[]), 503

    except Exception as e:
        # Generic error
        logger.error(f"Deployment failed: {e}")
        return render_template('error.html.j2',
            error_type="server_error",
            error_title="Server Error",
            error_message=f"Failed to process form: {e}",
            show_pods=False,
            pods=[]), 500

@app.route('/health')
def health():
    """Health check: validate GitHub connectivity and show rate limit"""
    try:
        # Test connectivity
        repo.get_contents(SPECS_PATH, ref=WORKFLOW_BRANCH)

        # Get rate limit info
        rate_limit = github.get_rate_limit()
        remaining = rate_limit.core.remaining
        limit = rate_limit.core.limit
        reset_timestamp = rate_limit.core.reset.timestamp()

        # D5B: Check workflow scope (best-effort)
        has_workflow_scope = False
        try:
            # Try to list workflows (requires workflow scope)
            workflows = repo.get_workflows()
            has_workflow_scope = workflows.totalCount > 0
        except:
            pass

        return jsonify({
            "status": "healthy",
            "github": "connected",
            "repo": GH_REPO,
            "scopes": {
                "repo": True,  # If we got here, we have repo scope
                "workflow": has_workflow_scope
            },
            "rate_limit": {
                "remaining": remaining,
                "limit": limit,
                "reset_at": int(reset_timestamp)
            }
        })

    except RateLimitExceededException as e:
        reset_time = github.get_rate_limit().core.reset
        return jsonify({
            "status": "unhealthy",
            "error": "Rate limit exceeded",
            "reset_at": int(reset_time.timestamp())
        }), 503

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors globally"""
    return render_template('error.html.j2',
                           error_type="not_found",
                           error_title="Page Not Found",
                           error_message="The page you're looking for doesn't exist",
                           show_pods=True,
                           pods=list_all_pods()), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors globally"""
    logger.error(f"Internal server error: {error}")
    return render_template('error.html.j2',
                           error_type="server_error",
                           error_title="Internal Server Error",
                           error_message="Something went wrong. Please try again later.",
                           show_pods=False,
                           pods=[]), 500

@app.errorhandler(503)
def service_unavailable_error(error):
    """Handle 503 errors (GitHub API issues)"""
    return render_template('error.html.j2',
                           error_type="service_unavailable",
                           error_title="Service Unavailable",
                           error_message="GitHub API is temporarily unavailable. Please try again later.",
                           show_pods=False,
                           pods=[]), 503

@app.context_processor
def utility_processor():
    """Add utility functions to all templates"""
    def env_badge_color(env):
        """Return Tailwind color classes for environment badges"""
        colors = {
            'dev': 'green',
            'stg': 'yellow',
            'prd': 'red'
        }
        return colors.get(env, 'gray')

    return dict(env_badge_color=env_badge_color)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
