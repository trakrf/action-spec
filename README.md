# ActionSpec

> Turn infrastructure specifications into deployable GitHub Actions

[![Security Scan](https://github.com/trakrf/action-spec/actions/workflows/security-scan.yml/badge.svg)](https://github.com/trakrf/action-spec/actions/workflows/security-scan.yml)
[![CodeQL](https://github.com/trakrf/action-spec/actions/workflows/codeql.yml/badge.svg)](https://github.com/trakrf/action-spec/actions/workflows/codeql.yml)

**ActionSpec** is an open-source demonstration of YAML-driven Infrastructure as Code, showcasing how specification files can drive GitHub Actions workflows for automated infrastructure deployment.

## 🎯 Project Status

**Demo POC (v0.1.0)**: ✅ Complete - Fully functional self-hosted deployment tool with web UI

This repository contains a **complete proof-of-concept demonstration** of YAML-driven infrastructure deployment. The demo showcases end-to-end workflow from specification editing to automated AWS deployment via GitHub Actions.

**Enterprise Solution (overengineered/PRD.md)**: ~50% Complete - Started Here, Pivoted to POC Mid-Build

**The journey:**
1. Designed ambitious enterprise architecture (see overengineered/PRD.md - serverless React + Lambda)
2. Built foundation: security, parsing, Lambda infrastructure (~1.5 days)
3. **Realization**: Remaining frontend/integration work would take another week+
4. **Decision**: Validate with complete POC before finishing enterprise build
5. **Result**: Shipped working demo (v0.1.0) that proves the entire concept

**Enterprise foundation already built** (~50% complete):
- ✅ Security framework (100%) - Pre-commit hooks, CodeQL, secrets scanning
- ✅ Spec parsing engine (90%) - JSON Schema validation, YAML parser, error handling
- ✅ Lambda infrastructure (100%) - SAM templates, security wrapper, API Gateway scaffold
- ✅ Cost controls (100%) - Budget alarms, remote state, Terraform modules

**Remaining for enterprise** (deferred, not blocked):
- 🚧 GitHub PR integration - Spec applier Lambda (Phase 3.3)
- 🚧 React frontend - Dynamic forms, WAF toggle UI (Phase 3.4)
- 🚧 API Gateway + WAF - CloudFront, static hosting (Phase 2)
- 🚧 Deployment automation & documentation (Phase 3.5)

**Learning:** Should have validated with POC before building enterprise foundation - but the foundation work informed the POC architecture and is ready when enterprise scaling is needed.

**See the implementation**: The `backend/` directory contains the main implementation. See [backend/README.md](backend/README.md) for architecture and setup.

---

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

- [overengineered/PRD.md](overengineered/PRD.md) - Original product requirements (archived)
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
