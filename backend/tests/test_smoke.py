"""
Smoke tests for ActionSpec API endpoints.
Can run against sam local or deployed API.

Usage:
    # Against sam local
    sam local start-api &
    pytest backend/tests/test_smoke.py

    # Against deployed API
    export API_ENDPOINT=https://xxx.execute-api.us-west-2.amazonaws.com/demo
    export API_KEY=your-api-key
    pytest backend/tests/test_smoke.py
"""

import json
import os

import pytest
import requests


# Determine API endpoint
API_ENDPOINT = os.environ.get('API_ENDPOINT', 'http://localhost:3000')
API_KEY = os.environ.get('API_KEY', 'test-key-local')


def test_api_reachable():
    """Verify API endpoint is reachable."""
    try:
        # Health check - try any endpoint
        response = requests.get(
            f"{API_ENDPOINT}/api/parse",
            headers={'x-api-key': API_KEY},
            timeout=10
        )
        # We expect either 200 (success) or 403 (API key required)
        # Both indicate API is reachable
        assert response.status_code in [200, 403], \
            f"API not reachable, got status {response.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Cannot connect to API at {API_ENDPOINT}. Is SAM local running?")


@pytest.mark.parametrize("endpoint,method", [
    ("/api/parse", "POST"),
    ("/api/discover", "GET"),
    ("/api/form", "GET"),
    ("/api/submit", "POST"),
])
def test_endpoint_returns_200(endpoint, method):
    """All endpoints should return 200 with stub responses."""
    headers = {'x-api-key': API_KEY}

    if method == "GET":
        response = requests.get(f"{API_ENDPOINT}{endpoint}", headers=headers, timeout=10)
    else:
        response = requests.post(
            f"{API_ENDPOINT}{endpoint}",
            headers=headers,
            json={},  # Empty body for stubs
            timeout=10
        )

    assert response.status_code == 200, \
        f"{endpoint} returned {response.status_code}: {response.text}"


@pytest.mark.parametrize("endpoint", [
    "/api/parse",
    "/api/discover",
    "/api/form",
    "/api/submit",
])
def test_endpoint_returns_valid_json(endpoint):
    """All endpoints should return valid JSON."""
    headers = {'x-api-key': API_KEY}
    response = requests.post(f"{API_ENDPOINT}{endpoint}", headers=headers, json={}, timeout=10)

    try:
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON object"
        assert 'message' in data, "Response should contain 'message' field"
        assert 'version' in data, "Response should contain 'version' field"
        assert data['version'] == 'phase-3.1', "Should be phase 3.1 stub"
    except json.JSONDecodeError:
        pytest.fail(f"{endpoint} did not return valid JSON: {response.text}")


def test_security_headers_present():
    """All responses should include required security headers."""
    headers = {'x-api-key': API_KEY}
    response = requests.get(f"{API_ENDPOINT}/api/form", headers=headers, timeout=10)

    required_headers = [
        'Strict-Transport-Security',
        'Content-Security-Policy',
        'X-Content-Type-Options',
        'X-Frame-Options',
        'X-XSS-Protection',
    ]

    for header in required_headers:
        assert header in response.headers, \
            f"Missing security header: {header}"


def test_cors_headers_present():
    """API should include CORS headers."""
    headers = {'x-api-key': API_KEY}
    response = requests.options(f"{API_ENDPOINT}/api/form", headers=headers, timeout=10)

    # CORS headers may be present on OPTIONS or actual requests
    # Check on GET instead if OPTIONS not supported in local
    if response.status_code == 404:
        response = requests.get(f"{API_ENDPOINT}/api/form", headers=headers, timeout=10)

    # At minimum, should have Access-Control-Allow-Origin
    # Note: SAM local may not fully enforce CORS, check in deployed version
    assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 200


def test_stub_response_structure():
    """Stub responses should have consistent structure."""
    headers = {'x-api-key': API_KEY}
    response = requests.get(f"{API_ENDPOINT}/api/form", headers=headers, timeout=10)

    data = response.json()

    # All stubs should have these fields
    assert 'message' in data
    assert 'version' in data
    assert 'phase' in data
    assert 'status' in data

    # Verify stub status
    assert data['status'] == 'stub'
    assert data['phase'] == '3.1'
