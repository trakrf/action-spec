# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
