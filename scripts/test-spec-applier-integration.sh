#!/usr/bin/env bash
#
# Integration test for spec-applier Lambda (Phase 3.3.4)
# Tests real GitHub PR creation with warnings
#
# Usage: ./scripts/test-spec-applier-integration.sh
#
# Prerequisites:
# - spec-applier Lambda deployed to AWS
# - API_URL environment variable set
# - API_KEY environment variable set
# - GitHub PAT configured in SSM Parameter Store
# - ALLOWED_REPOS includes test repository

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-}"
API_KEY="${API_KEY:-}"
TEST_REPO="${TEST_REPO:-trakrf/action-spec}"
SKIP_PREFLIGHT="${SKIP_PREFLIGHT:-false}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Spec Applier Integration Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
check_prerequisites() {
    local has_error=false

    if [ -z "$API_URL" ]; then
        echo -e "${RED}❌ Error: API_URL environment variable not set${NC}"
        echo "   Set it to your deployed API Gateway URL"
        echo "   Example: export API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Prod"
        has_error=true
    else
        echo -e "${GREEN}✅ API_URL set${NC}: $API_URL"
    fi

    if [ -z "$API_KEY" ]; then
        echo -e "${RED}❌ Error: API_KEY environment variable not set${NC}"
        echo "   Get API key from AWS Console or SAM outputs"
        echo "   Retrieve with: aws apigateway get-api-keys --query 'items[?name==\`actionspec-backend-api-key\`].value' --output text"
        has_error=true
    else
        echo -e "${GREEN}✅ API_KEY set${NC}: ${API_KEY:0:8}..."
    fi

    # Check for jq
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ Error: jq not found${NC}"
        echo "   Install with:"
        echo "     Ubuntu/Debian: sudo apt-get install jq"
        echo "     MacOS: brew install jq"
        has_error=true
    else
        echo -e "${GREEN}✅ jq installed${NC}"
    fi

    if [ "$has_error" = true ]; then
        exit 1
    fi
    echo ""
}

# Pre-flight deployment check
check_deployment() {
    if [ "$SKIP_PREFLIGHT" = "true" ]; then
        echo -e "${YELLOW}⚠️  Skipping pre-flight deployment checks${NC}"
        echo ""
        return 0
    fi

    echo "Checking deployment..."

    # Verify API endpoint is responsive
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "$API_URL/health" \
        -H "x-api-key: $API_KEY" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ API endpoint responsive${NC}"
    elif [ "$HTTP_CODE" = "403" ]; then
        echo -e "${RED}❌ API endpoint returned 403 Forbidden${NC}"
        echo "   Check API_KEY is correct"
        exit 1
    else
        echo -e "${YELLOW}⚠️  Could not verify API health endpoint (HTTP $HTTP_CODE)${NC}"
        echo "   This may be expected if /health endpoint not implemented"
        echo "   Continuing with tests..."
    fi
    echo ""
}

# Test 1: Safe change (no warnings)
test_safe_change() {
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

    TIMESTAMP=$(date +%s)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/spec/apply" \
        -H "x-api-key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d @- <<EOF
{
  "repo": "$TEST_REPO",
  "spec_path": "specs/examples/integration-test-$TIMESTAMP.yml",
  "new_spec_yaml": $(echo "$SAFE_SPEC" | jq -Rs .),
  "commit_message": "Integration test: safe change"
}
EOF
)

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

    if [ "$HTTP_CODE" != "200" ]; then
        echo -e "${RED}❌ Test failed - HTTP $HTTP_CODE${NC}"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        return 1
    fi

    if echo "$BODY" | jq -e '.success == true' > /dev/null 2>&1; then
        PR_URL=$(echo "$BODY" | jq -r '.pr_url')
        WARNING_COUNT=$(echo "$BODY" | jq '.warnings | length')
        echo -e "${GREEN}✅ PR created${NC}: $PR_URL"
        echo -e "${GREEN}✅ Warnings${NC}: $WARNING_COUNT (expected: 0)"

        if [ "$WARNING_COUNT" -ne 0 ]; then
            echo -e "${YELLOW}⚠️  Expected 0 warnings but got $WARNING_COUNT${NC}"
        fi
    else
        echo -e "${RED}❌ Test failed${NC}"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        return 1
    fi
    echo ""
}

# Test 2: Destructive change (WAF disabling)
test_waf_disable() {
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
      enabled: false
EOF
)

    TIMESTAMP=$(date +%s)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/spec/apply" \
        -H "x-api-key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d @- <<EOF
{
  "repo": "$TEST_REPO",
  "spec_path": "specs/examples/integration-test-$TIMESTAMP.yml",
  "new_spec_yaml": $(echo "$DESTRUCTIVE_SPEC" | jq -Rs .),
  "commit_message": "Integration test: disable WAF"
}
EOF
)

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

    if [ "$HTTP_CODE" != "200" ]; then
        echo -e "${RED}❌ Test failed - HTTP $HTTP_CODE${NC}"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        return 1
    fi

    if echo "$BODY" | jq -e '.success == true' > /dev/null 2>&1; then
        PR_URL=$(echo "$BODY" | jq -r '.pr_url')
        WARNING_COUNT=$(echo "$BODY" | jq '.warnings | length')
        HAS_WAF_WARNING=$(echo "$BODY" | jq -e '.warnings[] | select(.field_path | contains("waf"))' > /dev/null 2>&1 && echo "yes" || echo "no")

        echo -e "${GREEN}✅ PR created${NC}: $PR_URL"

        if [ "$WARNING_COUNT" -gt 0 ] && [ "$HAS_WAF_WARNING" = "yes" ]; then
            echo -e "${GREEN}✅ Warnings${NC}: $WARNING_COUNT (WAF warning detected)"
        else
            echo -e "${RED}❌ Expected WAF warning not found${NC}"
            echo "   Warnings: $WARNING_COUNT"
            echo "   Has WAF warning: $HAS_WAF_WARNING"
            return 1
        fi
    else
        echo -e "${RED}❌ Test failed${NC}"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        return 1
    fi
    echo ""
}

# Test 3: Invalid spec (validation error)
test_invalid_spec() {
    echo -e "${YELLOW}Test 3: Invalid spec (validation error)${NC}"
    echo "----------------------------------------"

    INVALID_SPEC="invalid: yaml without required fields"

    TIMESTAMP=$(date +%s)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/spec/apply" \
        -H "x-api-key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d @- <<EOF
{
  "repo": "$TEST_REPO",
  "spec_path": "specs/examples/integration-test-$TIMESTAMP.yml",
  "new_spec_yaml": $(echo "$INVALID_SPEC" | jq -Rs .),
  "commit_message": "Integration test: invalid spec"
}
EOF
)

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

    if [ "$HTTP_CODE" != "200" ] && echo "$BODY" | jq -e '.success == false' > /dev/null 2>&1; then
        ERROR=$(echo "$BODY" | jq -r '.error // "Unknown error"')
        echo -e "${GREEN}✅ Validation error detected${NC}: $ERROR"
    else
        echo -e "${RED}❌ Expected validation error not returned${NC}"
        echo "   HTTP Code: $HTTP_CODE"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        return 1
    fi
    echo ""
}

# Main execution
main() {
    check_prerequisites
    check_deployment

    local passed=0
    local failed=0

    # Run tests
    if test_safe_change; then
        ((passed++))
    else
        ((failed++))
    fi

    if test_waf_disable; then
        ((passed++))
    else
        ((failed++))
    fi

    if test_invalid_spec; then
        ((passed++))
    else
        ((failed++))
    fi

    # Summary
    echo -e "${BLUE}========================================${NC}"
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}✅ All integration tests passed!${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        echo "Passed: $passed/3"
        echo ""
        echo "Manual verification steps:"
        echo "1. Visit the PRs created above"
        echo "2. Verify PR descriptions show warnings correctly"
        echo "3. Verify labels 'infrastructure-change' and 'automated' are applied"
        echo "4. Close PRs after verification with:"
        echo "   gh pr list --repo $TEST_REPO --label automated --json number --jq '.[].number' | \\"
        echo "     xargs -I {} gh pr close {} --repo $TEST_REPO --delete-branch"
        exit 0
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        echo "Passed: $passed/3"
        echo "Failed: $failed/3"
        exit 1
    fi
}

# Run main function
main
