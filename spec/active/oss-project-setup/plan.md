# Implementation Plan: Open Source Project Setup
Generated: 2025-10-20
Specification: spec.md

## Understanding

This feature establishes complete OSS project documentation and configuration for ActionSpec, following patterns from claude-spec-workflow but adapted for an infrastructure-as-code demo project. The focus is on speed to market - comprehensive .gitignore now to prevent accidents, standard OSS docs to establish trust, and honest disclaimers that this is a portfolio/demo project moving fast.

**Key Decisions from Planning:**
- **Comprehensive .gitignore**: Full stack coverage (Node + IaC + IDE) to prevent accidents as we add features
- **Minimal templates**: Just basic bug report ISSUE_TEMPLATE (CSW doesn't have others, defer advanced templates)
- **Standard CoC**: Contributor Covenant 2.1 template (no network fetch)
- **Extended AWS vars**: Include session token and profile for assumed roles
- **Minimal infra testing**: Just mention OpenTofu/Terraform with docs link
- **Honest security policy**: Best-effort, demo project (no SLA - "the day you pay me...")
- **OpenTofu focus**: Use "OpenTofu" or "OpenTofu/Terraform" in docs per PRD
- **Alpha maturity**: Add "Velocity over stability" declaration to stack.md

## Relevant Files

**Reference Patterns** (existing files to follow):
- `/home/mike/claude-spec-workflow/LICENSE` - MIT template with copyright
- `/home/mike/claude-spec-workflow/CONTRIBUTING.md` - Structure and sections to adapt
- `/home/mike/claude-spec-workflow/CHANGELOG.md` - Keep a Changelog format
- `/home/mike/claude-spec-workflow/.gitignore` - Base patterns to extend
- `/home/mike/claude-spec-workflow/spec/stack.md` - Maturity declaration format

**Files to Create**:
- `LICENSE` - MIT License with "DevOps To AI LLC dba TrakRF" copyright
- `CONTRIBUTING.md` - Adapted for infrastructure project with OpenTofu workflow
- `CODE_OF_CONDUCT.md` - Standard Contributor Covenant 2.1
- `SECURITY.md` - Infrastructure-specific security policy with honest disclaimers
- `CHANGELOG.md` - Keep a Changelog format, fresh start with [Unreleased] placeholder
- `.gitignore` - Comprehensive coverage: Node/TypeScript + IaC + IDE + secrets
- `.envrc` - direnv configuration (identical to CSW)
- `.env.local.example` - Template with GH_TOKEN + extended AWS vars (no real secrets)
- `.github/ISSUE_TEMPLATE/bug_report.md` - Basic bug report template

**Files to Modify**:
- `spec/stack.md` - Add maturity declaration at top

## Architecture Impact
- **Subsystems affected**: Documentation/Configuration only (no code subsystems)
- **New dependencies**: None
- **Breaking changes**: None

## Task Breakdown

### Task 1: Create LICENSE file
**File**: `LICENSE`
**Action**: CREATE
**Pattern**: Copy from claude-spec-workflow/LICENSE, update copyright

**Implementation**:
```text
MIT License

Copyright (c) 2025 DevOps To AI LLC dba TrakRF

[Standard MIT License text - unchanged from CSW]
```

**Validation**:
- [ ] Copyright holder matches PRD.md specification
- [ ] Year is 2025
- [ ] MIT License text is complete

### Task 2: Create comprehensive .gitignore
**File**: `.gitignore`
**Action**: CREATE
**Pattern**: Base from claude-spec-workflow/.gitignore + comprehensive additions

**Implementation**:
```gitignore
# IDE (from CSW base)
.idea/
.vscode/
.claude/
*.swp
*.swo
*~

# OS (from CSW base)
.DS_Store
Thumbs.db

# Spec workflow logs (from CSW base)
spec/active/*/log.md

# Node.js / npm
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*
dist/
build/
*.tsbuildinfo

# Environment (expanded from CSW)
.env
.env.local
.env.*.local

# OpenTofu / Terraform
.terraform/
*.tfstate
*.tfstate.*
*.tfstate.backup
*.tfvars
!*.tfvars.example
.terraform.lock.hcl
crash.log
crash.*.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json

# AWS
.aws/

# Logs
*.log
logs/

# Testing
.spec/
coverage/
.nyc_output/

# Build artifacts
*.zip
*.tar.gz
```

**Validation**:
- [ ] Includes CSW base patterns (IDE, OS, spec logs)
- [ ] Includes Node/TypeScript patterns (node_modules, dist, .tsbuildinfo)
- [ ] Includes OpenTofu/Terraform patterns (.terraform, tfstate, tfvars)
- [ ] Includes environment patterns (.env*)
- [ ] Excludes example files (!*.tfvars.example)

### Task 3: Create CONTRIBUTING.md
**File**: `CONTRIBUTING.md`
**Action**: CREATE
**Pattern**: Adapt from claude-spec-workflow/CONTRIBUTING.md

**Implementation**:
Adapt CSW CONTRIBUTING.md with these changes:
- Update all repository URLs: `trakrf/claude-spec-workflow` → `trakrf/action-spec`
- Update "Ways to Contribute" section:
  - Keep: Report Issues, Submit Pull Requests, Share Experience
  - Adapt examples to infrastructure context
- Development Setup section:
  - Prerequisites: Git, Bash, OpenTofu/Terraform, AWS CLI, Claude Code
  - Remove CSW-specific testing (csw init, commands)
  - Add minimal infrastructure testing: "Run `tofu plan` to validate changes. See [OpenTofu docs](https://opentofu.org/docs/intro/) for setup."
- Remove "Adding New Stack Presets" section (CSW-specific)
- Keep: Code Style, Commit Messages (Conventional Commits), PR Process, Documentation, Questions, Code of Conduct, License

**Validation**:
- [ ] All URLs point to trakrf/action-spec
- [ ] Prerequisites include OpenTofu/Terraform and AWS CLI
- [ ] Testing section mentions OpenTofu with docs link
- [ ] Conventional Commits format preserved
- [ ] No CSW-specific content (stack presets, slash commands)

### Task 4: Create CODE_OF_CONDUCT.md
**File**: `CODE_OF_CONDUCT.md`
**Action**: CREATE
**Pattern**: Standard Contributor Covenant 2.1 template

**Implementation**:
```markdown
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, caste, color, religion, or sexual
identity and orientation.

[... standard Contributor Covenant 2.1 text ...]

## Enforcement

Project maintainers are responsible for clarifying and enforcing our standards of
acceptable behavior and will take appropriate and fair corrective action in
response to any behavior that they deem inappropriate, threatening, offensive,
or harmful.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage],
version 2.1, available at
[https://www.contributor-covenant.org/version/2/1/code_of_conduct.html][v2.1].

[homepage]: https://www.contributor-covenant.org
[v2.1]: https://www.contributor-covenant.org/version/2/1/code_of_conduct.html
```

**Validation**:
- [ ] Uses Contributor Covenant 2.1 text
- [ ] Includes attribution to Contributor Covenant
- [ ] Contact method mentioned (GitHub issues)

### Task 5: Create SECURITY.md
**File**: `SECURITY.md`
**Action**: CREATE
**Pattern**: Infrastructure-specific security policy (reference PRD.md lines 55-73, 141-172)

**Implementation**:
```markdown
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
```

**Validation**:
- [ ] Clear "demo project" disclaimer
- [ ] Honest "best effort" response timeline
- [ ] GitHub Security Advisories as preferred reporting method
- [ ] Safe harbor for security researchers
- [ ] Scope clearly defined (in/out)
- [ ] User security best practices included

### Task 6: Create CHANGELOG.md
**File**: `CHANGELOG.md`
**Action**: CREATE
**Pattern**: Copy structure from claude-spec-workflow/CHANGELOG.md, clear content

**Implementation**:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security
```

**Validation**:
- [ ] Includes Keep a Changelog and Semantic Versioning references
- [ ] Has [Unreleased] section with standard categories
- [ ] No version entries (fresh start)
- [ ] Format matches CSW CHANGELOG.md structure

### Task 7: Create .envrc
**File**: `.envrc`
**Action**: CREATE
**Pattern**: Identical to claude-spec-workflow/.envrc

**Implementation**:
```bash
dotenv_if_exists .env.local
```

**Validation**:
- [ ] Single line: `dotenv_if_exists .env.local`
- [ ] Matches CSW pattern exactly

### Task 8: Create .env.local.example
**File**: `.env.local.example`
**Action**: CREATE
**Pattern**: Based on CSW, extended with AWS variables

**Implementation**:
```bash
# GitHub Personal Access Token (for PR creation, repo access)
# Generate at: https://github.com/settings/tokens
GH_TOKEN=

# AWS Credentials (for infrastructure deployment)
# IMPORTANT: Never commit real credentials - use this template only
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
AWS_PROFILE=
AWS_SESSION_TOKEN=

# Optional: Linear API key (if using Linear for project management)
LINEAR_API_KEY=
```

**Validation**:
- [ ] All variables empty (no real secrets)
- [ ] GH_TOKEN with generation URL comment
- [ ] Extended AWS variables (6 total)
- [ ] Warning comment about not committing real credentials
- [ ] Optional LINEAR_API_KEY from CSW preserved

### Task 9: Create basic bug report template
**File**: `.github/ISSUE_TEMPLATE/bug_report.md`
**Action**: CREATE
**Pattern**: Standard GitHub bug report template

**Implementation**:
```markdown
---
name: Bug Report
about: Report a bug or unexpected behavior
title: '[BUG] '
labels: bug
assignees: ''
---

## Describe the Bug
A clear description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1.
2.
3.

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g., macOS, Linux, Windows]
- OpenTofu/Terraform version: [e.g., 1.6.0]
- AWS CLI version: [e.g., 2.13.0]

## Additional Context
Any other relevant information.
```

**Validation**:
- [ ] GitHub frontmatter with name, about, title, labels
- [ ] Standard sections: Describe, Reproduce, Expected, Actual, Environment
- [ ] Infrastructure-specific environment info (OpenTofu, AWS CLI)

### Task 10: Update spec/stack.md with maturity declaration
**File**: `spec/stack.md`
**Action**: MODIFY
**Pattern**: Add maturity declaration like claude-spec-workflow/spec/stack.md

**Implementation**:
Add after first heading, before metadata block:
```markdown
# Stack: TypeScript + React + Vite

**Maturity**: Alpha - Velocity over stability. Breaking changes expected.

> **Package Manager**: npm
[... rest unchanged ...]
```

**Validation**:
- [ ] Maturity declaration matches CSW format
- [ ] Inserted after heading, before metadata
- [ ] Rest of file unchanged

### Task 11: Validate no secrets committed
**Action**: VALIDATE

**Implementation**:
```bash
# Search for common secret patterns
grep -r "ghp_" .
grep -r "AKIA" .  # AWS access key pattern
grep -r "aws_secret_access_key.*=.*[^=]$" .
```

**Validation**:
- [ ] No GitHub tokens (ghp_)
- [ ] No AWS access keys (AKIA)
- [ ] No real AWS secret keys
- [ ] All .env.local.example variables are empty

### Task 12: Validate all links point to action-spec
**Action**: VALIDATE

**Implementation**:
```bash
# Check for CSW repository references
grep -r "claude-spec-workflow" *.md .github/
# Should only be references, no direct links
```

**Validation**:
- [ ] No links to claude-spec-workflow repo (except as references in SECURITY.md context)
- [ ] All issue/PR URLs point to trakrf/action-spec
- [ ] CONTRIBUTING.md has correct repository URLs

## Risk Assessment

**Risk**: Accidentally committing real secrets from .env.local
**Mitigation**: Comprehensive .gitignore includes .env.local, .env.local.example has no real values, validation task checks for secret patterns

**Risk**: Copy-paste errors leaving CSW URLs in docs
**Mitigation**: Validation task specifically checks for claude-spec-workflow references

**Risk**: .gitignore missing critical patterns, causing accidents later
**Mitigation**: Comprehensive .gitignore now covering all future stack components (Node, OpenTofu, AWS)

## Integration Points
- None - pure documentation and configuration
- No code changes, store updates, or route modifications

## VALIDATION GATES (MANDATORY)

Since this is documentation/configuration only (no compiled code), traditional validation gates don't fully apply. Instead:

**After each task:**
- Verify file content matches pattern
- Check for secret patterns (Task 11)
- Verify links point to correct repo (Task 12)

**Final validation:**
- [ ] All 10 files created successfully
- [ ] spec/stack.md updated with maturity declaration
- [ ] No secrets in any files
- [ ] All repository URLs point to action-spec
- [ ] Markdown files are properly formatted

**Note**: Lint, typecheck, test, and build commands from stack.md don't apply yet (no npm project). This is expected - OSS documentation precedes code implementation.

## Validation Sequence

After each file creation: Verify content, check for secrets
After all files created: Run comprehensive link/secret validation
Final check: Review all files for consistency and completeness

## Plan Quality Assessment

**Complexity Score**: 4/10 (LOW)
**Confidence Score**: 10/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Exact reference patterns from claude-spec-workflow
✅ All clarifying questions answered
✅ No code dependencies or external packages
✅ Simple file creation/templating tasks
✅ Straightforward validation criteria

**Assessment**: This is pure documentation and configuration work following established templates. All source files exist and are well-understood. Zero implementation risk.

**Estimated one-pass success probability**: 98%

**Reasoning**: Only potential issues are copy-paste errors (easily caught by validation tasks) or forgetting to update a URL. All templates are available, no complex logic required, no external dependencies. Success is nearly guaranteed with proper attention to detail.
