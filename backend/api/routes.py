"""
API route handlers.
"""

from flask import request
from github import GithubException

from . import api_blueprint
from .helpers import json_error, json_success, create_pod_deployment

# Import existing functions and globals from main app
# Using late imports to avoid circular dependency issues
import app as main_app


@api_blueprint.route("/pods", methods=["GET"])
def get_pods():
    """
    GET /api/pods

    List all pods discovered from GitHub repository structure.

    Returns:
        200: [{"customer": "foo", "env": "dev"}, ...]
        500: {"error": "message"}
    """
    try:
        pods = main_app.list_all_pods()
        return json_success(pods)
    except GithubException as e:
        return json_error(
            "Failed to fetch pod list from GitHub", 500, {"github_error": str(e)}
        )
    except Exception as e:
        return json_error("Unexpected error fetching pods", 500, {"details": str(e)})


@api_blueprint.route("/refresh", methods=["POST"])
def refresh_cache():
    """
    POST /api/refresh

    Clear the pod cache and return success.

    Returns:
        200: {"message": "Cache cleared"}
    """
    # Clear cache using main app's cache mechanism
    main_app._cache.clear()
    main_app.logger.info("Cache cleared via API")
    return json_success({"message": "Cache cleared"})


@api_blueprint.route("/pod/<customer>/<env>", methods=["GET"])
def get_pod(customer, env):
    """
    GET /api/pod/<customer>/<env>

    Fetch spec.yml for a specific pod.

    Args:
        customer: Customer name
        env: Environment name (dev, stg, prd)

    Returns:
        200: {parsed YAML structure}
        404: {"error": "Pod not found"}
        500: {"error": "message"}
    """
    # Validate path components
    try:
        customer = main_app.validate_path_component(customer, "customer")
        env = main_app.validate_path_component(env, "environment")
    except ValueError as e:
        return json_error(str(e), 400)

    try:
        spec = main_app.fetch_spec(customer, env)
        if spec is None:
            return json_error(f"Pod not found: {customer}/{env}", 404)
        return json_success(spec)
    except GithubException as e:
        if e.status == 404:
            return json_error(f"Pod not found: {customer}/{env}", 404)
        return json_error(
            "Failed to fetch pod from GitHub", 500, {"github_error": str(e)}
        )
    except Exception as e:
        return json_error("Unexpected error fetching pod", 500, {"details": str(e)})


@api_blueprint.route("/pod", methods=["POST"])
def create_or_update_pod():
    """
    POST /api/pod

    Create or update a pod specification.

    Request body:
        {
            "customer": "string",
            "env": "string",
            "spec": {
                "instance_name": "string",
                "waf_enabled": boolean
            },
            "commit_message": "string (optional)"
        }

    Returns:
        200: {
            "branch": "deploy-customer-env-timestamp",
            "pr_url": "https://github.com/.../pull/123",
            "pr_number": 123
        }
        400: {"error": "Validation error", "details": {...}}
        500: {"error": "GitHub API error"}
    """
    # Parse JSON body
    try:
        data = request.get_json()
        if not data:
            return json_error("Request body must be JSON", 400)
    except Exception as e:
        return json_error("Invalid JSON in request body", 400, {"details": str(e)})

    # Extract and validate required fields
    customer = data.get("customer")
    env = data.get("env")
    spec = data.get("spec", {})
    commit_message = data.get("commit_message")

    if not customer:
        return json_error("Missing required field: customer", 400)
    if not env:
        return json_error("Missing required field: env", 400)
    if not spec:
        return json_error("Missing required field: spec", 400)

    # Validate path components
    try:
        customer = main_app.validate_path_component(customer, "customer")
        env = main_app.validate_path_component(env, "environment")
    except ValueError as e:
        return json_error(str(e), 400)

    # Extract spec fields
    instance_name = spec.get("instance_name")
    waf_enabled = spec.get("waf_enabled", False)

    if not instance_name:
        return json_error("Missing required spec field: instance_name", 400)

    # Validate instance name
    try:
        instance_name = main_app.validate_instance_name(instance_name)
    except ValueError as e:
        return json_error(str(e), 400)

    # Generate YAML content
    try:
        spec_content = main_app.generate_spec_yaml(
            customer, env, instance_name, waf_enabled
        )
    except Exception as e:
        return json_error("Failed to generate spec YAML", 500, {"details": str(e)})

    # Create deployment (branch + PR)
    try:
        result = create_pod_deployment(
            main_app.repo,
            main_app.SPECS_PATH,
            customer,
            env,
            spec_content,
            commit_message,
        )
        return json_success(result)
    except GithubException as e:
        return json_error(
            "Failed to create GitHub deployment", 500, {"github_error": str(e)}
        )
    except Exception as e:
        return json_error(
            "Unexpected error creating deployment", 500, {"details": str(e)}
        )
