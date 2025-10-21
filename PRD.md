# ActionSpec - Infrastructure Specifications to GitHub Actions
## Product Requirements Document & Implementation Guide

> **"Turn infrastructure specifications into deployable GitHub Actions"**

---

## About This Project

**ActionSpec** is an open-source demonstration of YAML-driven Infrastructure as Code, showcasing how specification files can drive GitHub Actions workflows for automated infrastructure deployment. Built as both a portfolio piece and a practical template for teams using GitOps patterns.

### 🎯 **Perfect For:**
- Teams wanting to simplify infrastructure deployment
- Organizations adopting GitOps practices  
- Anyone needing template-driven infrastructure automation
- Demonstrating modern DevOps patterns (great for portfolios!)

### 🛡️ **Core Features:**
- YAML specifications drive all infrastructure
- GitHub Actions automation built-in
- AWS WAF deployment with one config change
- Cost-optimized for demos (<$5/month)
- Security-first design for public repos

---

## Executive Summary

ActionSpec demonstrates how YAML specifications can drive infrastructure deployment through GitHub Actions. This **PUBLIC** open-source project showcases enterprise patterns while maintaining security appropriate for portfolio demonstration.

### ⚠️ Security Notice
This project is designed from the ground up to be safely deployed in public. All examples use generic configurations, sanitized schemas, and defensive coding practices suitable for portfolio demonstration.

### 🎯 Project Philosophy: YAGNI
Given tight timelines (when aren't they?), this project follows strict YAGNI (You Aren't Gonna Need It) principles. Every feature directly supports the core demo. No custom GitHub Actions, no complex abstractions - just clean, working code that demonstrates the concept.

## Project Overview

### Vision
Demonstrate enterprise-grade infrastructure automation patterns through a secure, cost-effective platform that can be safely showcased in a public portfolio.

### Core Demonstrations
1. **Specification-Driven Infrastructure** - YAML specs become real infrastructure
2. **Security Through Simplicity** - Deploy AWS WAF with a single spec change
3. **GitOps Workflow** - Every change tracked through GitHub Actions
4. **Template for Teams** - Fork and adapt for your own infrastructure

### Target Audience
- DevOps teams seeking automation patterns
- Architects evaluating GitOps workflows
- Security teams interested in automated controls
- Open source community building similar tools
- Potential employers (it's a portfolio piece!)

## Security-First Architecture

### Public Repository Safety Measures

```yaml
# What This Demo Contains:
- Generic infrastructure patterns
- Sanitized configuration examples  
- Public cloud best practices
- Educational security controls

# What This Demo Never Contains:
- Real customer data or patterns
- Actual AWS account IDs
- Production CIDR blocks
- Proprietary business logic
- Sensitive configuration
```

### Repository Structure
```
actionspec/
├── .github/
│   ├── SECURITY.md              # Security policies
│   ├── workflows/
│   │   ├── deploy-from-spec.yml # Main deployment workflow
│   │   ├── validate-spec.yml    # Spec validation
│   │   ├── security-scan.yml    # CodeQL + Secrets scanning
│   │   └── destroy-demo.yml     # Cost protection
│   └── dependabot.yml           # Dependency updates
├── .gitignore                   # Paranoid exclusions
├── LICENSE                      # MIT License
├── README.md                    # Big warning labels
├── PROJECT_SPEC.md              # This document!
├── CONTRIBUTING.md              # How to contribute safely
├── SECURITY_CHECKLIST.md        # Pre-commit checklist
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SPEC_SCHEMA.md           # Specification format docs
│   ├── DEPLOYMENT_GUIDE.md
│   └── COST_MANAGEMENT.md
├── infrastructure/
│   ├── modules/                 # Generic, reusable modules
│   │   ├── waf-protection/
│   │   ├── api-gateway/
│   │   ├── serverless-backend/
│   │   └── static-hosting/
│   ├── environments/
│   │   └── demo/               # ONLY demo environment
│   │       ├── main.tf
│   │       ├── variables.tf    # No defaults that could leak
│   │       └── terraform.tfvars.example
│   └── emergency-shutdown/     # The "oh sh*t" button
├── backend/
│   ├── lambda/
│   │   ├── security-headers.py  # Shared security wrapper
│   │   └── functions/
│   │       ├── spec-parser/     # Parse and validate specs
│   │       ├── spec-applier/    # Apply spec changes
│   │       └── github-webhook/  # GitHub integration
│   └── tests/
├── frontend/
│   ├── public/
│   │   └── index.html          # CSP headers defined
│   ├── src/
│   │   ├── config.demo.js      # Demo-only configuration
│   │   └── components/
│   └── .env.example            # No real values
├── specs/                      # Infrastructure specifications
│   ├── examples/
│   │   ├── minimal-web.spec.yml
│   │   ├── secure-web-waf.spec.yml  # The star of the show
│   │   └── full-platform.spec.yml
│   └── schema/
│       └── actionspec-v1.schema.json
├── scripts/
│   ├── pre-commit-checks.sh    # Runs before every commit
│   ├── deploy-demo.sh          # With cost safeguards
│   ├── destroy-all.sh          # Nuclear option
│   └── validate-spec.sh        # Spec validation
└── monitoring/
    ├── budget-alarms.tf        # Cost protection
    ├── security-alarms.tf      # Attack detection
    └── dashboards/             # CloudWatch configs
```

### Core Security Requirements

#### 1. **Code Scanning Pipeline**
```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on: [push, pull_request]

jobs:
  secret-scanning:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Scan for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          
  pattern-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check for AWS Account IDs
        run: |
          ! grep -r "[0-9]{12}" . --include="*.tf" --include="*.py" --include="*.js"
      - name: Check for private IPs
        run: |
          ! grep -rE "10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\." . \
            --include="*.tf" --include="*.yml" --include="*.yaml"
```

#### 2. **Simplified ActionSpec Schema**
```yaml
# specs/examples/secure-web-waf.spec.yml
apiVersion: actionspec/v1
kind: WebApplication
metadata:
  name: "demo-secure-app"
  labels:
    purpose: "portfolio-demonstration"
    deployedBy: "github-actions"

spec:
  # Generic compute specification
  compute:
    tier: "web"
    size: "demo"  # Maps to t4g.nano in demo
    scaling:
      min: 1
      max: 3
      
  # Generic data specification  
  data:
    engine: "postgres"
    size: "demo"  # 20GB max in demo
    highAvailability: false
    
  # Security showcase - the star feature!
  security:
    waf:
      enabled: false  # One change deploys everything
      mode: "monitor"  # monitor or block
      rulesets:
        - "core-protection"
        - "rate-limiting"
        - "geo-blocking"
    
  # Cost controls built-in
  governance:
    maxMonthlySpend: 10
    autoShutdown:
      enabled: true
      afterHours: 24
      
  # What makes this ActionSpec
  actions:
    deploy: "deploy-from-spec"
    validate: "validate-spec"
    destroy: "cleanup-resources"
```

#### 3. **WAF-Protected API Gateway**
```hcl
# modules/api-gateway/main.tf
resource "aws_api_gateway_rest_api" "demo" {
  name = "${var.project_name}-demo-api"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  # Policy restricts to CloudFront only in production
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = "*"
      Action = "execute-api:Invoke"
      Resource = "*"
      Condition = {
        StringEquals = {
          "aws:SourceIp": var.allowed_ips
        }
      }
    }]
  })
}

resource "aws_wafv2_web_acl" "demo_protection" {
  name  = "${var.project_name}-demo-waf"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # Aggressive rate limiting for demo
  rule {
    name     = "RateLimitRule"
    priority = 1
    
    rate_based_statement {
      limit              = 100  # Very low for demo
      aggregate_key_type = "IP"
    }
    
    action {
      block {}
    }
  }
  
  # Block common scanners
  rule {
    name     = "BlockScanners"
    priority = 2
    
    statement {
      regex_pattern_set_reference_statement {
        arn = aws_wafv2_regex_pattern_set.scanner_patterns.arn
        
        field_to_match {
          uri_path {}
        }
      }
    }
    
    action {
      block {
        custom_response {
          response_code = 418  # I'm a teapot
        }
      }
    }
  }
}
```

#### 4. **Lambda Security Wrapper**
```python
# backend/lambda/security_headers.py
import json
import os
from functools import wraps
import logging

logger = logging.getLogger()

# Never log these fields
SENSITIVE_FIELDS = {
    'authorization', 'x-api-key', 'cookie', 'password',
    'secret', 'token', 'aws', 'key'
}

def secure_handler(func):
    """Wrapper that adds security headers and logging to all Lambda functions"""
    @wraps(func)
    def wrapper(event, context):
        # Sanitize event for logging
        safe_event = sanitize_for_logging(event)
        logger.info(f"Request: {json.dumps(safe_event)}")
        
        # Check if we're under attack
        if is_suspicious_request(event):
            return {
                'statusCode': 418,
                'body': json.dumps({'message': 'I am a teapot'}),
                'headers': get_security_headers()
            }
        
        try:
            # Call actual handler
            response = func(event, context)
            
            # Ensure security headers
            if 'headers' not in response:
                response['headers'] = {}
            response['headers'].update(get_security_headers())
            
            return response
            
        except Exception as e:
            logger.error(f"Handler error: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'message': 'Internal server error'}),
                'headers': get_security_headers()
            }
    
    return wrapper

def get_security_headers():
    return {
        'Strict-Transport-Security': 'max-age=63072000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'",
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
```

#### 5. **Cost Protection**
```hcl
# monitoring/budget-alarms.tf
resource "aws_budgets_budget" "demo_killswitch" {
  name         = "${var.project_name}-demo-killswitch"
  budget_type  = "COST"
  limit_amount = "10"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type           = "PERCENTAGE"
    notification_type        = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100
    threshold_type           = "PERCENTAGE"
    notification_type        = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.emergency_shutdown.arn]
  }
}

# Auto-shutdown Lambda
resource "aws_lambda_function" "cost_killer" {
  filename         = "cost-killer.zip"
  function_name    = "${var.project_name}-emergency-shutdown"
  role            = aws_iam_role.cost_killer.arn
  handler         = "index.handler"
  runtime         = "python3.12"
  timeout         = 300

  environment {
    variables = {
      PROJECT_TAG = var.project_name
    }
  }
}
```

## Implementation Plan

### 🎯 **Scope Management (YAGNI Applied)**

Given tight timeline constraints, we explicitly EXCLUDE:
- ❌ Custom GitHub Actions (use standard actions)
- ❌ Complex state management (simple S3 backend)
- ❌ Multi-region support (demo in us-west-2)
- ❌ Authentication system (API keys only)
- ❌ Fancy UI framework (plain React)
- ❌ Kubernetes integration (save for v2)
- ❌ Multiple cloud providers (AWS only)

We FOCUS on:
- ✅ Core spec → infrastructure flow
- ✅ WAF enablement demonstration
- ✅ Clean, readable code
- ✅ Security best practices
- ✅ Cost optimization
- ✅ Clear documentation

### Phase 0: Project Setup
- [x] Create https://github.com/trakrf/action-spec repo (manual/interactive)
- [ ] Install https://github.com/trakrf/claude-spec-workflow (manual/interactive)
- [ ] Create a one-off AWS account for demo and test purposes -> defer for time to market
- [ ] Copy open source project boilerplate from claude-spec-workflow project with appropriate project name updates
- [ ] Copy github repo security and branch protection rules from claude-spec-workflow
- [ ] Set up basic IAM and CI/CD creds
- [ ] Set up github PAT
- [ ] Add AWS creds and PAT to repo actions secrets
- [ ] Create a basic terraform/tofu friendly .gitignore

### Phase 1: Security Foundation
- [ ] Set up security automation (workflows + Dependabot + CodeQL)
- [ ] Implement pre-commit hooks
- [ ] Deploy cost controls and remote state

### Phase 2: Core Infrastructure
- [ ] Build Terraform modules with generic configurations
- [ ] Create Lambda security wrapper
- [ ] Implement API Gateway with WAF
- [ ] Set up static site hosting with CloudFront
- [ ] Build emergency shutdown mechanisms

### Phase 3: Application Logic
- [ ] Develop form generation Lambda
- [ ] Create GitHub integration (webhook only)
- [ ] Build configuration validator
- [ ] Implement simplified blueprint parser
- [ ] Create React frontend with CSP

### Phase 4: Demo Content
- [ ] Create generic blueprint examples
- [ ] Write comprehensive documentation
- [ ] Build demo scenarios
- [ ] Create architecture diagrams
- [ ] Record demo video (optional)

### Phase 5: Public Release Prep
- [ ] Security audit with scanning tools  
- [ ] Cost projection validation
- [ ] Documentation review
- [ ] Legal disclaimer additions
- [ ] Create demo script

## Phase 3: Application Logic - Work Breakdown

### High-Level Delivery Plan (Phases 3.1 - 3.5)

This phase represents the core application logic that transforms ActionSpec from infrastructure to a working product. Estimated total effort: 3-4 weeks with focused development.

#### Phase 3.1: Backend Foundation & SAM Infrastructure
**Goal**: Establish the Lambda runtime environment and API Gateway
**Estimated Effort**: 3-5 days

**Deliverables**:
- AWS SAM template with API Gateway configuration
- Lambda function scaffolding (all 4 functions: spec-parser, aws-discovery, form-generator, spec-applier)
- Shared security wrapper module with header injection and sanitization
- SSM Parameter Store configuration for GitHub PAT
- S3 bucket for specs storage with versioning enabled
- IAM roles and policies for Lambda execution
- Local development environment (SAM local)
- Basic smoke tests for API Gateway endpoints

**Success Criteria**:
- `sam local start-api` runs successfully
- All Lambda functions return 200 with stub responses
- Security headers present in all responses
- Can deploy to AWS without errors

**Dependencies**: None (can start immediately)

---

#### Phase 3.2: Spec Validation & Parsing
**Goal**: Implement core spec processing and validation logic
**Estimated Effort**: 4-6 days

**Deliverables**:
- JSON Schema definition (`actionspec-v1.schema.json`)
- Spec Parser Lambda implementation
  - YAML parsing with PyYAML
  - Schema validation with jsonschema
  - Error handling and user-friendly messages
- Configuration Validator module
  - Schema validation
  - Destructive change detection
  - Warning generation
- Example spec files (minimal, secure-waf, full)
- Unit test suite (pytest)
  - Valid spec parsing
  - Invalid spec rejection
  - Edge cases (missing fields, wrong types)
- Lambda layer for shared dependencies

**Success Criteria**:
- Parse valid specs successfully
- Reject invalid specs with clear error messages
- Detect destructive changes (WAF disable, compute downsize)
- 90%+ test coverage on validation logic

**Dependencies**: Phase 3.1 (requires Lambda runtime environment)

---

#### Phase 3.3: GitHub Integration & AWS Discovery
**Goal**: Connect to external systems (GitHub API, AWS APIs)
**Estimated Effort**: 5-7 days

**Deliverables**:
- GitHub client wrapper module
  - PyGithub integration with token caching
  - Fetch spec files from repository
  - Create feature branches
  - Generate pull requests with templates
  - Add labels and reviewers
- Spec Applier Lambda implementation
  - Branch creation: `action-spec-update-{timestamp}`
  - PR description generation with change summary
  - Error handling for GitHub API failures
- AWS Discovery Lambda implementation
  - Query VPCs and Subnets (ec2:Describe*)
  - List ALBs and Target Groups
  - Check existing WAF WebACLs
  - Return structured resource inventory
- Integration tests
  - Mock GitHub API responses
  - Test PR creation flow
  - Validate AWS resource queries
- Documentation for GitHub PAT setup

**Success Criteria**:
- Successfully create test PR in action-spec repo
- Fetch spec files from GitHub repository
- Discover existing AWS resources (VPCs, ALBs, WAF)
- Graceful handling of GitHub rate limits
- PR descriptions include accurate change summaries

**Dependencies**: Phase 3.2 (needs spec validation for PR creation)

---

#### Phase 3.4: Form Generator API & React Frontend
**Goal**: Build the user-facing application
**Estimated Effort**: 6-8 days

**Deliverables**:
- **Form Generator Lambda** (main orchestrator)
  - GET /form endpoint
  - Combine spec + discovery + schema
  - Return form structure with validation rules
  - Handle errors gracefully
- **React Frontend Setup**
  - Create React App with TypeScript
  - Dependencies: axios, react-hook-form, yup
  - ESLint and Prettier configuration
  - Environment variable management
- **Core Components**
  - `SpecForm`: Dynamic form generation from schema
  - `WafToggle`: Prominent toggle with visual feedback (the star!)
  - `ChangePreview`: Diff display before submission
  - `SubmitButton`: Loading states and error handling
  - `ErrorBoundary`: Graceful error handling
- **API Integration Layer**
  - Axios client with API key headers
  - Request/response interceptors
  - Error handling and retry logic
- **Security Implementation**
  - Content Security Policy in index.html
  - Strict CORS configuration
  - Input sanitization
- **Styling**
  - Responsive layout (mobile-friendly)
  - Accessibility (WCAG AA)
  - Loading states and animations
- **Build Pipeline**
  - Production build optimization
  - Source maps for debugging
  - Bundle size analysis

**Success Criteria**:
- Form loads with current spec from GitHub
- Can edit spec fields with real-time validation
- WAF toggle prominently displayed with visual indicators
- Submit creates PR successfully
- Form displays PR URL on success
- Works on desktop and mobile browsers
- No console errors or warnings

**Dependencies**: Phase 3.3 (needs all backend APIs functional)

---

#### Phase 3.5: Deployment Automation, Testing & Documentation
**Goal**: Make it production-ready and maintainable
**Estimated Effort**: 4-6 days

**Deliverables**:
- **Backend Deployment**
  - SAM deployment script with parameter management
  - Environment-specific configurations (dev, prod)
  - Output capture (API Gateway URL, etc.)
  - Deployment documentation
- **Frontend Deployment**
  - S3 sync script with cache control headers
  - CloudFront invalidation automation
  - Environment variable injection
  - Deployment GitHub Action workflow
- **Testing Suite**
  - End-to-end tests (Cypress or Playwright)
    - Load form → Edit spec → Submit → Verify PR created
  - Security tests
    - Invalid API keys rejected
    - Malformed specs handled gracefully
    - Rate limiting enforced
  - Performance tests
    - Lambda cold start times
    - API response times
    - Form load performance
  - Cost tests
    - Lambda execution time under limits
    - API Gateway request costs tracked
- **Documentation**
  - `/docs/API.md`: Complete API reference
  - `/docs/FRONTEND_SETUP.md`: Developer setup guide
  - `/docs/DEPLOYMENT.md`: Deployment procedures
  - `/docs/ENVIRONMENT_VARIABLES.md`: Configuration reference
  - `/docs/TROUBLESHOOTING.md`: Common issues and solutions
  - `/docs/DEMO_SCRIPT.md`: Step-by-step demo walkthrough
- **Monitoring & Observability**
  - CloudWatch dashboard for API metrics
  - Lambda function logs with structured logging
  - Error alerting via SNS
  - Cost tracking tags

**Success Criteria**:
- Can deploy full stack (backend + frontend) with one command
- All tests passing in CI/CD pipeline
- Zero security warnings from scanning tools
- Complete documentation allows new developer to deploy
- Demo script successfully demonstrates all features
- Monitoring dashboard shows key metrics

**Dependencies**: Phase 3.4 (requires complete application)

---

### Phase 3 Risk Management

**Technical Risks**:
- GitHub API rate limiting → Mitigation: Cache responses, implement exponential backoff
- AWS resource discovery timeouts → Mitigation: Parallel queries, reasonable timeouts
- Lambda cold starts affecting UX → Mitigation: Provisioned concurrency for form-generator
- CORS issues with API Gateway → Mitigation: Test early with frontend integration

**Schedule Risks**:
- Frontend complexity underestimated → Mitigation: Keep UI simple (YAGNI), use standard components
- Testing taking longer than expected → Mitigation: Automate early, test continuously
- Deployment issues in AWS → Mitigation: Test SAM deployments early and often

**Mitigation Strategies**:
1. **Daily deployments**: Deploy each PR to dev environment immediately
2. **Continuous testing**: Run tests on every commit
3. **Documentation as code**: Write docs alongside implementation
4. **Incremental complexity**: Start simple, add features iteratively
5. **Regular demos**: Show working software every few days

### Phase 3 Success Metrics

**Technical Quality**:
- [ ] All Lambda functions < 5s execution time (p99)
- [ ] API Gateway response time < 500ms (p95)
- [ ] Frontend load time < 2s (initial)
- [ ] Test coverage > 80% for backend
- [ ] Zero critical security findings
- [ ] All accessibility checks passing (WCAG AA)

**Functional Completeness**:
- [ ] Can load spec from GitHub repository
- [ ] Can edit all spec fields via form
- [ ] WAF toggle creates correct spec changes
- [ ] Submit creates PR with accurate description
- [ ] AWS resource discovery populates dropdowns
- [ ] Error messages are user-friendly

**Operational Readiness**:
- [ ] Deployment fully automated via GitHub Actions
- [ ] Monitoring dashboard shows key metrics
- [ ] Documentation complete and tested
- [ ] Demo script validated by external user
- [ ] Cost tracking confirms <$2/month baseline

---

## Phase 3: Application Logic - Detailed Requirements

### 3.1 Lambda Function Setup (AWS SAM)

#### 3.1.1 SAM Template Structure
```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 30
    Runtime: python3.12
    Environment:
      Variables:
        GITHUB_TOKEN_SSM_PARAM: /actionspec/github-token
        SPECS_BUCKET: !Ref SpecsBucket
        ALLOWED_REPOS: "trakrf/action-spec"  # Whitelist for security

Resources:
  # API Gateway with WAF
  ActionSpecApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Cors:
        AllowMethods: "'GET,POST,OPTIONS'"
        AllowHeaders: "'Content-Type,X-Api-Key'"
        AllowOrigin: "'*'"  # Tighten for production
      Auth:
        ApiKeyRequired: true
      MethodSettings:
        - ResourcePath: "/*"
          HttpMethod: "*"
          ThrottlingBurstLimit: 100
          ThrottlingRateLimit: 50
```

#### 3.1.2 Lambda Functions

**A. Spec Parser Lambda**
```python
# backend/lambda/functions/spec-parser/handler.py
"""
Parses ActionSpec YAML and validates against schema
Returns form structure for frontend
"""
Functions:
- Parse spec YAML from GitHub or S3
- Validate against actionspec-v1.schema.json
- Transform to form-friendly JSON structure
- Handle parsing errors gracefully

Dependencies:
- PyYAML
- jsonschema
- boto3
```

**B. AWS Discovery Lambda**
```python
# backend/lambda/functions/aws-discovery/handler.py
"""
Discovers existing AWS resources to pre-populate form fields
"""
Functions:
- Query VPCs, Subnets, Security Groups
- List existing ALBs and Target Groups
- Check for existing WAF WebACLs
- Return current resource state

Dependencies:
- boto3
Required IAM permissions:
- ec2:DescribeVpcs, ec2:DescribeSubnets
- elasticloadbalancing:Describe*
- wafv2:List*, wafv2:Get*
```

**C. Form Generator Lambda**
```python
# backend/lambda/functions/form-generator/handler.py
"""
Main endpoint that combines spec + discovery data
GET /form?repo=trakrf/action-spec&spec=demo-app.spec.yml
"""
Flow:
1. Fetch spec from GitHub using PyGithub
2. Parse spec with spec-parser
3. Enrich with AWS discovery data
4. Return complete form structure

Response format:
{
  "spec": { /* current spec */ },
  "discovered": { /* AWS resources */ },
  "schema": { /* validation rules */ },
  "formFields": [ /* UI structure */ ]
}
```

**D. Spec Applier Lambda**
```python
# backend/lambda/functions/spec-applier/handler.py
"""
Handles form submission and creates GitHub PR
POST /form/submit
"""
Flow:
1. Validate submitted spec against schema
2. Create feature branch: action-spec-update-{timestamp}
3. Update spec file in branch
4. Create PR with change summary
5. Add labels: "infrastructure-change", "automated"
6. Return PR URL to frontend

PR Description Template:
## ActionSpec Update
### Changes:
- [ ] WAF enabled: {before} → {after}
- [ ] Compute size: {before} → {after}
### Automated by ActionSpec
```

#### 3.1.3 Shared Security Wrapper
```python
# backend/lambda/security_wrapper.py
"""
Applied to ALL Lambda functions
"""
Features:
- Add security headers to all responses
- Validate API key from API Gateway
- Sanitize logs (no secrets/tokens)
- Rate limit per IP (in-memory cache)
- Block suspicious patterns
```

### 3.2 GitHub Integration

#### 3.2.1 Authentication Setup
```python
# Store PAT in SSM Parameter Store (SecureString)
aws ssm put-parameter \
  --name /actionspec/github-token \
  --type SecureString \
  --value "ghp_xxxxxxxxxxxx"

# Lambda retrieves at runtime:
ssm = boto3.client('ssm')
token = ssm.get_parameter(
    Name='/actionspec/github-token',
    WithDecryption=True
)['Parameter']['Value']
```

#### 3.2.2 PyGithub Integration
```python
# backend/lambda/shared/github_client.py
from github import Github
from functools import lru_cache

@lru_cache(maxsize=1)
def get_github_client():
    token = get_parameter('/actionspec/github-token')
    return Github(token)

def fetch_spec_file(repo_name, file_path, ref='main'):
    """Fetch spec file content from GitHub"""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    file = repo.get_contents(file_path, ref=ref)
    return file.decoded_content.decode('utf-8')

def create_spec_pr(repo_name, spec_path, new_content, message):
    """Create PR with updated spec"""
    # Implementation from earlier in thread
    pass
```

### 3.3 Configuration Validator

#### 3.3.1 JSON Schema Definition
```json
// specs/schema/actionspec-v1.schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["apiVersion", "kind", "metadata", "spec"],
  "properties": {
    "apiVersion": {
      "type": "string",
      "enum": ["actionspec/v1"]
    },
    "kind": {
      "type": "string",
      "enum": ["WebApplication", "APIService", "StaticSite"]
    },
    "spec": {
      "type": "object",
      "properties": {
        "compute": {
          "type": "object",
          "properties": {
            "tier": {"enum": ["web", "api", "worker"]},
            "size": {"enum": ["demo", "small", "medium", "large"]}
          }
        },
        "security": {
          "type": "object",
          "properties": {
            "waf": {
              "type": "object",
              "properties": {
                "enabled": {"type": "boolean"},
                "mode": {"enum": ["monitor", "block"]}
              }
            }
          }
        }
      }
    }
  }
}
```

#### 3.3.2 Validation Logic
```python
# backend/lambda/shared/validator.py
import json
import jsonschema

def validate_spec(spec_dict):
    """Validate spec against schema"""
    with open('schema/actionspec-v1.schema.json') as f:
        schema = json.load(f)
    
    try:
        jsonschema.validate(spec_dict, schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)

def check_destructive_changes(old_spec, new_spec):
    """Identify potentially destructive changes"""
    warnings = []
    
    # Check for compute downsizing
    if old_spec.get('compute', {}).get('size') > new_spec.get('compute', {}).get('size'):
        warnings.append("⚠️ Compute size reduction may cause downtime")
    
    # Check for security downgrades
    if old_spec.get('security', {}).get('waf', {}).get('enabled') and \
       not new_spec.get('security', {}).get('waf', {}).get('enabled'):
        warnings.append("⚠️ Disabling WAF will remove security protection")
    
    return warnings
```

### 3.4 React Frontend

#### 3.4.1 Project Setup
```bash
# Using Create React App for simplicity (YAGNI!)
pnpm dlx create-react-app frontend --template typescript
cd frontend
pnpm install axios react-hook-form @hookform/resolvers yup
```

#### 3.4.2 Core Components

**A. SpecForm Component**
```typescript
// src/components/SpecForm/SpecForm.tsx
Features:
- Dynamic form generation from schema
- Real-time validation
- Change preview/diff display
- Submit handling with loading states
- Error boundaries

Key sections:
- Repository selector (dropdown of allowed repos)
- Spec file selector
- Dynamic form fields based on spec schema
- AWS resource discovery display
- Change summary before submit
```

**B. WafToggle Component**
```typescript
// src/components/WafToggle/WafToggle.tsx
The star of the show!
- Big prominent toggle switch
- Animated expansion of WAF options when enabled
- Cost estimate display
- Visual security indicators
```

**C. Security Headers Implementation**
```typescript
// public/index.html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'unsafe-inline'; 
               style-src 'self' 'unsafe-inline'; 
               connect-src 'self' https://*.execute-api.amazonaws.com">
```

#### 3.4.3 API Integration
```typescript
// src/services/api.ts
const API_BASE = process.env.REACT_APP_API_URL || 'https://demo.execute-api.us-west-2.amazonaws.com/prod';
const API_KEY = process.env.REACT_APP_API_KEY;

export const actionSpecApi = {
  async getForm(repo: string, specPath: string) {
    const response = await axios.get(`${API_BASE}/form`, {
      headers: { 'X-Api-Key': API_KEY },
      params: { repo, spec: specPath }
    });
    return response.data;
  },
  
  async submitSpec(data: SpecSubmission) {
    const response = await axios.post(`${API_BASE}/form/submit`, data, {
      headers: { 'X-Api-Key': API_KEY }
    });
    return response.data; // Returns PR URL
  }
};
```

### 3.5 Local Development Setup

#### 3.5.1 SAM Local Testing
```bash
# Start local API
sam local start-api --env-vars env.json

# env.json for local testing
{
  "Parameters": {
    "GITHUB_TOKEN_SSM_PARAM": "/actionspec/github-token",
    "SPECS_BUCKET": "actionspec-demo-specs"
  }
}
```

#### 3.5.2 Frontend Development
```bash
# .env.development
REACT_APP_API_URL=http://localhost:3000
REACT_APP_API_KEY=local-dev-key

# Start React dev server
npm start
```

### 3.6 Deployment Strategy

#### 3.6.1 Backend Deployment
```bash
# Build and deploy SAM application
sam build
sam deploy --guided \
  --stack-name actionspec-backend \
  --parameter-overrides \
    GithubTokenParam=/actionspec/github-token

# Output includes API Gateway URL
```

#### 3.6.2 Frontend Deployment
```bash
# Build React app
npm run build

# Sync to S3 (created in Phase 2)
aws s3 sync build/ s3://actionspec-frontend-bucket \
  --delete \
  --cache-control "public, max-age=3600"

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/*"
```

### 3.7 Testing Requirements

- [ ] Unit tests for spec validation logic
- [ ] Integration tests for GitHub API calls  
- [ ] End-to-end test: Form load → Edit → Submit → PR created
- [ ] Security tests: Invalid API keys, malformed specs
- [ ] Cost tests: Ensure Lambdas don't run too long

### 3.8 Documentation Updates

- [ ] Add API documentation to `/docs/API.md`
- [ ] Create frontend setup guide
- [ ] Document environment variables needed
- [ ] Add troubleshooting section

This should give you everything needed for Phase 3! The key is keeping it simple (YAGNI) while hitting all the essential features for the demo.

### Consciously Deferred from Phase 0

**Separate AWS Account for Demo**
- **Status**: Deferred for time to market
- **Current**: Using existing AWS account
- **Risk**: Demo resources mixed with other infrastructure
- **Mitigation**: Strict resource tagging, budget alarms, manual monitoring
- **Future**: Set up dedicated demo account via AWS Organizations
- **Effort**: 1-2 hours (account creation, IAM setup, credential rotation)

**Account Vending Machine (AVM)**
- **Status**: Future enhancement (post-MVP)
- **Current**: Manual AWS account management
- **Vision**: Automated account provisioning for different demo environments
- **Use Case**: Spin up isolated demo accounts per customer/presentation
- **Effort**: 8-16 hours (Terraform module, Service Catalog integration, guardrails)

### Descoped from Phase 1

**Emergency Shutdown Lambda**
- **Status**: Descoped for speed to market
- **Current**: Manual cost control (budget alerts → email → run destroy script)
- **What's Missing**: Automatic infrastructure teardown at budget threshold
- **Risk**: Requires human in the loop; potential for delayed response
- **Mitigation**: Email alerts at 80% and 100%, manual destroy script ready
- **Future**: Build auto-remediation Lambda triggered by SNS
- **Effort**: 2-3 hours (Lambda function, IAM policies, testing)
- **Code Reference**: PRD.md lines 391-405 (already designed)

**Enhanced Cost Monitoring**
- **Status**: Deferred (basic budget alarm sufficient for demo)
- **What's Missing**:
  - CloudWatch dashboards for cost visualization
  - Cost anomaly detection
  - Per-resource cost allocation tags
  - Daily cost reports
- **Future**: Add after demo proves concept
- **Effort**: 4-6 hours (dashboards, alarms, tagging strategy)

### Nice-to-Have Features (Post-Demo)

**Multi-Region Support**
- **Current**: Single region (us-west-2)
- **Future**: Deploy to multiple regions for global demo
- **Effort**: 8-12 hours (refactor modules, region variables, testing)

**Advanced Security Features**
- GuardDuty integration
- Security Hub consolidation
- Automated compliance scanning
- **Effort**: 6-10 hours

**CI/CD Pipeline Enhancements**
- Terraform plan preview on PRs
- Cost estimation in CI (Infracost)
- Automated testing with Terratest
- **Effort**: 8-12 hours

---

## Demo Architecture

### The ActionSpec Flow
```
Developer modifies spec.yml → Commits to GitHub → 
GitHub Action triggered → Parses spec → 
Applies infrastructure changes → Updates complete
```

### What Runs Continuously (Pennies)
```
┌─────────────────┐
│   CloudFront    │ ← S3 static site ($0.50/mo)
│   Distribution  │
└────────┬────────┘
         │
┌────────┴────────┐
│  WAF Web ACL    │ ← Protects API ($5/mo)
└────────┬────────┘
         │
┌────────┴────────┐
│  API Gateway    │ ← REST API ($0 until used)
└────────┬────────┘
         │
┌────────┴────────┐
│ Lambda Functions│ ← Spec processor ($0 until invoked)
└─────────────────┘
```

### What Gets Created by Specs (Temporary)
```yaml
# When spec says: waf.enabled = true
┌─────────────────┐
│   WAF Rules     │ ← Created automatically
├─────────────────┤
│   CloudWatch    │ ← Monitoring enabled
├─────────────────┤  
│   Alarms        │ ← Attack detection
└─────────────────┘

# When spec includes compute resources
┌─────────────────┐
│   Demo VPC      │ ← NO NAT Gateway!
├─────────────────┤
│ t4g.nano + ALB  │ ← ~$5/day, auto-destroyed
└─────────────────┘
```

## Cost Management

### Always Running (Portfolio Display)
- Lambda + API Gateway: ~$0.00/month (pay per request)
- S3 Static Hosting: ~$0.50/month
- CloudWatch Logs: ~$0.50/month  
- Route53 (optional): $0.50/month
- **Total: <$2/month**

### Demo Mode (Temporary)
- VPC + EC2 (t4g.nano): ~$3/month
- ALB: ~$22/month (minimize time!)
- RDS: ~$15/month (only if essential)
- **Demo Total: ~$40/month** (destroy immediately)

### Cost Safeguards
1. Budget alarms at $10 and $20
2. Auto-shutdown Lambda at $25
3. No NAT Gateways (ever!)
4. Use spot instances for demos
5. Destroy scripting mandatory

## Security Checklist

### Before EVERY Commit
- [ ] Run `git secrets --scan`
- [ ] Check for hardcoded IPs/CIDRs
- [ ] Verify no AWS account IDs
- [ ] Ensure no customer-specific patterns
- [ ] Test with example data only

### Before Going Public
- [ ] Enable GitHub security features
- [ ] Add security policy
- [ ] Review all environment variables
- [ ] Scan with multiple tools
- [ ] Have someone else review

### Demo Operations
- [ ] Use separate AWS account
- [ ] Enable GuardDuty
- [ ] Set up billing alerts
- [ ] Use temporary credentials
- [ ] Have shutdown script ready

## Legal & Compliance

### README Disclaimers
```markdown
## ⚠️ IMPORTANT DISCLAIMER

This is a PORTFOLIO DEMONSTRATION PROJECT showcasing cloud architecture patterns.

**NOT FOR PRODUCTION USE**
- Educational and demonstration purposes only
- No warranty or support provided
- You are responsible for all AWS charges
- Review all code before deployment

**Security Notice**
- Contains simplified security for demo purposes
- Not a complete security solution
- Always follow AWS security best practices

This project demonstrates common B2B SaaS patterns but is not based on any specific implementation.
```

### License (MIT)
```
MIT License

Copyright (c) 2025 DevOps To AI LLC dba TrakRF

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[Standard MIT continues...]
```

## Project Boilerplate

Based on established patterns from similar projects:
- Copy structure from https://github.com/trakrf/claude-spec-workflow
- Adapt security policies for infrastructure code
- Include standard OSS documentation:
  - README.md (with warnings)
  - CONTRIBUTING.md
  - CODE_OF_CONDUCT.md
  - SECURITY.md
  - LICENSE

## Open Source Value Proposition

### For the Community
ActionSpec serves as a production-ready template for teams implementing:
- YAML-driven infrastructure automation
- GitOps workflows with GitHub Actions
- Automated security controls deployment
- Cost-optimized demo environments

### Fork and Adapt
Teams can fork ActionSpec and modify for their needs:
```yaml
# Your custom spec format
apiVersion: yourcompany/v1
kind: YourInfrastructure
spec:
  # Your specific requirements
  database: 
    type: "aurora-serverless"
  messaging:
    type: "kafka"
  # etc...
```

### Contributing Back
We welcome contributions that:
- Enhance security patterns
- Add new infrastructure modules
- Improve cost optimization
- Expand documentation
- Share success stories

## Success Metrics

### Technical Excellence
- Zero security warnings in scans
- <$2/month passive running cost  
- <5 minute demo deployment
- 100% infrastructure as code
- Comprehensive documentation

### Portfolio Impact
- Clear architecture documentation
- Live demo capability
- Security-first implementation
- Cost optimization showcase
- Modern DevOps practices

## Demo Script Highlights

### Demo
1. **Opening**: "ActionSpec turns infrastructure specifications into deployed resources via GitHub Actions"
2. **Basic Demo**: Show a simple web app deployment from spec
3. **The Hook**: "Now let's add enterprise security..."
   ```yaml
   security:
     waf:
       enabled: true  # This one line...
   ```
4. **The Magic**: Watch GitHub Actions deploy complete WAF protection
5. **The Value**: "Any infrastructure component can be controlled this way"

### Key Talking Points
- "Specifications are version controlled and reviewed"
- "GitHub Actions provide the automation layer"
- "Security isn't bolted on - it's part of the specification"
- "This pattern scales from demo to production"
- "Fork it and make it your own"

## Conclusion

ActionSpec demonstrates that enterprise infrastructure automation doesn't require complex tooling - just clear specifications and good engineering practices. By following these guidelines, you create:

1. **A Portfolio Piece** - Shows real cloud architecture skills
2. **An Open Source Contribution** - Others can build upon your work
3. **A Practical Demo** - Solves real problem
4. **A Learning Tool** - Clear code others can understand

Remember: **Specifications drive actions. Actions deploy infrastructure. Simple.**

---

*Built with [claude-spec-workflow](https://github.com/trakrf/claude-spec-workflow) - because of course it is.*
