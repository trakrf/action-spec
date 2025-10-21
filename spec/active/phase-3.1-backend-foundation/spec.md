# Feature: Phase 3.1 - Backend Foundation & SAM Infrastructure

## Origin
This specification emerged from the Phase 3 work breakdown planning for the ActionSpec project. Phase 3.1 establishes the foundational backend infrastructure that all subsequent application logic phases (3.2-3.5) will build upon.

## Outcome
A deployable AWS Serverless Application Model (SAM) backend with:
- Working API Gateway endpoint (local and AWS)
- 4 scaffolded Lambda functions with proper security wrappers
- Secure credential management via SSM Parameter Store
- S3 bucket for spec storage
- Complete local development environment
- Deployment automation

**Success Definition**: A developer can clone the repo, run `sam local start-api`, and get proper HTTP responses with security headers from all endpoints.

## User Story
**As a** backend developer working on Phases 3.2-3.5
**I want** a solid, secure, deployable Lambda foundation with local dev support
**So that** I can focus on implementing business logic without worrying about infrastructure boilerplate

**As a** security-conscious engineer maintaining a public portfolio project
**I want** security headers and IAM policies enforced at the infrastructure level
**So that** security cannot be accidentally bypassed in future code changes

## Context

**Discovery**:
- ActionSpec is a public demo project showcasing infrastructure automation
- Phase 3 implements the application logic layer (Lambdas + React frontend)
- Security is paramount - this will be publicly visible on GitHub
- Local development velocity is critical for the 3-4 week timeline

**Current State**:
- Project has PRD.md with detailed requirements
- Repository structure planned but not implemented
- No backend infrastructure exists yet
- Phases 0-2 (security foundation, core infrastructure) are prerequisites

**Desired State**:
- Working SAM application deployable to AWS
- All 4 Lambda functions scaffolded and returning stub responses
- Local development environment functional
- Security wrapper applied to all functions
- Can run `sam build && sam deploy` successfully

## Technical Requirements

### 1. AWS SAM Template (`template.yaml`)

**Infrastructure as Code**:
- SAM template defining complete backend stack
- API Gateway with REGIONAL endpoint configuration
- All 4 Lambda function definitions (stub implementations)
- S3 bucket for spec file storage with versioning
- SSM Parameter references for secrets (GitHub PAT)
- IAM roles following least-privilege principle

**API Gateway Configuration**:
```yaml
Globals:
  Api:
    Cors:
      AllowMethods: "'GET,POST,OPTIONS'"
      AllowHeaders: "'Content-Type,X-Api-Key'"
      AllowOrigin: "'*'"  # Tighten in production
    Auth:
      ApiKeyRequired: true  # API key enforcement
    MethodSettings:
      - ResourcePath: "/*"
        HttpMethod: "*"
        ThrottlingBurstLimit: 100
        ThrottlingRateLimit: 50
```

**Key Points**:
- CORS configured from the start (mitigates Phase 3 risk)
- API key required for all endpoints
- Throttling limits prevent abuse
- Regional endpoint (not edge-optimized) for cost control

### 2. Lambda Function Scaffolding

**All 4 Functions Must Exist** (stub implementations):

**A. Spec Parser** (`backend/lambda/functions/spec-parser/handler.py`)
```python
@secure_handler
def lambda_handler(event, context):
    """Parse and validate ActionSpec YAML - STUB"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Spec Parser - Stub Implementation',
            'version': 'phase-3.1'
        })
    }
```

**B. AWS Discovery** (`backend/lambda/functions/aws-discovery/handler.py`)
```python
@secure_handler
def lambda_handler(event, context):
    """Discover AWS resources - STUB"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'AWS Discovery - Stub Implementation',
            'version': 'phase-3.1'
        })
    }
```

**C. Form Generator** (`backend/lambda/functions/form-generator/handler.py`)
```python
@secure_handler
def lambda_handler(event, context):
    """Generate form from spec + discovery - STUB"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Form Generator - Stub Implementation',
            'version': 'phase-3.1'
        })
    }
```

**D. Spec Applier** (`backend/lambda/functions/spec-applier/handler.py`)
```python
@secure_handler
def lambda_handler(event, context):
    """Apply spec changes via GitHub PR - STUB"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Spec Applier - Stub Implementation',
            'version': 'phase-3.1'
        })
    }
```

**Requirements**:
- All functions use `@secure_handler` decorator (no exceptions)
- All return valid HTTP responses (200 status, JSON body)
- All have proper error handling structure (even in stubs)
- All include version identifier for debugging

### 3. Security Wrapper Module

**Critical Component**: This enforces security across all Lambda functions.

**Location**: `backend/lambda/shared/security_wrapper.py`

**Functionality**:
- Add security headers to ALL responses
- Validate API key from API Gateway
- Sanitize logs (never log sensitive fields)
- Rate limiting per IP (in-memory cache with TTL)
- Block suspicious patterns in requests
- Wrap all exceptions with safe error messages

**Required Security Headers**:
```python
SECURITY_HEADERS = {
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'",
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
}
```

**Sensitive Field Filtering**:
```python
SENSITIVE_FIELDS = {
    'authorization', 'x-api-key', 'cookie', 'password',
    'secret', 'token', 'aws', 'key'
}
```

**Decorator Pattern** (must be importable):
```python
from shared.security_wrapper import secure_handler

@secure_handler
def lambda_handler(event, context):
    # Business logic here - security handled automatically
    pass
```

### 4. IAM Roles and Policies

**Least-Privilege Requirements**:

**Spec Parser Role**:
- `s3:GetObject` on specs bucket only
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**AWS Discovery Role**:
- `ec2:DescribeVpcs`, `ec2:DescribeSubnets`, `ec2:DescribeSecurityGroups`
- `elasticloadbalancing:Describe*` (read-only)
- `wafv2:List*`, `wafv2:Get*` (read-only)
- `logs:*` for CloudWatch

**Form Generator Role**:
- All permissions from Spec Parser + AWS Discovery
- `ssm:GetParameter` with `WithDecryption` for GitHub token

**Spec Applier Role**:
- `s3:PutObject` on specs bucket
- `ssm:GetParameter` with `WithDecryption` for GitHub token
- `logs:*` for CloudWatch

**Critical**: No wildcard permissions (`*`), no admin roles, no cross-account access.

### 5. SSM Parameter Store Configuration

**GitHub PAT Storage**:
```bash
aws ssm put-parameter \
  --name /actionspec/github-token \
  --type SecureString \
  --value "ghp_xxxxxxxxxxxx" \
  --description "GitHub Personal Access Token for ActionSpec"
```

**SAM Template Reference**:
```yaml
Environment:
  Variables:
    GITHUB_TOKEN_SSM_PARAM: /actionspec/github-token
```

**Lambda Runtime Retrieval**:
```python
ssm = boto3.client('ssm')
token = ssm.get_parameter(
    Name=os.environ['GITHUB_TOKEN_SSM_PARAM'],
    WithDecryption=True
)['Parameter']['Value']
```

**Requirements**:
- Never hardcode tokens in code or environment variables
- Use SecureString type for encryption at rest
- Cache parameter lookups (don't fetch on every request)

### 6. S3 Bucket for Specs Storage

**Configuration**:
```yaml
SpecsBucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: !Sub "${AWS::StackName}-specs"
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
```

**Requirements**:
- Versioning enabled (audit trail for spec changes)
- No public access (private bucket only)
- Lifecycle policy to manage costs
- Bucket name derived from stack name (no hardcoding)

### 7. Local Development Environment

**Setup Requirements**:
```bash
# Must work with these commands
sam build
sam local start-api
curl http://localhost:3000/form
```

**Local Environment File** (`env.json`):
```json
{
  "Parameters": {
    "GITHUB_TOKEN_SSM_PARAM": "/actionspec/github-token",
    "SPECS_BUCKET": "actionspec-demo-specs-local",
    "ENVIRONMENT": "local"
  }
}
```

**Documentation** (`docs/LOCAL_DEVELOPMENT.md`):
- Prerequisites (SAM CLI, Docker, Python 3.12)
- Installation steps
- Running local API
- Testing endpoints with curl/Postman
- Troubleshooting common issues

### 8. Basic Smoke Tests

**Test Suite** (`backend/tests/test_smoke.py`):
```python
def test_all_endpoints_return_200():
    """All Lambda functions return 200 with stub responses"""
    endpoints = [
        '/spec-parser',
        '/aws-discovery',
        '/form',
        '/form/submit'
    ]
    for endpoint in endpoints:
        response = requests.get(f"http://localhost:3000{endpoint}")
        assert response.status_code == 200

def test_security_headers_present():
    """All responses include required security headers"""
    response = requests.get("http://localhost:3000/form")
    assert 'Strict-Transport-Security' in response.headers
    assert 'Content-Security-Policy' in response.headers
    assert 'X-Frame-Options' in response.headers

def test_api_key_required():
    """Endpoints reject requests without API key"""
    response = requests.get("http://localhost:3000/form")
    # SAM local may not enforce API key - check in AWS deployment
```

**Requirements**:
- pytest framework
- Tests can run against `sam local` or deployed API
- All tests pass before Phase 3.1 is complete

## Implementation Structure

```
action-spec/
├── template.yaml                          # SAM template (main deliverable)
├── backend/
│   ├── lambda/
│   │   ├── shared/
│   │   │   ├── __init__.py
│   │   │   └── security_wrapper.py        # Security decorator module
│   │   └── functions/
│   │       ├── spec-parser/
│   │       │   ├── handler.py             # Stub implementation
│   │       │   └── requirements.txt       # PyYAML, jsonschema (for 3.2)
│   │       ├── aws-discovery/
│   │       │   ├── handler.py             # Stub implementation
│   │       │   └── requirements.txt       # boto3
│   │       ├── form-generator/
│   │       │   ├── handler.py             # Stub implementation
│   │       │   └── requirements.txt       # PyGithub (for 3.3)
│   │       └── spec-applier/
│   │           ├── handler.py             # Stub implementation
│   │           └── requirements.txt       # PyGithub (for 3.3)
│   └── tests/
│       ├── test_smoke.py                  # Basic endpoint tests
│       └── test_security_wrapper.py       # Security wrapper unit tests
├── docs/
│   └── LOCAL_DEVELOPMENT.md               # Local setup guide
├── scripts/
│   ├── deploy-backend.sh                  # SAM build + deploy wrapper
│   └── setup-ssm-params.sh                # SSM parameter creation
└── env.json.example                       # Local development config
```

## Validation Criteria

**Phase 3.1 is complete when:**

- [ ] **Local Development Works**
  - `sam build` completes without errors
  - `sam local start-api` starts successfully
  - All 4 endpoints return 200 responses
  - Security headers present in all responses

- [ ] **AWS Deployment Works**
  - `sam deploy --guided` completes successfully
  - API Gateway endpoint accessible via HTTPS
  - All Lambda functions visible in AWS Console
  - S3 bucket created with versioning enabled
  - SSM parameter accessible by Form Generator and Spec Applier

- [ ] **Security Baseline Established**
  - All Lambda functions use `@secure_handler` decorator
  - No function can return response without security headers
  - API Gateway requires API key
  - IAM roles follow least-privilege (verified with IAM Policy Simulator)
  - No secrets in code or environment variables

- [ ] **Foundation for Future Phases**
  - Adding new Lambda function requires only SAM template update
  - Security wrapper is importable and reusable
  - requirements.txt includes dependencies for phases 3.2-3.3
  - Structure supports easy expansion

- [ ] **Documentation Complete**
  - LOCAL_DEVELOPMENT.md tested by external developer
  - All scripts have usage comments
  - SAM template has descriptive comments
  - env.json.example provided with clear instructions

- [ ] **Tests Passing**
  - `pytest backend/tests/` passes 100%
  - Smoke tests validate all endpoints
  - Security wrapper unit tests cover header injection and sanitization

## Non-Goals (Explicitly Out of Scope for 3.1)

- ❌ Business logic implementation (comes in 3.2-3.5)
- ❌ Real GitHub integration (stub responses only in 3.1)
- ❌ Actual spec parsing logic (scaffolded in 3.1, implemented in 3.2)
- ❌ AWS resource discovery implementation (comes in 3.3)
- ❌ React frontend (Phase 3.4)
- ❌ CI/CD pipelines (Phase 3.5)
- ❌ Comprehensive E2E tests (Phase 3.5)

## Key Decisions & Context

**Decision: Why SAM instead of raw CloudFormation/Terraform?**
- SAM provides local development (`sam local start-api`)
- Simpler syntax for serverless applications
- Good fit for YAGNI principle (no over-engineering)
- Easy migration to Terraform later if needed

**Decision: Why stub implementations vs waiting for 3.2?**
- Validates infrastructure works before adding complexity
- Enables parallel work (frontend dev can start mocking against stubs)
- Catches deployment issues early (API Gateway config, IAM roles)
- Provides clear success criteria for Phase 3.1

**Decision: Why security wrapper as decorator vs middleware?**
- Python decorators are simple and explicit
- Impossible to forget (linter can check for `@secure_handler`)
- Easier to test in isolation
- Familiar pattern for Python developers

**Concern: Lambda cold starts affecting UX**
- Addressed in Phase 3.5 with provisioned concurrency
- Phase 3.1 establishes baseline performance metrics
- Not a blocker for foundational work

**Concern: CORS issues with API Gateway**
- Mitigated by configuring CORS in SAM template from day 1
- Testing with frontend in Phase 3.4 will validate
- Preflight OPTIONS requests handled automatically by API Gateway

## Conversation References

**Key Insight**:
> "This phase represents the core application logic that transforms ActionSpec from infrastructure to a working product."

**Decision**:
> "Let's call those phases 3.1 - 3.5" - Established naming convention for sub-phases

**Requirement**:
> "AWS SAM template with API Gateway configuration" - SAM chosen over other IaC tools

**Success Criteria**:
> "`sam local start-api` runs successfully" - Local development is first-class requirement

**Security Emphasis**:
> "This is a PUBLIC open-source project showcasing enterprise patterns while maintaining security appropriate for portfolio demonstration."

## Effort Estimate

**Time**: 3-5 days

**Breakdown**:
- Day 1: SAM template + basic Lambda scaffolding
- Day 2: Security wrapper implementation + IAM roles
- Day 3: S3 bucket, SSM parameters, local dev setup
- Day 4: Testing, documentation, deployment validation
- Day 5: Buffer for unexpected issues (CORS, IAM policies, etc.)

**Developer Profile**: Mid-level backend engineer familiar with AWS Lambda and Python

---

## Next Steps

After Phase 3.1 completion:
1. **Phase 3.2**: Implement actual spec parsing and validation logic
2. **Phase 3.3**: Add GitHub and AWS integration
3. **Phase 3.4**: Build Form Generator and React frontend
4. **Phase 3.5**: Complete testing and deployment automation

**Immediate Action**: Review this spec and confirm it captures Phase 3.1 requirements accurately.
