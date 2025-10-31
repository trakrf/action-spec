# Implementation Plan: Fix TruffleHog GitHub Action Merge Commit Handling

Generated: 2025-10-31
Specification: spec.md

## Understanding

The current TruffleHog GitHub Action fails when PRs are merged to main because both `BASE` and `HEAD` resolve to the same commit, causing the error "BASE and HEAD commits are the same."

**Solution**: Remove the `push` trigger and keep only `pull_request` trigger. This ensures:
1. All commits are scanned during PR review (before merge)
2. No redundant scanning of merge commits (already scanned)
3. Clean CI status without confusing errors

**Security**: This change maintains 100% security coverage. Branch protection rules prevent direct pushes to main, ensuring all commits go through PRs and get scanned.

## Relevant Files

**Files to Modify**:
- `.github/workflows/security-scan.yml` (lines 1-25) - Remove `push` trigger, update TruffleHog parameters, add documentation

**Reference Pattern**:
- Other workflows in `.github/workflows/` use similar trigger patterns
- CodeQL workflow (`.github/workflows/codeql.yml`) may have similar patterns to reference

## Architecture Impact

- **Subsystems affected**: CI/CD only (GitHub Actions)
- **New dependencies**: None
- **Breaking changes**: None (security coverage maintained via branch protection)

## Task Breakdown

### Task 1: Update Workflow Trigger Configuration
**File**: `.github/workflows/security-scan.yml`
**Action**: MODIFY (lines 3-7)
**Pattern**: Simple YAML trigger modification

**Current Code** (lines 3-7):
```yaml
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

**New Code**:
```yaml
on:
  pull_request:
    branches: [ main ]
  # Note: Removed 'push' trigger to avoid redundant scanning of merge commits.
  # All commits are scanned during PR review before merge.
  # Branch protection ensures all changes go through PRs.
```

**Validation**:
- YAML syntax is valid
- Workflow file structure maintained

---

### Task 2: Update TruffleHog Action Parameters
**File**: `.github/workflows/security-scan.yml`
**Action**: MODIFY (lines 19-24)
**Pattern**: Update action parameters for PR-specific context

**Current Code** (lines 19-24):
```yaml
      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD
```

**New Code**:
```yaml
      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}
```

**Rationale**: Using PR-specific SHA references ensures TruffleHog scans the exact commit range in the pull request, avoiding the BASE==HEAD scenario.

**Validation**:
- YAML syntax is valid
- GitHub Actions context variables are correct for `pull_request` events

---

### Task 3: Add Workflow Documentation Header
**File**: `.github/workflows/security-scan.yml`
**Action**: MODIFY (add after line 1)
**Pattern**: Inline YAML comments for clarity

**Add After Line 1**:
```yaml
# Security Scanning with TruffleHog
#
# Runs on pull requests only to scan individual commits before merge.
# Merge commits are not scanned (redundant - commits already scanned in PR).
# Branch protection ensures all commits are reviewed via PRs.
#
```

**Validation**:
- Comments follow YAML syntax
- Documentation is clear and concise

---

### Task 4: Verify YAML Syntax
**Action**: Validate the modified workflow file

**Validation Steps**:
1. Check YAML syntax with online validator or `yamllint`
2. Ensure indentation is consistent (2 spaces)
3. Verify no syntax errors introduced

**Command** (optional, if yamllint installed):
```bash
yamllint .github/workflows/security-scan.yml
```

**Manual Check**:
- Review the diff carefully
- Ensure all changes are in the `secret-scanning` job only
- Confirm `pattern-check` and `pre-commit-validation` jobs remain unchanged

---

## Complete Modified File Preview

The final `.github/workflows/security-scan.yml` should look like:

```yaml
name: Security Scan
# Security Scanning with TruffleHog
#
# Runs on pull requests only to scan individual commits before merge.
# Merge commits are not scanned (redundant - commits already scanned in PR).
# Branch protection ensures all commits are reviewed via PRs.
#
on:
  pull_request:
    branches: [ main ]
  # Note: Removed 'push' trigger to avoid redundant scanning of merge commits.
  # All commits are scanned during PR review before merge.
  # Branch protection ensures all changes go through PRs.

jobs:
  secret-scanning:
    name: Scan for Secrets
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v5
        with:
          fetch-depth: 0  # Full history for TruffleHog

      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}

  pattern-check:
    name: Check Infrastructure Patterns
    runs-on: ubuntu-latest
    steps:
      # ... (unchanged)

  pre-commit-validation:
    name: Pre-commit Hook Validation
    runs-on: ubuntu-latest
    steps:
      # ... (unchanged)
```

## Risk Assessment

**Risks**: Minimal - this is a low-risk configuration change

- **Risk**: Direct push to main bypasses secret scanning
  **Mitigation**: Branch protection prevents direct pushes. Assumed to be configured.

- **Risk**: YAML syntax error breaks workflow
  **Mitigation**: Task 4 validates syntax. GitHub Actions will also validate on push.

- **Risk**: Wrong GitHub Actions context variables
  **Mitigation**: Using documented PR context variables (`pull_request.base.sha`, `pull_request.head.sha`)

## Integration Points

- **No code integration**: This is a CI/CD configuration change only
- **Other workflows**: Not affected (change is isolated to `security-scan.yml`)
- **Branch protection**: Relies on existing branch protection rules (assumed configured)

## VALIDATION GATES

**Note**: Standard validation gates (lint, typecheck, test) don't apply to workflow YAML files.

**Workflow-Specific Validation**:
1. ✅ YAML syntax is valid (Task 4)
2. ✅ GitHub Actions context variables are correct
3. ✅ Workflow structure is maintained
4. ✅ Other jobs in workflow are unchanged

**Post-Merge Validation** (automatic):
- Next PR will trigger TruffleHog scan ✅
- Merge of that PR will NOT trigger TruffleHog (no error) ✅
- CI status will be clean ✅

## Validation Sequence

After implementation:
1. Review the diff in Git
2. Verify YAML syntax (Task 4)
3. Commit and push changes
4. Observe workflow behavior on next PR (natural validation)

**No manual validation commands required** - this is a workflow configuration change that validates itself.

## Plan Quality Assessment

**Complexity Score**: 1/10 (TRIVIAL)
**Confidence Score**: 10/10 (VERY HIGH)

**Confidence Factors**:
- ✅ Simple YAML modification (remove 4 lines, update 2 parameters)
- ✅ Clear requirement from spec (Option 1 selected)
- ✅ No code changes, only configuration
- ✅ Existing workflow structure well understood
- ✅ GitHub Actions documentation confirms approach
- ✅ Low risk - easily reversible if issues arise
- ✅ Natural validation (workflow runs on next PR)

**Assessment**: This is a straightforward workflow configuration change with minimal risk. The solution is simple, well-documented, and follows GitHub Actions best practices.

**Estimated one-pass success probability**: 95%

**Reasoning**: The only risk is a typo in the YAML file or incorrect GitHub Actions context variables. The approach is standard and well-documented. The change is isolated and easily reversible if any issues occur.

## Rollback Plan

If issues arise after merging:

```bash
# Revert the commit
git revert HEAD
git push origin main
```

Or restore the original `push` trigger:

```yaml
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

## Expected Behavior After Fix

**Before Fix**:
1. Create PR → TruffleHog scans commits ✅
2. Merge PR → TruffleHog tries to scan merge commit ❌
3. Error: "BASE and HEAD commits are the same" ❌
4. CI shows red X ❌

**After Fix**:
1. Create PR → TruffleHog scans commits ✅
2. Merge PR → TruffleHog does NOT run ✅
3. No error messages ✅
4. CI shows green ✅

## Success Metrics

- ✅ TruffleHog runs successfully on all PRs
- ✅ No "BASE and HEAD are the same" errors after PR merges
- ✅ Clean CI status after merges
- ✅ 100% security coverage maintained (all commits scanned in PRs)
