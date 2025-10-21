# Feature: Security Automation Setup

## Metadata
- **Feature**: security-automation-setup
- **Type**: Infrastructure / Security
- **Complexity**: Medium
- **Stack**: GitHub Actions, Dependabot

## Origin
This specification consolidates Phase 1 tasks #1 and #2 from PRD.md (lines 441). During conversation analysis, we discovered that "Initialize repository with security tooling" and "Set up GitHub security scanning" had significant overlap and most GitHub security features were already enabled during Phase 0.

## Outcome
ActionSpec will have comprehensive automated security scanning running on every PR and commit, preventing secrets, sensitive patterns, and vulnerable dependencies from entering the codebase.

## User Story
As a **developer contributing to ActionSpec**
I want **automated security checks in CI/CD**
So that **I can't accidentally commit secrets or deploy vulnerable code to this public demo project**

## Context

### Discovery
Analysis revealed current security posture:
- ✅ Secret scanning: **enabled** (from Phase 0)
- ✅ Push protection: **enabled** (from Phase 0)
- ✅ Branch protection: **main-branch-protection ruleset** active
- ❌ Dependabot: **disabled** (same as claude-spec-workflow reference)
- ❌ GitHub Actions workflows: **none** (no `.github/workflows/` directory)
- ❌ CodeQL scanning: **not configured**

### Current State
- GitHub security features partially enabled
- No automated CI/CD security checks
- Manual secret scanning required before commits
- Dependabot updates disabled

### Desired State
Complete security automation with:
- GitHub Actions workflows scanning every PR/commit
- TruffleHog secret detection
- Infrastructure-specific pattern checks (AWS IDs, private IPs)
- Dependabot monitoring dependencies
- Optional: CodeQL code analysis
- Documented security posture

## Technical Requirements

### 1. GitHub Actions Workflow: Security Scanning
**File**: `.github/workflows/security-scan.yml`

**Jobs**:
- **secret-scanning**: TruffleHog job scanning for leaked credentials
  - Uses: `trufflesecurity/trufflehog@main`
  - Scans: All files in repository
  - Trigger: On push and pull_request

- **pattern-check**: Infrastructure-specific pattern detection
  - Check for AWS account IDs: `grep -r "[0-9]{12}"`
  - Check for private IPs: `grep -rE "10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\."`
  - Scope: `*.tf`, `*.py`, `*.js`, `*.yml`, `*.yaml` files
  - Exit code: Fail if patterns found

**Source reference**: PRD.md lines 143-171

### 2. GitHub Actions Workflow: CodeQL (Optional)
**File**: `.github/workflows/codeql.yml`

**Purpose**: Static code analysis for security vulnerabilities
**Languages**: JavaScript/TypeScript (when frontend added), Python (for Lambdas)
**Trigger**: On push to main, pull_request, weekly schedule
**Note**: May defer until we have significant code to scan

### 3. Dependabot Configuration
**File**: `.github/dependabot.yml`

**Ecosystems to monitor**:
- npm (package.json - when added)
- pip (requirements.txt - when added)
- github-actions (workflow dependencies)

**Update schedule**: Weekly
**Reviewers**: Auto-assign to maintainers
**Commit message**: Conventional commits format

### 4. Documentation Update
**File**: `SECURITY.md`

**Additions**:
- Document enabled security features
- List automated scanning workflows
- Explain how contributors can run checks locally
- Link to GitHub security settings

### 5. README Update (Optional)
Add security badge/section:
- List security measures in place
- Link to SECURITY.md
- Mention automated scanning

## Validation Criteria

### Must Have
- [ ] `.github/workflows/security-scan.yml` exists with TruffleHog and pattern checks
- [ ] `.github/dependabot.yml` exists and monitors github-actions
- [ ] Dependabot enabled in repository settings
- [ ] Workflows trigger on PR creation (test with dummy PR)
- [ ] Pattern check correctly identifies test case (12-digit number in .tf file)
- [ ] SECURITY.md documents all security features
- [ ] All workflows passing on main branch

### Quality Checks
- [ ] Workflow YAML validated (no syntax errors)
- [ ] TruffleHog configured to scan from default branch
- [ ] Pattern regex tested with known false positives/negatives
- [ ] Dependabot doesn't spam with excessive PRs (weekly schedule)

### Documentation
- [ ] SECURITY.md explains how to run checks locally
- [ ] README mentions automated security scanning
- [ ] Workflow files have clear comments explaining each step

## Success Metrics

Define measurable success criteria (tracked in SHIPPED.md):

### Immediate
- [ ] **3 security workflows active** (secret scan, pattern check, and Dependabot configured)
- [ ] **100% PR coverage** - All new PRs automatically scanned before merge
- [ ] **Zero false positives in first week** - Pattern checks don't block legitimate code
- [ ] **Dependabot PR within 7 days** - Confirms monitoring is working

### Long-term
- [ ] **Zero secrets merged to main** - TruffleHog catches all accidental commits
- [ ] **Dependency CVEs addressed within 2 weeks** - Dependabot alerts acted upon
- [ ] **Security documentation viewed** - SECURITY.md gets traffic (GitHub insights)

## Technical Decisions

### Why TruffleHog over git-secrets?
- **TruffleHog**: Runs in CI, catches issues before merge
- **git-secrets**: Local pre-commit hook (addressed in separate Phase 1 task)
- **Decision**: Use both - TruffleHog for automation, git-secrets for developer experience

### Why pattern checks for AWS IDs and private IPs?
- **Portfolio project context**: Publicly visible repository
- **Risk**: Accidentally exposing AWS account structure or network topology
- **Examples from PRD**: Lines 164-170 show exact patterns to block
- **False positives**: Minimal - infrastructure code rarely needs hardcoded IDs/IPs

### Dependabot configuration choices
- **Weekly updates**: Balance security vs PR noise
- **Auto-assign**: Ensures visibility without manual tracking
- **Ecosystem focus**: Start with github-actions, expand as we add npm/pip

### CodeQL deferred decision
- **Rationale**: No significant code to scan yet (Phase 1 is mostly config)
- **Defer until**: Phase 2 (Core Infrastructure) or Phase 3 (Application Logic)
- **Effort saved**: ~30 minutes setup, reduces initial PR scope

## Constraints

- **No breaking changes**: Existing workflows (none) continue to work
- **Performance**: Scans should complete in <2 minutes total
- **Maintenance**: Low-touch automation, minimal manual intervention
- **Cost**: GitHub Actions free tier sufficient (2000 minutes/month)

## References

### Source Material
- **PRD.md lines 143-171**: Security scanning pipeline requirements
- **PRD.md lines 441**: Phase 1 consolidated tasks
- **PRD.md lines 473-532**: Technical debt section (deferred items)

### Similar Projects
- **claude-spec-workflow**: Reference for security posture baseline
  - Has: Secret scanning, push protection
  - Lacks: Workflows, Dependabot (we're adding these)

### GitHub Documentation
- [TruffleHog Action](https://github.com/marketplace/actions/trufflehog-oss)
- [Dependabot configuration](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [CodeQL setup](https://docs.github.com/en/code-security/code-scanning/automatically-scanning-your-code-for-vulnerabilities-and-errors/setting-up-code-scanning-for-a-repository)

## Conversation References

**Key insights:**
- "We already have secret scanning and push protection enabled from Phase 0" - Avoided duplicate work
- "CSW doesn't have Dependabot either" - We're improving on reference project
- "Pattern checks specific to infrastructure (AWS account IDs, private IPs)" - Domain-specific security

**Decisions:**
- Consolidate GitHub features + workflows into one cohesive PR (vs 2 separate PRs)
- Defer CodeQL until we have code worth scanning
- Enable Dependabot even though CSW doesn't (best practice for public project)

**Concerns addressed:**
- "Should we set up security scanning before we have infrastructure code?" - YES, preventive > reactive
- "Is this PR too large?" - At ~150 lines across 3-4 files, still reviewable

## Deferred Items

Captured in PRD.md Technical Debt section:
- Advanced security features (GuardDuty, Security Hub) - Post-demo
- CI/CD enhancements (Terraform plan preview, cost estimation) - Post-demo
- Automated compliance scanning - Future enhancement
