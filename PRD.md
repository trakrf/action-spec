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

## Technical Debt & Future Enhancements

### Consciously Deferred from Phase 0

**Separate AWS Account for Demo**
- **Status**: Deferred for time to market
- **Current**: Using existing AWS account (252374924199)
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
