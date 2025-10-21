"""
Unit tests for security_wrapper module.
Tests decorator behavior, sanitization, and error handling.
"""

import json
import sys
import os

import pytest

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))

from security_wrapper import (
    sanitize_for_logging,
    is_suspicious_request,
    secure_handler,
    SECURITY_HEADERS,
    SENSITIVE_FIELDS
)


class MockContext:
    """Mock Lambda context for testing."""
    request_id = 'test-request-123'
    function_name = 'test-function'
    memory_limit_in_mb = 128
    invoked_function_arn = 'arn:aws:lambda:us-west-2:999999999999:function:test'


def test_sanitize_for_logging_redacts_passwords():
    """Passwords should be redacted in logs."""
    data = {
        'username': 'testuser',
        'password': 'secret123',
        'email': 'test@example.com'
    }

    sanitized = sanitize_for_logging(data)

    assert sanitized['username'] == 'testuser'
    assert sanitized['password'] == '[REDACTED]'
    assert sanitized['email'] == 'test@example.com'


def test_sanitize_for_logging_redacts_api_keys():
    """API keys should be redacted."""
    data = {
        'x-api-key': 'sk-1234567890',
        'authorization': 'Bearer token123',
        'data': 'public'
    }

    sanitized = sanitize_for_logging(data)

    assert sanitized['x-api-key'] == '[REDACTED]'
    assert sanitized['authorization'] == '[REDACTED]'
    assert sanitized['data'] == 'public'


def test_sanitize_for_logging_handles_nested_structures():
    """Sanitization should work recursively."""
    data = {
        'user': {
            'name': 'Alice',
            'credentials': {
                'password': 'secret',
                'token': 'abc123'
            }
        }
    }

    sanitized = sanitize_for_logging(data)

    assert sanitized['user']['name'] == 'Alice'
    assert sanitized['user']['credentials']['password'] == '[REDACTED]'
    assert sanitized['user']['credentials']['token'] == '[REDACTED]'


def test_sanitize_for_logging_handles_lists():
    """Sanitization should work with lists."""
    data = {
        'items': [
            {'name': 'item1', 'secret': 'hidden'},
            {'name': 'item2', 'secret': 'hidden2'}
        ]
    }

    sanitized = sanitize_for_logging(data)

    assert len(sanitized['items']) == 2
    assert sanitized['items'][0]['name'] == 'item1'
    assert sanitized['items'][0]['secret'] == '[REDACTED]'


def test_sanitize_for_logging_truncates_long_strings():
    """Very long strings should be truncated."""
    data = {'long_text': 'a' * 2000}

    sanitized = sanitize_for_logging(data)

    assert len(sanitized['long_text']) < 2000
    assert '[TRUNCATED]' in sanitized['long_text']


def test_is_suspicious_request_detects_sql_injection():
    """Should detect SQL injection patterns."""
    event = {
        'queryStringParameters': {
            'id': '1 OR 1=1; DROP TABLE users--'
        }
    }

    assert is_suspicious_request(event) is True


def test_is_suspicious_request_detects_path_traversal():
    """Should detect path traversal attempts."""
    event = {
        'path': '/api/../../../etc/passwd'
    }

    assert is_suspicious_request(event) is True


def test_is_suspicious_request_allows_normal_requests():
    """Normal requests should not be flagged."""
    event = {
        'path': '/api/form',
        'queryStringParameters': {
            'name': 'test',
            'value': '123'
        }
    }

    assert is_suspicious_request(event) is False


def test_secure_handler_adds_security_headers():
    """Decorator should add security headers to response."""
    @secure_handler
    def test_handler(event, context):
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'OK'})
        }

    response = test_handler({}, MockContext())

    assert response['statusCode'] == 200
    assert 'headers' in response

    for header in SECURITY_HEADERS:
        assert header in response['headers']


def test_secure_handler_blocks_suspicious_requests():
    """Decorator should block suspicious requests."""
    @secure_handler
    def test_handler(event, context):
        return {'statusCode': 200, 'body': 'OK'}

    suspicious_event = {
        'path': '/api/../../../etc/passwd'
    }

    response = test_handler(suspicious_event, MockContext())

    assert response['statusCode'] == 418  # I'm a teapot
    body = json.loads(response['body'])
    assert 'error' in body


def test_secure_handler_catches_exceptions():
    """Decorator should catch and wrap exceptions."""
    @secure_handler
    def test_handler(event, context):
        raise ValueError("Something went wrong")

    response = test_handler({}, MockContext())

    assert response['statusCode'] == 500
    assert 'headers' in response
    body = json.loads(response['body'])
    assert 'error' in body


def test_secure_handler_ensures_body_is_string():
    """Decorator should convert dict body to JSON string."""
    @secure_handler
    def test_handler(event, context):
        return {
            'statusCode': 200,
            'body': {'message': 'OK', 'data': [1, 2, 3]}
        }

    response = test_handler({}, MockContext())

    assert isinstance(response['body'], str)
    body = json.loads(response['body'])
    assert body['message'] == 'OK'
    assert body['data'] == [1, 2, 3]


def test_secure_handler_preserves_existing_headers():
    """Decorator should merge with existing headers, not replace."""
    @secure_handler
    def test_handler(event, context):
        return {
            'statusCode': 200,
            'headers': {'X-Custom-Header': 'custom-value'},
            'body': json.dumps({'message': 'OK'})
        }

    response = test_handler({}, MockContext())

    # Custom header should be preserved
    assert response['headers']['X-Custom-Header'] == 'custom-value'

    # Security headers should be added
    assert 'Strict-Transport-Security' in response['headers']


def test_secure_handler_adds_default_status_code():
    """Decorator should add default status code if missing."""
    @secure_handler
    def test_handler(event, context):
        return {'body': json.dumps({'message': 'OK'})}

    response = test_handler({}, MockContext())

    assert response['statusCode'] == 200


def test_secure_handler_adds_default_body():
    """Decorator should add default body if missing."""
    @secure_handler
    def test_handler(event, context):
        return {'statusCode': 200}

    response = test_handler({}, MockContext())

    assert 'body' in response
    body = json.loads(response['body'])
    assert 'message' in body
