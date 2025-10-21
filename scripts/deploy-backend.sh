#!/bin/bash
set -euo pipefail

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ActionSpec Backend Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for required environment variables
check_env_var() {
    local var_name=$1
    local default_value=${2:-}

    if [ -z "${!var_name:-}" ]; then
        if [ -n "$default_value" ]; then
            export "$var_name=$default_value"
            echo -e "${YELLOW}⚠  $var_name not set, using default: $default_value${NC}"
        else
            echo -e "${RED}❌ Error: $var_name environment variable not set${NC}"
            echo ""
            echo "Required environment variables:"
            echo "  AWS_REGION - AWS region (default: us-west-2)"
            echo "  ENVIRONMENT - Deployment environment (default: demo)"
            echo "  GITHUB_TOKEN_SSM_PARAM - SSM parameter name (default: /actionspec/github-token)"
            echo ""
            echo "Example:"
            echo "  export AWS_REGION=us-west-2"
            echo "  export ENVIRONMENT=demo"
            echo "  ./scripts/deploy-backend.sh"
            exit 1
        fi
    fi
}

# Set defaults
export AWS_REGION="${AWS_REGION:-us-west-2}"
export ENVIRONMENT="${ENVIRONMENT:-demo}"
export GITHUB_TOKEN_SSM_PARAM="${GITHUB_TOKEN_SSM_PARAM:-/actionspec/github-token}"

echo -e "${GREEN}Configuration:${NC}"
echo "  AWS Region: $AWS_REGION"
echo "  Environment: $ENVIRONMENT"
echo "  GitHub Token SSM Param: $GITHUB_TOKEN_SSM_PARAM"
echo "  Stack Name: actionspec-backend"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# Step 1: Build
echo -e "${BLUE}Step 1: Building SAM application...${NC}"
if sam build --use-container; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi
echo ""

# Step 2: Validate
echo -e "${BLUE}Step 2: Validating template...${NC}"
if sam validate --lint; then
    echo -e "${GREEN}✓ Validation successful${NC}"
else
    echo -e "${RED}❌ Validation failed${NC}"
    exit 1
fi
echo ""

# Step 3: Deploy
echo -e "${BLUE}Step 3: Deploying to AWS...${NC}"
echo -e "${YELLOW}This will deploy Lambda functions, API Gateway, S3 bucket, and IAM roles.${NC}"
echo ""

if sam deploy \
    --stack-name actionspec-backend \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        "Environment=$ENVIRONMENT" \
        "GithubTokenParamName=$GITHUB_TOKEN_SSM_PARAM" \
    --no-fail-on-empty-changeset \
    --resolve-s3; then

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Deployment Successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # Get outputs
    echo -e "${BLUE}Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name actionspec-backend \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs' \
        --output table

    # Get API endpoint
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name actionspec-backend \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
        --output text)

    # Get API Key ID
    API_KEY_ID=$(aws cloudformation describe-stacks \
        --stack-name actionspec-backend \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiKeyId`].OutputValue' \
        --output text)

    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Get API key value:"
    echo "   aws apigateway get-api-key --api-key $API_KEY_ID --include-value --query 'value' --output text"
    echo ""
    echo "2. Test endpoints:"
    echo "   export API_KEY=\$(aws apigateway get-api-key --api-key $API_KEY_ID --include-value --query 'value' --output text)"
    echo "   curl -H \"x-api-key: \$API_KEY\" $API_ENDPOINT/api/form"
    echo ""
    echo "3. Run smoke tests:"
    echo "   export API_ENDPOINT=$API_ENDPOINT"
    echo "   pytest backend/tests/test_smoke.py"

else
    echo ""
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi
