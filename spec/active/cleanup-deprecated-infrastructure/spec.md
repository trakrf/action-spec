# Feature: Comprehensive Cleanup - Remove SAM and Update OAuth Documentation

## Origin
Discovery of duplicate environment configuration files (env.json and .env.local) revealed multiple deprecated components still in the repository:
1. SAM/Lambda infrastructure was deprecated in favor of Flask+Docker+Terraform
2. GH_TOKEN was removed in commit 206de92 (OAuth-only since v0.2.0)
3. overengineered/ directory exists but serves no purpose
4. demo/ directory contains only outdated deployment docs
5. .env.example is an outdated subset of .env.local.example

## Outcome
- Repository contains only active, maintained code
- All documentation and configuration reflects OAuth-only authentication
- Single source of truth for environment configuration (.env.local.example)
- Historical context preserved in CHANGELOG and README

## Why This Matters
- **Clarity**: Developers shouldn't wonder which files are current vs deprecated
- **Maintenance**: No need to update multiple env templates or outdated docs
- **Onboarding**: New contributors see only relevant, active code
- **OAuth-only**: Backend has been OAuth-only since v0.2.0, docs should reflect this

## Context

### What Led Here
- Project started with enterprise SAM/Lambda architecture (overengineered/PRD.md)
- Pivoted to simpler Flask+Docker+Terraform approach (~v0.1.0)
- SAM was ~50% built before pivot, served as "what not to do" example
- Commit 206de92 removed all GH_TOKEN support, backend now OAuth-only
- These artifacts served their educational purpose but now clutter the repo

### Current Problems
- Multiple environment file templates (.env.example vs .env.local.example) causing confusion
- Documentation references GH_TOKEN authentication that no longer works
- SAM config files suggest SAM is still an option (it's not)
- demo/ directory has outdated deployment instructions
- overengineered/ served its purpose as learning artifact

## Requirements

### Files to Remove

**SAM Infrastructure**
- env.json
- env.json.example
- samconfig.toml
- template.yaml
- scripts/deploy-backend.sh
- scripts/test-local.sh
- scripts/test-github-integration.sh
- docs/LOCAL_DEVELOPMENT.md

**Deprecated Directories**
- overengineered/ (entire directory)
- demo/ (entire directory)

**Redundant Configuration**
- .env.example (superseded by .env.local.example)

### Files to Update

**OAuth Migration**
- README-TESTING.md - Remove GH_TOKEN setup instructions, note OAuth-only authentication
- docker-compose.yml - Remove GH_TOKEN environment variable
- .env.local.example - Ensure GH_TOKEN removed, OAuth variables present (GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET, FLASK_SECRET_KEY)
- justfile - Remove GH_TOKEN from check-env recipe
- scripts/test-docker-local.sh - Remove GH_TOKEN logic
- scripts/test-docker-quick.sh - Remove GH_TOKEN passing

**Cleanup**
- .gitignore - Remove SAM-related patterns (env.json, samconfig.toml.bak)

### Documentation Updates

**CHANGELOG.md** - Add entry documenting:
- Removal of SAM/Lambda infrastructure
- Removal of overengineered/ and demo/ directories
- Removal of .env.example in favor of .env.local.example
- Migration to OAuth-only (GH_TOKEN removed from all docs/config)

**README.md** - Add historical note:
- Repository previously contained partially-built SAM/Lambda implementation
- These were removed as they served their educational purpose
- Project uses GitHub OAuth exclusively (GH_TOKEN removed in v0.2.0)

### Files to Keep

- `.env.local` - Active development environment file (gitignored)
- `.env.local.example` - **Single source of truth** for environment configuration template

## Validation Criteria

**Deletions Complete**
- All SAM files removed from repository
- overengineered/ directory removed
- demo/ directory removed
- .env.example removed
- No references to removed files in active code

**OAuth Migration Complete**
- No GH_TOKEN references in application code or documentation
- Terraform/infra references to GH_TOKEN SSM parameters are acceptable (infrastructure config)
- All docs clearly state OAuth-only authentication
- .env.local.example contains OAuth configuration

**Documentation Updated**
- CHANGELOG documents all removals
- README contains historical note
- No broken references to deleted content

**Tests Pass**
- Repository builds successfully
- Docker E2E tests pass
- No broken imports or missing dependencies

## Constraints

- Preserve Terraform/infra references to GH_TOKEN SSM parameter names (infrastructure config, not app auth)
- Maintain git history (use git rm, not manual deletion)
- Document changes in CHANGELOG before merging

## Success Metrics

- `git grep "env\.json"` returns no results
- `git grep "sam local"` returns no results
- `git grep "overengineered"` returns only CHANGELOG/README references
- `git grep "GH_TOKEN"` returns only Terraform/infra SSM parameter references
- Single .env template exists (.env.local.example)
- All tests pass

## Notes

- .env.local.example becomes the single authoritative environment configuration template
- Historical context preserved in version control and CHANGELOG
- This cleanup removes ~50% of repository cruft
- Aligns all documentation with v0.2.0+ OAuth-only reality
