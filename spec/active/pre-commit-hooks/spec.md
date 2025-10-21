# Feature: Pre-commit Security Hooks

## Origin
This specification emerged from Phase 1 implementation planning (Security Foundation). After merging the Security Automation Setup PR, pre-commit hooks are the next critical safety layer before deploying infrastructure in Phase 2.

## Outcome
Developers will have automated, local validation that catches security violations **before** they enter the Git history. Once code is committed to a public repo, it's effectively public forever - this is the last line of defense.

## User Story
As a developer working on ActionSpec
I want automatic security checks before each commit
So that I never accidentally expose AWS credentials, account IDs, or internal network topology to the public repository

## Context

**Discovery**: This is a public, open-source portfolio project demonstrating infrastructure automation. Any security slip (exposed credentials, AWS account numbers, private IPs) would be:
- A real security risk (account 252374924199 is the actual AWS account)
- Professionally embarrassing (undermines "security-first" positioning)
- Potentially permanent (Git history is hard to truly erase)

**Current State**:
- GitHub Actions security scanning exists (CodeQL, secret scanning via security-scan.yml)
- But CI runs AFTER code is pushed
- No local pre-commit validation
- Easy to accidentally commit sensitive patterns

**Desired State**:
- Fast, local validation before commit
- Hard blocks on security violations
- Clear error messages showing what was caught and where
- Hybrid approach: Can run as Git hook OR standalone script
- Zero external dependencies (just bash + standard Unix tools)

## Technical Requirements

### 1. Script Location & Structure
- **Path**: `scripts/pre-commit-checks.sh`
- **Permissions**: Executable (`chmod +x`)
- **Shebang**: `#!/bin/bash` with `set -euo pipefail` for safety
- **Exit codes**: 0 = pass, 1 = violations found

### 2. Security Patterns to Detect

**MUST block on these patterns**:

```bash
# AWS Account IDs (12 digits)
[0-9]{12}

# Specific real account number
252374924199

# Private IP ranges
10\.([0-9]{1,3}\.){2}[0-9]{1,3}
172\.(1[6-9]|2[0-9]|3[01])\.([0-9]{1,3}\.)[0-9]{1,3}
192\.168\.([0-9]{1,3}\.)[0-9]{1,3}

# Common secret patterns
(aws_access_key_id|aws_secret_access_key|password|secret|token|api_key)\s*=\s*[^\s]+

# Terraform state files
\.tfstate
\.tfstate\.backup

# Environment files
\.env
\.env\.local
\.env\.production
credentials\.json
```

**File Types to Scan**:
- `.tf` - Terraform files
- `.py` - Python/Lambda code
- `.js`, `.jsx`, `.ts`, `.tsx` - Frontend code
- `.yml`, `.yaml` - GitHub Actions, configs
- `.json` - Configuration files
- `.sh` - Shell scripts
- `.md` - Documentation (could contain examples)

**Exclusions** (do NOT scan):
- `.git/` directory
- `node_modules/`
- `.terraform/`
- Binary files
- Files in `.gitignore`
- Files explicitly allowed (e.g., `terraform.tfvars.example`)

### 3. Hybrid Installation Strategy

**Option A: Install as Git Hook**
```bash
# Installer helper
scripts/install-hooks.sh

# Creates symlink:
ln -s ../../scripts/pre-commit-checks.sh .git/hooks/pre-commit
```

**Option B: Run Standalone**
```bash
# Developer can manually run
./scripts/pre-commit-checks.sh

# Or in CI/CD workflow
- name: Pre-commit checks
  run: ./scripts/pre-commit-checks.sh
```

### 4. Performance Requirements
- **Speed**: Must complete in <5 seconds for typical changeset
- **Efficiency**: Only scan staged files (not entire repo)
- **Feedback**: Show progress for slow operations

### 5. Error Reporting

When violations found, output MUST include:
```
❌ Pre-commit check FAILED!

Found security violations:

📄 infrastructure/demo/main.tf:42
   ⚠️  AWS Account ID detected: 252374924199

📄 backend/lambda/config.py:15
   ⚠️  Private IP address detected: 10.0.1.45

🚫 Commit blocked. Fix these issues before committing.

To bypass (NOT recommended): git commit --no-verify
```

### 6. User Experience

**First-time setup** (when developer clones repo):
```bash
# Simple one-liner in README
make install-hooks
# OR
./scripts/install-hooks.sh
```

**Daily usage**:
- Transparent - only shows output if violations found
- Fast - doesn't slow down commit workflow
- Helpful - tells you exactly what's wrong and where

## Code Examples

### Core Hook Script Structure
```bash
#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

# Exit if no files staged
if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

VIOLATIONS_FOUND=0

# Check for AWS account IDs
# Check for private IPs
# Check for secret patterns
# Check for forbidden files

if [ $VIOLATIONS_FOUND -gt 0 ]; then
  echo -e "${RED}❌ Pre-commit check FAILED!${NC}"
  echo ""
  echo "🚫 Commit blocked. Fix these issues before committing."
  echo "To bypass (NOT recommended): git commit --no-verify"
  exit 1
fi

echo -e "✅ Pre-commit checks passed"
exit 0
```

### Installation Script
```bash
#!/bin/bash
# scripts/install-hooks.sh

HOOK_DIR=".git/hooks"
HOOK_SOURCE="scripts/pre-commit-checks.sh"

if [ ! -d ".git" ]; then
  echo "❌ Not a git repository"
  exit 1
fi

mkdir -p "$HOOK_DIR"
ln -sf "../../$HOOK_SOURCE" "$HOOK_DIR/pre-commit"
chmod +x "$HOOK_SOURCE"

echo "✅ Pre-commit hook installed"
echo "   Run './scripts/pre-commit-checks.sh' to test"
```

## Validation Criteria

- [ ] Hook catches all defined security patterns
- [ ] Hook only scans staged files (not entire repo)
- [ ] Hook completes in <5 seconds for typical commits
- [ ] Error messages clearly identify file, line, and violation
- [ ] Can be installed with single command
- [ ] Can be run standalone without installation
- [ ] Works on both macOS and Linux
- [ ] Does not produce false positives on example files (*.example)
- [ ] Can be bypassed with `--no-verify` (standard Git behavior)
- [ ] Provides helpful output (not just "failed")

## Implementation Notes

### Design Decisions

**Why custom regex instead of external tools?**
- Speed: No tool installation/initialization overhead
- Simplicity: Works on any machine with bash
- Control: Exact patterns we care about
- Belt & Suspenders: CI still runs comprehensive scanning (trufflehog)

**Why hard block instead of warnings?**
- Public repository - once pushed, damage is done
- Security-first philosophy of the project
- Better safe than sorry with credentials

**Why hybrid approach?**
- Flexibility: Works for single dev or team
- Testing: Can run manually to verify patterns
- CI Integration: Same script runs in GitHub Actions
- Onboarding: Optional for contributors, required for maintainers

### Edge Cases to Handle

1. **Example files**: `terraform.tfvars.example` should be allowed
2. **Documentation**: This spec itself mentions AWS account patterns - allow in docs
3. **Binary files**: Skip scanning (grep fails on binaries)
4. **Large files**: Consider size limit to prevent slowdowns
5. **Already committed**: Hook only checks new commits, not history

### Integration Points

**GitHub Actions**: Add to existing workflow
```yaml
# .github/workflows/validate-spec.yml (or new workflow)
- name: Run pre-commit checks
  run: ./scripts/pre-commit-checks.sh
```

**Documentation**: Update README with:
```markdown
## Development Setup

1. Clone the repository
2. Install pre-commit hooks: `./scripts/install-hooks.sh`
3. Make changes and commit - hooks will validate automatically
```

## Conversation References

**Key Decision**:
> "im good with recommendations. definitely block on violation."

This confirms:
- Hard failure (not warnings)
- Hybrid script approach
- Lightweight implementation
- Block-first security posture

**Context from PRD** (lines 608-614):
```markdown
### Before EVERY Commit
- [ ] Run `git secrets --scan`
- [ ] Check for hardcoded IPs/CIDRs
- [ ] Verify no AWS account IDs
- [ ] Ensure no customer-specific patterns
- [ ] Test with example data only
```

This spec automates these manual checklist items.

**Security Philosophy** (PRD lines 29-32):
> "This **PUBLIC** open-source project showcases enterprise patterns while maintaining security appropriate for portfolio demonstration."

The pre-commit hook is a critical implementation of this philosophy - preventing public exposure of sensitive patterns before they enter Git history.

## Success Metrics

**Technical**:
- Zero false positives on legitimate commits
- 100% catch rate on defined violation patterns
- <5 second execution time
- Zero external dependencies

**User Experience**:
- One-command installation
- Clear, actionable error messages
- Doesn't interfere with normal workflow
- Easy to test/debug

**Security**:
- No AWS account IDs committed after hook installation
- No private IP ranges in committed code
- No .tfstate files accidentally committed
- No credentials in Git history
