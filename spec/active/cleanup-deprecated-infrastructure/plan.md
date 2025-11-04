# Implementation Plan: Comprehensive Cleanup - Remove SAM and Update OAuth Documentation

Generated: 2025-01-04
Specification: spec.md

## Understanding

This is a repository cleanup task to remove deprecated SAM/Lambda infrastructure and update all documentation to reflect the OAuth-only authentication approach (active since v0.2.0). The cleanup will:
1. Delete all SAM-related files and unused directories
2. Remove all GH_TOKEN references and replace with OAuth-only documentation
3. Consolidate environment configuration to a single template (.env.local.example)
4. Document the changes in CHANGELOG and README

This is primarily a deletion and documentation task with minimal code changes, reducing repository clutter by ~50%.

## Relevant Files

**Files to Delete** (via git rm):
- `env.json` - SAM local testing config
- `env.json.example` - SAM config template
- `samconfig.toml` - SAM CLI configuration
- `template.yaml` - SAM CloudFormation template
- `scripts/deploy-backend.sh` - SAM deployment script
- `scripts/test-local.sh` - SAM local test script
- `scripts/test-github-integration.sh` - SAM integration test
- `docs/LOCAL_DEVELOPMENT.md` - SAM-focused documentation
- `overengineered/` - Entire directory (historical "what not to do" examples)
- `demo/` - Entire directory (only contains outdated DEPLOY.md)
- `.env.example` - Outdated GH_TOKEN-only template

**Files to Modify**:
- `.env.local.example` (lines 1-3) - Remove GH_TOKEN, enhance OAuth comments
- `docker-compose.yml` (line 20) - Remove GH_TOKEN environment variable
- `justfile` (lines 86-92) - Remove GH_TOKEN from check-env recipe
- `README-TESTING.md` (lines 29-44, 63, 128-134) - Rewrite to remove GH_TOKEN instructions
- `scripts/test-docker-local.sh` (lines 16, 39-56, 169-180) - Remove GH_TOKEN logic
- `scripts/test-docker-quick.sh` (line 19) - Remove GH_TOKEN passing
- `.gitignore` (lines 82-86) - Remove SAM-related patterns
- `CHANGELOG.md` (after line 8) - Add new [0.3.0] version entry
- `README.md` (after line 37) - Add historical note in "Learning" section

**Reference Patterns**:
- CHANGELOG.md (lines 22-44) - Follow this format for new version entry
- README.md (line 37) - Insert historical note after this line
- .env.local.example (lines 17-25) - OAuth variables already present, good format

## Architecture Impact

- **Subsystems affected**: Documentation, Configuration
- **New dependencies**: None
- **Breaking changes**: None (deletions are all deprecated/unused)

## Task Breakdown

### Task 1: Delete SAM Configuration Files
**Files**: env.json, env.json.example, samconfig.toml, template.yaml
**Action**: DELETE (git rm)

**Implementation**:
```bash
git rm env.json env.json.example samconfig.toml template.yaml
```

**Validation**:
- Files deleted from working directory
- Files staged for deletion in git
- `ls -la` confirms files no longer present

### Task 2: Delete SAM Scripts
**Files**: scripts/deploy-backend.sh, scripts/test-local.sh, scripts/test-github-integration.sh
**Action**: DELETE (git rm)

**Implementation**:
```bash
git rm scripts/deploy-backend.sh scripts/test-local.sh scripts/test-github-integration.sh
```

**Validation**:
- Files deleted from working directory
- Files staged for deletion in git
- `ls -la scripts/` confirms files no longer present

### Task 3: Delete SAM Documentation
**File**: docs/LOCAL_DEVELOPMENT.md
**Action**: DELETE (git rm)

**Implementation**:
```bash
git rm docs/LOCAL_DEVELOPMENT.md
```

**Validation**:
- File deleted from working directory
- File staged for deletion in git

### Task 4: Delete Deprecated Directories
**Files**: overengineered/, demo/
**Action**: DELETE (git rm -r)

**Implementation**:
```bash
git rm -r overengineered/
git rm -r demo/
```

**Validation**:
- Directories deleted from working directory
- All files in directories staged for deletion
- `ls -la` confirms directories no longer present

### Task 5: Delete Outdated Environment Template
**File**: .env.example
**Action**: DELETE (git rm)

**Implementation**:
```bash
git rm .env.example
```

**Validation**:
- File deleted from working directory
- File staged for deletion in git

### Task 6: Update .env.local.example - Remove GH_TOKEN
**File**: .env.local.example
**Action**: MODIFY

**Implementation**:
Remove lines 1-3 (GH_TOKEN section) and update OAuth comment:

```bash
# GitHub OAuth Configuration
# Register a GitHub OAuth App to get these credentials:
#   1. Go to https://github.com/settings/developers
#   2. Click "New OAuth App"
#   3. Set callback URL: http://localhost:5000/auth/callback (for local dev)
#   4. Copy Client ID and Client Secret to variables below
# For production deployment, see deployment documentation for GitHub App setup
GITHUB_OAUTH_CLIENT_ID=your_client_id_here
GITHUB_OAUTH_CLIENT_SECRET=your_client_secret_here

# Flask Session Secret (for CSRF protection during OAuth)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY=your_secret_key_here

# AWS Credentials (for infrastructure deployment)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-west-2
AWS_DEFAULT_REGION=us-west-2
AWS_PROFILE=
AWS_SESSION_TOKEN=

# Optional: Linear API key (if using Linear for project management)
LINEAR_API_KEY=
```

**Validation**:
- No GH_TOKEN variable present
- OAuth variables present with enhanced comments
- File format preserved

### Task 7: Update docker-compose.yml - Remove GH_TOKEN
**File**: docker-compose.yml
**Action**: MODIFY (line 20)

**Implementation**:
Remove line 20: `- GH_TOKEN=${GH_TOKEN}`

Update comment on line 19 to:
```yaml
    environment:
      - FLASK_APP=app
      - FLASK_ENV=development
      - FLASK_DEBUG=1
      # OAuth configuration loaded from .env.local
      - GH_REPO=${GH_REPO:-trakrf/action-spec}
      - SPECS_PATH=${SPECS_PATH:-infra}
      - WORKFLOW_BRANCH=${WORKFLOW_BRANCH:-main}
```

**Validation**:
- No GH_TOKEN variable in environment section
- OAuth comment added
- docker-compose.yml syntax valid (docker compose config --quiet)

### Task 8: Update justfile - Remove GH_TOKEN Check
**File**: justfile
**Action**: MODIFY (lines 86-92)

**Implementation**:
Replace check-env recipe:

```bash
# Check environment variables
check-env:
    #!/usr/bin/env bash
    [ -f ".env.local" ] && source .env.local
    echo "Checking OAuth configuration..."
    [ -z "${GITHUB_OAUTH_CLIENT_ID:-}" ] && echo "⚠️  GITHUB_OAUTH_CLIENT_ID not set (optional for local dev)" || echo "✓ GITHUB_OAUTH_CLIENT_ID is set"
    [ -z "${FLASK_SECRET_KEY:-}" ] && echo "⚠️  FLASK_SECRET_KEY not set (optional for local dev)" || echo "✓ FLASK_SECRET_KEY is set"
    echo "✓ GH_REPO=${GH_REPO:-trakrf/action-spec}"
    echo "✓ SPECS_PATH=${SPECS_PATH:-infra}"
```

**Validation**:
- No GH_TOKEN check present
- OAuth variables checked instead
- `just check-env` runs without error

### Task 9: Update README-TESTING.md - OAuth-Only Documentation
**File**: README-TESTING.md
**Action**: MODIFY

**Implementation**:
Replace Prerequisites section (lines 29-44):

```markdown
## Prerequisites

- Docker installed and running
- `jq` for JSON parsing (comprehensive test only)

## Authentication

This application uses **GitHub OAuth exclusively** for authentication (as of v0.2.0).

The test scripts validate:
- Container builds and starts successfully
- Health endpoint responds
- Static assets load correctly
- Application UI is accessible

**Note**: API endpoints require OAuth authentication. To test authenticated endpoints:
1. Start the application: `docker compose up`
2. Visit http://localhost:5000
3. Log in with GitHub OAuth
4. Test API endpoints from your authenticated browser session

The E2E test scripts focus on infrastructure validation (Docker, health checks, static assets) rather than authenticated API testing.
```

Remove "Setting GitHub Token" section (lines 35-44).

Update "What Gets Tested" section (line 63):
- Remove: "7. ✅ `/api/pods` endpoint (if GH_TOKEN available)"
- Add: "7. ⚠️ `/api/pods` endpoint returns 401 (requires OAuth login)"

Update "Known Issues" section (lines 131-135):
- Remove: "Without `GH_TOKEN`, API endpoints will return auth errors"
- Add: "API endpoints return 401 without OAuth authentication (expected behavior)"

**Validation**:
- No GH_TOKEN mentioned in file
- OAuth authentication clearly documented
- File renders correctly as markdown

### Task 10: Update scripts/test-docker-local.sh - Remove GH_TOKEN
**File**: scripts/test-docker-local.sh
**Action**: MODIFY

**Implementation**:
Remove line 16: `GITHUB_TOKEN="${GH_TOKEN:-}"`

Remove lines 39-56 (GH_TOKEN conditional logic):
```bash
echo "🚀 Step 2: Starting container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8080" \
    -e FLASK_ENV=production \
    "$IMAGE_NAME:test"
echo "✓ Container started: $CONTAINER_NAME"
```

Remove/update lines 169-182 (Test 5):
```bash
echo "  Test 5: OAuth authentication"
echo "    ⚠️  API endpoints require OAuth login (expected 401)"
PODS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/api/pods)
if [ "$PODS_CODE" = "401" ]; then
    echo "    ✓ API correctly requires authentication (HTTP 401)"
else
    echo "    ⚠️  Unexpected response: HTTP $PODS_CODE"
fi
echo ""
```

**Validation**:
- No GH_TOKEN variable or logic present
- Script runs successfully
- OAuth requirement documented in output
- `./scripts/test-docker-local.sh` exits 0

### Task 11: Update scripts/test-docker-quick.sh - Remove GH_TOKEN
**File**: scripts/test-docker-quick.sh
**Action**: MODIFY (line 19)

**Implementation**:
Remove line 19: `-e GH_TOKEN="${GH_TOKEN:-}" \`

Result:
```bash
echo "Starting container..."
docker run -d --name $CONTAINER -p $PORT:8080 \
    $IMAGE:latest
```

**Validation**:
- No GH_TOKEN variable present
- Script runs successfully
- `./scripts/test-docker-quick.sh` exits 0

### Task 12: Update .gitignore - Remove SAM Patterns
**File**: .gitignore
**Action**: MODIFY (lines 82-86)

**Implementation**:
Remove lines 82-86:
```
# AWS SAM
.aws-sam/
samconfig.toml.bak
env.json
!env.json.example
```

**Validation**:
- No SAM-related patterns in .gitignore
- File format preserved

### Task 13: Update CHANGELOG.md - Document Changes
**File**: CHANGELOG.md
**Action**: MODIFY (add after line 8)

**Implementation**:
Replace [Unreleased] section with new version:

```markdown
## [0.3.0] - 2025-01-04

### Removed
- **SAM/Lambda infrastructure** - Deleted unused AWS SAM config files (env.json, samconfig.toml, template.yaml, env.json.example)
- **SAM deployment scripts** - Removed scripts/deploy-backend.sh, test-local.sh, test-github-integration.sh
- **SAM documentation** - Removed docs/LOCAL_DEVELOPMENT.md (SAM-specific local development guide)
- **overengineered/ directory** - Removed historical "what not to do" examples and partially-built enterprise architecture
  - Original SAM approach was ~50% built before pivot to Flask+Docker+Terraform
  - Served educational purpose but cluttered repository
  - See commit `130932d` for deleted content
- **demo/ directory** - Removed outdated deployment documentation with deprecated GH_TOKEN instructions
- **.env.example** - Removed GH_TOKEN-only template, use .env.local.example instead

### Changed
- **OAuth-only documentation** - All docs and config updated to reflect OAuth-only authentication (active since v0.2.0)
  - Updated README-TESTING.md: Removed GH_TOKEN setup instructions, documented OAuth authentication
  - Updated docker-compose.yml: Removed GH_TOKEN environment variable
  - Updated .env.local.example: Removed GH_TOKEN, enhanced OAuth setup documentation
  - Updated justfile: Replaced GH_TOKEN check with OAuth variable checks
  - Updated test scripts: Removed GH_TOKEN passing, documented OAuth requirement
- **.env.local.example is now single source of truth** for environment configuration

### Fixed
- Eliminated confusion between .env.example and .env.local.example templates
- Removed misleading references to GH_TOKEN authentication (removed in v0.2.0)

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security
```

**Validation**:
- New version entry follows Keep a Changelog format
- All changes documented accurately
- [Unreleased] section preserved for future changes

### Task 14: Update README.md - Add Historical Note
**File**: README.md
**Action**: MODIFY (after line 37)

**Implementation**:
Add after line 37 ("**Learning:** Should have validated..."):

```markdown

**Historical Note** (January 2025): This repository previously contained a partially-built SAM/Lambda implementation and "overengineered" examples to demonstrate what not to do. These were removed as they served their educational purpose but cluttered the repository. The project uses GitHub OAuth exclusively for authentication (GH_TOKEN removed in v0.2.0). See commit `130932d` for deleted content or check CHANGELOG.md for details.
```

**Validation**:
- Historical note inserted in correct location (after line 37)
- Note is concise and informative
- Markdown formatting correct

## Risk Assessment

**Risk**: Missing a GH_TOKEN reference in an obscure file
**Mitigation**: Use `git grep "GH_TOKEN"` to verify all references after updates. Allow Terraform/infra references (those are SSM parameter names, not auth variables).

**Risk**: Breaking test scripts by removing environment variables
**Mitigation**: Run both test scripts (test-docker-local.sh, test-docker-quick.sh) after modifications to verify they still work.

**Risk**: Accidentally deleting tracked but uncommitted work in demo/ or overengineered/
**Mitigation**: Run `git status` before git rm to verify no untracked changes. User confirmed these directories should be deleted.

## Integration Points

None - this is a cleanup task affecting only documentation and configuration.

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After file modifications (Tasks 6-14), use commands from `spec/stack.md`:
- Gate 1: Lint (just lint)
- Gate 2: Test (just test)
- Gate 3: Build (just build)

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

**After each file modification task (6-14)**:
```bash
just lint    # Must pass
just test    # Must pass
```

**After all modifications complete**:
```bash
# Verify deletions
git grep "env\.json" || echo "✓ No env.json references"
git grep "sam local" || echo "✓ No SAM references"
git grep "overengineered" | grep -v "CHANGELOG\|README" || echo "✓ Only CHANGELOG/README references"

# Verify GH_TOKEN only in infra
git grep "GH_TOKEN" | grep -v "infra/" || echo "✓ GH_TOKEN only in infrastructure"

# Run test scripts
./scripts/test-docker-quick.sh
./scripts/test-docker-local.sh

# Full validation
just validate  # lint + test + build
```

## Plan Quality Assessment

**Complexity Score**: 4/10 (LOW)
**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements with explicit file lists
✅ Straightforward deletions and documentation updates
✅ No code logic changes required
✅ Similar cleanup patterns common in projects
✅ Comprehensive validation strategy defined
✅ All target files verified to exist
✅ Test scripts available for validation

**Assessment**: High confidence cleanup task with clear success criteria and minimal risk.

**Estimated one-pass success probability**: 95%

**Reasoning**: This is a well-defined cleanup task with explicit requirements and no complex logic changes. Primary risk is missing a reference, mitigated by grep validation. Test script modifications are straightforward (remove variable passing). Documentation updates follow existing patterns.
