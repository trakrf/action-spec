"""
Spec Editor Flask App - Demo Phase D4A
Read-only UI for viewing infrastructure pod specifications.
"""

from flask import Flask, render_template, jsonify, abort
from github import Github
from github.GithubException import BadCredentialsException, RateLimitExceededException
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

# Fail fast if GH_TOKEN missing
if not GH_TOKEN:
    logger.error("GH_TOKEN environment variable is required")
    logger.error("Set GH_TOKEN in your environment or .env.local file")
    sys.exit(1)

logger.info(f"Initializing Spec Editor")
logger.info(f"GitHub Repo: {GH_REPO}")
logger.info(f"Specs Path: {SPECS_PATH}")

# Initialize GitHub client (fail fast on auth errors)
try:
    github = Github(GH_TOKEN)
    repo = github.get_repo(GH_REPO)
    # Test connectivity
    repo.get_contents(SPECS_PATH)
    logger.info(f"✓ Successfully connected to GitHub repo: {GH_REPO}")
except BadCredentialsException:
    logger.error("GitHub authentication failed: Invalid or expired token")
    logger.error("Check that GH_TOKEN has 'repo' scope")
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to initialize GitHub client: {e}")
    logger.error(f"Repository: {GH_REPO}, Path: {SPECS_PATH}")
    sys.exit(1)

# Simple cache with 5-minute TTL
_cache = {}
CACHE_TTL = 300  # 5 minutes in seconds

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
        content = repo.get_contents(path)
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
        customers = repo.get_contents(SPECS_PATH)

        for customer in customers:
            if customer.type != "dir":
                continue

            try:
                envs = repo.get_contents(f"{SPECS_PATH}/{customer.name}")
                for env in envs:
                    if env.type != "dir":
                        continue

                    # Check if spec.yml exists
                    try:
                        repo.get_contents(f"{SPECS_PATH}/{customer.name}/{env.name}/spec.yml")
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

@app.route('/pod/<customer>/<env>')
def view_pod(customer, env):
    """Pod detail page: show spec.yml configuration in read-only form"""
    try:
        # Validate input parameters
        customer = validate_path_component(customer, "customer")
        env = validate_path_component(env, "environment")

        # Fetch and parse spec
        spec = fetch_spec(customer, env)

        # Render form with spec data
        return render_template('form.html.j2',
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

@app.route('/health')
def health():
    """Health check: validate GitHub connectivity and show rate limit"""
    try:
        # Test connectivity
        repo.get_contents(SPECS_PATH)

        # Get rate limit info
        rate_limit = github.get_rate_limit()
        remaining = rate_limit.core.remaining
        limit = rate_limit.core.limit
        reset_timestamp = rate_limit.core.reset.timestamp()

        return jsonify({
            "status": "healthy",
            "github": "connected",
            "repo": GH_REPO,
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
