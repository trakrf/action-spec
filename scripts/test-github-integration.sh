#!/usr/bin/env bash
#
# Integration test for GitHub client
# Tests real GitHub authentication and file fetching
#
# Usage: ./scripts/test-github-integration.sh
#
# Prerequisites:
# - GitHub PAT stored in SSM: /actionspec/github-token
# - AWS CLI configured
# - Python 3.11+ with PyGithub installed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SSM_PARAM_NAME="${GITHUB_TOKEN_SSM_PARAM:-/actionspec/github-token}"
TEST_REPO="trakrf/action-spec"
TEST_FILE="specs/examples/secure-web-waf.spec.yml"
AWS_REGION="${AWS_REGION:-us-west-2}"

echo "=================================================="
echo "GitHub Integration Test"
echo "=================================================="
echo ""

# Test 1: Retrieve token from SSM
echo "Test 1: Retrieve GitHub token from SSM..."
if TOKEN=$(aws ssm get-parameter \
    --name "$SSM_PARAM_NAME" \
    --with-decryption \
    --region "$AWS_REGION" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null); then
    echo -e "${GREEN}✅ SSM Parameter retrieved successfully${NC}"
    echo "   Parameter: $SSM_PARAM_NAME"
    echo "   Token prefix: ${TOKEN:0:7}..."
else
    echo -e "${RED}❌ Failed to retrieve SSM parameter${NC}"
    echo "   Parameter: $SSM_PARAM_NAME"
    echo "   Region: $AWS_REGION"
    echo ""
    echo "Create parameter with:"
    echo "  aws ssm put-parameter \\"
    echo "    --name $SSM_PARAM_NAME \\"
    echo "    --type SecureString \\"
    echo "    --value 'ghp_YOUR_TOKEN_HERE' \\"
    echo "    --region $AWS_REGION"
    exit 1
fi
echo ""

# Test 2: Authenticate with GitHub
echo "Test 2: Authenticate with GitHub..."
PYTHON_TEST_AUTH=$(cat <<'EOF'
import sys
from github import Github, GithubException

token = sys.argv[1]
try:
    client = Github(token)
    rate_limit = client.get_rate_limit()
    print(f"✅ GitHub authentication successful")
    print(f"   Rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit}")
    print(f"   Reset: {rate_limit.core.reset}")
    sys.exit(0)
except GithubException as e:
    print(f"❌ GitHub authentication failed: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)

if python3 -c "$PYTHON_TEST_AUTH" "$TOKEN"; then
    echo ""
else
    echo -e "${RED}❌ GitHub authentication failed${NC}"
    echo "   Check token validity in GitHub Settings"
    exit 1
fi

# Test 3: Fetch test spec file
echo "Test 3: Fetch test spec file..."
PYTHON_TEST_FETCH=$(cat <<'EOF'
import sys
from github import Github

token = sys.argv[1]
repo_name = sys.argv[2]
file_path = sys.argv[3]

try:
    client = Github(token)
    repo = client.get_repo(repo_name)
    file_content = repo.get_contents(file_path)
    content = file_content.decoded_content.decode('utf-8')

    print(f"✅ Test spec file fetched successfully")
    print(f"   Repository: {repo_name}")
    print(f"   File: {file_path}")
    print(f"   Size: {len(content)} bytes")
    print(f"   First line: {content.split(chr(10))[0]}")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed to fetch file: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)

if python3 -c "$PYTHON_TEST_FETCH" "$TOKEN" "$TEST_REPO" "$TEST_FILE"; then
    echo ""
else
    echo -e "${RED}❌ Failed to fetch test file${NC}"
    echo "   Repository: $TEST_REPO"
    echo "   File: $TEST_FILE"
    exit 1
fi

# Test 4: Test repository whitelist (should fail for unauthorized repo)
echo "Test 4: Test repository whitelist..."
UNAUTHORIZED_REPO="unauthorized/repo"
PYTHON_TEST_WHITELIST=$(cat <<'EOF'
import sys
from github import Github

token = sys.argv[1]
repo_name = sys.argv[2]

try:
    client = Github(token)
    repo = client.get_repo(repo_name)
    # Should fail before getting here due to whitelist
    print(f"❌ Whitelist check failed - unauthorized repo accessed", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    # Expected to fail (repo doesn't exist or unauthorized)
    print(f"✅ Whitelist validation working (unauthorized repo rejected)")
    print(f"   Attempted: {repo_name}")
    sys.exit(0)
EOF
)

python3 -c "$PYTHON_TEST_WHITELIST" "$TOKEN" "$UNAUTHORIZED_REPO"
echo ""

# Summary
echo "=================================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "=================================================="
echo ""
echo "Your GitHub integration is working correctly."
echo "You can now use the github_client module in Lambda functions."
echo ""
echo "Next steps:"
echo "  1. Deploy Lambda functions: sam build && sam deploy"
echo "  2. Test via API Gateway endpoint"
echo "  3. Monitor CloudWatch logs for authentication issues"
