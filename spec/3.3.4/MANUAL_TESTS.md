# Manual Integration Tests - Spec Applier (Phase 3.3.4)

## Overview
This document provides comprehensive manual testing procedures for validating the spec-applier Lambda's PR creation functionality, including UI presentation, warning display, and error handling.

## Prerequisites

Before running manual tests, ensure:

- [ ] **spec-applier Lambda deployed to AWS**
  - Verify with: `aws cloudformation describe-stacks --stack-name actionspec-backend --query 'Stacks[0].StackStatus'`
  - Expected: `CREATE_COMPLETE` or `UPDATE_COMPLETE`

- [ ] **API Gateway URL obtained**
  - Retrieve with: `sam list stack-outputs --stack-name actionspec-backend --output json | jq -r '.[] | select(.OutputKey=="ApiUrl") | .OutputValue'`
  - Export: `export API_URL="https://xxxxx.execute-api.us-west-2.amazonaws.com/demo"`

- [ ] **API Key obtained**
  - Retrieve with: `aws apigateway get-api-keys --query 'items[?name==\`actionspec-backend-api-key\`].value' --output text`
  - Export: `export API_KEY="your-api-key-here"`

- [ ] **GitHub PAT configured in SSM Parameter Store**
  - Verify with: `aws ssm get-parameter --name /actionspec/github-token --with-decryption --region us-west-2`

- [ ] **ALLOWED_REPOS includes test repository**
  - Check SAM template.yaml for ALLOWED_REPOS environment variable
  - Default: `trakrf/action-spec`

## Test Environment Setup

```bash
# Set environment variables
export API_URL="https://xxxxx.execute-api.us-west-2.amazonaws.com/demo"
export API_KEY="your-api-key-here"
export TEST_REPO="trakrf/action-spec"

# Verify jq is installed (required for JSON parsing)
command -v jq || echo "Install jq: sudo apt-get install jq"

# Verify gh CLI is installed (for PR verification)
command -v gh || echo "Install gh: https://cli.github.com/"
```

---

## Test Scenarios

### Test 1: Safe Change (No Warnings)

**Objective**: Verify PR creation with no destructive changes

**Spec Content** (save as `test-safe-change.json`):
```json
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/manual-test-1.yml",
  "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: test-safe-change\n  description: Manual test - safe change\nspec:\n  type: StaticSite\n  compute:\n    size: demo\n  security:\n    waf:\n      enabled: true\n",
  "commit_message": "Manual test: safe change (compute upgrade)"
}
```

**Steps**:
1. Submit request:
   ```bash
   curl -X POST "$API_URL/spec/apply" \
     -H "x-api-key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d @test-safe-change.json | jq '.'
   ```

2. Record response:
   - `success`: ___________
   - `pr_url`: ___________
   - `warnings` count: ___________

3. Visit PR URL in GitHub UI

4. Verify PR presentation:
   - [ ] Title includes "Update ActionSpec configuration"
   - [ ] Description shows "No warnings - changes appear safe ✅"
   - [ ] Labels applied: `infrastructure-change`, `automated`
   - [ ] Branch name format: `action-spec-update-{timestamp}`

**Expected Results**:
- ✅ HTTP 200 response
- ✅ `success: true`
- ✅ No warnings in response array (`warnings: []`)
- ✅ PR created with clean description
- ✅ Both labels visible in GitHub UI

**Troubleshooting**:
| Error | Cause | Solution |
|-------|-------|----------|
| 403 Forbidden | Invalid API key | Verify API_KEY is correct |
| 404 Not Found | spec_path doesn't exist | Create directory path in repo first |
| 502 Bad Gateway | Lambda error | Check CloudWatch logs: `aws logs tail /aws/lambda/actionspec-spec-applier --follow` |

---

### Test 2: WAF Disable (WARNING Severity)

**Objective**: Verify warning appears in PR description with correct severity

**Spec Content** (save as `test-waf-disable.json`):
```json
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/manual-test-2.yml",
  "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: test-waf-disable\n  description: Manual test - WAF disable\nspec:\n  type: StaticSite\n  compute:\n    size: demo\n  security:\n    waf:\n      enabled: false\n",
  "commit_message": "Manual test: disable WAF"
}
```

**Steps**:
1. Submit request:
   ```bash
   curl -X POST "$API_URL/spec/apply" \
     -H "x-api-key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d @test-waf-disable.json | jq '.'
   ```

2. Record response warnings:
   ```bash
   # Extract warnings
   curl -X POST "$API_URL/spec/apply" \
     -H "x-api-key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d @test-waf-disable.json | jq '.warnings'
   ```

3. Visit PR in GitHub

4. Verify warning display:
   - [ ] Warning emoji (⚠️) appears in PR description
   - [ ] Severity shows "WARNING"
   - [ ] Message: "Disabling WAF will remove security protection"
   - [ ] Field path: `spec.security.waf.enabled`

**Expected Results**:
- ✅ HTTP 200 response
- ✅ `warnings` array contains 1 item
- ✅ Warning object includes:
  ```json
  {
    "severity": "warning",
    "message": "⚠️ WARNING: Disabling WAF will remove security protection",
    "field_path": "spec.security.waf.enabled"
  }
  ```
- ✅ PR description displays warning with emoji

**Notes**:
- Emoji rendering may vary by browser
- GitHub UI should show ⚠️ correctly
- Screenshot recommended for documentation

---

### Test 3: Database Engine Change (CRITICAL Severity)

**Objective**: Verify critical warnings are visually distinct from warnings

**Spec Content** (save as `test-engine-change.json`):
```json
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/manual-test-3.yml",
  "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: test-engine-change\n  description: Manual test - database engine change\nspec:\n  type: WebService\n  data:\n    engine: mysql\n    version: '8.0'\n",
  "commit_message": "Manual test: change database engine"
}
```

**Steps**:
1. Submit request
2. Record critical warning details
3. Visit PR in GitHub
4. Verify critical severity presentation:
   - [ ] Red emoji (🔴) appears
   - [ ] Severity shows "CRITICAL"
   - [ ] Message explains data migration requirement
   - [ ] Visually distinct from standard warnings

**Expected Results**:
- ✅ `severity: "critical"` in response
- ✅ PR description shows 🔴 CRITICAL
- ✅ Clear distinction from WARNING severity

---

### Test 4: Multiple Warnings

**Objective**: Verify multiple warnings appear correctly in PR description

**Spec Content** (save as `test-multiple-warnings.json`):
```json
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/manual-test-4.yml",
  "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: test-multiple-warnings\n  description: Manual test - multiple warnings\nspec:\n  type: StaticSite\n  compute:\n    size: nano\n  security:\n    waf:\n      enabled: false\n",
  "commit_message": "Manual test: multiple destructive changes"
}
```

**Steps**:
1. Submit spec with multiple destructive changes:
   - WAF disable (warning)
   - Compute downsize (warning)
2. Verify both warnings in response
3. Check PR description shows all warnings

**Expected Results**:
- ✅ `warnings` array contains 2+ items
- ✅ Each warning on separate line in PR description
- ✅ All warnings visible and formatted correctly

---

### Test 5: Invalid Spec (Validation Error)

**Objective**: Verify validation errors prevent PR creation

**Spec Content** (save as `test-invalid-spec.json`):
```json
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/manual-test-5.yml",
  "new_spec_yaml": "invalid: yaml\nwithout: required fields\nno metadata or spec",
  "commit_message": "Manual test: invalid spec"
}
```

**Steps**:
1. Submit invalid spec
2. Verify error response
3. Confirm NO PR created

**Expected Results**:
- ❌ HTTP 400 Bad Request
- ❌ `success: false`
- ❌ Error message indicates validation failure
- ❌ No PR created in GitHub
- ✅ Error details explain what's missing

**Example Error**:
```json
{
  "success": false,
  "error": "Validation failed",
  "details": "Missing required field: metadata.name"
}
```

---

### Test 6: Spec File Not Found (404 Error)

**Objective**: Verify proper error handling when spec_path doesn't exist

**Spec Content** (save as `test-file-not-found.json`):
```json
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/nonexistent/missing.yml",
  "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: test\nspec:\n  type: StaticSite",
  "commit_message": "Manual test: file not found"
}
```

**Steps**:
1. Submit with nonexistent spec_path
2. Verify 404 error

**Expected Results**:
- ❌ HTTP 404 Not Found
- ❌ `success: false`
- ✅ Error message mentions file path: "File 'specs/nonexistent/missing.yml' not found"

---

### Test 7: Branch Name Uniqueness

**Objective**: Verify collision avoidance for branch names

**Steps**:
1. Create first PR (any test above)
2. Immediately submit same spec again (< 1 second)
3. Verify both PRs created successfully
4. Check branch names are different

**Expected Results**:
- ✅ Two separate PRs created
- ✅ First branch: `action-spec-update-{timestamp}`
- ✅ Second branch: `action-spec-update-{timestamp}-{random}` or different timestamp
- ✅ Both PRs successful with no errors

---

## Test Execution Log

**Date**: __________
**Tester**: __________
**Environment**: __________
**API URL**: __________

| Test | Pass | Fail | PR URL | Notes |
|------|------|------|--------|-------|
| 1. Safe Change | ☐ | ☐ | | |
| 2. WAF Disable | ☐ | ☐ | | |
| 3. Engine Change | ☐ | ☐ | | |
| 4. Multiple Warnings | ☐ | ☐ | | |
| 5. Invalid Spec | ☐ | ☐ | N/A | Should NOT create PR |
| 6. File Not Found | ☐ | ☐ | N/A | Should NOT create PR |
| 7. Branch Uniqueness | ☐ | ☐ | | |

**Overall Result**: ☐ Pass ☐ Fail

**Issues Found**:
```
_____________________
_____________________
_____________________
```

**Screenshots Captured**:
- [ ] Safe change PR (no warnings)
- [ ] WARNING severity PR
- [ ] CRITICAL severity PR
- [ ] Multiple warnings PR
- [ ] Validation error response
- [ ] GitHub labels screenshot

---

## Cleanup After Testing

After completing all manual tests, clean up test PRs:

### Option A: Close PRs Individually
```bash
# List all automated PRs
gh pr list --repo $TEST_REPO --label automated

# Close specific PR
gh pr close {pr-number} --repo $TEST_REPO --delete-branch
```

### Option B: Bulk Close All Automated PRs
```bash
# Close all automated PRs in one command
gh pr list --repo $TEST_REPO --label automated --json number --jq '.[].number' | \
  xargs -I {} gh pr close {} --repo $TEST_REPO --delete-branch
```

### Verify Cleanup
```bash
# Should return empty list
gh pr list --repo $TEST_REPO --label automated --state open
```

---

## Common Issues & Solutions

### Issue: API returns 403 Forbidden
**Cause**: Invalid API key
**Solution**:
```bash
# Verify API key
aws apigateway get-api-keys --query 'items[?name==`actionspec-backend-api-key`]'

# Get correct value
aws apigateway get-api-key --api-key {key-id} --include-value
```

### Issue: PR not created (502 error)
**Cause**: Lambda execution error
**Solution**:
```bash
# Check Lambda logs
aws logs tail /aws/lambda/actionspec-spec-applier --follow --region us-west-2

# Check recent errors
aws logs filter-pattern /aws/lambda/actionspec-spec-applier --pattern "ERROR" --region us-west-2
```

### Issue: Warnings not appearing in PR description
**Cause**: PR description generation logic error
**Solution**:
1. Check Lambda logs for PR creation step
2. Verify warning detection in response JSON
3. Manually inspect PR body in GitHub API

### Issue: Labels not applied
**Cause**: GitHub token lacks repo permissions
**Solution**:
1. Verify PAT has `repo` scope
2. Check token is not expired
3. Regenerate token if needed (see docs/GITHUB_SETUP.md)

---

## Additional Validation

### Verify API Health
```bash
# Test API endpoint is responsive
curl -X GET "$API_URL/health" -H "x-api-key: $API_KEY" -v
```

### Verify Lambda Permissions
```bash
# Check Lambda has SSM parameter access
aws lambda get-function-configuration \
  --function-name actionspec-spec-applier \
  --query 'Role'
```

### Verify GitHub Token Validity
```bash
# Test token directly with GitHub API
TOKEN=$(aws ssm get-parameter --name /actionspec/github-token --with-decryption --query 'Parameter.Value' --output text)
curl -H "Authorization: token $TOKEN" https://api.github.com/user
```

---

## Documentation

After completing manual tests, document:

1. **Test Results**: Fill out execution log above
2. **Screenshots**: Capture key PRs showing:
   - Warning display
   - Critical warnings
   - Labels applied
   - Clean PR formatting
3. **Issues Found**: Document any bugs or unexpected behavior
4. **Recommendations**: Note any improvements for future iterations
