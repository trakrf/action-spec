# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [0.2.0] - 2025-11-01

### Added
- GitHub OAuth authentication for user login
- Custom domain with SSL certificate (action-spec.aws.trakrf.id)
- User session management with Flask sessions
- User menu in navigation bar showing GitHub avatar and username
- Login/logout functionality
- DNS configuration with ACM certificate validation

### Changed
- Replaced service account PAT (GH_TOKEN) with user OAuth tokens
- Updated App Runner configuration with OAuth environment variables
- All GitHub API operations now use authenticated user tokens

### Removed
- Service account Personal Access Token (GH_TOKEN) from infrastructure

### Security
- OAuth credentials securely stored in AWS Secrets Manager
- Flask secret key auto-generated for session security
- HTTPS enforced via ACM SSL certificate
- IAM policies updated for least-privilege OAuth secret access
