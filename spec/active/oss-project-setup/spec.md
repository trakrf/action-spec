# Feature: Open Source Project Setup

## Metadata
- **Feature**: oss-project-setup
- **Type**: Infrastructure / Project Setup
- **Complexity**: Low
- **Stack**: N/A (documentation and configuration files)

## Origin
This specification emerged from Phase 0 requirements in PRD.md (line 434): "Copy open source project boilerplate from claude-spec-workflow project with appropriate project name updates"

## Outcome
ActionSpec will have a complete, professional open source project structure with all standard OSS documentation files, following the same patterns as claude-spec-workflow but customized for an infrastructure-as-code project.

## User Story
As an **open source contributor or user**
I want **clear documentation, contribution guidelines, and security policies**
So that **I can safely use, contribute to, and trust the ActionSpec project**

## Context

### Discovery
- ActionSpec is a portfolio/demo project for YAML-driven infrastructure deployment
- PRD.md explicitly calls for standard OSS files: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, LICENSE
- Source project (claude-spec-workflow) has established patterns we should follow
- Project uses CSW (Claude Spec Workflow) for development

### Current State
- Repository exists at https://github.com/trakrf/action-spec
- Only has: PRD.md, spec/ directory with CSW structure
- No OSS documentation files
- No environment configuration
- No contribution guidelines

### Desired State
Complete OSS project setup with:
- LICENSE (MIT, correct copyright)
- CONTRIBUTING.md (adapted for infrastructure code)
- CODE_OF_CONDUCT.md (standard Contributor Covenant)
- SECURITY.md (infrastructure-specific security policy)
- CHANGELOG.md (Keep a Changelog format, starting fresh)
- .envrc (direnv setup)
- .env.local (template with infrastructure-specific variables)
- .gitignore updates (terraform/infrastructure patterns)

## Technical Requirements

### 1. License File
- **Source**: claude-spec-workflow/LICENSE
- **Action**: Copy and update copyright
- **Changes**:
  - Copyright holder: `DevOps To AI LLC dba TrakRF` (per PRD.md line 594)
  - Year: 2025
  - Keep MIT License terms unchanged

### 2. Contributing Guidelines
- **Source**: claude-spec-workflow/CONTRIBUTING.md
- **Action**: Adapt for ActionSpec
- **Changes**:
  - Update repository URLs to `trakrf/action-spec`
  - Adapt "Development Setup" for infrastructure project:
    - Prerequisites: Git, Bash, Terraform/OpenTofu, AWS CLI, Claude Code
    - Local testing with terraform plan/apply
    - Security scanning requirements
  - Keep: Contribution workflow, commit message format, code style guides
  - Adapt "Stack Presets" section → "Infrastructure Modules" section
  - Update "Questions" link to action-spec issues

### 3. Code of Conduct
- **Source**: Create from Contributor Covenant 2.1 template
- **Action**: Add standard Code of Conduct
- **Content**:
  - Standard Contributor Covenant text
  - Enforcement: Project maintainers
  - Contact: Via GitHub issues or email

### 4. Security Policy
- **Source**: Create new (PRD.md has security requirements)
- **Action**: Create infrastructure-specific security policy
- **Content**:
  - Reporting vulnerabilities (GitHub Security Advisories + email)
  - Scope: What's in/out of scope for this demo project
  - Response timeline
  - Safe harbor for security researchers
  - Disclaimer: Demo project, not production-ready
  - Reference PRD.md security guidelines (lines 55-73, 141-172)

### 5. Changelog
- **Source**: claude-spec-workflow/CHANGELOG.md
- **Action**: Copy structure, clear content
- **Changes**:
  - Keep format: "Keep a Changelog" + Semantic Versioning
  - Clear all version entries
  - Add placeholder: `## [Unreleased]` with empty sections
  - Keep format explanation at top

### 6. Environment Configuration
- **Source**: claude-spec-workflow/.envrc and .env.local
- **Action**: Copy pattern, update variables

#### .envrc
- Identical to source: `dotenv_if_exists .env.local`

#### .env.local (Template)
- Create `.env.local.example` with:
  ```bash
  # GitHub Personal Access Token (for PR creation, repo access)
  GH_TOKEN=

  # AWS Credentials (for infrastructure deployment)
  AWS_ACCESS_KEY_ID=
  AWS_SECRET_ACCESS_KEY=
  AWS_REGION=us-east-1

  # Optional: Linear API key (if using Linear for project management)
  LINEAR_API_KEY=
  ```
- Add to .gitignore: `.env.local` (real secrets)
- DO NOT copy actual tokens from source

### 7. Gitignore Updates
- **Source**: Check if claude-spec-workflow has terraform/IaC patterns
- **Action**: Add infrastructure-specific patterns
- **Additions**:
  ```
  # Terraform / OpenTofu
  .terraform/
  *.tfstate
  *.tfstate.*
  *.tfvars
  !*.tfvars.example
  .terraform.lock.hcl
  crash.log
  crash.*.log

  # Environment
  .env
  .env.local

  # AWS
  .aws/

  # Logs
  *.log
  ```

### 8. Additional OSS Files (Optional)
Consider creating (defer to planning):
- .github/ISSUE_TEMPLATE/ (bug, feature, security)
- .github/PULL_REQUEST_TEMPLATE.md
- .github/FUNDING.yml (if accepting sponsorships)
- .editorconfig (code style consistency)

## Validation Criteria

### Must Have
- [ ] LICENSE file exists with correct copyright: "DevOps To AI LLC dba TrakRF"
- [ ] CONTRIBUTING.md exists with action-spec repository URLs
- [ ] CODE_OF_CONDUCT.md exists (Contributor Covenant)
- [ ] SECURITY.md exists with vulnerability reporting process
- [ ] CHANGELOG.md exists with Keep a Changelog format
- [ ] .envrc exists with direnv configuration
- [ ] .env.local.example exists (no real secrets)
- [ ] .gitignore includes terraform/infrastructure patterns
- [ ] All markdown files use consistent formatting
- [ ] All links point to trakrf/action-spec (not claude-spec-workflow)

### Quality Checks
- [ ] No secrets or tokens copied to any files
- [ ] All repository URLs updated correctly
- [ ] Contributing guide reflects infrastructure development workflow
- [ ] Security policy appropriate for demo/portfolio project
- [ ] Changelog format matches Keep a Changelog specification

### Documentation
- [ ] Files follow established patterns from claude-spec-workflow
- [ ] Customizations appropriate for infrastructure project
- [ ] Security considerations for public demo project addressed

## Success Metrics

### Immediate
- 8 new OSS documentation files created
- Zero secrets in repository
- All links point to correct repository
- Passes GitHub's community standards check

### Long-term
- Contributors understand how to contribute safely
- Security researchers know how to report issues
- Project appears professional and trustworthy
- Reduces barriers to open source contributions

## References

### Source Material
- claude-spec-workflow repository structure
- PRD.md lines 606-617 (OSS documentation requirements)
- PRD.md lines 55-73, 141-172 (security guidelines)
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/
- Contributor Covenant: https://www.contributor-covenant.org/version/2/1/code_of_conduct/
- Semantic Versioning: https://semver.org/spec/v2.0.0.html

### Key Decisions
- **Copyright holder**: "DevOps To AI LLC dba TrakRF" (per PRD.md)
- **Repository**: https://github.com/trakrf/action-spec
- **License**: MIT (same as claude-spec-workflow)
- **Changelog format**: Keep a Changelog with Semantic Versioning
- **Environment**: direnv + .env.local pattern

### Assumptions
- Using same organizational patterns as claude-spec-workflow
- GitHub Actions for CI/CD (will need GH_TOKEN)
- AWS for infrastructure (will need AWS credentials)
- Demo project appropriate disclaimers in security policy
- Terraform/OpenTofu for IaC (per PRD.md)

### Deferred to Planning
- Specific AWS environment variables beyond basic credentials
- GitHub issue/PR templates (nice-to-have)
- Detailed contributing workflow for infrastructure testing
- Whether to include TESTING.md initially
- EditorConfig settings
