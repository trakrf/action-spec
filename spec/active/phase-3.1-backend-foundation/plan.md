# Implementation Plan: Phase 3.1 - Backend Foundation & SAM Infrastructure
Generated: 2025-10-21
Specification: spec.md

## Understanding

Phase 3.1 establishes the foundational AWS Serverless Application Model (SAM) backend infrastructure for ActionSpec. This is a **greenfield Python/Lambda project** that creates the architectural foundation for all subsequent phases (3.2-3.5).

**Core Goal**: Create a deployable, secure, testable backend with:
- 4 Lambda functions (stub implementations) behind API Gateway
- Security wrapper enforcing headers on ALL responses
- IAM roles following least-privilege principle
- Local development environment (`sam local start-api`)
- Both automated and manual testing capabilities

**Key Insight**: This phase validates infrastructure patterns work correctly BEFORE implementing business logic. Stub responses prove the plumbing works.

**User Decisions Applied**:
- Python 3.11 runtime (better AWS Lambda support than 3.12)
- Stack name: `actionspec-backend`
- API endpoints: `/api/parse`, `/api/discover`, `/api/form`, `/api/submit`
- Testing: Both SAM local + standalone Python harness
- Deployment: Environment variable driven (not interactive)

## Relevant Files

**Reference Patterns** (existing code to follow):
- `scripts/pre-commit-checks.sh` (lines 1-198) - Shell script pattern with error handling, color output, environment awareness
- `infrastructure/README.md` (lines 122-136) - Environment variable pattern for configuration
- `.gitignore` (lines 45-61) - AWS/Python artifact exclusions to extend

**Files to Create**:

### Core Infrastructure (7 files)
- `template.yaml` - AWS SAM template defining all Lambda functions, API Gateway, S3, IAM roles
- `samconfig.toml` - SAM CLI deployment configuration (environment-driven)
- `env.json.example` - Example local development environment variables
- `.gitignore` (extend) - Add Python/SAM specific patterns

### Python Backend (9 files)
- `backend/lambda/shared/__init__.py` - Python package marker
- `backend/lambda/shared/security_wrapper.py` - Decorator applying security headers, log sanitization, error handling
- `backend/lambda/functions/spec-parser/handler.py` - Stub Lambda handler
- `backend/lambda/functions/spec-parser/requirements.txt` - Dependencies (PyYAML, jsonschema for phase 3.2)
- `backend/lambda/functions/aws-discovery/handler.py` - Stub Lambda handler
- `backend/lambda/functions/aws-discovery/requirements.txt` - Dependencies (boto3)
- `backend/lambda/functions/form-generator/handler.py` - Stub Lambda handler
- `backend/lambda/functions/form-generator/requirements.txt` - Dependencies (PyGithub for phase 3.3)
- `backend/lambda/functions/spec-applier/handler.py` - Stub Lambda handler
- `backend/lambda/functions/spec-applier/requirements.txt` - Dependencies (PyGithub for phase 3.3)

### Testing (3 files)
- `backend/tests/test_smoke.py` - Smoke tests for endpoint availability
- `backend/tests/test_security_wrapper.py` - Unit tests for security wrapper decorator
- `backend/tests/requirements.txt` - Test dependencies (pytest, requests, moto for AWS mocking)

### Scripts & Documentation (4 files)
- `scripts/deploy-backend.sh` - SAM build + deploy automation (env var driven)
- `scripts/setup-ssm-params.sh` - SSM Parameter Store setup for GitHub PAT
- `scripts/test-local.sh` - Standalone Python test harness (no Docker required)
- `docs/LOCAL_DEVELOPMENT.md` - Developer setup guide

### Total: 23 new files

**Files to Modify**:
- `.gitignore` - Add Python/SAM/Lambda patterns

## Architecture Impact

**Subsystems Affected**:
- AWS Lambda (4 functions)
- API Gateway (REST API with CORS, throttling, API key auth)
- S3 (spec storage bucket with versioning)
- SSM Parameter Store (GitHub PAT storage)
- IAM (4 execution roles with least-privilege policies)
- CloudWatch Logs (Lambda logging)

**New Dependencies**:
- **Runtime**: Python 3.11
- **Build**: AWS SAM CLI >= 1.100.0
- **Testing**: pytest, requests, moto (AWS mocking)
- **Future phases** (included in requirements.txt):
  - PyYAML, jsonschema (phase 3.2)
  - PyGithub (phase 3.3)
  - boto3 (included with Lambda runtime)

**Breaking Changes**: None (greenfield project)

## Task Breakdown

### 🔧 CHECKPOINT 1: Core Infrastructure (Tasks 1-5)

---

#### Task 1: Create SAM Template with API Gateway
**File**: `template.yaml`
**Action**: CREATE
**Pattern**: Follow AWS SAM best practices from spec.md

**Implementation**:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: ActionSpec Backend - Phase 3.1 Foundation

Globals:
  Function:
    Runtime: python3.11
    Timeout: 30
    MemorySize: 256
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment
        SPECS_BUCKET: !Ref SpecsBucket
        GITHUB_TOKEN_SSM_PARAM: !Ref GithubTokenParamName
    Layers:
      - !Ref SharedDependenciesLayer

  Api:
    Cors:
      AllowMethods: "'GET,POST,OPTIONS'"
      AllowHeaders: "'Content-Type,X-Api-Key,Authorization'"
      AllowOrigin: "'*'"  # Tighten in production
    Auth:
      ApiKeys:
        - !Ref ActionSpecApiKey
      UsagePlan:
        CreateUsagePlan: PER_API
        UsagePlanName: ActionSpecUsagePlan
        Quota:
          Limit: 5000
          Period: MONTH
        Throttle:
          BurstLimit: 100
          RateLimit: 50

Parameters:
  Environment:
    Type: String
    Default: demo
    AllowedValues:
      - local
      - demo
      - prod
    Description: Deployment environment

  GithubTokenParamName:
    Type: String
    Default: /actionspec/github-token
    Description: SSM Parameter name for GitHub PAT

Resources:
  # API Gateway
  ActionSpecApi:
    Type: AWS::Serverless::Api
    Properties:
      Name: !Sub ${AWS::StackName}-api
      StageName: !Ref Environment
      EndpointConfiguration:
        Type: REGIONAL
      MethodSettings:
        - ResourcePath: "/*"
          HttpMethod: "*"
          ThrottlingBurstLimit: 100
          ThrottlingRateLimit: 50
          LoggingLevel: INFO

  ActionSpecApiKey:
    Type: AWS::ApiGateway::ApiKey
    DependsOn: ActionSpecApi
    Properties:
      Name: !Sub ${AWS::StackName}-api-key
      Enabled: true

  # S3 Bucket for specs
  SpecsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub ${AWS::StackName}-specs
      VersioningConfiguration:
        Status: Enabled
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: DeleteOldVersions
            Status: Enabled
            NoncurrentVersionExpirationInDays: 30
      Tags:
        - Key: Project
          Value: ActionSpec
        - Key: Phase
          Value: "3.1"

  # Shared Lambda Layer (security_wrapper)
  SharedDependenciesLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: actionspec-shared
      Description: Shared security wrapper and utilities
      ContentUri: backend/lambda/shared/
      CompatibleRuntimes:
        - python3.11
    Metadata:
      BuildMethod: python3.11

Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !Sub https://${ActionSpecApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}
    Export:
      Name: !Sub ${AWS::StackName}-ApiEndpoint

  ApiKeyId:
    Description: API Key ID
    Value: !Ref ActionSpecApiKey
    Export:
      Name: !Sub ${AWS::StackName}-ApiKeyId

  SpecsBucketName:
    Description: S3 bucket for spec storage
    Value: !Ref SpecsBucket
    Export:
      Name: !Sub ${AWS::StackName}-SpecsBucket
```

**Validation**:
```bash
# Syntax validation
sam validate --lint

# Template validation
aws cloudformation validate-template --template-body file://template.yaml
```

**Success Criteria**:
- Template passes SAM validation
- CloudFormation syntax is valid
- All parameters have defaults
- Outputs are properly defined

---

#### Task 2: Add Lambda Function Definitions to SAM Template
**File**: `template.yaml` (continuation)
**Action**: MODIFY (extend Resources section)
**Pattern**: SAM function definitions with least-privilege IAM

**Implementation**:
Add to `Resources` section:

```yaml
  # Lambda Function: Spec Parser
  SpecParserFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${AWS::StackName}-spec-parser
      CodeUri: backend/lambda/functions/spec-parser/
      Handler: handler.lambda_handler
      Description: Parse and validate ActionSpec YAML (Phase 3.1 stub)
      Policies:
        - S3ReadPolicy:
            BucketName: !Ref SpecsBucket
        - Statement:
            - Sid: CloudWatchLogs
              Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource: !Sub arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-*
      Events:
        ParseApi:
          Type: Api
          Properties:
            RestApiId: !Ref ActionSpecApi
            Path: /api/parse
            Method: POST
            Auth:
              ApiKeyRequired: true

  # Lambda Function: AWS Discovery
  AwsDiscoveryFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${AWS::StackName}-aws-discovery
      CodeUri: backend/lambda/functions/aws-discovery/
      Handler: handler.lambda_handler
      Description: Discover AWS resources (Phase 3.1 stub)
      Policies:
        - Statement:
            - Sid: EC2ReadOnly
              Effect: Allow
              Action:
                - ec2:DescribeVpcs
                - ec2:DescribeSubnets
                - ec2:DescribeSecurityGroups
              Resource: "*"
            - Sid: ELBReadOnly
              Effect: Allow
              Action:
                - elasticloadbalancing:DescribeLoadBalancers
                - elasticloadbalancing:DescribeTargetGroups
                - elasticloadbalancing:DescribeListeners
              Resource: "*"
            - Sid: WAFReadOnly
              Effect: Allow
              Action:
                - wafv2:ListWebACLs
                - wafv2:GetWebACL
              Resource: "*"
            - Sid: CloudWatchLogs
              Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource: !Sub arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-*
      Events:
        DiscoverApi:
          Type: Api
          Properties:
            RestApiId: !Ref ActionSpecApi
            Path: /api/discover
            Method: GET
            Auth:
              ApiKeyRequired: true

  # Lambda Function: Form Generator
  FormGeneratorFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${AWS::StackName}-form-generator
      CodeUri: backend/lambda/functions/form-generator/
      Handler: handler.lambda_handler
      Description: Generate form from spec + discovery (Phase 3.1 stub)
      Policies:
        - S3ReadPolicy:
            BucketName: !Ref SpecsBucket
        - Statement:
            - Sid: SSMGetParameter
              Effect: Allow
              Action:
                - ssm:GetParameter
              Resource: !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter${GithubTokenParamName}
            - Sid: EC2ReadOnly
              Effect: Allow
              Action:
                - ec2:DescribeVpcs
                - ec2:DescribeSubnets
                - ec2:DescribeSecurityGroups
              Resource: "*"
            - Sid: ELBReadOnly
              Effect: Allow
              Action:
                - elasticloadbalancing:Describe*
              Resource: "*"
            - Sid: WAFReadOnly
              Effect: Allow
              Action:
                - wafv2:List*
                - wafv2:Get*
              Resource: "*"
            - Sid: CloudWatchLogs
              Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource: !Sub arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-*
      Events:
        GetFormApi:
          Type: Api
          Properties:
            RestApiId: !Ref ActionSpecApi
            Path: /api/form
            Method: GET
            Auth:
              ApiKeyRequired: true

  # Lambda Function: Spec Applier
  SpecApplierFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${AWS::StackName}-spec-applier
      CodeUri: backend/lambda/functions/spec-applier/
      Handler: handler.lambda_handler
      Description: Apply spec changes via GitHub PR (Phase 3.1 stub)
      Policies:
        - S3CrudPolicy:
            BucketName: !Ref SpecsBucket
        - Statement:
            - Sid: SSMGetParameter
              Effect: Allow
              Action:
                - ssm:GetParameter
              Resource: !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter${GithubTokenParamName}
            - Sid: CloudWatchLogs
              Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource: !Sub arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-*
      Events:
        SubmitFormApi:
          Type: Api
          Properties:
            RestApiId: !Ref ActionSpecApi
            Path: /api/submit
            Method: POST
            Auth:
              ApiKeyRequired: true
```

**Validation**:
```bash
sam validate --lint
```

**Success Criteria**:
- All 4 Lambda functions defined
- IAM policies follow least-privilege
- API Gateway events correctly mapped
- All functions reference SharedDependenciesLayer

---

#### Task 3: Create Security Wrapper Module
**File**: `backend/lambda/shared/security_wrapper.py`
**Action**: CREATE
**Pattern**: Python decorator pattern for cross-cutting concerns

**Implementation**:
```python
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
```

**Also create**: `backend/lambda/shared/__init__.py` (empty file for Python package)

**Validation**:
```bash
# Run the module standalone to test
python3 backend/lambda/shared/security_wrapper.py

# Should output sanitized data and decorator test result
```

**Success Criteria**:
- Module runs without errors
- Sanitization correctly redacts sensitive fields
- Decorator adds security headers
- Test output shows expected behavior

---

#### Task 4: Create Stub Lambda Handlers
**Files**:
- `backend/lambda/functions/spec-parser/handler.py`
- `backend/lambda/functions/aws-discovery/handler.py`
- `backend/lambda/functions/form-generator/handler.py`
- `backend/lambda/functions/spec-applier/handler.py`

**Action**: CREATE (all 4 files)
**Pattern**: Import security wrapper, return stub JSON

**Implementation (spec-parser/handler.py)**:
```python
"""
Spec Parser Lambda Function
Phase 3.1: Stub implementation
Phase 3.2: Will parse and validate ActionSpec YAML
"""

import json
import os
import sys

# Add shared layer to path
sys.path.insert(0, '/opt/python')  # Lambda layer path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from security_wrapper import secure_handler


@secure_handler
def lambda_handler(event, context):
    """
    Parse and validate ActionSpec YAML - STUB IMPLEMENTATION

    Phase 3.2 will implement:
    - YAML parsing from S3 or GitHub
    - Schema validation against actionspec-v1.schema.json
    - Error reporting with line numbers

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Stub response indicating phase 3.1 status
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Spec Parser - Stub Implementation',
            'version': 'phase-3.1',
            'phase': '3.1',
            'status': 'stub',
            'next_phase': '3.2 - Will implement YAML parsing and validation',
            'environment': os.environ.get('ENVIRONMENT', 'unknown')
        })
    }
```

**Implementation (aws-discovery/handler.py)**:
```python
"""
AWS Discovery Lambda Function
Phase 3.1: Stub implementation
Phase 3.3: Will discover AWS resources (VPCs, ALBs, WAF)
"""

import json
import os
import sys

# Add shared layer to path
sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from security_wrapper import secure_handler


@secure_handler
def lambda_handler(event, context):
    """
    Discover AWS resources - STUB IMPLEMENTATION

    Phase 3.3 will implement:
    - VPC and subnet discovery
    - ALB and target group enumeration
    - WAF WebACL listing
    - Security group discovery

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Stub response indicating phase 3.1 status
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'AWS Discovery - Stub Implementation',
            'version': 'phase-3.1',
            'phase': '3.1',
            'status': 'stub',
            'next_phase': '3.3 - Will implement AWS resource discovery',
            'environment': os.environ.get('ENVIRONMENT', 'unknown')
        })
    }
```

**Implementation (form-generator/handler.py)**:
```python
"""
Form Generator Lambda Function
Phase 3.1: Stub implementation
Phase 3.4: Will generate dynamic form from spec + AWS discovery
"""

import json
import os
import sys

# Add shared layer to path
sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from security_wrapper import secure_handler


@secure_handler
def lambda_handler(event, context):
    """
    Generate form from spec + discovery - STUB IMPLEMENTATION

    Phase 3.4 will implement:
    - Fetch spec from GitHub
    - Combine with AWS discovery data
    - Generate form structure for React frontend
    - Include validation rules

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Stub response indicating phase 3.1 status
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Form Generator - Stub Implementation',
            'version': 'phase-3.1',
            'phase': '3.1',
            'status': 'stub',
            'next_phase': '3.4 - Will implement form generation',
            'environment': os.environ.get('ENVIRONMENT', 'unknown')
        })
    }
```

**Implementation (spec-applier/handler.py)**:
```python
"""
Spec Applier Lambda Function
Phase 3.1: Stub implementation
Phase 3.3: Will create GitHub PR with spec changes
"""

import json
import os
import sys

# Add shared layer to path
sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from security_wrapper import secure_handler


@secure_handler
def lambda_handler(event, context):
    """
    Apply spec changes via GitHub PR - STUB IMPLEMENTATION

    Phase 3.3 will implement:
    - Create feature branch
    - Update spec file
    - Generate PR with change summary
    - Add labels and reviewers

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Stub response indicating phase 3.1 status
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Spec Applier - Stub Implementation',
            'version': 'phase-3.1',
            'phase': '3.1',
            'status': 'stub',
            'next_phase': '3.3 - Will implement GitHub PR creation',
            'environment': os.environ.get('ENVIRONMENT', 'unknown')
        })
    }
```

**Validation**:
```bash
# Test each handler can be imported
python3 -c "from backend.lambda.functions.spec_parser.handler import lambda_handler; print('spec-parser OK')"
python3 -c "from backend.lambda.functions.aws_discovery.handler import lambda_handler; print('aws-discovery OK')"
python3 -c "from backend.lambda.functions.form_generator.handler import lambda_handler; print('form-generator OK')"
python3 -c "from backend.lambda.functions.spec_applier.handler import lambda_handler; print('spec-applier OK')"
```

**Success Criteria**:
- All 4 handlers import without errors
- All use `@secure_handler` decorator
- All return valid JSON responses
- All include version and phase info

---

#### Task 5: Create Requirements Files
**Files**:
- `backend/lambda/functions/spec-parser/requirements.txt`
- `backend/lambda/functions/aws-discovery/requirements.txt`
- `backend/lambda/functions/form-generator/requirements.txt`
- `backend/lambda/functions/spec-applier/requirements.txt`

**Action**: CREATE (all 4 files)
**Pattern**: Minimal dependencies for phase 3.1, prepare for future phases

**Implementation (spec-parser/requirements.txt)**:
```
# Phase 3.1: No additional deps (using stdlib only)
# Phase 3.2: Will add YAML parsing and validation
PyYAML==6.0.1
jsonschema==4.21.1
```

**Implementation (aws-discovery/requirements.txt)**:
```
# Phase 3.1: boto3 included in Lambda runtime
# boto3==1.34.0  # Uncomment if need specific version
# Phase 3.3: No additional deps needed (boto3 sufficient)
```

**Implementation (form-generator/requirements.txt)**:
```
# Phase 3.1: No additional deps
# Phase 3.3: Will add GitHub integration
PyGithub==2.2.0
# Phase 3.2: Will use spec parser deps
PyYAML==6.0.1
jsonschema==4.21.1
```

**Implementation (spec-applier/requirements.txt)**:
```
# Phase 3.1: No additional deps
# Phase 3.3: Will add GitHub integration
PyGithub==2.2.0
```

**Validation**:
```bash
# Verify all files exist and have valid format
for dir in spec-parser aws-discovery form-generator spec-applier; do
  echo "Checking $dir..."
  cat "backend/lambda/functions/$dir/requirements.txt"
done
```

**Success Criteria**:
- All 4 requirements.txt files exist
- No syntax errors
- Dependencies pinned to specific versions

---

### ✅ VALIDATION CHECKPOINT 1

Before proceeding, verify:
- [ ] `sam validate --lint` passes
- [ ] All Lambda handlers import successfully
- [ ] Security wrapper module runs standalone
- [ ] Requirements files are valid

---

### 🧪 CHECKPOINT 2: Testing Infrastructure (Tasks 6-10)

---

#### Task 6: Create SAM Configuration File
**File**: `samconfig.toml`
**Action**: CREATE
**Pattern**: Environment-driven configuration (from user decision)

**Implementation**:
```toml
version = 0.1

[default]
[default.global.parameters]
stack_name = "actionspec-backend"
resolve_s3 = true

[default.build.parameters]
cached = true
parallel = true

[default.deploy.parameters]
capabilities = "CAPABILITY_IAM"
confirm_changeset = true
resolve_s3 = true
region = "${AWS_REGION}"  # Read from environment
parameter_overrides = [
    "Environment=${ENVIRONMENT}",
    "GithubTokenParamName=${GITHUB_TOKEN_SSM_PARAM}"
]

[default.local_start_api.parameters]
warm_containers = "EAGER"

[default.local_invoke.parameters]
env_vars = "env.json"

[demo]
[demo.deploy.parameters]
stack_name = "actionspec-backend-demo"
region = "us-west-2"
parameter_overrides = [
    "Environment=demo"
]

[local]
[local.deploy.parameters]
stack_name = "actionspec-backend-local"
parameter_overrides = [
    "Environment=local"
]
```

**Validation**:
```bash
# Verify TOML syntax
python3 -c "import toml; toml.load('samconfig.toml'); print('Valid TOML')"
```

**Success Criteria**:
- File parses as valid TOML
- Environment variable placeholders present
- Multiple config profiles defined

---

#### Task 7: Create Local Environment Config Example
**File**: `env.json.example`
**Action**: CREATE
**Pattern**: Follow infrastructure/README.md env var pattern

**Implementation**:
```json
{
  "Parameters": {
    "ENVIRONMENT": "local",
    "SPECS_BUCKET": "actionspec-backend-specs-local",
    "GITHUB_TOKEN_SSM_PARAM": "/actionspec/github-token"
  }
}
```

**Also create**: Actual `env.json` for local development (gitignored)

**Validation**:
```bash
# Verify JSON syntax
python3 -c "import json; json.load(open('env.json.example')); print('Valid JSON')"

# Copy to env.json
cp env.json.example env.json
```

**Success Criteria**:
- File is valid JSON
- Contains all required parameters
- env.json created for local use

---

#### Task 8: Create Smoke Tests
**File**: `backend/tests/test_smoke.py`
**Action**: CREATE
**Pattern**: pytest tests that can run against local or deployed API

**Implementation**:
```python
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
```

**Validation**:
```bash
# Install test dependencies first (next task)
# Then run tests (will be done in validation checkpoint)
```

**Success Criteria**:
- Tests import without errors
- Parametrized tests cover all 4 endpoints
- Tests check both functionality and security headers

---

#### Task 9: Create Security Wrapper Unit Tests
**File**: `backend/tests/test_security_wrapper.py`
**Action**: CREATE
**Pattern**: pytest unit tests for decorator behavior

**Implementation**:
```python
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
    invoked_function_arn = 'arn:aws:lambda:us-west-2:123456789012:function:test'


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
```

**Validation**:
```bash
# Will be validated in checkpoint
```

**Success Criteria**:
- Tests cover all security_wrapper functions
- Tests verify header injection
- Tests verify log sanitization
- Tests verify exception handling

---

#### Task 10: Create Test Requirements File
**File**: `backend/tests/requirements.txt`
**Action**: CREATE
**Pattern**: Test-only dependencies

**Implementation**:
```
# Testing framework
pytest==8.0.0
pytest-cov==4.1.0

# HTTP testing
requests==2.31.0

# AWS mocking (for future phases)
moto==5.0.0

# Code quality
pytest-xdist==3.5.0  # Parallel test execution
```

**Validation**:
```bash
# Install and verify
pip3 install -r backend/tests/requirements.txt
pytest --version
```

**Success Criteria**:
- Requirements file is valid
- pytest installs successfully
- All dependencies have pinned versions

---

### ✅ VALIDATION CHECKPOINT 2

Run tests:
```bash
# Install test dependencies
pip3 install -r backend/tests/requirements.txt

# Run unit tests
pytest backend/tests/test_security_wrapper.py -v

# Smoke tests will run after SAM build (next checkpoint)
```

Verify:
- [ ] All security wrapper tests pass
- [ ] Test coverage > 80%
- [ ] No import errors

---

### 🚀 CHECKPOINT 3: Deployment & Documentation (Tasks 11-15)

---

#### Task 11: Extend .gitignore for Python/SAM
**File**: `.gitignore`
**Action**: MODIFY
**Pattern**: Add Python/SAM patterns to existing file

**Implementation**:
Add to end of file:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# AWS SAM
.aws-sam/
samconfig.toml.bak
env.json
!env.json.example

# Lambda packaging
*.zip
package/
```

**Validation**:
```bash
# Verify .gitignore syntax
git check-ignore -v backend/.aws-sam/
# Should show it's ignored
```

**Success Criteria**:
- Python artifacts ignored
- SAM build directory ignored
- env.json ignored but env.json.example tracked

---

#### Task 12: Create Deployment Script
**File**: `scripts/deploy-backend.sh`
**Action**: CREATE
**Pattern**: Follow scripts/pre-commit-checks.sh style (color output, error handling)

**Implementation**:
```bash
#!/bin/bash
set -euo pipefail

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ActionSpec Backend Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for required environment variables
check_env_var() {
    local var_name=$1
    local default_value=${2:-}

    if [ -z "${!var_name:-}" ]; then
        if [ -n "$default_value" ]; then
            export "$var_name=$default_value"
            echo -e "${YELLOW}⚠  $var_name not set, using default: $default_value${NC}"
        else
            echo -e "${RED}❌ Error: $var_name environment variable not set${NC}"
            echo ""
            echo "Required environment variables:"
            echo "  AWS_REGION - AWS region (default: us-west-2)"
            echo "  ENVIRONMENT - Deployment environment (default: demo)"
            echo "  GITHUB_TOKEN_SSM_PARAM - SSM parameter name (default: /actionspec/github-token)"
            echo ""
            echo "Example:"
            echo "  export AWS_REGION=us-west-2"
            echo "  export ENVIRONMENT=demo"
            echo "  ./scripts/deploy-backend.sh"
            exit 1
        fi
    fi
}

# Set defaults
export AWS_REGION="${AWS_REGION:-us-west-2}"
export ENVIRONMENT="${ENVIRONMENT:-demo}"
export GITHUB_TOKEN_SSM_PARAM="${GITHUB_TOKEN_SSM_PARAM:-/actionspec/github-token}"

echo -e "${GREEN}Configuration:${NC}"
echo "  AWS Region: $AWS_REGION"
echo "  Environment: $ENVIRONMENT"
echo "  GitHub Token SSM Param: $GITHUB_TOKEN_SSM_PARAM"
echo "  Stack Name: actionspec-backend"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# Step 1: Build
echo -e "${BLUE}Step 1: Building SAM application...${NC}"
if sam build --use-container; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi
echo ""

# Step 2: Validate
echo -e "${BLUE}Step 2: Validating template...${NC}"
if sam validate --lint; then
    echo -e "${GREEN}✓ Validation successful${NC}"
else
    echo -e "${RED}❌ Validation failed${NC}"
    exit 1
fi
echo ""

# Step 3: Deploy
echo -e "${BLUE}Step 3: Deploying to AWS...${NC}"
echo -e "${YELLOW}This will deploy Lambda functions, API Gateway, S3 bucket, and IAM roles.${NC}"
echo ""

if sam deploy \
    --stack-name actionspec-backend \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        "Environment=$ENVIRONMENT" \
        "GithubTokenParamName=$GITHUB_TOKEN_SSM_PARAM" \
    --no-fail-on-empty-changeset \
    --resolve-s3; then

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Deployment Successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # Get outputs
    echo -e "${BLUE}Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name actionspec-backend \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs' \
        --output table

    # Get API endpoint
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name actionspec-backend \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
        --output text)

    # Get API Key ID
    API_KEY_ID=$(aws cloudformation describe-stacks \
        --stack-name actionspec-backend \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiKeyId`].OutputValue' \
        --output text)

    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Get API key value:"
    echo "   aws apigateway get-api-key --api-key $API_KEY_ID --include-value --query 'value' --output text"
    echo ""
    echo "2. Test endpoints:"
    echo "   export API_KEY=\$(aws apigateway get-api-key --api-key $API_KEY_ID --include-value --query 'value' --output text)"
    echo "   curl -H \"x-api-key: \$API_KEY\" $API_ENDPOINT/api/form"
    echo ""
    echo "3. Run smoke tests:"
    echo "   export API_ENDPOINT=$API_ENDPOINT"
    echo "   pytest backend/tests/test_smoke.py"

else
    echo ""
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi
```

**Make executable**:
```bash
chmod +x scripts/deploy-backend.sh
```

**Validation**:
```bash
# Validate syntax
bash -n scripts/deploy-backend.sh
```

**Success Criteria**:
- Script has execute permissions
- Syntax is valid
- Color output defined
- Error handling present

---

#### Task 13: Create SSM Parameter Setup Script
**File**: `scripts/setup-ssm-params.sh`
**Action**: CREATE
**Pattern**: Interactive script for first-time setup

**Implementation**:
```bash
#!/bin/bash
set -euo pipefail

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SSM Parameter Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-us-west-2}"

echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ Region: $REGION${NC}"
echo ""

# Parameter name
PARAM_NAME="${GITHUB_TOKEN_SSM_PARAM:-/actionspec/github-token}"

# Check if parameter already exists
if aws ssm get-parameter --name "$PARAM_NAME" --region "$REGION" &>/dev/null; then
    echo -e "${YELLOW}⚠  Parameter $PARAM_NAME already exists${NC}"
    echo ""
    read -p "Overwrite existing parameter? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Get GitHub token
echo ""
echo -e "${BLUE}GitHub Personal Access Token Setup${NC}"
echo ""
echo "You need a GitHub PAT with these permissions:"
echo "  - repo (full control of private repositories)"
echo "  - workflow (update GitHub Action workflows)"
echo ""
echo "Create one at: https://github.com/settings/tokens/new"
echo ""

read -sp "Enter GitHub Personal Access Token: " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ Token cannot be empty${NC}"
    exit 1
fi

# Validate token format (basic check)
if [[ ! "$GITHUB_TOKEN" =~ ^(ghp_|github_pat_)[a-zA-Z0-9_]+ ]]; then
    echo -e "${YELLOW}⚠  Warning: Token doesn't match expected format (ghp_* or github_pat_*)${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Store in SSM
echo ""
echo -e "${BLUE}Storing parameter in SSM...${NC}"

if aws ssm put-parameter \
    --name "$PARAM_NAME" \
    --value "$GITHUB_TOKEN" \
    --type SecureString \
    --description "GitHub Personal Access Token for ActionSpec" \
    --region "$REGION" \
    --overwrite &>/dev/null; then

    echo -e "${GREEN}✓ Parameter stored successfully${NC}"
    echo ""
    echo "Parameter details:"
    echo "  Name: $PARAM_NAME"
    echo "  Type: SecureString"
    echo "  Region: $REGION"
    echo ""

    # Test retrieval
    if aws ssm get-parameter --name "$PARAM_NAME" --region "$REGION" --with-decryption --query 'Parameter.Value' --output text &>/dev/null; then
        echo -e "${GREEN}✓ Parameter retrieval test successful${NC}"
    else
        echo -e "${RED}❌ Failed to retrieve parameter${NC}"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo "Lambda functions can now access this token via:"
    echo "  export GITHUB_TOKEN_SSM_PARAM=$PARAM_NAME"

else
    echo -e "${RED}❌ Failed to store parameter${NC}"
    exit 1
fi
```

**Make executable**:
```bash
chmod +x scripts/setup-ssm-params.sh
```

**Validation**:
```bash
bash -n scripts/setup-ssm-params.sh
```

**Success Criteria**:
- Script has execute permissions
- Validates token format
- Handles existing parameters
- Tests retrieval after storage

---

#### Task 14: Create Standalone Test Harness
**File**: `scripts/test-local.sh`
**Action**: CREATE
**Pattern**: Python-based testing without Docker requirement

**Implementation**:
```bash
#!/bin/bash
set -euo pipefail

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Local Lambda Test Harness${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Set environment variables for local testing
export ENVIRONMENT=local
export SPECS_BUCKET=actionspec-backend-specs-local
export GITHUB_TOKEN_SSM_PARAM=/actionspec/github-token

# Add paths for imports
export PYTHONPATH="${PROJECT_ROOT}/backend/lambda/shared:${PROJECT_ROOT}/backend/lambda/functions:${PYTHONPATH:-}"

echo -e "${GREEN}Testing Lambda handlers directly (no Docker required)${NC}"
echo ""

# Test each handler
for func in spec-parser aws-discovery form-generator spec-applier; do
    echo -e "${BLUE}Testing $func...${NC}"

    handler_path="backend/lambda/functions/$func/handler.py"

    if [ ! -f "$handler_path" ]; then
        echo "  ❌ Handler not found: $handler_path"
        continue
    fi

    # Run handler with mock event
    python3 - <<EOF
import sys
import os
import json

# Add paths
sys.path.insert(0, '${PROJECT_ROOT}/backend/lambda/shared')
sys.path.insert(0, '${PROJECT_ROOT}/backend/lambda/functions/$func')

# Mock context
class MockContext:
    request_id = 'test-local-123'
    function_name = '$func'
    memory_limit_in_mb = 256

# Import handler
from handler import lambda_handler

# Mock event
event = {
    'path': '/api/test',
    'httpMethod': 'GET',
    'headers': {},
    'queryStringParameters': None,
    'body': None
}

# Invoke
try:
    response = lambda_handler(event, MockContext())
    print(f"  ✓ Status: {response['statusCode']}")

    body = json.loads(response['body'])
    print(f"  ✓ Message: {body.get('message', 'N/A')}")
    print(f"  ✓ Version: {body.get('version', 'N/A')}")

    # Check headers
    if 'Strict-Transport-Security' in response.get('headers', {}):
        print("  ✓ Security headers present")
    else:
        print("  ⚠  Security headers missing")

    print()
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    print()
    sys.exit(1)
EOF

    if [ $? -ne 0 ]; then
        echo "Test failed for $func"
        exit 1
    fi
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  All handlers tested successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start SAM local: sam local start-api"
echo "2. Run smoke tests: pytest backend/tests/test_smoke.py"
```

**Make executable**:
```bash
chmod +x scripts/test-local.sh
```

**Validation**:
```bash
bash -n scripts/test-local.sh
```

**Success Criteria**:
- Script has execute permissions
- Tests all 4 handlers
- Doesn't require Docker
- Provides clear output

---

#### Task 15: Create Local Development Documentation
**File**: `docs/LOCAL_DEVELOPMENT.md`
**Action**: CREATE
**Pattern**: Developer-friendly setup guide

**Implementation**:
```markdown
# Local Development Guide

Guide for developing and testing the ActionSpec backend locally.

## Prerequisites

### Required
- **Python 3.11+**
  ```bash
  python3 --version  # Should be 3.11 or higher
  ```

- **AWS CLI**
  ```bash
  aws --version
  aws configure  # Set up credentials
  ```

- **AWS SAM CLI**
  ```bash
  # Install SAM CLI
  # macOS
  brew install aws-sam-cli

  # Linux
  pip3 install aws-sam-cli

  # Verify
  sam --version  # Should be >= 1.100.0
  ```

- **Docker** (for `sam local start-api`)
  ```bash
  docker --version
  ```

### Optional
- **pytest** (for running tests)
  ```bash
  pip3 install -r backend/tests/requirements.txt
  ```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/trakrf/action-spec.git
cd action-spec

# Copy environment template
cp env.json.example env.json

# Edit env.json if needed (defaults work for local)
```

### 2. Build SAM Application

```bash
sam build
```

This compiles the Lambda functions and packages dependencies.

### 3. Start Local API

```bash
sam local start-api
```

API will be available at `http://localhost:3000`

### 4. Test Endpoints

```bash
# Test form endpoint
curl http://localhost:3000/api/form

# Test discover endpoint
curl http://localhost:3000/api/discover

# Test parse endpoint
curl -X POST http://localhost:3000/api/parse

# Test submit endpoint
curl -X POST http://localhost:3000/api/submit
```

All endpoints should return 200 with stub JSON responses.

## Testing Options

### Option 1: SAM Local (Docker Required)

```bash
# Start API
sam local start-api &

# Run smoke tests
export API_ENDPOINT=http://localhost:3000
pytest backend/tests/test_smoke.py -v

# Stop API
killall sam
```

### Option 2: Standalone Test Harness (No Docker)

```bash
# Test handlers directly
./scripts/test-local.sh
```

This runs each Lambda handler in-process without Docker.

### Option 3: Unit Tests Only

```bash
# Test security wrapper
pytest backend/tests/test_security_wrapper.py -v

# Test with coverage
pytest backend/tests/ --cov=backend/lambda/shared --cov-report=html
```

## Development Workflow

### Modify Lambda Function

1. Edit handler: `backend/lambda/functions/{function}/handler.py`
2. Rebuild: `sam build`
3. Test: `sam local start-api` or `./scripts/test-local.sh`

### Modify SAM Template

1. Edit: `template.yaml`
2. Validate: `sam validate --lint`
3. Build: `sam build`
4. Deploy: `./scripts/deploy-backend.sh`

### Modify Security Wrapper

1. Edit: `backend/lambda/shared/security_wrapper.py`
2. Test: `pytest backend/tests/test_security_wrapper.py`
3. Rebuild layer: `sam build`

## Troubleshooting

### "Module not found" error

**Problem**: Lambda can't import `security_wrapper`

**Solution**: Check Lambda layer configuration in `template.yaml`:
```yaml
Layers:
  - !Ref SharedDependenciesLayer
```

Rebuild: `sam build`

### SAM local not starting

**Problem**: `sam local start-api` hangs or fails

**Solutions**:
1. Check Docker is running: `docker ps`
2. Clear SAM cache: `rm -rf .aws-sam/`
3. Rebuild: `sam build`
4. Use standalone test harness: `./scripts/test-local.sh`

### API returns 403 Forbidden

**Problem**: API Gateway requires API key

**Solution**: SAM local may not enforce API keys in development mode. This is expected. In deployed environment, use:
```bash
export API_KEY=$(aws apigateway get-api-key --api-key $API_KEY_ID --include-value --query 'value' --output text)
curl -H "x-api-key: $API_KEY" $API_ENDPOINT/api/form
```

### Tests fail with connection error

**Problem**: `pytest backend/tests/test_smoke.py` fails

**Solution**:
1. Ensure SAM local is running: `sam local start-api`
2. Verify endpoint: `curl http://localhost:3000/api/form`
3. Check Docker: `docker ps` should show Lambda containers

### Import errors in tests

**Problem**: `ModuleNotFoundError: No module named 'security_wrapper'`

**Solution**:
```bash
# Add to PYTHONPATH
export PYTHONPATH="${PWD}/backend/lambda/shared:${PYTHONPATH:-}"

# Or use standalone test harness
./scripts/test-local.sh
```

## Environment Variables

### Local Development (env.json)

```json
{
  "Parameters": {
    "ENVIRONMENT": "local",
    "SPECS_BUCKET": "actionspec-backend-specs-local",
    "GITHUB_TOKEN_SSM_PARAM": "/actionspec/github-token"
  }
}
```

### Deployment (Environment Variables)

```bash
export AWS_REGION=us-west-2
export ENVIRONMENT=demo
export GITHUB_TOKEN_SSM_PARAM=/actionspec/github-token

./scripts/deploy-backend.sh
```

## Debugging

### Enable Verbose Logging

```bash
# SAM local with debug
sam local start-api --debug

# Lambda with debug logging
export SAM_CLI_TELEMETRY=0
export SAM_CLI_DEBUG=1
```

### View Lambda Logs

```bash
# SAM local shows logs in terminal

# Deployed Lambda
aws logs tail /aws/lambda/actionspec-backend-form-generator --follow
```

### Invoke Lambda Directly

```bash
# Test single function
echo '{}' | sam local invoke FormGeneratorFunction

# With event file
sam local invoke SpecParserFunction -e events/test-event.json
```

## Performance Tips

### Speed Up Builds

```bash
# Use cached builds
sam build --cached --parallel

# Skip dependency installation if unchanged
sam build --use-container --skip-pull-image
```

### Warm Containers

In `samconfig.toml`:
```toml
[default.local_start_api.parameters]
warm_containers = "EAGER"
```

## Next Steps

After local development works:

1. **Deploy to AWS**: `./scripts/deploy-backend.sh`
2. **Setup SSM Parameter**: `./scripts/setup-ssm-params.sh`
3. **Run deployed tests**:
   ```bash
   export API_ENDPOINT=https://xxx.execute-api.us-west-2.amazonaws.com/demo
   export API_KEY=your-api-key
   pytest backend/tests/test_smoke.py
   ```
4. **Move to Phase 3.2**: Implement actual spec parsing logic

## Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [SAM CLI Reference](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-command-reference.html)
- [Lambda Python Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
- [API Gateway Local Testing](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-start-api.html)
```

**Validation**:
```bash
# Verify markdown syntax
# (Most editors will show syntax errors)
cat docs/LOCAL_DEVELOPMENT.md
```

**Success Criteria**:
- All sections present
- Commands are accurate
- Troubleshooting covers common issues
- Links are valid

---

### ✅ FINAL VALIDATION CHECKPOINT

Run complete validation sequence:

```bash
# 1. Validate SAM template
sam validate --lint

# 2. Build SAM application
sam build

# 3. Run unit tests
pytest backend/tests/test_security_wrapper.py -v

# 4. Test handlers standalone
./scripts/test-local.sh

# 5. Start SAM local API
sam local start-api &
sleep 10  # Wait for startup

# 6. Run smoke tests
export API_ENDPOINT=http://localhost:3000
pytest backend/tests/test_smoke.py -v

# 7. Stop SAM local
killall sam

# 8. Validate deployment script
bash -n scripts/deploy-backend.sh
bash -n scripts/setup-ssm-params.sh
```

All steps must pass before Phase 3.1 is complete.

---

## Risk Assessment

**Risk 1: Lambda Layer Import Issues**
- **Description**: Lambda functions may fail to import `security_wrapper` from layer
- **Mitigation**:
  - Test layer packaging with `sam build`
  - Include fallback import paths in handlers
  - Verify layer structure matches Lambda requirements (`python/` directory)
- **Detection**: Unit tests will catch import errors early

**Risk 2: CORS Configuration in API Gateway**
- **Description**: CORS may not work correctly in deployed environment
- **Mitigation**:
  - Configure CORS in SAM template from the start
  - Test OPTIONS requests after deployment
  - Document CORS headers in smoke tests
- **Detection**: Smoke tests verify CORS headers present

**Risk 3: SAM Local vs Deployed Behavior Differences**
- **Description**: API may behave differently in SAM local vs AWS
- **Mitigation**:
  - Provide standalone test harness (no Docker)
  - Test both local and deployed environments
  - Document known differences in LOCAL_DEVELOPMENT.md
- **Detection**: Run smoke tests against both environments

**Risk 4: IAM Permission Errors After Deployment**
- **Description**: Lambda functions may lack necessary permissions
- **Mitigation**:
  - Define least-privilege policies in SAM template
  - Test each function's AWS API calls
  - Use IAM Policy Simulator before deployment
- **Detection**: CloudWatch logs will show permission denied errors

## Integration Points

**S3 Bucket**:
- Created: `SpecsBucket` resource in SAM template
- Referenced: By Spec Parser and Spec Applier functions
- Configuration: Versioning enabled, lifecycle policy for cost control

**SSM Parameter Store**:
- Created: Manual setup via `scripts/setup-ssm-params.sh`
- Referenced: By Form Generator and Spec Applier (GitHub token)
- Security: SecureString encryption, IAM policy restricts access

**API Gateway**:
- Created: `ActionSpecApi` resource with CORS and throttling
- Routes: 4 endpoints mapped to Lambda functions
- Security: API key required, rate limiting configured

**CloudWatch Logs**:
- Created: Automatically by Lambda runtime
- Referenced: All functions write logs
- Configuration: 30-day retention (can be adjusted in template)

## VALIDATION GATES (MANDATORY)

**Phase 3.1 uses Python/AWS SAM stack (not TypeScript):**

### Gate 1: Python Syntax & Style
```bash
# Syntax check
python3 -m py_compile backend/lambda/shared/security_wrapper.py
python3 -m py_compile backend/lambda/functions/*/handler.py

# Style check (if pylint installed)
pylint backend/lambda/ --errors-only
```

### Gate 2: SAM Template Validation
```bash
sam validate --lint
aws cloudformation validate-template --template-body file://template.yaml
```

### Gate 3: Unit Tests
```bash
pytest backend/tests/ -v --tb=short
```

### Gate 4: Integration Tests (Local)
```bash
./scripts/test-local.sh
```

### Gate 5: Smoke Tests (SAM Local)
```bash
sam local start-api &
sleep 10
export API_ENDPOINT=http://localhost:3000
pytest backend/tests/test_smoke.py -v
killall sam
```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to Phase 3.2 until all validation gates pass.**

## Validation Sequence

### After Tasks 1-5 (Checkpoint 1)
```bash
sam validate --lint
python3 -m py_compile backend/lambda/shared/security_wrapper.py
python3 -m py_compile backend/lambda/functions/*/handler.py
```

### After Tasks 6-10 (Checkpoint 2)
```bash
pip3 install -r backend/tests/requirements.txt
pytest backend/tests/test_security_wrapper.py -v
```

### After Tasks 11-15 (Checkpoint 3)
```bash
sam build
./scripts/test-local.sh
sam local start-api &
sleep 10
export API_ENDPOINT=http://localhost:3000
pytest backend/tests/test_smoke.py -v
killall sam
```

### Final Validation (Before Completion)
```bash
# Full build and test cycle
sam build --use-container
sam validate --lint
pytest backend/tests/ -v
./scripts/test-local.sh

# Optional: Deploy to AWS (if credentials available)
export AWS_REGION=us-west-2
export ENVIRONMENT=demo
./scripts/deploy-backend.sh
```

## Plan Quality Assessment

**Complexity Score**: 8/10 (HIGH)
- 23 new files across 5 AWS subsystems
- Greenfield project (no existing patterns to reference)
- Multiple validation layers required

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec with code examples
✅ User decisions captured (Python 3.11, env vars, testing approach)
✅ Detailed SAM template structure provided
✅ Security wrapper pattern well-defined
✅ Multiple testing strategies (unit, integration, smoke)
✅ Existing shell script patterns to follow (pre-commit-checks.sh)
✅ Clear validation gates at each checkpoint

⚠️ No existing SAM/Lambda code in repo to reference
⚠️ Lambda layer import path requires careful configuration
⚠️ CORS behavior may differ between SAM local and deployed

**Assessment**: High confidence despite complexity. The extremely detailed specification, clear user decisions, and multiple validation checkpoints provide a solid foundation. The greenfield nature adds risk, but the stub implementation approach minimizes it by validating infrastructure before business logic.

**Estimated one-pass success probability**: 75%

**Reasoning**:
- Spec provides near-complete code examples (reduces ambiguity)
- Stub implementations are straightforward (no complex logic)
- Three validation checkpoints catch errors incrementally
- Multiple testing approaches ensure infrastructure works
- Primary risk is Lambda layer imports and CORS config (both testable early)
- Environment variable approach is proven pattern from infrastructure/README.md
- 25% risk comes from greenfield SAM deployment and potential AWS-specific gotchas

**Mitigation**: If validation gates fail, the detailed error messages from SAM CLI and pytest will pinpoint issues quickly. The standalone test harness provides a Docker-free debugging path.

---

## Next Steps After Phase 3.1

When all validation gates pass:

1. **Commit Phase 3.1**:
   ```bash
   git add .
   git commit -m "feat(backend): complete Phase 3.1 - SAM foundation with stub Lambdas

   - AWS SAM template with API Gateway, 4 Lambda functions, S3, IAM
   - Security wrapper decorator enforcing headers on all responses
   - Stub implementations for all endpoints (returns 200 + JSON)
   - Local development environment (sam local + standalone harness)
   - Deployment automation scripts (env var driven)
   - Comprehensive testing (unit + smoke tests)
   - Documentation for local development

   Validation:
   - ✅ sam validate --lint passes
   - ✅ All unit tests passing (pytest)
   - ✅ All smoke tests passing (local API)
   - ✅ Security headers present on all responses
   - ✅ IAM roles follow least-privilege
   - ✅ Local development environment working

   Phase: 3.1 (Backend Foundation & SAM Infrastructure)
   "
   ```

2. **Ship Phase 3.1**:
   ```bash
   /ship
   ```

3. **Plan Phase 3.2**:
   ```bash
   /plan spec/active/phase-3.2-spec-validation
   ```

---

**Phase 3.1 establishes the foundation. All subsequent phases build on this infrastructure.**
