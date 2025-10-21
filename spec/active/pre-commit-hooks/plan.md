# Implementation Plan: Pre-commit Security Hooks
Generated: 2025-10-21
Specification: spec.md

## Understanding

This feature implements local pre-commit validation to catch security violations before they enter Git history. This is the critical "last line of defense" for a public repository where any committed secrets/credentials become effectively permanent.

**Core Requirements:**
- Bash scripts with zero external dependencies
- Scan only staged files for performance (<5 seconds)
- Hard block on violations (security-first)
- Hybrid usage: Git hook OR standalone script
- Clear, actionable error messages with file:line references
- Industry best practices for B2B SaaS security

**Key Design Decisions (from clarifying questions):**
1. ✅ Integrate into existing `security-scan.yml` workflow
2. ✅ Skip all `.example` files (blanket rule for templates)
3. ✅ Relaxed patterns for `.md` files (allow generic examples, block real secrets)
4. ✅ Use `grep -I` to auto-skip binary files
5. ✅ Create README.md with development setup section

## Relevant Files

**Reference Patterns**:
- `.github/workflows/security-scan.yml` (lines 33-56) - Existing AWS account ID and private IP pattern checks
  - Shows project's grep patterns and exclusion approach
  - Demonstrates error message format currently in use

**Files to Create**:
- `scripts/pre-commit-checks.sh` - Main validation script with all security pattern checks
- `scripts/install-hooks.sh` - One-command hook installer for developer setup
- `README.md` - Project README with development setup instructions

**Files to Modify**:
- `.github/workflows/security-scan.yml` - Add new job `pre-commit-validation` that runs the script

## Architecture Impact

- **Subsystems affected**: Developer tooling, CI/CD pipeline
- **New dependencies**: None (pure bash + standard Unix tools)
- **Breaking changes**: None (purely additive)

## Task Breakdown

### Task 1: Create Main Pre-commit Validation Script
**File**: `scripts/pre-commit-checks.sh`
**Action**: CREATE

**Pattern**: Reference `.github/workflows/security-scan.yml` lines 33-56 for existing grep patterns

**Implementation**:
```bash
#!/bin/bash
set -euo pipefail

# ANSI color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Initialize violation counter
VIOLATIONS_FOUND=0

# Get list of staged files (or all files if not in git context)
if git rev-parse --git-dir > /dev/null 2>&1; then
  STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || echo "")
else
  # Not in git context (CI environment) - scan all tracked files
  STAGED_FILES=$(git ls-files 2>/dev/null || find . -type f)
fi

# Exit early if no files to check
if [ -z "$STAGED_FILES" ]; then
  echo -e "${GREEN}✅ No files to check${NC}"
  exit 0
fi

# Filter out files we should skip
FILTERED_FILES=""
for file in $STAGED_FILES; do
  # Skip .example files (templates with placeholder values)
  if [[ "$file" =~ \.example$ ]] || [[ "$file" =~ \.example\. ]]; then
    continue
  fi

  # Skip excluded directories
  if [[ "$file" =~ ^(node_modules|\.git|dist|build|\.terraform)/.*$ ]]; then
    continue
  fi

  # Only include relevant file types
  if [[ "$file" =~ \.(tf|py|js|jsx|ts|tsx|yml|yaml|json|sh|md)$ ]]; then
    FILTERED_FILES="$FILTERED_FILES $file"
  fi
done

# Exit if no relevant files
if [ -z "$FILTERED_FILES" ]; then
  echo -e "${GREEN}✅ No relevant files to scan${NC}"
  exit 0
fi

echo "🔍 Scanning $(echo $FILTERED_FILES | wc -w | tr -d ' ') staged files for security violations..."

# Function to report violations
report_violation() {
  local file=$1
  local line_num=$2
  local pattern_name=$3
  local matched_text=$4

  echo -e "\n📄 ${YELLOW}${file}:${line_num}${NC}"
  echo -e "   ⚠️  ${pattern_name}: ${matched_text}"
  VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
}

# Check 1: AWS Account IDs (12 consecutive digits)
# Relaxed for .md files (docs can have examples)
echo "  Checking for AWS account IDs..."
for file in $FILTERED_FILES; do
  if [ ! -f "$file" ]; then
    continue
  fi

  # For markdown files, only check for the real account number
  if [[ "$file" =~ \.md$ ]]; then
    while IFS=: read -r line_num line_text; do
      if [[ "$line_text" =~ 252374924199 ]]; then
        report_violation "$file" "$line_num" "Real AWS Account ID detected" "252374924199"
      fi
    done < <(grep -nI "252374924199" "$file" 2>/dev/null || true)
  else
    # For code files, block any 12-digit pattern
    while IFS=: read -r line_num line_text; do
      if [[ "$line_text" =~ [0-9]{12} ]]; then
        matched=$(echo "$line_text" | grep -oE '[0-9]{12}' | head -1)
        report_violation "$file" "$line_num" "AWS Account ID pattern detected" "$matched"
      fi
    done < <(grep -nIE '[0-9]{12}' "$file" 2>/dev/null || true)
  fi
done

# Check 2: Private IP Addresses
# Relaxed for .md files
echo "  Checking for private IP addresses..."
for file in $FILTERED_FILES; do
  if [ ! -f "$file" ]; then
    continue
  fi

  # Skip markdown files for IP checks (docs often have IP examples)
  if [[ "$file" =~ \.md$ ]]; then
    continue
  fi

  # Check for 10.x.x.x
  while IFS=: read -r line_num line_text; do
    matched=$(echo "$line_text" | grep -oE '10\.([0-9]{1,3}\.){2}[0-9]{1,3}' | head -1)
    if [ -n "$matched" ]; then
      report_violation "$file" "$line_num" "Private IP address (10.x.x.x)" "$matched"
    fi
  done < <(grep -nIE '10\.([0-9]{1,3}\.){2}[0-9]{1,3}' "$file" 2>/dev/null || true)

  # Check for 172.16-31.x.x
  while IFS=: read -r line_num line_text; do
    matched=$(echo "$line_text" | grep -oE '172\.(1[6-9]|2[0-9]|3[01])\.([0-9]{1,3}\.)[0-9]{1,3}' | head -1)
    if [ -n "$matched" ]; then
      report_violation "$file" "$line_num" "Private IP address (172.16-31.x.x)" "$matched"
    fi
  done < <(grep -nIE '172\.(1[6-9]|2[0-9]|3[01])\.([0-9]{1,3}\.)[0-9]{1,3}' "$file" 2>/dev/null || true)

  # Check for 192.168.x.x
  while IFS=: read -r line_num line_text; do
    matched=$(echo "$line_text" | grep -oE '192\.168\.([0-9]{1,3}\.)[0-9]{1,3}' | head -1)
    if [ -n "$matched" ]; then
      report_violation "$file" "$line_num" "Private IP address (192.168.x.x)" "$matched"
    fi
  done < <(grep -nIE '192\.168\.([0-9]{1,3}\.)[0-9]{1,3}' "$file" 2>/dev/null || true)
done

# Check 3: Common Secret Patterns
echo "  Checking for secrets and credentials..."
SECRET_PATTERNS=(
  "aws_access_key_id\s*=\s*[A-Z0-9]+"
  "aws_secret_access_key\s*=\s*[A-Za-z0-9/+]+"
  "password\s*=\s*[^\s]+"
  "secret\s*=\s*[^\s]+"
  "token\s*=\s*[^\s]+"
  "api_key\s*=\s*[^\s]+"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
  for file in $FILTERED_FILES; do
    if [ ! -f "$file" ]; then
      continue
    fi

    # Skip markdown files for secret patterns (docs have examples)
    if [[ "$file" =~ \.md$ ]]; then
      continue
    fi

    while IFS=: read -r line_num line_text; do
      matched=$(echo "$line_text" | grep -oE "$pattern" | head -1)
      if [ -n "$matched" ]; then
        report_violation "$file" "$line_num" "Potential secret detected" "$matched"
      fi
    done < <(grep -nIE "$pattern" "$file" 2>/dev/null || true)
  done
done

# Check 4: Forbidden Files (should be in .gitignore, but double-check)
echo "  Checking for forbidden files..."
FORBIDDEN_PATTERNS=(
  "\.tfstate$"
  "\.tfstate\.backup$"
  "^\.env$"
  "^\.env\.local$"
  "^\.env\.production$"
  "credentials\.json$"
)

for file in $STAGED_FILES; do
  for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if [[ "$file" =~ $pattern ]]; then
      # Don't show line number for file-level violations
      echo -e "\n📄 ${YELLOW}${file}${NC}"
      echo -e "   ⚠️  Forbidden file type: Should be in .gitignore"
      VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
    fi
  done
done

# Report results
echo ""
if [ $VIOLATIONS_FOUND -gt 0 ]; then
  echo -e "${RED}❌ Pre-commit check FAILED!${NC}"
  echo ""
  echo -e "${RED}Found ${VIOLATIONS_FOUND} security violation(s)${NC}"
  echo ""
  echo "🚫 Commit blocked. Fix these issues before committing."
  echo ""
  echo "To bypass (NOT recommended): git commit --no-verify"
  exit 1
else
  echo -e "${GREEN}✅ Pre-commit checks passed${NC}"
  exit 0
fi
```

**Validation**:
```bash
# Make script executable
chmod +x scripts/pre-commit-checks.sh

# Test with no files staged
./scripts/pre-commit-checks.sh
# Expected: "✅ No files to check" or "✅ Pre-commit checks passed"

# Test detection (create temp file with violation)
echo "aws_access_key_id = AKIAIOSFODNN7EXAMPLE" > /tmp/test-violation.tf
git add /tmp/test-violation.tf
./scripts/pre-commit-checks.sh
# Expected: Should detect and report the secret
git reset HEAD /tmp/test-violation.tf
rm /tmp/test-violation.tf
```

---

### Task 2: Create Hook Installer Script
**File**: `scripts/install-hooks.sh`
**Action**: CREATE

**Pattern**: Standard Git hook installation pattern for teams

**Implementation**:
```bash
#!/bin/bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

HOOK_DIR=".git/hooks"
HOOK_SOURCE="scripts/pre-commit-checks.sh"
HOOK_TARGET="$HOOK_DIR/pre-commit"

echo "🔧 Installing pre-commit hooks..."

# Verify we're in a git repository
if [ ! -d ".git" ]; then
  echo -e "${RED}❌ Not a git repository${NC}"
  echo "Run this script from the root of the repository"
  exit 1
fi

# Verify source script exists
if [ ! -f "$HOOK_SOURCE" ]; then
  echo -e "${RED}❌ Source script not found: $HOOK_SOURCE${NC}"
  exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DIR"

# Make source script executable
chmod +x "$HOOK_SOURCE"

# Check if hook already exists
if [ -f "$HOOK_TARGET" ] || [ -L "$HOOK_TARGET" ]; then
  echo -e "${YELLOW}⚠️  Pre-commit hook already exists${NC}"
  read -p "Overwrite? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled"
    exit 0
  fi
  rm -f "$HOOK_TARGET"
fi

# Create symlink
ln -sf "../../$HOOK_SOURCE" "$HOOK_TARGET"

echo -e "${GREEN}✅ Pre-commit hook installed successfully${NC}"
echo ""
echo "The hook will run automatically on 'git commit'"
echo ""
echo "Test it now:"
echo "  ./scripts/pre-commit-checks.sh"
echo ""
echo "To bypass the hook (not recommended):"
echo "  git commit --no-verify"
```

**Validation**:
```bash
# Make installer executable
chmod +x scripts/install-hooks.sh

# Test installation
./scripts/install-hooks.sh
# Expected: "✅ Pre-commit hook installed successfully"

# Verify symlink was created
ls -la .git/hooks/pre-commit
# Expected: symlink pointing to ../../scripts/pre-commit-checks.sh

# Test re-installation (should prompt for overwrite)
./scripts/install-hooks.sh
# Expected: "⚠️  Pre-commit hook already exists" + prompt
```

---

### Task 3: Update Security Scan Workflow
**File**: `.github/workflows/security-scan.yml`
**Action**: MODIFY

**Pattern**: Add new job to existing workflow (lines 26-56 show job structure)

**Implementation**:
Add this job after the `pattern-check` job:

```yaml
  pre-commit-validation:
    name: Pre-commit Hook Validation
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run pre-commit checks
        run: ./scripts/pre-commit-checks.sh
```

**Exact change**:
After line 57 (end of `pattern-check` job), add the new job.

**Validation**:
```bash
# Validate YAML syntax
yamllint .github/workflows/security-scan.yml 2>/dev/null || python3 -c "import yaml; yaml.safe_load(open('.github/workflows/security-scan.yml'))"

# Or just check if file is valid YAML
cat .github/workflows/security-scan.yml | grep -q "pre-commit-validation"
echo "✅ Workflow updated"
```

---

### Task 4: Create Project README
**File**: `README.md`
**Action**: CREATE

**Pattern**: Standard B2B SaaS open-source README with security emphasis

**Implementation**:
```markdown
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
```

**Validation**:
```bash
# Check README exists and has required sections
grep -q "Development Setup" README.md && \
grep -q "install-hooks.sh" README.md && \
echo "✅ README has development setup section"
```

---

### Task 5: Manual Hook Testing
**File**: N/A (testing task)
**Action**: VALIDATE

**Implementation**:
Test the hook against various scenarios to ensure correct behavior:

```bash
# Test 1: Clean commit (should pass)
echo "# Test comment" > test-clean.md
git add test-clean.md
git commit -m "test: clean file"
# Expected: ✅ Passes

# Test 2: AWS Account ID in code file (should block)
echo "account_id = 123456789012" > test-violation.tf
git add test-violation.tf
git commit -m "test: violation"
# Expected: ❌ Blocks with "AWS Account ID pattern detected"

# Test 3: AWS Account ID in .example file (should allow)
echo "account_id = 123456789012" > test.tfvars.example
git add test.tfvars.example
git commit -m "test: example file"
# Expected: ✅ Passes (example files skipped)

# Test 4: Generic 12-digit in markdown (should allow)
echo "Use a 12-digit account ID like 123456789012" > test-docs.md
git add test-docs.md
git commit -m "test: docs"
# Expected: ✅ Passes (relaxed for .md)

# Test 5: Real account ID in markdown (should block)
echo "Our account is 252374924199" > test-real.md
git add test-real.md
git commit -m "test: real account in docs"
# Expected: ❌ Blocks with "Real AWS Account ID detected"

# Test 6: Private IP in code (should block)
echo 'server_ip = "10.0.1.45"' > test-ip.py
git add test-ip.py
git commit -m "test: private IP"
# Expected: ❌ Blocks with "Private IP address detected"

# Test 7: Secret pattern (should block)
echo 'password = "secretvalue123"' > test-secret.js
git add test-secret.js
git commit -m "test: secret"
# Expected: ❌ Blocks with "Potential secret detected"

# Cleanup test files
git reset HEAD .
rm -f test-*.{md,tf,py,js}
```

**Validation**:
All tests must behave as expected. Document any edge cases discovered.

---

### Task 6: CI Workflow Validation
**File**: N/A (validation task)
**Action**: VALIDATE

**Implementation**:
Commit the changes and verify the CI workflow runs successfully:

```bash
# Create a test branch to verify CI
git checkout -b test/pre-commit-validation

# Commit all changes
git add scripts/ .github/workflows/security-scan.yml README.md
git commit -m "feat: add pre-commit security hooks

- Create pre-commit-checks.sh with security pattern validation
- Add install-hooks.sh for easy setup
- Integrate validation into security-scan.yml workflow
- Document development setup in README.md

Implements Phase 1 security foundation per PRD.md"

# Push and watch Actions
git push -u origin test/pre-commit-validation

# Monitor the workflow
# Go to: https://github.com/trakrf/action-spec/actions
# Verify: pre-commit-validation job runs and passes
```

**Validation**:
- All three jobs in `security-scan.yml` pass (secret-scanning, pattern-check, pre-commit-validation)
- Workflow completes in <2 minutes
- No false positives reported

---

## Risk Assessment

**Risk**: Regex patterns may have false positives or negatives
- **Mitigation**: Conservative patterns that prioritize security over convenience; extensive manual testing in Task 5

**Risk**: Performance degradation on large commits
- **Mitigation**: Only scan staged files; use grep -I to skip binaries; filter by relevant file extensions

**Risk**: Platform differences (macOS vs Linux bash)
- **Mitigation**: Use POSIX-compliant bash syntax; avoid GNU-specific grep flags; test on multiple platforms

**Risk**: Developers bypassing hooks with --no-verify
- **Mitigation**: CI runs the same validation; document that bypass is not recommended; team culture emphasis

## Integration Points

- **GitHub Actions**: New job in `security-scan.yml` runs on all PRs and pushes to main
- **Git Hooks**: Symlink from `.git/hooks/pre-commit` to `scripts/pre-commit-checks.sh`
- **Documentation**: README.md provides setup instructions for new contributors

## VALIDATION GATES (MANDATORY)

**Note**: This feature is pure bash scripting with no TypeScript/build requirements.

**Validation for this feature**:
1. **Script Syntax**: `bash -n scripts/pre-commit-checks.sh` (check syntax)
2. **Script Syntax**: `bash -n scripts/install-hooks.sh` (check syntax)
3. **YAML Validation**: `yamllint .github/workflows/security-scan.yml` (or Python YAML parser)
4. **Manual Testing**: All tests in Task 5 must pass
5. **CI Validation**: Workflow must run successfully in Task 6

**Standard validation commands from spec/stack.md are not applicable** since this is not TypeScript/Node.js code.

After each script creation:
- Run `bash -n <script>` to validate syntax
- Run `shellcheck <script>` if available (optional but recommended)
- Test execution manually

## Validation Sequence

**Per Task**:
- Task 1: Bash syntax check + manual execution test
- Task 2: Bash syntax check + manual installation test
- Task 3: YAML syntax validation
- Task 4: README markdown validation (grep for required sections)
- Task 5: Full manual test suite (all scenarios)
- Task 6: CI workflow green check

**Final Validation**:
```bash
# All scripts are syntactically valid
bash -n scripts/pre-commit-checks.sh
bash -n scripts/install-hooks.sh

# Hook can be installed
./scripts/install-hooks.sh

# Hook catches violations
# (manual test per Task 5)

# CI workflow passes
# (verify in GitHub Actions UI)
```

## Plan Quality Assessment

**Complexity Score**: 3/10 (LOW)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ Similar patterns found in `.github/workflows/security-scan.yml` (existing grep patterns)
- ✅ All clarifying questions answered with industry best practices
- ✅ Pure bash - no external dependencies or version conflicts
- ✅ Well-defined test scenarios in spec
- ⚠️ No existing shell scripts in repo to reference (new pattern)
- ✅ Extensive validation plan (manual + CI)

**Assessment**: High confidence implementation. The requirements are clear, patterns are straightforward, and validation is comprehensive. Main risk is regex accuracy, mitigated by conservative patterns and extensive testing.

**Estimated one-pass success probability**: 85%

**Reasoning**: Bash scripting is deterministic and well-understood. The spec provides exact patterns to implement. Risk areas are regex edge cases and platform differences, both addressed through testing. The 15% risk accounts for potential false positives/negatives that may require pattern refinement.
