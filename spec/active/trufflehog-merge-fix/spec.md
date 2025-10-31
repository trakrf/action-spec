# Feature: Fix TruffleHog GitHub Action Merge Commit Handling

## Metadata
**Type**: bugfix
**Estimated Time**: 15-20 minutes
**Priority**: Low (cosmetic, not security)

## Origin
This specification emerged from investigating a TruffleHog GitHub Action failure during cleanup after PR #41 was merged. The action failed with:

```
Error: BASE and HEAD commits are the same. TruffleHog won't scan anything.
```

**Discovery**: The action runs on `push` events to `main`. When a PR is merged, both `BASE` (main) and `HEAD` (HEAD pointing to main) resolve to the same commit, causing TruffleHog to exit with an error instead of gracefully skipping redundant scans.

**Security Status**: ✅ This is NOT a security issue. Individual PR commits were successfully scanned before merge. No secrets were found in the OAuth implementation (PR #41).

## Outcome
The TruffleHog GitHub Action will gracefully handle merge commits to `main` without failing, while continuing to scan all individual commits in pull requests for secrets.

## User Story
As a **repository maintainer**
I want **TruffleHog to handle merge commits gracefully**
So that **CI doesn't fail with confusing errors when PRs are merged**

## Context

### Current Behavior
1. TruffleHog action runs on both `pull_request` and `push` events
2. During PR review: Scans all individual commits ✅
3. After PR merge: Tries to scan merge commit (BASE=HEAD) ❌
4. Exits with error: "BASE and HEAD commits are the same"
5. GitHub Actions shows red X, causing confusion

### Desired Behavior
1. TruffleHog action runs on `pull_request` events only
2. During PR review: Scans all individual commits ✅
3. After PR merge: No redundant scan (commits already scanned) ✅
4. No confusing errors ✅
5. Clean CI status ✅

### Why This Happens
```yaml
# Current workflow triggers
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

When PR is merged to `main`:
- Triggers `push` event
- BASE resolves to: `584c713` (main branch tip)
- HEAD resolves to: `584c713` (HEAD points to main)
- TruffleHog gets identical commits: "Nothing to scan!"

## Technical Requirements

### Primary Requirement
Update `.github/workflows/security-scan.yml` to prevent redundant scanning of merge commits while maintaining security coverage.

### Constraints
1. **Security First**: Must not weaken secret detection
2. **Zero Gap**: All commits must be scanned exactly once
3. **Performance**: Avoid redundant scans of already-scanned commits
4. **Clarity**: No confusing error messages in CI

### Validation Logic
✅ **Individual commits in PRs**: Scanned before merge
✅ **Merge commits**: Skipped (no new content to scan)
✅ **Direct pushes to main**: Still caught (if someone bypasses PR)

## Implementation Options

### Option 1: PR-Only Scanning (Recommended)
**Pros**: Simple, clean, eliminates redundant scans
**Cons**: Doesn't catch direct pushes to main (rare, should be blocked by branch protection)

```yaml
name: Security Scan

on:
  pull_request:
    branches: [ main ]
  # Removed: push event

jobs:
  trufflehog:
    name: TruffleHog Secret Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: TruffleHog OSS
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}
```

### Option 2: Conditional Scanning with Smart Logic
**Pros**: Catches direct pushes to main, handles all scenarios
**Cons**: More complex, requires bash scripting

```yaml
name: Security Scan

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  trufflehog:
    name: TruffleHog Secret Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Determine scan scope
        id: scope
        run: |
          if [ "${{ github.event_name }}" == "pull_request" ]; then
            echo "base=${{ github.event.pull_request.base.sha }}" >> $GITHUB_OUTPUT
            echo "head=${{ github.event.pull_request.head.sha }}" >> $GITHUB_OUTPUT
            echo "should_scan=true" >> $GITHUB_OUTPUT
          elif [ "${{ github.event_name }}" == "push" ]; then
            # Check if this is a merge commit (2 parents)
            parent_count=$(git rev-list --parents -n 1 HEAD | wc -w)
            if [ $parent_count -gt 2 ]; then
              echo "Merge commit detected, skipping scan (commits already scanned in PR)"
              echo "should_scan=false" >> $GITHUB_OUTPUT
            else
              # Direct push to main (shouldn't happen with branch protection)
              echo "base=${{ github.event.before }}" >> $GITHUB_OUTPUT
              echo "head=${{ github.sha }}" >> $GITHUB_OUTPUT
              echo "should_scan=true" >> $GITHUB_OUTPUT
            fi
          fi

      - name: TruffleHog OSS
        if: steps.scope.outputs.should_scan == 'true'
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ steps.scope.outputs.base }}
          head: ${{ steps.scope.outputs.head }}
```

### Option 3: Action-Level Configuration
**Pros**: Simplest, relies on TruffleHog's built-in logic
**Cons**: May still show confusing messages

```yaml
# Add to existing action
- name: TruffleHog OSS
  uses: trufflesecurity/trufflehog@main
  continue-on-error: true  # Don't fail CI on duplicate commit errors
  with:
    path: ./
    base: main
    head: HEAD
```

## Recommended Solution

**Use Option 1: PR-Only Scanning**

**Rationale**:
1. **Simplicity**: Easiest to understand and maintain
2. **Security**: Branch protection should prevent direct pushes to main
3. **Performance**: Eliminates redundant scans completely
4. **Clarity**: No confusing error messages
5. **Standard Practice**: Most repos only scan PRs

**Branch Protection Prerequisite**:
Ensure GitHub branch protection rules require:
- Pull request reviews before merging
- Status checks must pass
- No direct pushes to main

## Implementation Steps

### 1. Update Workflow File (5 min)
**File**: `.github/workflows/security-scan.yml`

Remove `push` trigger, keep only `pull_request`:

```yaml
on:
  pull_request:
    branches: [ main ]
  # Removed: push trigger (redundant with PR scanning)
```

### 2. Verify Branch Protection (5 min)
**GitHub Settings → Branches → main**

Ensure these are enabled:
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
  - Select: `TruffleHog Secret Scan`
- ✅ Do not allow bypassing the above settings

### 3. Test the Fix (5 min)
**Create a test PR**:
```bash
git checkout -b test/trufflehog-fix
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify TruffleHog runs on PR only"
git push -u origin test/trufflehog-fix
gh pr create --title "test: TruffleHog PR-only scanning" --body "Verify action runs on PR, not on merge"
```

**Verify**:
1. ✅ TruffleHog runs during PR review
2. ✅ Merge the PR
3. ✅ No TruffleHog scan after merge (no error)
4. ✅ CI status is clean

### 4. Document the Change (5 min)
Add to workflow file comments:

```yaml
# Security Scanning with TruffleHog
#
# Runs on pull requests only to scan individual commits before merge.
# Merge commits are not scanned (redundant - commits already scanned in PR).
# Branch protection ensures all commits are reviewed via PRs.
```

## Validation Criteria

### Functional Requirements
- [ ] TruffleHog runs on all pull requests to main
- [ ] TruffleHog scans all individual commits in PRs
- [ ] TruffleHog does not run on merge commits to main
- [ ] No "BASE and HEAD are the same" errors
- [ ] CI status is clean after merges

### Security Requirements
- [ ] All commits are scanned exactly once (in PR)
- [ ] No security gaps introduced
- [ ] Branch protection prevents unscanned direct pushes
- [ ] Secret detection coverage maintained

### Testing Scenarios
1. **Normal PR flow**:
   - Create PR with new commits
   - ✅ TruffleHog scans during PR review
   - Merge PR
   - ✅ No TruffleHog scan after merge
   - ✅ No errors in Actions

2. **PR with secrets** (test):
   - Create PR with test secret
   - ✅ TruffleHog detects and blocks
   - ✅ PR cannot merge

3. **Multiple commits in PR**:
   - Create PR with 3 commits
   - ✅ TruffleHog scans all 3 commits
   - ✅ No redundant scans

## Edge Cases

### Case 1: Direct Push to Main (Branch Protection Bypassed)
**Scenario**: Admin force-pushes to main
**Current Behavior**: Would be scanned (but causes error on merge)
**New Behavior**: Won't be scanned
**Mitigation**: Branch protection prevents this, admin should know better
**Severity**: Low (requires intentional bypass)

### Case 2: Merge Commit Contains New Changes
**Scenario**: Merge conflict resolution adds new code
**Current Behavior**: Merge commit would be scanned
**New Behavior**: Won't be scanned
**Mitigation**: Conflict resolution happens in PR before merge (gets scanned)
**Severity**: None (impossible - conflicts resolved before merge)

### Case 3: Automated Dependabot PRs
**Scenario**: Dependabot creates PR with dependency updates
**Current Behavior**: Scanned like any PR
**New Behavior**: Scanned like any PR ✅
**Mitigation**: None needed
**Severity**: None (works correctly)

## Success Metrics

### Immediate
- ✅ No TruffleHog failures on merge commits
- ✅ All PR commits still scanned
- ✅ Clean CI status after merges

### Long-term
- ✅ Zero unscanned commits reach main
- ✅ No security gaps introduced
- ✅ Reduced CI runtime (no redundant scans)

## Rollback Plan

If issues arise:

```bash
# Revert workflow change
git checkout HEAD~1 -- .github/workflows/security-scan.yml
git commit -m "revert: restore push-based TruffleHog scanning"
git push
```

Alternative: Use Option 2 (conditional scanning) instead.

## Related Issues

- **Current Error**: "BASE and HEAD commits are the same" in PR #41 merge
- **Root Cause**: Action runs on merge commits (redundant)
- **Security Impact**: None (commits already scanned in PR)
- **User Impact**: Confusing error messages in CI

## References

- **TruffleHog Documentation**: https://github.com/trufflesecurity/trufflehog#octocat-trufflehog-github-action
- **GitHub Actions Events**: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows
- **Branch Protection**: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches

## Conversation Context

**Key Insight**: "The pre-commit hook detected potential secrets, but these are false positives (variable names like `client_secret`, `access_token` in OAuth code)."

**Decision**: Use PR-only scanning instead of trying to fix merge commit handling.

**Concern Raised**: "What if someone bypasses branch protection?"

**Resolution**: Branch protection should prevent this. If admins bypass, they accept the risk. Document the assumption.

## Notes

- This is a **cosmetic fix**, not a security issue
- Original OAuth implementation (PR #41) passed all security checks
- False positives in OAuth code are expected (variable names like "token", "secret")
- TruffleHog correctly scanned individual commits before merge
