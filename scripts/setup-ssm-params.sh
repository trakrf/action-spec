#!/bin/bash
set -euo pipefail

# TODO: Migrate to Terraform/Tofu management
# This should be: .env.local → TF_VAR_github_token → aws_ssm_parameter resource
# Current approach is manual but functional
# Planned for Phase 3.5 or Terraform migration spec

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SSM Parameter Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-us-west-2}"

echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ Region: $REGION${NC}"
echo ""

# Parameter name
PARAM_NAME="${GITHUB_TOKEN_SSM_PARAM:-/actionspec/github-token}"

# Check if parameter already exists
if aws ssm get-parameter --name "$PARAM_NAME" --region "$REGION" &>/dev/null; then
    echo -e "${YELLOW}⚠  Parameter $PARAM_NAME already exists${NC}"
    echo ""
    read -p "Overwrite existing parameter? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Get GitHub token
echo ""
echo -e "${BLUE}GitHub Personal Access Token Setup${NC}"
echo ""
echo "You need a GitHub PAT with these permissions:"
echo "  - repo (full control of private repositories)"
echo "  - workflow (update GitHub Action workflows)"
echo ""
echo "Create one at: https://github.com/settings/tokens/new"
echo ""

read -sp "Enter GitHub Personal Access Token: " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ Token cannot be empty${NC}"
    exit 1
fi

# Validate token format (basic check)
if [[ ! "$GITHUB_TOKEN" =~ ^(ghp_|github_pat_)[a-zA-Z0-9_]+ ]]; then
    echo -e "${YELLOW}⚠  Warning: Token doesn't match expected format (ghp_* or github_pat_*)${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Store in SSM
echo ""
echo -e "${BLUE}Storing parameter in SSM...${NC}"

if aws ssm put-parameter \
    --name "$PARAM_NAME" \
    --value "$GITHUB_TOKEN" \
    --type SecureString \
    --description "GitHub Personal Access Token for ActionSpec" \
    --region "$REGION" \
    --overwrite &>/dev/null; then

    echo -e "${GREEN}✓ Parameter stored successfully${NC}"
    echo ""
    echo "Parameter details:"
    echo "  Name: $PARAM_NAME"
    echo "  Type: SecureString"
    echo "  Region: $REGION"
    echo ""

    # Test retrieval
    if aws ssm get-parameter --name "$PARAM_NAME" --region "$REGION" --with-decryption --query 'Parameter.Value' --output text &>/dev/null; then
        echo -e "${GREEN}✓ Parameter retrieval test successful${NC}"
    else
        echo -e "${RED}❌ Failed to retrieve parameter${NC}"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo "Lambda functions can now access this token via:"
    echo "  export GITHUB_TOKEN_SSM_PARAM=$PARAM_NAME"

else
    echo -e "${RED}❌ Failed to store parameter${NC}"
    exit 1
fi
