"""
Shared helper functions for API endpoints.
"""
from flask import jsonify
import time
from github import GithubException


def json_error(message, status_code, details=None):
    """
    Return consistent JSON error response.

    Args:
        message: Human-readable error message
        status_code: HTTP status code (400, 404, 500, etc.)
        details: Optional dict with additional error context

    Returns:
        tuple: (jsonify response, status_code)
    """
    response = {"error": message}
    if details:
        response["details"] = details
    return jsonify(response), status_code


def json_success(data, status_code=200):
    """
    Return consistent JSON success response.

    Args:
        data: Dict or list to return as JSON
        status_code: HTTP status code (default 200)

    Returns:
        tuple: (jsonify response, status_code)
    """
    return jsonify(data), status_code


def create_pod_deployment(repo, specs_path, customer, env, spec_content, commit_message=None):
    """
    Create GitHub branch, commit spec file, and open PR.

    Extracted from /deploy endpoint to be reusable by API.

    Args:
        repo: PyGithub Repository object
        specs_path: Base path for specs (e.g., 'infra')
        customer: Customer name (validated)
        env: Environment name (validated)
        spec_content: YAML content as string
        commit_message: Optional commit message (default: "Deploy {customer}/{env}")

    Returns:
        dict: {
            'branch': branch_name,
            'pr_url': pr.html_url,
            'pr_number': pr.number
        }

    Raises:
        GithubException: On GitHub API errors
    """
    timestamp = int(time.time())
    branch_name = f"deploy-{customer}-{env}-{timestamp}"
    spec_path = f"{specs_path}/{customer}/{env}/spec.yml"

    if not commit_message:
        commit_message = f"Deploy {customer}/{env}"

    # 1. Create branch from main
    base = repo.get_branch('main')
    base_sha = base.commit.sha
    repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)

    # 2. Check if file exists (update vs create)
    try:
        existing_file = repo.get_contents(spec_path, ref='main')
        repo.update_file(
            path=spec_path,
            message=commit_message,
            content=spec_content,
            sha=existing_file.sha,
            branch=branch_name
        )
    except GithubException as e:
        if e.status == 404:
            # File doesn't exist, create it
            repo.create_file(
                path=spec_path,
                message=commit_message,
                content=spec_content,
                branch=branch_name
            )
        else:
            raise

    # 3. Create pull request
    pr_title = f"Deploy: {customer}/{env}"
    pr_body = f"Automated deployment for {customer}/{env}\n\nBranch: `{branch_name}`"

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base='main'
    )

    return {
        'branch': branch_name,
        'pr_url': pr.html_url,
        'pr_number': pr.number
    }
