# ActionSpec

> Turn infrastructure specifications into deployable GitHub Actions

[![Security Scan](https://github.com/trakrf/action-spec/actions/workflows/security-scan.yml/badge.svg)](https://github.com/trakrf/action-spec/actions/workflows/security-scan.yml)
[![CodeQL](https://github.com/trakrf/action-spec/actions/workflows/codeql.yml/badge.svg)](https://github.com/trakrf/action-spec/actions/workflows/codeql.yml)

**ActionSpec** is an open-source demonstration of YAML-driven Infrastructure as Code, showcasing how specification files can drive GitHub Actions workflows for automated infrastructure deployment.

## ⚠️ IMPORTANT DISCLAIMER

This is a **PORTFOLIO DEMONSTRATION PROJECT** showcasing cloud architecture patterns.

**NOT FOR PRODUCTION USE**
- Educational and demonstration purposes only
- No warranty or support provided
- You are responsible for all AWS charges
- Review all code before deployment

## 🎯 Features

- **YAML specifications drive all infrastructure** - Change a spec file, deploy infrastructure
- **GitHub Actions automation built-in** - GitOps workflow out of the box
- **AWS WAF deployment with one config change** - Security-first design
- **Cost-optimized for demos** - <$5/month passive costs
- **Security-first design** - Automated scanning and pre-commit hooks

## 🚀 Quick Start

### Prerequisites

- AWS account (recommend dedicated demo account)
- GitHub repository with Actions enabled
- AWS credentials configured as repository secrets

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/trakrf/action-spec.git
   cd action-spec
   ```

2. **Install pre-commit hooks** (REQUIRED for contributors)
   ```bash
   ./scripts/install-hooks.sh
   ```

   This installs security validation that runs before each commit to prevent accidental exposure of:
   - AWS credentials and account IDs
   - Private IP addresses
   - Terraform state files
   - Environment configuration

3. **Test the hook**
   ```bash
   ./scripts/pre-commit-checks.sh
   ```

4. **Make changes and commit** - hooks validate automatically
   ```bash
   git add .
   git commit -m "feat: your changes"
   # Pre-commit hook runs automatically
   ```

## 🛡️ Security

This project implements multiple layers of security validation:

- **Pre-commit hooks** - Local validation before code enters Git history
- **GitHub Actions scanning** - TruffleHog secret detection + pattern validation
- **CodeQL analysis** - Static code analysis for vulnerabilities
- **Dependabot** - Automated dependency updates

See [SECURITY.md](.github/SECURITY.md) for reporting security issues.

## 📖 Documentation

- [PRD.md](PRD.md) - Product Requirements and architecture
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute safely
- [SECURITY.md](.github/SECURITY.md) - Security policies

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2025 DevOps To AI LLC dba TrakRF

## 🤝 Contributing

Contributions welcome! Please:
1. Install pre-commit hooks (required)
2. Follow security best practices
3. Include tests for new features
4. Update documentation as needed

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

*Built with [claude-spec-workflow](https://github.com/trakrf/claude-spec-workflow)*
