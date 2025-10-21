# Implementation Plan: Security Automation Setup
Generated: 2025-10-21
Specification: spec.md

## Understanding

This feature establishes comprehensive automated security scanning for ActionSpec's CI/CD pipeline. We're building on GitHub security features already enabled in Phase 0 (secret scanning, push protection, branch protection) by adding automated workflows that run on every PR and commit.

**Key Goals**:
1. Prevent secrets/credentials from being committed (TruffleHog)
2. Block infrastructure-specific patterns (AWS IDs, private IPs)
3. Monitor dependencies for vulnerabilities (Dependabot)
4. Establish code scanning foundation (minimal CodeQL)
5. Document security posture for contributors

**Approach**: Industry-standard B2B SaaS security practices:
- Required status checks blocking PR merges (security-first)
- Exclude standard directories from scans (performance + accuracy)
- Wednesday weekly Dependabot updates (mid-week, team available)
- Minimal CodeQL setup now (expand when we have code)
- Security Hall of Fame to encourage responsible disclosure

## Relevant Files

**Reference Patterns**:
- N/A - No existing workflows in this repository
- **External reference**: [GitHub Actions security best practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- **External reference**: PRD.md lines 143-171 (security scanning requirements)

**Files to Create**:
- `.github/workflows/security-scan.yml` - TruffleHog + pattern checks workflow
- `.github/workflows/codeql.yml` - Minimal CodeQL code scanning
- `.github/dependabot.yml` - Dependency update automation

**Files to Modify**:
- `SECURITY.md` - Add automation documentation + Hall of Fame section

## Architecture Impact

- **Subsystems affected**: GitHub Actions CI/CD only
- **New dependencies**: None (using GitHub-provided actions)
- **Breaking changes**: None (adding new automation, not changing existing code)
- **Branch protection impact**: Will add security-scan as required status check

## Task Breakdown

### Task 1: Create Security Scanning Workflow
**File**: `.github/workflows/security-scan.yml`
**Action**: CREATE
**Pattern**: Standard GitHub Actions workflow with security focus

**Implementation**:
```yaml
name: Security Scan

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  secret-scanning:
    name: Scan for Secrets
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for TruffleHog

      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

  pattern-check:
    name: Check Infrastructure Patterns
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Check for AWS Account IDs
        run: |
          # Exclude standard directories
          if grep -r --exclude-dir={node_modules,.git,dist,build} \
             -E "[0-9]{12}" \
             --include="*.tf" --include="*.py" --include="*.js" \
             --include="*.yml" --include="*.yaml" .; then
            echo "❌ Found AWS account ID patterns"
            echo "Review and use variables instead of hardcoded IDs"
            exit 1
          fi
          echo "✅ No AWS account IDs found"

      - name: Check for Private IP Addresses
        run: |
          # Exclude standard directories
          if grep -r --exclude-dir={node_modules,.git,dist,build} \
             -E "10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\." \
             --include="*.tf" --include="*.yml" --include="*.yaml" .; then
            echo "❌ Found private IP address patterns"
            echo "Review and use variables instead of hardcoded IPs"
            exit 1
          fi
          echo "✅ No private IP addresses found"
```

**Validation**:
- [ ] YAML syntax valid (use yamllint or GitHub's validator)
- [ ] Workflow triggers on push to main and PRs
- [ ] TruffleHog scans full git history
- [ ] Pattern checks exclude standard directories
- [ ] Exit codes correct (0 = pass, 1 = fail)

### Task 2: Create Minimal CodeQL Workflow
**File**: `.github/workflows/codeql.yml`
**Action**: CREATE
**Pattern**: GitHub's CodeQL starter template, minimally configured

**Implementation**:
```yaml
name: CodeQL

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    # Run weekly on Wednesdays at 3 AM UTC
    - cron: '0 3 * * 3'

jobs:
  analyze:
    name: Analyze Code
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        # Start minimal, add languages as project grows
        # language: [ 'javascript', 'python' ]
        # For now, we have minimal code, so just set up the workflow
        language: [ ]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      # Note: Uncomment when we have actual code to scan
      # - name: Initialize CodeQL
      #   uses: github/codeql-action/init@v2
      #   with:
      #     languages: ${{ matrix.language }}

      # - name: Perform CodeQL Analysis
      #   uses: github/codeql-action/analyze@v2
      #   with:
      #     category: "/language:${{ matrix.language }}"
```

**Validation**:
- [ ] YAML syntax valid
- [ ] Workflow file exists and is committable
- [ ] Schedule set for Wednesdays
- [ ] Languages array empty (commented setup ready for Phase 2/3)
- [ ] Permissions configured correctly

**Note**: This creates the workflow file but doesn't run analysis yet. We'll uncomment and add languages in Phase 2 when we have Python/JS code.

### Task 3: Create Dependabot Configuration
**File**: `.github/dependabot.yml`
**Action**: CREATE
**Pattern**: Standard Dependabot config for multi-ecosystem monitoring

**Implementation**:
```yaml
version: 2
updates:
  # Monitor GitHub Actions for updates
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "wednesday"
      time: "09:00"
      timezone: "America/Los_Angeles"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"
    labels:
      - "dependencies"
      - "security"
    reviewers:
      - "mikestankavich"
    open-pull-requests-limit: 5

  # Monitor npm packages (when package.json added)
  # Uncomment when project has npm dependencies
  # - package-ecosystem: "npm"
  #   directory: "/"
  #   schedule:
  #     interval: "weekly"
  #     day: "wednesday"
  #     time: "09:00"
  #     timezone: "America/Los_Angeles"
  #   commit-message:
  #     prefix: "chore(deps)"
  #     include: "scope"
  #   labels:
  #     - "dependencies"
  #     - "security"
  #   reviewers:
  #     - "mikestankavich"

  # Monitor Python packages (when requirements.txt added)
  # Uncomment when project has Python dependencies
  # - package-ecosystem: "pip"
  #   directory: "/backend/lambda"
  #   schedule:
  #     interval: "weekly"
  #     day: "wednesday"
  #     time: "09:00"
  #     timezone: "America/Los_Angeles"
  #   commit-message:
  #     prefix: "chore(deps)"
  #     include: "scope"
  #   labels:
  #     - "dependencies"
  #     - "security"
  #   reviewers:
  #     - "mikestankavich"
```

**Validation**:
- [ ] YAML syntax valid
- [ ] github-actions ecosystem active
- [ ] npm and pip ecosystems commented (ready for future)
- [ ] Schedule: Wednesday 9 AM PT (industry standard)
- [ ] Conventional commit format (chore(deps))
- [ ] Reviewer set to maintainer
- [ ] PR limit set to 5 (prevents spam)

### Task 4: Update SECURITY.md Documentation
**File**: `SECURITY.md`
**Action**: MODIFY
**Pattern**: Expand existing security policy with automation details

**Implementation**:
Add new sections after existing content:

```markdown
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

---

**Last Updated**: 2025-10-21
```

**Validation**:
- [ ] Markdown syntax valid
- [ ] All commands tested locally
- [ ] Installation instructions accurate
- [ ] Hall of Fame section properly formatted
- [ ] Document matches actual workflow configuration

### Task 5: Enable Dependabot in Repository Settings
**Action**: MANUAL (via GitHub UI or API)
**Pattern**: GitHub repository configuration

**Implementation**:
Use GitHub CLI to enable Dependabot:

```bash
# Dependabot is enabled via the configuration file presence
# But we should verify it's active in repo settings

# Check current Dependabot status
gh api repos/trakrf/action-spec --jq '.security_and_analysis.dependabot_security_updates.status'

# If disabled, enable it:
# Note: Dependabot security updates are different from version updates
# Version updates are enabled by .github/dependabot.yml file
# Security updates can be enabled via API:

gh api --method PATCH repos/trakrf/action-spec \
  -f security_and_analysis[dependabot_security_updates][status]=enabled
```

**Validation**:
- [ ] Dependabot security updates enabled (check via gh api)
- [ ] .github/dependabot.yml file detected by GitHub
- [ ] First Dependabot PR appears within 7 days (success metric)

### Task 6: Configure Branch Protection for Security Workflows
**Action**: MODIFY (via GitHub API)
**Pattern**: Update existing branch protection ruleset

**Implementation**:
Add security-scan workflow as required status check:

```bash
# Get current ruleset
gh api repos/trakrf/action-spec/rulesets | jq '.[0]'

# The ruleset already requires PRs
# We need to add required status checks for our new workflows

# Note: This may need to be done via UI or after first workflow runs
# GitHub doesn't allow requiring status checks that haven't run yet

# Alternative: Document this as post-merge task
# After merging this PR and workflows run once, add as required check
```

**Validation**:
- [ ] Document need to add required status check post-merge
- [ ] Add to SHIPPED.md as follow-up task
- [ ] Test by creating dummy PR after merge

**Note**: We'll add this as a required status check after the first workflow run, documented in SHIPPED.md.

### Task 7: Test Workflows with Dummy Data
**Action**: VALIDATE
**Pattern**: Create test cases to verify pattern detection

**Implementation**:
After creating workflows, test with intentional violations:

1. Create test file with AWS ID pattern: `test/security/test-aws-id.txt`
   - Content: `123456789012`
   - Verify pattern-check job fails

2. Create test file with private IP: `test/security/test-private-ip.txt`
   - Content: `192.168.1.1`
   - Verify pattern-check job fails

3. Remove test files, verify workflows pass

**Validation**:
- [ ] Pattern checks correctly identify test violations
- [ ] Removing test files makes workflows pass
- [ ] Workflow logs are clear and actionable
- [ ] Exit codes correct (1 for fail, 0 for pass)

## Risk Assessment

**Risk**: TruffleHog false positives blocking legitimate commits
**Mitigation**:
- TruffleHog uses entropy analysis and regex patterns (low false positive rate)
- If false positive occurs, can add .trufflehogignore file
- Monitor first week for false positives (success metric)

**Risk**: Pattern checks blocking legitimate infrastructure code
**Mitigation**:
- Patterns are very specific (12 consecutive digits, exact IP ranges)
- Infrastructure code should use variables, not hardcoded values
- If needed, can add specific exclusions to grep commands

**Risk**: Dependabot creating too many PRs
**Mitigation**:
- Set open-pull-requests-limit: 5
- Weekly schedule (not daily) reduces PR volume
- Can pause Dependabot if overwhelming

**Risk**: CodeQL workflow consuming excessive Actions minutes
**Mitigation**:
- Currently no languages configured (won't run analysis)
- When enabled, runs only on schedule (weekly) + PRs
- GitHub provides 2000 free minutes/month (more than sufficient)

**Risk**: Required status checks preventing urgent hotfixes
**Mitigation**:
- Maintainers team (already configured) can bypass ruleset
- Emergency procedures documented in tech debt
- Can temporarily disable check if needed

## Integration Points

- **GitHub Actions**: New workflows integrate with existing PR process
- **Branch Protection**: Will add required status checks post-merge
- **SECURITY.md**: Expands existing security documentation
- **Dependabot**: Creates automated PRs for dependency updates
- **No code changes**: This is pure CI/CD configuration

## VALIDATION GATES (MANDATORY)

**CRITICAL**: Since this feature is configuration-only (no code), traditional validation gates don't apply. Instead:

**After each file creation:**
- ✅ YAML syntax validation (yamllint or GitHub validator)
- ✅ File committed successfully to git
- ✅ Markdown rendered correctly (for SECURITY.md)

**After all files created:**
- ✅ Commit and push to feature branch
- ✅ Create test PR to trigger workflows
- ✅ Verify workflows appear in Actions tab
- ✅ Verify workflows execute successfully
- ✅ Test pattern checks with intentional violations

**Final validation:**
- ✅ All workflows passing on feature branch
- ✅ SECURITY.md renders correctly on GitHub
- ✅ Dependabot config detected by GitHub
- ✅ No YAML syntax errors in any file

**Note**: Stack validation commands (lint, typecheck, test, build) defined in spec/stack.md don't apply yet since we have no npm project. Validation is workflow execution + YAML syntax.

## Validation Sequence

1. **Per-file validation**: YAML syntax check after creating each workflow
2. **Integration validation**: Push branch, verify workflows appear in Actions tab
3. **Functional validation**: Create test PR, verify workflows execute
4. **Pattern validation**: Test with intentional violations, verify detection
5. **Documentation validation**: Review SECURITY.md rendering on GitHub

## Plan Quality Assessment

**Complexity Score**: 2/10 (LOW)
**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec (detailed in spec.md)
✅ Industry-standard patterns (GitHub Actions, Dependabot, CodeQL)
✅ All clarifying questions answered (5/5 with industry best practices)
✅ No external dependencies (GitHub built-in features)
✅ No code complexity (pure configuration files)
✅ Well-documented in GitHub's official docs
✅ Low risk (non-breaking, additive only)
⚠️ Requires post-merge configuration (required status checks)

**Assessment**: This is straightforward configuration work following GitHub's standard practices. All patterns are well-documented, no custom code required, and the feature is purely additive (no breaking changes). The only uncertainty is verifying workflows execute correctly, which we'll validate via test PR.

**Estimated one-pass success probability**: 95%

**Reasoning**: High confidence because:
1. Configuration-only (no code logic to debug)
2. GitHub Actions/Dependabot are mature, well-documented platforms
3. YAML syntax is the main error vector (easily caught)
4. Pattern checks use simple grep (minimal complexity)
5. Industry best practices applied consistently
6. Test validation strategy is clear

The 5% uncertainty accounts for:
- Potential YAML syntax errors (easily fixed)
- GitHub Actions behavior quirks (rare but possible)
- Branch protection API nuances (documented workaround in place)
