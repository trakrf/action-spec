# Spec Applier API - Documentation

## Overview
The Spec Applier API enables programmatic updates to ActionSpec configurations via GitHub pull requests. It analyzes changes, detects destructive operations, and creates PRs with appropriate warnings.

**Base URL**: Provided via SAM deployment outputs
**Authentication**: API Key required
**Version**: 1.0 (Phase 3.3.4)

---

## Endpoint

### POST `/spec/apply`

Creates a GitHub pull request with updated ActionSpec configuration and destructive change warnings.

**Path**: `/spec/apply`
**Method**: `POST`
**Authentication**: Required (API Key)

---

## Authentication

All requests must include an API key in the header:

```http
x-api-key: {your-api-key}
```

### Obtaining API Key

**Via AWS CLI**:
```bash
# Get API key ID
aws apigateway get-api-keys \
  --query 'items[?name==`actionspec-backend-api-key`].id' \
  --output text

# Get API key value
aws apigateway get-api-key \
  --api-key {key-id} \
  --include-value \
  --query 'value' \
  --output text
```

**Via SAM Outputs**:
```bash
sam list stack-outputs --stack-name actionspec-backend
```

---

## Request

### Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |
| `x-api-key` | Your API key | Yes |

### Body Schema

```json
{
  "repo": "string (required)",
  "spec_path": "string (required)",
  "new_spec_yaml": "string (required)",
  "commit_message": "string (optional)"
}
```

#### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo` | string | Yes | Repository in format `owner/name`. Must be in ALLOWED_REPOS whitelist. |
| `spec_path` | string | Yes | Path to spec file in repository (e.g., `specs/my-app.yml`) |
| `new_spec_yaml` | string | Yes | New spec content as YAML string with escaped newlines |
| `commit_message` | string | No | Custom commit message (default: "Update ActionSpec configuration") |

### Example Request

```bash
curl -X POST "https://abc123.execute-api.us-west-2.amazonaws.com/demo/spec/apply" \
  -H "x-api-key: abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "trakrf/action-spec",
    "spec_path": "specs/examples/my-app.yml",
    "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: my-app\n  description: My application\nspec:\n  type: StaticSite\n  compute:\n    size: demo\n  security:\n    waf:\n      enabled: true\n",
    "commit_message": "Enable WAF protection"
  }'
```

### YAML Escaping Example

**Original YAML**:
```yaml
apiVersion: actionspec/v1
metadata:
  name: my-app
spec:
  type: StaticSite
```

**Escaped for JSON** (using `jq`):
```bash
# Convert YAML file to escaped JSON string
cat my-spec.yml | jq -Rs .
```

**Result**:
```json
"apiVersion: actionspec/v1\nmetadata:\n  name: my-app\nspec:\n  type: StaticSite\n"
```

---

## Response

### Success Response (200 OK)

Indicates PR was created successfully.

```json
{
  "success": true,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_number": 123,
  "branch_name": "action-spec-update-1699999999",
  "warnings": [
    {
      "severity": "warning",
      "message": "⚠️ WARNING: Disabling WAF will remove security protection",
      "field_path": "spec.security.waf.enabled"
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` for successful responses |
| `pr_url` | string | GitHub UI URL for the created pull request |
| `pr_number` | integer | Pull request number |
| `branch_name` | string | Name of created branch (format: `action-spec-update-{timestamp}`) |
| `warnings` | array | Array of destructive change warnings (may be empty) |

#### Warning Object Structure

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `severity` | string | `"info"`, `"warning"`, `"critical"` | Severity level of the warning |
| `message` | string | - | Human-readable warning message with emoji prefix |
| `field_path` | string | - | JSON path to changed field (e.g., `spec.security.waf.enabled`) |

#### Severity Levels

| Severity | Emoji | Use Case | Example |
|----------|-------|----------|---------|
| `info` | ℹ️ | Non-breaking informational changes | Configuration updates with no risk |
| `warning` | ⚠️ | Changes with moderate risk | Disabling security features, downgrading resources |
| `critical` | 🔴 | Changes requiring manual intervention | Database engine changes, data migrations |

### Example Success Response with Multiple Warnings

```json
{
  "success": true,
  "pr_url": "https://github.com/trakrf/action-spec/pull/45",
  "pr_number": 45,
  "branch_name": "action-spec-update-1730000000",
  "warnings": [
    {
      "severity": "warning",
      "message": "⚠️ WARNING: Disabling WAF will remove security protection",
      "field_path": "spec.security.waf.enabled"
    },
    {
      "severity": "warning",
      "message": "⚠️ WARNING: Downsizing compute may impact performance",
      "field_path": "spec.compute.size"
    }
  ]
}
```

### Example Success Response with No Warnings

```json
{
  "success": true,
  "pr_url": "https://github.com/trakrf/action-spec/pull/46",
  "pr_number": 46,
  "branch_name": "action-spec-update-1730000001",
  "warnings": []
}
```

---

## Error Responses

All error responses follow this structure:

```json
{
  "success": false,
  "error": "string (error type)",
  "details": "string (specific error message)"
}
```

### 400 Bad Request - Validation Error

**Cause**: Invalid YAML or spec doesn't match ActionSpec schema

```json
{
  "success": false,
  "error": "Validation failed",
  "details": "Missing required field: metadata.name"
}
```

**Common Causes**:
- Missing required fields (`apiVersion`, `metadata.name`, `spec.type`)
- Invalid YAML syntax
- Unsupported values (e.g., invalid `spec.type`)

**Resolution**:
1. Validate YAML syntax: `yamllint your-spec.yml`
2. Check all required fields present
3. Verify against ActionSpec schema

---

### 404 Not Found - Spec File Missing

**Cause**: `spec_path` doesn't exist in repository

```json
{
  "success": false,
  "error": "Spec file not found",
  "details": "File 'specs/missing.yml' not found in trakrf/action-spec"
}
```

**Resolution**:
1. Verify `spec_path` is correct
2. Check file exists in repository
3. Ensure path is relative to repository root

---

### 409 Conflict - PR Already Exists

**Cause**: A PR already exists for the generated branch name (rare)

```json
{
  "success": false,
  "error": "Pull request already exists",
  "details": "A PR already exists for branch 'action-spec-update-123'"
}
```

**Resolution**:
- Retry request (new timestamp will be generated)
- This is extremely rare due to timestamp-based branch names

---

### 502 Bad Gateway - GitHub API Error

**Cause**: GitHub API failure (rate limit, permissions, network issues)

```json
{
  "success": false,
  "error": "GitHub API error",
  "details": "Rate limit exceeded"
}
```

**Common Causes**:
- GitHub API rate limit exceeded (5000 requests/hour)
- Invalid GitHub token or expired PAT
- Network issues between Lambda and GitHub
- Repository not in ALLOWED_REPOS whitelist

**Resolution**:
1. Check GitHub API status: https://www.githubstatus.com/
2. Verify PAT is valid and not expired
3. Wait for rate limit reset (included in error details)
4. Check repository is in ALLOWED_REPOS

---

### 500 Internal Server Error

**Cause**: Unexpected Lambda error

```json
{
  "success": false,
  "error": "Internal server error",
  "details": "Unexpected error message"
}
```

**Resolution**:
1. Check CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/actionspec-spec-applier --follow
   ```
2. Report issue with request details
3. Retry after checking logs

---

## Frontend Integration Guide

### React/TypeScript Example

**Type Definitions**:

```typescript
// Request type
interface SpecApplyRequest {
  repo: string;
  spec_path: string;
  new_spec_yaml: string;
  commit_message?: string;
}

// Response type
interface SpecApplyResponse {
  success: boolean;
  pr_url?: string;
  pr_number?: number;
  branch_name?: string;
  warnings?: SpecWarning[];
  error?: string;
  details?: string;
}

// Warning object
interface SpecWarning {
  severity: 'info' | 'warning' | 'critical';
  message: string;
  field_path: string;
}
```

**API Client Implementation**:

```typescript
const API_URL = process.env.REACT_APP_API_URL;
const API_KEY = process.env.REACT_APP_API_KEY;

async function applySpec(
  request: SpecApplyRequest
): Promise<SpecApplyResponse> {
  const response = await fetch(`${API_URL}/spec/apply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY || '',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    // Handle HTTP errors
    const errorBody = await response.json();
    throw new Error(errorBody.details || errorBody.error || 'Request failed');
  }

  return response.json();
}
```

**Usage Example**:

```typescript
import { useState } from 'react';

function SpecApplier() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SpecApplyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleApplySpec = async (yamlContent: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await applySpec({
        repo: 'trakrf/action-spec',
        spec_path: 'specs/my-app.yml',
        new_spec_yaml: yamlContent,
        commit_message: 'Update configuration via UI',
      });

      setResult(response);

      // Show success message
      if (response.success) {
        console.log(`PR created: ${response.pr_url}`);

        // Display warnings if any
        if (response.warnings && response.warnings.length > 0) {
          response.warnings.forEach((warning) => {
            console.warn(`${warning.severity}: ${warning.message}`);
          });
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={() => handleApplySpec('...')} disabled={loading}>
        {loading ? 'Creating PR...' : 'Apply Spec'}
      </button>

      {error && <div className="error">{error}</div>}

      {result?.success && (
        <div className="success">
          <p>PR created: <a href={result.pr_url}>{result.pr_url}</a></p>
          {result.warnings && result.warnings.length > 0 && (
            <div className="warnings">
              <h3>Warnings:</h3>
              <ul>
                {result.warnings.map((w, i) => (
                  <li key={i} className={`severity-${w.severity}`}>
                    {w.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

**Error Handling Best Practices**:

```typescript
async function applySpecWithRetry(
  request: SpecApplyRequest,
  maxRetries = 3
): Promise<SpecApplyResponse> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await applySpec(request);
    } catch (error) {
      // Don't retry on validation errors (400)
      if (error instanceof Error && error.message.includes('Validation failed')) {
        throw error;
      }

      // Retry on network errors or 502
      if (attempt === maxRetries) {
        throw error;
      }

      // Exponential backoff
      await new Promise((resolve) => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
    }
  }

  throw new Error('Max retries exceeded');
}
```

---

## Rate Limiting

### API Gateway Limits
- Default: No explicit rate limiting configured
- Can be configured per API key if needed
- Contact administrator for rate limit adjustments

### GitHub API Limits
- **Authenticated requests**: 5,000 requests/hour
- **Rate limit shared** across all spec-applier operations
- Rate limit status included in 502 error responses

**Checking Rate Limit**:
```bash
# Via GitHub API directly
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

**Best Practices**:
- Implement exponential backoff on 502 errors
- Cache spec validation results when possible
- Batch spec changes when applicable

---

## Security

### Repository Whitelist
- Only repositories in `ALLOWED_REPOS` can be modified
- Whitelist configured in Lambda environment variables
- Unauthorized repositories return 502 error from GitHub API

**Current Default**:
```
trakrf/action-spec
```

**Adding Repositories**:
Update `template.yaml`:
```yaml
Environment:
  Variables:
    ALLOWED_REPOS: "owner1/repo1,owner2/repo2"
```

### API Key Security
- Store API keys securely (environment variables, secrets manager)
- Rotate keys periodically
- Never commit keys to version control
- Use separate keys for dev/staging/prod

### GitHub Token Security
- Stored in AWS SSM Parameter Store (encrypted)
- Lambda retrieves via IAM role (no hardcoded credentials)
- Token requires `repo` scope for PR creation
- Tokens expire (recommend 90-day rotation)

---

## Testing the API

### Quick Test (curl)

```bash
# Set variables
export API_URL="https://xxxxx.execute-api.us-west-2.amazonaws.com/demo"
export API_KEY="your-api-key-here"

# Test with safe change
curl -X POST "$API_URL/spec/apply" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "trakrf/action-spec",
    "spec_path": "specs/examples/test.yml",
    "new_spec_yaml": "apiVersion: actionspec/v1\nmetadata:\n  name: test\nspec:\n  type: StaticSite\n",
    "commit_message": "Test API"
  }' | jq '.'
```

### Integration Test Script

Run comprehensive tests:
```bash
./scripts/test-spec-applier-integration.sh
```

See: `scripts/test-spec-applier-integration.sh` and `spec/3.3.4/MANUAL_TESTS.md`

---

## Troubleshooting

### Issue: 403 Forbidden
**Symptoms**: All requests return 403
**Cause**: Invalid or missing API key
**Solution**:
```bash
# Verify API key
aws apigateway get-api-keys --query 'items[?name==`actionspec-backend-api-key`]'
```

### Issue: PR not created (502)
**Symptoms**: 502 error with GitHub API message
**Causes**:
- GitHub PAT expired or invalid
- Repository not in ALLOWED_REPOS
- GitHub API rate limit exceeded

**Solution**:
```bash
# Check Lambda logs
aws logs tail /aws/lambda/actionspec-spec-applier --follow

# Verify GitHub token
aws ssm get-parameter --name /actionspec/github-token --with-decryption

# Test token directly
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

### Issue: Warnings not detected
**Symptoms**: Response shows no warnings for destructive change
**Cause**: Warning detection logic incomplete for specific field
**Solution**:
- Check Lambda logs for warning detection logic
- Verify field path matches detection rules
- Report missing detection rules as enhancement

---

## Changelog

### Version 1.0 (Phase 3.3.4)
- Initial release
- POST `/spec/apply` endpoint
- Destructive change detection (WAF, compute, database)
- PR creation with warnings
- API key authentication

---

## Support

**Documentation**: See `spec/3.3.4/` and `docs/`
**Integration Tests**: `scripts/test-spec-applier-integration.sh`
**Manual Tests**: `spec/3.3.4/MANUAL_TESTS.md`
**CloudWatch Logs**: `/aws/lambda/actionspec-spec-applier`

For issues or feature requests, contact the development team.
