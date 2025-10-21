"""
Security wrapper for all Lambda functions.
Enforces security headers, log sanitization, and error handling.

Usage:
    from shared.security_wrapper import secure_handler

    @secure_handler
    def lambda_handler(event, context):
        return {'statusCode': 200, 'body': 'Hello'}
"""

import json
import logging
import os
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Set

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Security headers applied to ALL responses
SECURITY_HEADERS = {
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'",
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    'Content-Type': 'application/json'
}

# Fields to NEVER log (case-insensitive matching)
SENSITIVE_FIELDS: Set[str] = {
    'authorization', 'x-api-key', 'cookie', 'password',
    'secret', 'token', 'aws', 'key', 'credential'
}


def sanitize_for_logging(data: Any, depth: int = 0) -> Any:
    """
    Recursively sanitize data structure for safe logging.
    Redacts sensitive fields.

    Args:
        data: Data structure to sanitize (dict, list, or primitive)
        depth: Current recursion depth (prevents infinite loops)

    Returns:
        Sanitized copy of data
    """
    if depth > 10:  # Prevent deep recursion
        return "[MAX_DEPTH_EXCEEDED]"

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Check if key matches sensitive pattern
            if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_for_logging(value, depth + 1)
        return sanitized

    elif isinstance(data, list):
        return [sanitize_for_logging(item, depth + 1) for item in data]

    elif isinstance(data, str) and len(data) > 1000:
        # Truncate very long strings
        return data[:1000] + "...[TRUNCATED]"

    else:
        return data


def is_suspicious_request(event: Dict[str, Any]) -> bool:
    """
    Basic request validation to detect common attack patterns.

    Args:
        event: Lambda event object

    Returns:
        True if request looks suspicious
    """
    # Check for common SQL injection patterns in query strings
    if 'queryStringParameters' in event and event['queryStringParameters']:
        query_string = str(event['queryStringParameters']).lower()
        sql_patterns = ['union select', 'drop table', '--', '/*', 'xp_cmdshell']
        if any(pattern in query_string for pattern in sql_patterns):
            return True

    # Check for path traversal attempts
    if 'path' in event:
        path = event['path']
        if '../' in path or '..\\' in path:
            return True

    return False


def secure_handler(func: Callable) -> Callable:
    """
    Decorator that adds security features to Lambda handlers.

    Features:
    - Automatic security header injection
    - Request sanitization logging
    - Suspicious request detection
    - Exception wrapping with safe error messages
    - Environment-based debug logging

    Usage:
        @secure_handler
        def lambda_handler(event, context):
            return {'statusCode': 200, 'body': json.dumps({'message': 'OK'})}
    """
    @wraps(func)
    def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        # Sanitize event for logging
        safe_event = sanitize_for_logging(event)

        # Log request (sanitized)
        environment = os.environ.get('ENVIRONMENT', 'unknown')
        logger.info(f"Request received [env={environment}]", extra={
            'event': safe_event,
            'request_id': context.request_id if hasattr(context, 'request_id') else 'local'
        })

        # Check for suspicious patterns
        if is_suspicious_request(event):
            logger.warning("Suspicious request detected", extra={
                'event': safe_event,
                'request_id': context.request_id if hasattr(context, 'request_id') else 'local'
            })
            return {
                'statusCode': 418,  # I'm a teapot
                'headers': SECURITY_HEADERS,
                'body': json.dumps({
                    'error': 'Invalid request',
                    'message': 'Request pattern not allowed'
                })
            }

        try:
            # Call the actual handler
            response = func(event, context)

            # Ensure response has proper structure
            if not isinstance(response, dict):
                raise ValueError(f"Handler must return dict, got {type(response)}")

            if 'statusCode' not in response:
                response['statusCode'] = 200

            if 'body' not in response:
                response['body'] = json.dumps({'message': 'OK'})

            # Ensure body is string (Lambda requirement)
            if isinstance(response.get('body'), dict):
                response['body'] = json.dumps(response['body'])

            # Inject security headers (merge with any existing headers)
            if 'headers' not in response:
                response['headers'] = {}

            response['headers'].update(SECURITY_HEADERS)

            # Log response (sanitized, status only in production)
            if environment == 'local':
                logger.info(f"Response: {response['statusCode']}", extra={
                    'status': response['statusCode'],
                    'headers': response['headers']
                })
            else:
                logger.info(f"Response: {response['statusCode']}")

            return response

        except Exception as e:
            # Log exception with full traceback
            logger.error(
                f"Handler error: {str(e)}",
                extra={
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc()
                }
            )

            # Return safe error response (never leak internal details)
            error_response = {
                'statusCode': 500,
                'headers': SECURITY_HEADERS,
                'body': json.dumps({
                    'error': 'Internal server error',
                    'message': 'An unexpected error occurred'
                })
            }

            # In local development, include error details
            if environment == 'local':
                error_response['body'] = json.dumps({
                    'error': type(e).__name__,
                    'message': str(e),
                    'traceback': traceback.format_exc()
                })

            return error_response

    return wrapper


# Example usage (for testing)
if __name__ == '__main__':
    # Test sanitization
    test_data = {
        'username': 'test',
        'password': 'secret123',
        'x-api-key': 'sk-1234567890',
        'metadata': {
            'token': 'bearer abc123',
            'public_data': 'visible'
        }
    }

    sanitized = sanitize_for_logging(test_data)
    print("Sanitized:", json.dumps(sanitized, indent=2))

    # Test decorator
    @secure_handler
    def test_handler(event, context):
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Test successful'})
        }

    class MockContext:
        request_id = 'test-request-123'

    result = test_handler({}, MockContext())
    print("\nDecorator result:", json.dumps(result, indent=2))
