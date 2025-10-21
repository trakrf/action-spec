# Security Policy

## Overview

ActionSpec is a **demonstration and portfolio project** showcasing YAML-driven infrastructure deployment patterns. It is designed to be safely used in public repositories with appropriate security considerations.

## ⚠️ Important Disclaimers

- **Not Production-Ready**: This is a demo/portfolio project to showcase patterns
- **No Warranty**: Use at your own risk (see LICENSE for details)
- **Best Effort Support**: Maintained by volunteers, no SLAs or guaranteed response times
- **Public Repository**: All code and configurations are designed for safe public disclosure

## Reporting a Vulnerability

### How to Report

If you discover a security vulnerability, please report it via:

1. **Preferred**: [GitHub Security Advisories](https://github.com/trakrf/action-spec/security/advisories/new)
2. **Alternative**: Open a private issue describing the vulnerability

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

### Response Timeline

**Best effort** - This is a volunteer-maintained demo project:
- We'll acknowledge receipt when we can
- Fixes will be prioritized based on severity and available time
- No guaranteed timeline for patches

### Safe Harbor

We support responsible disclosure and will not take legal action against security researchers who:
- Report vulnerabilities in good faith
- Avoid privacy violations and service disruption
- Give us reasonable time to address issues before public disclosure

## Scope

### In Scope
- Vulnerabilities in infrastructure code (OpenTofu/Terraform modules)
- Security issues in GitHub Actions workflows
- Exposed secrets or credentials in code/config
- Documentation errors that could lead to insecure deployments

### Out of Scope
- Issues in demo AWS infrastructure (intentionally simplified)
- Rate limiting on demo endpoints
- Performance/availability of demo environment
- Social engineering attempts

## Security Best Practices for Users

When using ActionSpec:
- **Never commit real AWS credentials** - Use example files only
- **Review all infrastructure code** before deploying
- **Use separate AWS account** for testing/demos
- **Enable AWS budget alarms** to prevent cost surprises
- **Follow AWS security best practices** for production deployments

## Automated Security Scanning

ActionSpec uses automated security tools to prevent vulnerabilities from reaching production:

### GitHub Actions Workflows

**Secret Scanning** (TruffleHog)
- Scans every commit for leaked credentials
- Runs on: Push to main, all pull requests
- Status: Required check (blocks PR merge on failure)
- What it catches: API keys, tokens, passwords, private keys

**Pattern Checks** (Infrastructure-specific)
- Scans for hardcoded AWS account IDs (12-digit numbers)
- Scans for private IP addresses (RFC 1918 ranges)
- Runs on: Push to main, all pull requests
- Status: Required check (blocks PR merge on failure)
- Excluded directories: node_modules/, .git/, dist/, build/

**CodeQL** (Code Analysis)
- Static analysis for security vulnerabilities
- Languages: JavaScript/TypeScript, Python (when added)
- Runs on: Push to main, pull requests, weekly schedule
- Status: Informational (will become required in future)

### Dependency Monitoring (Dependabot)

- Monitors: GitHub Actions, npm (when added), pip (when added)
- Schedule: Weekly on Wednesdays at 9 AM PT
- Auto-creates PRs for security updates
- Labels: dependencies, security
- PR limit: 5 concurrent updates

### Running Security Checks Locally

**Before committing:**
```bash
# Check for secrets (requires trufflehog installation)
trufflehog filesystem . --only-verified

# Check for AWS account IDs
grep -r --exclude-dir={node_modules,.git,dist,build} \
  -E "[0-9]{12}" \
  --include="*.tf" --include="*.py" --include="*.js"

# Check for private IPs
grep -r --exclude-dir={node_modules,.git,dist,build} \
  -E "10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\." \
  --include="*.tf" --include="*.yml" --include="*.yaml"
```

**Installing TruffleHog locally:**
```bash
# macOS
brew install trufflehog

# Linux
curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin

# Verify installation
trufflehog --version
```

## Security Hall of Fame

We recognize and thank security researchers who responsibly disclose vulnerabilities:

<!-- Add entries as: - **[Researcher Name](github/profile)** - [Vulnerability Type] - [Date] -->

_No entries yet. Be the first to responsibly disclose a security issue!_

### Recognition Criteria

To be listed:
- Responsible disclosure via GitHub Security Advisories
- Vulnerability confirmed and addressed
- No public disclosure before fix is available
- Good faith security research

## References

See PRD.md for additional security considerations and cost protection measures.

---

**Last Updated**: 2025-10-21

**Remember**: This is educational infrastructure. Always review and understand code before deploying to your AWS account.
