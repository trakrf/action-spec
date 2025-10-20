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

## References

See PRD.md for additional security considerations and cost protection measures.

---

**Remember**: This is educational infrastructure. Always review and understand code before deploying to your AWS account.
