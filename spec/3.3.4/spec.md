# Phase 3.3.4: Spec Applier Integration Testing & Validation

## Origin
This specification is Part 3 of the Spec Applier & PR Creation feature (split from original 3.3.2). This phase validates the end-to-end flow with real GitHub PRs and documents the integration for frontend consumption.

## Outcome
The spec-applier Lambda is validated with real GitHub PR creation, destructive change warnings appear correctly, and the API is documented for Phase 3.4 frontend integration.

**What will change:**
- Create integration test script that calls real spec-applier API
- Manually test PR creation with real GitHub repository
- Verify warnings appear in PR descriptions
- Verify labels are applied correctly
- Document API contract for frontend
- Create example request/response payloads

## User Story
As a **developer validating the PR creation feature**
I want **end-to-end tests with real GitHub API calls**
So that **I can verify PRs are created correctly with warnings**

## Context

**Discovery**: Phases 3.3.2 and 3.3.3 provide GitHub write operations and Lambda handler. Now we need to validate it works end-to-end with real GitHub API.

**Current State**:
- spec-applier handler implemented (Phase 3.3.3)
- Unit tests pass for all components
- No integration tests with real GitHub
- No manual validation with real PRs
- API contract not documented

**Desired State**:
- Integration test script exercises real API
- At least 3 test PRs created successfully
- Warnings verified in PR descriptions
- Labels verified in GitHub UI
- API documented for frontend team

**Why This Matters**:
- **Confidence**: Unit tests mock GitHub - need real API validation
- **Bug Detection**: Integration issues only found with real PRs
- **Frontend Ready**: Documentation enables Phase 3.4 development
- **User Safety**: Verify warnings display correctly in GitHub UI

## Technical Requirements

### 1. Integration Test Script

Create `scripts/test-spec-applier-integration.sh`:

```bash
#!/bin/bash
# Integration test for spec-applier Lambda (Phase 3.3.4)
# Tests real GitHub PR creation with warnings

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Spec Applier Integration Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
if [ -z "$API_URL" ]; then
    echo -e "${RED}❌ Error: API_URL environment variable not set${NC}"
    echo "   Set it to your deployed API Gateway URL"
    echo "   Example: export API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Prod"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ Error: API_KEY environment variable not set${NC}"
    echo "   Get API key from AWS Console or SAM outputs"
    exit 1
fi

echo -e "${GREEN}✓${NC} API_URL: $API_URL"
echo -e "${GREEN}✓${NC} API_KEY: ${API_KEY:0:8}..."
echo ""

# Test 1: Safe change (no warnings)
echo -e "${YELLOW}Test 1: Safe change (no warnings)${NC}"
echo "----------------------------------------"

SAFE_SPEC=$(cat <<'EOF'
apiVersion: actionspec/v1
metadata:
  name: test-safe-change
  description: Integration test - safe change
spec:
  type: StaticSite
  compute:
    size: demo
  security:
    waf:
      enabled: true
EOF
)

RESPONSE=$(curl -s -X POST "$API_URL/spec/apply" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/integration-test.yml",
  "new_spec_yaml": "$SAFE_SPEC",
  "commit_message": "Integration test: safe change"
}
EOF
)

if echo "$RESPONSE" | jq -e '.success == true' > /dev/null; then
    PR_URL=$(echo "$RESPONSE" | jq -r '.pr_url')
    WARNING_COUNT=$(echo "$RESPONSE" | jq '.warnings | length')
    echo -e "${GREEN}✓${NC} PR created: $PR_URL"
    echo -e "${GREEN}✓${NC} Warnings: $WARNING_COUNT (expected: 0)"
else
    echo -e "${RED}❌ Test failed${NC}"
    echo "$RESPONSE" | jq '.'
    exit 1
fi
echo ""

# Test 2: Destructive change (WAF disabling)
echo -e "${YELLOW}Test 2: Destructive change (WAF disable)${NC}"
echo "----------------------------------------"

DESTRUCTIVE_SPEC=$(cat <<'EOF'
apiVersion: actionspec/v1
metadata:
  name: test-destructive-change
  description: Integration test - WAF disable
spec:
  type: StaticSite
  compute:
    size: demo
  security:
    waf:
      enabled: false  # ⚠️ This should trigger warning
EOF
)

RESPONSE=$(curl -s -X POST "$API_URL/spec/apply" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/integration-test.yml",
  "new_spec_yaml": "$DESTRUCTIVE_SPEC",
  "commit_message": "Integration test: disable WAF"
}
EOF
)

if echo "$RESPONSE" | jq -e '.success == true' > /dev/null; then
    PR_URL=$(echo "$RESPONSE" | jq -r '.pr_url')
    WARNING_COUNT=$(echo "$RESPONSE" | jq '.warnings | length')
    HAS_WAF_WARNING=$(echo "$RESPONSE" | jq '.warnings[] | select(.field_path == "spec.security.waf.enabled")')

    echo -e "${GREEN}✓${NC} PR created: $PR_URL"

    if [ "$WARNING_COUNT" -gt 0 ] && [ -n "$HAS_WAF_WARNING" ]; then
        echo -e "${GREEN}✓${NC} Warnings: $WARNING_COUNT (WAF warning detected)"
    else
        echo -e "${RED}❌ Expected WAF warning not found${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Test failed${NC}"
    echo "$RESPONSE" | jq '.'
    exit 1
fi
echo ""

# Test 3: Invalid spec (validation error)
echo -e "${YELLOW}Test 3: Invalid spec (validation error)${NC}"
echo "----------------------------------------"

INVALID_SPEC="invalid: yaml without required fields"

RESPONSE=$(curl -s -X POST "$API_URL/spec/apply" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "repo": "trakrf/action-spec",
  "spec_path": "specs/examples/integration-test.yml",
  "new_spec_yaml": "$INVALID_SPEC",
  "commit_message": "Integration test: invalid spec"
}
EOF
)

if echo "$RESPONSE" | jq -e '.success == false' > /dev/null; then
    ERROR=$(echo "$RESPONSE" | jq -r '.error')
    echo -e "${GREEN}✓${NC} Validation error detected: $ERROR"
else
    echo -e "${RED}❌ Expected validation error not returned${NC}"
    exit 1
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ All integration tests passed!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Manual verification steps:"
echo "1. Visit the PRs created above"
echo "2. Verify PR descriptions show warnings correctly"
echo "3. Verify labels 'infrastructure-change' and 'automated' are applied"
echo "4. Close PRs after verification"
```

### 2. Manual Test Checklist

Create `spec/3.3.4/MANUAL_TESTS.md`:

```markdown
# Manual Integration Tests - Spec Applier (Phase 3.3.4)

## Prerequisites
- [ ] spec-applier Lambda deployed to AWS
- [ ] API Gateway URL obtained
- [ ] API Key obtained
- [ ] GitHub PAT configured in SSM Parameter Store
- [ ] ALLOWED_REPOS includes test repository

## Test Scenarios

### Test 1: Safe Change (No Warnings)

**Spec**: Increase compute size from demo → small

**Expected Behavior**:
- ✅ PR created successfully
- ✅ PR description shows "No warnings - changes appear safe ✅"
- ✅ Labels applied: infrastructure-change, automated
- ✅ Branch name: action-spec-update-{timestamp}

**Verification**:
- [ ] PR URL returned in response
- [ ] Response contains zero warnings
- [ ] GitHub UI shows PR with correct title/body
- [ ] Labels visible in GitHub UI

---

### Test 2: WAF Disable (WARNING Severity)

**Spec**: Change waf.enabled from true → false

**Expected Behavior**:
- ✅ PR created successfully
- ✅ PR description shows: "⚠️ WARNING: Disabling WAF will remove security protection"
- ✅ Response includes warning object with severity="warning"
- ✅ Labels applied

**Verification**:
- [ ] Warning appears in PR description
- [ ] Warning emoji (⚠️) visible
- [ ] Warning includes field_path: spec.security.waf.enabled
- [ ] Response JSON contains warnings array

---

### Test 3: Database Engine Change (CRITICAL Severity)

**Spec**: Change data.engine from "postgresql" → "mysql"

**Expected Behavior**:
- ✅ PR created successfully
- ✅ PR description shows: "🔴 CRITICAL: Changing database engine requires data migration"
- ✅ Response includes warning with severity="critical"

**Verification**:
- [ ] Critical warning appears with red emoji (🔴)
- [ ] Severity is "CRITICAL" in PR description
- [ ] Response JSON reflects critical severity

---

### Test 4: Multiple Warnings

**Spec**: Multiple destructive changes (WAF disable + compute downsize)

**Expected Behavior**:
- ✅ PR created successfully
- ✅ PR description shows multiple warnings
- ✅ Response contains 2+ warnings

**Verification**:
- [ ] All warnings appear in PR description
- [ ] Each warning on separate line
- [ ] Response contains multiple warning objects

---

### Test 5: Invalid Spec (Validation Error)

**Spec**: Malformed YAML or missing required fields

**Expected Behavior**:
- ❌ PR NOT created
- ❌ 400 Bad Request response
- ❌ Error message indicates validation failure

**Verification**:
- [ ] Response success=false
- [ ] Status code is 400
- [ ] Error details explain validation issue
- [ ] No PR created in GitHub

---

### Test 6: Spec File Not Found (404 Error)

**Spec**: Valid YAML but spec_path doesn't exist in repo

**Expected Behavior**:
- ❌ PR NOT created
- ❌ 404 Not Found response
- ❌ Error indicates file not found

**Verification**:
- [ ] Response success=false
- [ ] Status code is 404
- [ ] Error message mentions file path
- [ ] No PR created

---

### Test 7: Branch Name Uniqueness

**Spec**: Submit same spec twice rapidly

**Expected Behavior**:
- ✅ First PR created with timestamp branch name
- ✅ Second PR created with timestamp-{random} branch name (collision avoidance)

**Verification**:
- [ ] Two separate PRs created
- [ ] Different branch names
- [ ] Both PRs successful

---

## Test Execution Log

Date: __________
Tester: __________

| Test | Pass | Fail | Notes |
|------|------|------|-------|
| 1. Safe Change | ☐ | ☐ | |
| 2. WAF Disable | ☐ | ☐ | |
| 3. Engine Change | ☐ | ☐ | |
| 4. Multiple Warnings | ☐ | ☐ | |
| 5. Invalid Spec | ☐ | ☐ | |
| 6. File Not Found | ☐ | ☐ | |
| 7. Branch Uniqueness | ☐ | ☐ | |

**Overall Result**: ☐ Pass ☐ Fail

**Issues Found**:
_____________________
_____________________
```

### 3. API Documentation

Create `docs/API_SPEC_APPLIER.md`:

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

**Fields**:
- `repo` (required): Repository in format "owner/name" (must be in ALLOWED_REPOS whitelist)
- `spec_path` (required): Path to spec file in repository
- `new_spec_yaml` (required): New spec content as YAML string
- `commit_message` (optional): Commit message (default: "Update ActionSpec configuration")

### Example Request
```bash
curl -X POST "https://your-api.amazonaws.com/Prod/spec/apply" \
  -H "x-api-key: abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "trakrf/action-spec",
    "spec_path": "specs/examples/my-app.yml",
    "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: my-app\nspec:\n  type: StaticSite\n  ...",
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

**Fields**:
- `success`: Always `true` for successful responses
- `pr_url`: GitHub UI URL for the created pull request
- `pr_number`: PR number (integer)
- `branch_name`: Name of created branch
- `warnings`: Array of destructive change warnings (may be empty)

**Warning Object**:
- `severity`: One of "info", "warning", "critical"
- `message`: Human-readable warning with emoji
- `field_path`: JSON path to changed field (e.g., "spec.security.waf.enabled")

### Error Responses

#### 400 Bad Request - Validation Error
```json
{
  "success": false,
  "error": "Validation failed",
  "details": "Missing required field: metadata.name"
}
```

**Cause**: Invalid YAML or spec doesn't match schema

---

#### 404 Not Found - Spec File Missing
```json
{
  "success": false,
  "error": "Spec file not found",
  "details": "File 'specs/missing.yml' not found in trakrf/action-spec"
}
```

**Cause**: spec_path doesn't exist in repository

---

#### 409 Conflict - PR Already Exists
```json
{
  "success": false,
  "error": "Pull request already exists",
  "details": "A PR already exists for branch 'action-spec-update-123'"
}
```

**Cause**: Rare collision - PR already created for generated branch name

---

#### 502 Bad Gateway - GitHub API Error
```json
{
  "success": false,
  "error": "GitHub API error",
  "details": "Rate limit exceeded"
}
```

**Cause**: GitHub API failure (rate limit, permissions, network)

---

#### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Internal server error",
  "details": "Unexpected error message"
}
```

**Cause**: Unexpected Lambda error

## Frontend Integration Guide

### React Example (Phase 3.4)

```typescript
interface SpecApplyRequest {
  repo: string;
  spec_path: string;
  new_spec_yaml: string;
  commit_message?: string;
}

interface SpecApplyResponse {
  success: boolean;
  pr_url?: string;
  pr_number?: number;
  branch_name?: string;
  warnings?: Array<{
    severity: 'info' | 'warning' | 'critical';
    message: string;
    field_path: string;
  }>;
  error?: string;
  details?: string;
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

// Usage
const result = await applySpec({
  repo: 'trakrf/action-spec',
  spec_path: 'specs/my-app.yml',
  new_spec_yaml: yamlContent,
  commit_message: 'Update configuration',
});

if (result.success) {
  // Show success message with PR link
  console.log(`PR created: ${result.pr_url}`);

  // Show warnings if any
  if (result.warnings && result.warnings.length > 0) {
    result.warnings.forEach(w => {
      console.warn(`${w.severity}: ${w.message}`);
    });
  }
} else {
  // Handle error
  console.error(`Error: ${result.error} - ${result.details}`);
}
```

## Rate Limiting

- No built-in rate limiting in spec-applier
- Constrained by GitHub API rate limits (5000 requests/hour for authenticated users)
- GitHub API errors propagate as 502 responses

## Security

- Repository whitelist enforced via ALLOWED_REPOS environment variable
- Unauthorized repositories return GitHub API error
- API Key authentication required for all requests
```

## Validation Criteria

### Prerequisites (Before Implementation):
- [ ] Phase 3.3.3 complete (spec-applier handler deployed)
- [ ] API Gateway URL obtained
- [ ] API Key obtained from AWS
- [ ] Test repository accessible with GitHub PAT

### Immediate (Measured at Completion):
- [ ] **Integration test script created** - scripts/test-spec-applier-integration.sh
- [ ] **Manual test checklist created** - spec/3.3.4/MANUAL_TESTS.md
- [ ] **API documentation created** - docs/API_SPEC_APPLIER.md
- [ ] **At least 3 PRs created successfully** - Using integration script
- [ ] **Warnings verified in PR descriptions** - Check GitHub UI
- [ ] **Labels verified in GitHub** - infrastructure-change, automated
- [ ] **All 7 manual tests pass** - Complete checklist
- [ ] **Error scenarios tested** - 400, 404, 502 responses

### Documentation Quality:
- [ ] API documentation includes all endpoints
- [ ] Request/response schemas documented
- [ ] Error codes explained with examples
- [ ] Frontend integration example provided
- [ ] Manual test checklist is comprehensive

## Success Metrics

**Validation:**
- 3+ PRs created via integration test script
- All PRs show correct warnings in descriptions
- All PRs have correct labels
- Zero unexpected errors during testing

**Documentation:**
- Frontend team can integrate without asking questions
- All error scenarios documented
- Example code provided for common use cases

## Dependencies
- **Requires**: Phase 3.3.3 (spec-applier handler deployed)
- **Requires**: Phase 3.3.2 (GitHub write ops working)
- **Blocks**: Phase 3.4 (frontend needs API documentation)

## Implementation Notes

### Integration Test Script
- Uses real API Gateway endpoint
- Creates real PRs (must clean up after)
- Tests success and error scenarios
- Uses jq for JSON parsing

### Manual Testing
- Validates UI presentation (emojis, formatting)
- Confirms labels applied correctly
- Verifies review checklist appears
- Tests edge cases (collisions, errors)

### API Documentation
- Follows REST API documentation standards
- Includes curl examples for testing
- Provides TypeScript integration code
- Documents all error codes

## Cleanup After Testing

After running integration tests, clean up test PRs:

```bash
# List PRs created by integration tests
gh pr list --repo trakrf/action-spec --label automated

# Close each PR
gh pr close {pr-number} --repo trakrf/action-spec --delete-branch

# Or close all automated PRs
gh pr list --repo trakrf/action-spec --label automated --json number --jq '.[].number' | \
  xargs -I {} gh pr close {} --repo trakrf/action-spec --delete-branch
```
