#!/bin/bash
set -euo pipefail

# ANSI color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Initialize violation counter
VIOLATIONS_FOUND=0

# Get list of staged files (or all files if not in git context)
if git rev-parse --git-dir > /dev/null 2>&1; then
  STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || echo "")
else
  # Not in git context (CI environment) - scan all tracked files
  STAGED_FILES=$(git ls-files 2>/dev/null || find . -type f)
fi

# Exit early if no files to check
if [ -z "$STAGED_FILES" ]; then
  echo -e "${GREEN}✅ No files to check${NC}"
  exit 0
fi

# Filter out files we should skip
FILTERED_FILES=""
for file in $STAGED_FILES; do
  # Skip .example files (templates with placeholder values)
  if [[ "$file" =~ \.example$ ]] || [[ "$file" =~ \.example\. ]]; then
    continue
  fi

  # Skip excluded directories
  if [[ "$file" =~ ^(node_modules|\.git|dist|build|\.terraform)/.*$ ]]; then
    continue
  fi

  # Only include relevant file types
  if [[ "$file" =~ \.(tf|py|js|jsx|ts|tsx|yml|yaml|json|sh|md)$ ]]; then
    FILTERED_FILES="$FILTERED_FILES $file"
  fi
done

# Exit if no relevant files
if [ -z "$FILTERED_FILES" ]; then
  echo -e "${GREEN}✅ No relevant files to scan${NC}"
  exit 0
fi

echo "🔍 Scanning $(echo $FILTERED_FILES | wc -w | tr -d ' ') staged files for security violations..."

# Function to report violations
report_violation() {
  local file=$1
  local line_num=$2
  local pattern_name=$3
  local matched_text=$4

  echo -e "\n📄 ${YELLOW}${file}:${line_num}${NC}"
  echo -e "   ⚠️  ${pattern_name}: ${matched_text}"
  VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
}

# Check 1: AWS Account IDs (12 consecutive digits)
# Relaxed for .md files (docs can have examples)
echo "  Checking for AWS account IDs..."
for file in $FILTERED_FILES; do
  if [ ! -f "$file" ]; then
    continue
  fi

  # For markdown files, only check for the real account number
  if [[ "$file" =~ \.md$ ]]; then
    while IFS=: read -r line_num line_text; do
      if [[ "$line_text" =~ 252374924199 ]]; then
        report_violation "$file" "$line_num" "Real AWS Account ID detected" "252374924199"
      fi
    done < <(grep -nI "252374924199" "$file" 2>/dev/null || true)
  else
    # For code files, block any 12-digit pattern except clearly fake test IDs
    while IFS=: read -r line_num line_text; do
      if [[ "$line_text" =~ [0-9]{12} ]]; then
        matched=$(echo "$line_text" | grep -oE '[0-9]{12}' | head -1)
        # Skip common fake/test account IDs (all same digit or standard examples)
        if [[ ! "$matched" =~ ^(000000000000|111111111111|999999999999|123456789012)$ ]]; then
          report_violation "$file" "$line_num" "AWS Account ID pattern detected" "$matched"
        fi
      fi
    done < <(grep -nIE '[0-9]{12}' "$file" 2>/dev/null || true)
  fi
done

# Check 2: Private IP Addresses
# Relaxed for .md files
echo "  Checking for private IP addresses..."
for file in $FILTERED_FILES; do
  if [ ! -f "$file" ]; then
    continue
  fi

  # Skip markdown files for IP checks (docs often have IP examples)
  if [[ "$file" =~ \.md$ ]]; then
    continue
  fi

  # Check for 10.x.x.x
  while IFS=: read -r line_num line_text; do
    matched=$(echo "$line_text" | grep -oE '10\.([0-9]{1,3}\.){2}[0-9]{1,3}' | head -1)
    if [ -n "$matched" ]; then
      report_violation "$file" "$line_num" "Private IP address (10.x.x.x)" "$matched"
    fi
  done < <(grep -nIE '10\.([0-9]{1,3}\.){2}[0-9]{1,3}' "$file" 2>/dev/null || true)

  # Check for 172.16-31.x.x
  while IFS=: read -r line_num line_text; do
    matched=$(echo "$line_text" | grep -oE '172\.(1[6-9]|2[0-9]|3[01])\.([0-9]{1,3}\.)[0-9]{1,3}' | head -1)
    if [ -n "$matched" ]; then
      report_violation "$file" "$line_num" "Private IP address (172.16-31.x.x)" "$matched"
    fi
  done < <(grep -nIE '172\.(1[6-9]|2[0-9]|3[01])\.([0-9]{1,3}\.)[0-9]{1,3}' "$file" 2>/dev/null || true)

  # Check for 192.168.x.x
  while IFS=: read -r line_num line_text; do
    matched=$(echo "$line_text" | grep -oE '192\.168\.([0-9]{1,3}\.)[0-9]{1,3}' | head -1)
    if [ -n "$matched" ]; then
      report_violation "$file" "$line_num" "Private IP address (192.168.x.x)" "$matched"
    fi
  done < <(grep -nIE '192\.168\.([0-9]{1,3}\.)[0-9]{1,3}' "$file" 2>/dev/null || true)
done

# Check 3: Common Secret Patterns
echo "  Checking for secrets and credentials..."
SECRET_PATTERNS=(
  "aws_access_key_id\s*=\s*[A-Z0-9]+"
  "aws_secret_access_key\s*=\s*[A-Za-z0-9/+]+"
  "password\s*=\s*[^\s]+"
  "secret\s*=\s*[^\s]+"
  "token\s*=\s*[^\s]+"
  "api_key\s*=\s*[^\s]+"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
  for file in $FILTERED_FILES; do
    if [ ! -f "$file" ]; then
      continue
    fi

    # Skip markdown files for secret patterns (docs have examples)
    if [[ "$file" =~ \.md$ ]]; then
      continue
    fi

    while IFS=: read -r line_num line_text; do
      matched=$(echo "$line_text" | grep -oE "$pattern" | head -1)
      if [ -n "$matched" ]; then
        report_violation "$file" "$line_num" "Potential secret detected" "$matched"
      fi
    done < <(grep -nIE "$pattern" "$file" 2>/dev/null || true)
  done
done

# Check 4: Forbidden Files (should be in .gitignore, but double-check)
echo "  Checking for forbidden files..."
FORBIDDEN_PATTERNS=(
  "\.tfstate$"
  "\.tfstate\.backup$"
  "^\.env$"
  "^\.env\.local$"
  "^\.env\.production$"
  "credentials\.json$"
)

for file in $STAGED_FILES; do
  for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if [[ "$file" =~ $pattern ]]; then
      # Don't show line number for file-level violations
      echo -e "\n📄 ${YELLOW}${file}${NC}"
      echo -e "   ⚠️  Forbidden file type: Should be in .gitignore"
      VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
    fi
  done
done

# Report results
echo ""
if [ $VIOLATIONS_FOUND -gt 0 ]; then
  echo -e "${RED}❌ Pre-commit check FAILED!${NC}"
  echo ""
  echo -e "${RED}Found ${VIOLATIONS_FOUND} security violation(s)${NC}"
  echo ""
  echo "🚫 Commit blocked. Fix these issues before committing."
  echo ""
  echo "To bypass (NOT recommended): git commit --no-verify"
  exit 1
else
  echo -e "${GREEN}✅ Pre-commit checks passed${NC}"
  exit 0
fi
