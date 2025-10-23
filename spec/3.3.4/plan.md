# Implementation Plan: Phase 3.3.4 - Spec Applier Integration Testing & Validation
Generated: 2025-01-23
Specification: spec/3.3.4/spec.md

## Understanding

This phase validates the end-to-end functionality of the spec-applier Lambda (completed in Phase 3.3.3) through real GitHub API integration tests and comprehensive documentation for Phase 3.4 frontend integration.

**Key Objectives**:
1. Create automated integration test script that exercises real spec-applier API
2. Provide comprehensive manual testing guide for UI validation
3. Document complete API contract for frontend developers
4. Verify PRs are created correctly with destructive change warnings
5. Validate labels, formatting, and error handling

**Prerequisites** (User confirmed):
- Spec-applier Lambda needs deployment before testing
- Integration tests will use trakrf/action-spec repo (configurable)
- Comprehensive documentation style preferred
- Pre-flight deployment checks with optional skip flag

## Relevant Files

**Reference Patterns** (existing code to follow):
- `scripts/test-github-integration.sh` (lines 1-80) - Color-coded output, error handling, AWS/GitHub checks
- `scripts/deploy-backend.sh` (lines 1-80) - Environment variable validation, AWS checks, deployment flow
- `docs/GITHUB_SETUP.md` (lines 1-50) - Documentation structure with clear sections, code examples
- `backend/lambda/functions/spec-applier/handler.py` (lines 1-50) - API endpoint `/spec/apply`, request/response format
- `template.yaml` (lines 1-150) - SAM outputs for API URL and API Key extraction

**Files to Create**:
- `scripts/test-spec-applier-integration.sh` - Automated integration test with 3 test scenarios (safe change, WAF disable, invalid spec)
- `spec/3.3.4/MANUAL_TESTS.md` - Comprehensive manual testing guide with 7 scenarios, troubleshooting, execution log
- `docs/API_SPEC_APPLIER.md` - Complete API documentation with curl examples, TypeScript integration, error codes

**Files to Modify**:
- None (purely additive phase)

## Architecture Impact
- **Subsystems affected**: Testing/Documentation only (no code changes)
- **New dependencies**: None (uses standard tools: bash, curl, jq, aws-cli)
- **Breaking changes**: None

## Task Breakdown

### Task 1: Create Integration Test Script
**File**: `scripts/test-spec-applier-integration.sh`
**Action**: CREATE
**Pattern**: Reference `scripts/test-github-integration.sh` structure (color output, checks, error handling)

**Implementation**:
```bash
#!/usr/bin/env bash
# Integration test for spec-applier Lambda (Phase 3.3.4)
# Pattern: Follow test-github-integration.sh structure

set -euo pipefail

# Color codes (from test-github-integration.sh pattern)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration (similar to deploy-backend.sh)
API_URL="${API_URL:-}"
API_KEY="${API_KEY:-}"
TEST_REPO="${TEST_REPO:-trakrf/action-spec}"
SKIP_PREFLIGHT="${SKIP_PREFLIGHT:-false}"

# Pre-flight checks (deployment verification)
check_deployment() {
  # Verify SAM stack exists
  # Check API Gateway is responsive
  # Validate API key works
}

# Test 1: Safe change (no warnings)
test_safe_change() {
  # POST to /spec/apply with waf.enabled=true
  # Verify PR created
  # Verify warnings=0
}

# Test 2: Destructive change (WAF disable)
test_waf_disable() {
  # POST with waf.enabled=false
  # Verify warning present in response
  # Verify PR description shows warning
}

# Test 3: Invalid spec (validation error)
test_invalid_spec() {
  # POST with malformed YAML
  # Verify 400 error
  # Verify success=false
}
```

**Validation**:
```bash
# Syntax check
bash -n scripts/test-spec-applier-integration.sh

# Shellcheck (if available)
shellcheck scripts/test-spec-applier-integration.sh || true

# Make executable
chmod +x scripts/test-spec-applier-integration.sh
```

**Acceptance Criteria**:
- [ ] Script executable with proper shebang
- [ ] Color-coded output for readability
- [ ] Pre-flight checks validate deployment (can be skipped)
- [ ] 3 test scenarios implemented (safe, destructive, invalid)
- [ ] Uses jq for JSON parsing (with install check)
- [ ] Clear error messages with remediation steps
- [ ] Returns exit code 0 on success, 1 on failure

---

### Task 2: Create Manual Testing Guide
**File**: `spec/3.3.4/MANUAL_TESTS.md`
**Action**: CREATE
**Pattern**: Reference `docs/GITHUB_SETUP.md` structure (clear sections, step-by-step instructions)

**Implementation**:
```markdown
# Manual Integration Tests - Spec Applier (Phase 3.3.4)

## Prerequisites
- [ ] spec-applier Lambda deployed to AWS
- [ ] API Gateway URL obtained from: `sam list stack-outputs`
- [ ] API Key obtained from AWS Console or SAM outputs
- [ ] GitHub PAT configured in SSM Parameter Store
- [ ] ALLOWED_REPOS includes test repository

## Test Scenarios

### Test 1: Safe Change (No Warnings)
**Objective**: Verify PR creation with no destructive changes

**Steps**:
1. Set environment variables:
   ```bash
   export API_URL="https://xxxx.execute-api.us-west-2.amazonaws.com/demo"
   export API_KEY="your-api-key-here"
   ```
2. Submit spec with safe change (compute upgrade):
   ```bash
   curl -X POST "$API_URL/spec/apply" \
     -H "x-api-key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d @test-safe-change.json
   ```
3. Verify response contains `"success": true`
4. Visit PR URL in GitHub UI
5. Check PR description shows "No warnings - changes appear safe ✅"
6. Verify labels: `infrastructure-change`, `automated`

**Expected Results**:
- ✅ HTTP 200 response
- ✅ PR created successfully
- ✅ No warnings in response array
- ✅ PR description clean and formatted
- ✅ Both labels applied

**Troubleshooting**:
- If 403 Forbidden → Check API key is correct
- If 404 Not Found → Verify spec_path exists in repo
- If 502 Bad Gateway → Check Lambda logs in CloudWatch

[... 6 more test scenarios with same structure ...]
```

**Validation**:
No code validation needed (markdown documentation)

**Acceptance Criteria**:
- [ ] All 7 test scenarios documented (from spec.md lines 241-377)
- [ ] Each scenario has clear steps, expected results, troubleshooting
- [ ] Prerequisites section complete
- [ ] Execution log template included
- [ ] Screenshots guidance provided
- [ ] Common errors documented with solutions

---

### Task 3: Create API Documentation
**File**: `docs/API_SPEC_APPLIER.md`
**Action**: CREATE
**Pattern**: Reference `docs/GITHUB_SETUP.md` for documentation style

**Implementation**:
```markdown
# Spec Applier API - Documentation

## Endpoint

**POST** `/spec/apply`

Creates a GitHub pull request with updated ActionSpec configuration and destructive change warnings.

## Authentication

Requires API Key in header:
```
x-api-key: {your-api-key}
```

## Request

### Headers
```
Content-Type: application/json
x-api-key: {api-key}
```

### Body Schema
```json
{
  "repo": "owner/repository",
  "spec_path": "path/to/spec.yml",
  "new_spec_yaml": "apiVersion: actionspec/v1\n...",
  "commit_message": "Optional commit message"
}
```

### Example Request (curl)
```bash
curl -X POST "https://your-api.amazonaws.com/demo/spec/apply" \
  -H "x-api-key: abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "trakrf/action-spec",
    "spec_path": "specs/examples/my-app.yml",
    "new_spec_yaml": "...",
    "commit_message": "Enable WAF protection"
  }'
```

## Response

### Success Response (200 OK)
```json
{
  "success": true,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_number": 123,
  "branch_name": "action-spec-update-1699999999",
  "warnings": [
    {
      "severity": "warning",
      "message": "⚠️ WARNING: Disabling WAF will remove security protection",
      "field_path": "spec.security.waf.enabled"
    }
  ]
}
```

### Error Responses

#### 400 Bad Request - Validation Error
```json
{
  "success": false,
  "error": "Validation failed",
  "details": "Missing required field: metadata.name"
}
```

[... all error codes from spec.md lines 470-532 ...]

## Frontend Integration Guide

### React Example (Phase 3.4)
```typescript
interface SpecApplyRequest {
  repo: string;
  spec_path: string;
  new_spec_yaml: string;
  commit_message?: string;
}

async function applySpec(spec: SpecApplyRequest): Promise<SpecApplyResponse> {
  const response = await fetch(`${API_URL}/spec/apply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
    },
    body: JSON.stringify(spec),
  });
  return response.json();
}
```

[... complete frontend integration examples ...]
```

**Validation**:
No code validation needed (markdown documentation)

**Acceptance Criteria**:
- [ ] Complete API endpoint documentation
- [ ] Request/response schemas with examples
- [ ] All error codes documented (400, 404, 409, 502, 500)
- [ ] curl examples for each scenario
- [ ] TypeScript integration code provided
- [ ] Rate limiting information included
- [ ] Security notes (whitelist, API key)

---

### Task 4: Deploy Lambda to AWS
**File**: N/A (uses existing `scripts/deploy-backend.sh`)
**Action**: EXECUTE DEPLOYMENT
**Pattern**: Reference `scripts/deploy-backend.sh` deployment flow

**Implementation**:
```bash
# Step 1: Verify GitHub PAT is in SSM
aws ssm get-parameter \
  --name /actionspec/github-token \
  --with-decryption \
  --region us-west-2

# Step 2: Set environment variables
export AWS_REGION=us-west-2
export ENVIRONMENT=demo
export GITHUB_TOKEN_SSM_PARAM=/actionspec/github-token

# Step 3: Deploy using existing script
cd /home/mike/action-spec
./scripts/deploy-backend.sh

# Step 4: Capture outputs
sam list stack-outputs --stack-name actionspec-backend

# Step 5: Extract API URL and API Key
API_URL=$(sam list stack-outputs --stack-name actionspec-backend \
  --output json | jq -r '.[] | select(.OutputKey=="ApiUrl") | .OutputValue')

API_KEY=$(aws apigateway get-api-keys \
  --query 'items[?name==`actionspec-backend-api-key`].id' \
  --output text)
```

**Validation**:
```bash
# Verify stack deployed
aws cloudformation describe-stacks \
  --stack-name actionspec-backend \
  --query 'Stacks[0].StackStatus'

# Should return: CREATE_COMPLETE or UPDATE_COMPLETE
```

**Acceptance Criteria**:
- [ ] SAM build completes without errors
- [ ] SAM deploy succeeds (stack CREATE_COMPLETE)
- [ ] API Gateway URL obtained from outputs
- [ ] API Key retrieved from AWS
- [ ] All 4 Lambda functions deployed
- [ ] spec-applier endpoint responds (smoke test)

---

### Task 5: Run Integration Tests
**File**: N/A (executes `scripts/test-spec-applier-integration.sh`)
**Action**: EXECUTE TESTS
**Pattern**: Follow test execution workflow

**Implementation**:
```bash
# Step 1: Set environment variables (from Task 4)
export API_URL="https://xxxx.execute-api.us-west-2.amazonaws.com/demo"
export API_KEY="your-api-key-from-task4"
export TEST_REPO="trakrf/action-spec"

# Step 2: Run integration tests
./scripts/test-spec-applier-integration.sh

# Expected output:
# ========================================
# Spec Applier Integration Test
# ========================================
#
# ✓ API_URL: https://...
# ✓ API_KEY: abc123...
#
# Test 1: Safe change (no warnings)
# ----------------------------------------
# ✓ PR created: https://github.com/trakrf/action-spec/pull/XX
# ✓ Warnings: 0 (expected: 0)
#
# Test 2: Destructive change (WAF disable)
# ----------------------------------------
# ✓ PR created: https://github.com/trakrf/action-spec/pull/YY
# ✓ Warnings: 1 (WAF warning detected)
#
# Test 3: Invalid spec (validation error)
# ----------------------------------------
# ✓ Validation error detected: Missing required field...
#
# ========================================
# ✅ All integration tests passed!
# ========================================
```

**Validation**:
```bash
# Verify 3 PRs created in GitHub
gh pr list --repo trakrf/action-spec --label automated

# Check test exit code
echo $?  # Should be 0
```

**Acceptance Criteria**:
- [ ] All 3 automated tests pass
- [ ] 3 PRs created in GitHub (1 safe, 1 WAF warning, 1 invalid rejected)
- [ ] Warnings appear correctly in PR descriptions
- [ ] Labels applied correctly (infrastructure-change, automated)
- [ ] Script exits with code 0
- [ ] No unexpected errors in output

---

### Task 6: Execute Manual Tests & Document Results
**File**: `spec/3.3.4/MANUAL_TESTS.md` (update execution log)
**Action**: MODIFY
**Pattern**: Follow manual test checklist

**Implementation**:
Execute each of the 7 manual test scenarios from MANUAL_TESTS.md:

1. Safe Change (compute upgrade)
2. WAF Disable (WARNING severity)
3. Database Engine Change (CRITICAL severity)
4. Multiple Warnings (WAF + compute downsize)
5. Invalid Spec (validation error)
6. Spec File Not Found (404 error)
7. Branch Name Uniqueness (collision handling)

For each test:
- Follow documented steps
- Verify expected results
- Check GitHub UI presentation
- Document any issues found
- Mark pass/fail in execution log

**Validation**:
Visual inspection of GitHub PRs for:
- Proper emoji rendering (⚠️, 🔴, ℹ️)
- Formatted PR descriptions
- Correct labels applied
- Review checklist present

**Acceptance Criteria**:
- [ ] All 7 manual tests executed
- [ ] Execution log filled out with results
- [ ] Screenshots captured (optional but recommended)
- [ ] Any issues documented
- [ ] Overall result: PASS (all tests passing)

---

### Task 7: Clean Up Test PRs
**File**: N/A (GitHub cleanup)
**Action**: EXECUTE CLEANUP
**Pattern**: Use gh CLI for bulk operations

**Implementation**:
```bash
# List all automated PRs created during testing
gh pr list --repo trakrf/action-spec --label automated

# Close each PR with branch deletion
# Get PR numbers
PR_NUMBERS=$(gh pr list --repo trakrf/action-spec \
  --label automated \
  --json number \
  --jq '.[].number')

# Close all test PRs
for pr in $PR_NUMBERS; do
  echo "Closing PR #$pr..."
  gh pr close "$pr" --repo trakrf/action-spec --delete-branch
done

# Verify cleanup
gh pr list --repo trakrf/action-spec --label automated
# Should return empty list
```

**Validation**:
```bash
# Verify no automated PRs remain open
gh pr list --repo trakrf/action-spec --label automated --state open
# Should be empty
```

**Acceptance Criteria**:
- [ ] All test PRs closed
- [ ] All test branches deleted
- [ ] No open PRs with 'automated' label
- [ ] Cleanup documented in MANUAL_TESTS.md

---

## Risk Assessment

- **Risk**: Lambda deployment fails due to missing dependencies
  **Mitigation**: Use existing deploy-backend.sh script (proven in Phase 3.1-3.3). Verify all dependencies in requirements.txt.

- **Risk**: Integration tests create too many PRs and spam repository
  **Mitigation**: Make TEST_REPO configurable. Document cleanup procedure. Consider using separate test repo for future.

- **Risk**: jq not installed on testing machine
  **Mitigation**: Add jq check to integration script with helpful install instructions (apt-get install jq / brew install jq).

- **Risk**: API endpoint changes between deployment and testing
  **Mitigation**: Extract API_URL dynamically from SAM outputs. Don't hardcode URLs.

- **Risk**: Manual tests are too time-consuming
  **Mitigation**: Prioritize automated tests (Tasks 1-5). Manual tests validate UI only (emojis, formatting).

## Integration Points

- **SAM Deployment**: Uses existing deploy-backend.sh script (no changes needed)
- **GitHub API**: Uses existing github_client.py functions (no changes needed)
- **Spec Parser**: Uses existing spec-applier handler (no changes needed)
- **Documentation**: New API docs enable Phase 3.4 frontend development

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

### For Scripts (Task 1):
```bash
# Gate 1: Bash syntax check
bash -n scripts/test-spec-applier-integration.sh

# Gate 2: Shellcheck (if available)
shellcheck scripts/test-spec-applier-integration.sh || echo "⚠️ shellcheck not available"

# Gate 3: Make executable
chmod +x scripts/test-spec-applier-integration.sh
test -x scripts/test-spec-applier-integration.sh
```

### For Documentation (Tasks 2-3):
```bash
# Gate 1: Markdown syntax check (using markdownlint if available)
markdownlint spec/3.3.4/MANUAL_TESTS.md docs/API_SPEC_APPLIER.md || echo "⚠️ markdownlint not available"

# Gate 2: Link validation (manual - verify all links are valid)
# Check: GitHub URLs, internal file references, API endpoints
```

### For Integration Tests (Tasks 4-6):
```bash
# Gate 1: Deployment successful
aws cloudformation describe-stacks \
  --stack-name actionspec-backend \
  --query 'Stacks[0].StackStatus' | grep -q "COMPLETE"

# Gate 2: All automated tests pass
./scripts/test-spec-applier-integration.sh
# Exit code must be 0

# Gate 3: Manual tests complete
# Verify execution log in MANUAL_TESTS.md shows all tests passing
```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Do not proceed to next task until current task passes all gates

## Validation Sequence

**After Task 1 (Integration Script)**:
```bash
bash -n scripts/test-spec-applier-integration.sh
shellcheck scripts/test-spec-applier-integration.sh || true
chmod +x scripts/test-spec-applier-integration.sh
```

**After Task 2 (Manual Tests Guide)**:
```bash
# Visual review of MANUAL_TESTS.md
# - All 7 scenarios documented
# - Prerequisites clear
# - Execution log template present
```

**After Task 3 (API Documentation)**:
```bash
# Visual review of API_SPEC_APPLIER.md
# - All endpoints documented
# - Example code syntax-checked (copy to temp file, run through interpreter)
# - All error codes covered
```

**After Task 4 (Deployment)**:
```bash
sam list stack-outputs --stack-name actionspec-backend
# Verify outputs present: ApiUrl, ApiKey
```

**After Task 5 (Integration Tests)**:
```bash
./scripts/test-spec-applier-integration.sh
# Exit code 0 = success

gh pr list --repo trakrf/action-spec --label automated
# Verify PRs created
```

**After Task 6 (Manual Tests)**:
```bash
# Review execution log in MANUAL_TESTS.md
# All tests marked PASS
```

**After Task 7 (Cleanup)**:
```bash
gh pr list --repo trakrf/action-spec --label automated --state open
# Should be empty
```

**Final Validation**:
```bash
# 1. All scripts executable
ls -la scripts/test-spec-applier-integration.sh | grep -q "x"

# 2. All documentation files exist
test -f spec/3.3.4/MANUAL_TESTS.md
test -f docs/API_SPEC_APPLIER.md

# 3. No open test PRs
gh pr list --repo trakrf/action-spec --label automated --state open | wc -l | grep -q "0"
```

## Plan Quality Assessment

**Complexity Score**: 2/10 (LOW - WELL-SCOPED)

**Complexity Factors**:
- 📁 File Impact: Creating 3 files, modifying 0 files (3 files total)
- 🔗 Subsystems: Touching 1 subsystem (testing/documentation)
- 🔢 Task Estimate: 7 subtasks (well below 13 task threshold)
- 📦 Dependencies: 0 new packages (bash, curl, jq, aws-cli, gh are standard)
- 🆕 Pattern Novelty: Existing patterns (follows test-github-integration.sh, deploy-backend.sh)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec.md (all 3 deliverables specified)
- ✅ Similar patterns found in codebase (test-github-integration.sh, deploy-backend.sh)
- ✅ All clarifying questions answered (deployment status, test repo, documentation level, pre-flight checks)
- ✅ Existing deployment infrastructure working (Phase 3.1-3.3.3 complete)
- ✅ No new code changes (purely testing/documentation)
- ✅ Low risk (no breaking changes possible)
- ⚠️ Dependency on external service (GitHub API) - minor risk of rate limiting

**Assessment**: High confidence in successful implementation. This is primarily testing and documentation work following established patterns. The only external dependency is GitHub API, which has proven stable in Phase 3.3.1-3.3.3.

**Estimated one-pass success probability**: 90%

**Reasoning**:
- Testing/documentation phases have fewer failure modes than code implementation
- All patterns exist and are proven (test-github-integration.sh works)
- User confirmed deployment needed first (no surprise blockers)
- GitHub API integration already validated in Phase 3.3.1-3.3.3
- Only risk is GitHub rate limiting (mitigated by exponential backoff in github_client.py)
- Manual testing is inherently self-validating (human in loop catches issues)
