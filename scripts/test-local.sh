#!/bin/bash
set -euo pipefail

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Local Lambda Test Harness${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Set environment variables for local testing
export ENVIRONMENT=local
export SPECS_BUCKET=actionspec-backend-specs-local
export GITHUB_TOKEN_SSM_PARAM=/actionspec/github-token

# Add paths for imports
export PYTHONPATH="${PROJECT_ROOT}/backend/lambda/shared:${PROJECT_ROOT}/backend/lambda/functions:${PYTHONPATH:-}"

echo -e "${GREEN}Testing Lambda handlers directly (no Docker required)${NC}"
echo ""

# Test each handler
for func in spec-parser aws-discovery form-generator spec-applier; do
    echo -e "${BLUE}Testing $func...${NC}"

    handler_path="backend/lambda/functions/$func/handler.py"

    if [ ! -f "$handler_path" ]; then
        echo "  ❌ Handler not found: $handler_path"
        continue
    fi

    # Run handler with mock event
    python3 - <<EOF
import sys
import os
import json

# Add paths
sys.path.insert(0, '${PROJECT_ROOT}/backend/lambda/shared')
sys.path.insert(0, '${PROJECT_ROOT}/backend/lambda/functions/$func')

# Mock context
class MockContext:
    request_id = 'test-local-123'
    function_name = '$func'
    memory_limit_in_mb = 256

# Import handler
from handler import lambda_handler

# Mock event
event = {
    'path': '/api/test',
    'httpMethod': 'GET',
    'headers': {},
    'queryStringParameters': None,
    'body': None
}

# Invoke
try:
    response = lambda_handler(event, MockContext())
    print(f"  ✓ Status: {response['statusCode']}")

    body = json.loads(response['body'])
    print(f"  ✓ Message: {body.get('message', 'N/A')}")
    print(f"  ✓ Version: {body.get('version', 'N/A')}")

    # Check headers
    if 'Strict-Transport-Security' in response.get('headers', {}):
        print("  ✓ Security headers present")
    else:
        print("  ⚠  Security headers missing")

    print()
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    print()
    sys.exit(1)
EOF

    if [ $? -ne 0 ]; then
        echo "Test failed for $func"
        exit 1
    fi
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  All handlers tested successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start SAM local: sam local start-api"
echo "2. Run smoke tests: pytest backend/tests/test_smoke.py"
