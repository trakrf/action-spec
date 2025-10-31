# Spec: Production Dockerfile + Secrets Manager Integration

**Status**: Active
**Linear Issue**: [D2A-29](https://linear.app/trakrf/issue/D2A-29)
**Branch**: `feature/active-dockerfile-secrets-manager`
**Estimate**: 45 minutes

---

## Objective

Create a production-ready multi-stage Docker image that:
1. Builds the Vue 3 frontend
2. Serves it via Flask backend with Gunicorn
3. Fetches GitHub token from AWS Secrets Manager at runtime
4. Provides health check endpoint for App Runner

---

## Context

### Current State
- ✅ Vue 3 SPA frontend built with Vite
- ✅ Flask REST API backend
- ✅ Docker Compose for local development
- ❌ No production Dockerfile
- ❌ GitHub token hardcoded in environment
- ❌ No health check endpoint

### Why This Matters
- **Security**: GitHub token needs to be in Secrets Manager, not environment variables
- **Production Ready**: Gunicorn instead of Flask dev server
- **App Runner**: Requires health check endpoint and proper container setup
- **Single Artifact**: Multi-stage build creates one production image

---

## Success Criteria

### Must Have
1. Multi-stage Dockerfile builds successfully
2. GitHub token fetched from Secrets Manager on startup
3. `/health` endpoint returns 200 OK
4. Vue production build served by Flask
5. Container runs on port 8080
6. `.dockerignore` excludes development files
7. Gunicorn runs Flask in production mode

### Nice to Have
- Health check includes dependency status (AWS connectivity)
- Graceful degradation if Secrets Manager unavailable
- Build caching optimized for layers

---

## Technical Specification

### 1. Multi-Stage Dockerfile

**Location**: `/Dockerfile` (root of repo - NEW FILE)

**Note**: This is separate from the existing `backend/Dockerfile` and `frontend/Dockerfile` which are for local development. This production Dockerfile combines both into a single container for App Runner.

```dockerfile
# Stage 1: Build Vue frontend
FROM node:22 AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json frontend/pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

# Stage 2: Python runtime
FROM python:3.14-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn boto3

# Copy backend code
COPY backend/ ./backend/

# Copy Vue build from stage 1
COPY --from=frontend-builder /app/frontend/dist ./backend/static/

# Environment variables (defaults, override at runtime)
ENV FLASK_ENV=production \
    PORT=8080 \
    AWS_REGION=us-east-1 \
    SECRET_NAME=mediaco/github-token

# Expose port
EXPOSE 8080

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "backend.app:app"]
```

### 2. .dockerignore

**Location**: `/.dockerignore` (root of repo)

```
# Git
.git
.gitignore

# Node
node_modules
frontend/node_modules
frontend/dist
frontend/.vite

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
backend/__pycache__
*.egg-info
.pytest_cache
.coverage

# Development
.env
.env.local
docker-compose.yml
*.md
.vscode
.idea

# Tests
frontend/test-results
frontend/playwright-report
backend/tests

# Terraform
infra/
overengineered/
```

### 3. Secrets Manager Integration

**Update**: `backend/app.py`

Add at the top of the file (after imports):

```python
import os
import boto3
from botocore.exceptions import ClientError

def get_github_token():
    """
    Fetch GitHub token from AWS Secrets Manager.
    Falls back to environment variable for local development.
    """
    # Local development fallback
    if os.environ.get('FLASK_ENV') == 'development':
        return os.environ.get('GITHUB_TOKEN', '')

    # Production: fetch from Secrets Manager
    secret_name = os.environ.get('SECRET_NAME', 'mediaco/github-token')
    region_name = os.environ.get('AWS_REGION', 'us-east-1')

    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']

    except ClientError as e:
        logger.error(f"Failed to fetch secret from Secrets Manager: {e}")
        raise RuntimeError("Cannot start without GitHub token")

# Initialize GitHub token at startup
GITHUB_TOKEN = get_github_token()
logger.info("GitHub token loaded successfully")
```

**Replace existing token usage**:
```python
# OLD: headers = {"Authorization": f"token {os.environ.get('GITHUB_TOKEN')}"}
# NEW:
headers = {"Authorization": f"token {GITHUB_TOKEN}"}
```

### 4. Health Check Endpoint

**Update**: `backend/app.py`

Add before the SPA catch-all route:

```python
@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for App Runner.
    Returns 200 if service is healthy, 503 if not.
    """
    try:
        # Basic health: app is running
        health_status = {
            "status": "healthy",
            "service": "action-spec",
            "version": "1.0.0"
        }

        # Optional: Check AWS connectivity (don't fail on this)
        try:
            boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
            health_status["aws_connectivity"] = "ok"
        except Exception as aws_err:
            logger.warning(f"AWS connectivity check failed: {aws_err}")
            health_status["aws_connectivity"] = "degraded"

        return jsonify(health_status), 200

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": "Service unavailable"
        }), 503
```

### 5. Requirements Update

**Update**: `backend/requirements.txt`

Add:
```
gunicorn==21.2.0
boto3==1.34.0
```

### 6. IAM Permissions Documentation

**Create**: `docs/IAM_PERMISSIONS.md`

```markdown
# IAM Permissions for App Runner

The App Runner service role needs these permissions:

## Secrets Manager Read

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:mediaco/github-token-*"
    }
  ]
}
```

## CloudWatch Logs Write

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/aws/apprunner/*"
    }
  ]
}
```
```

---

## Testing Plan

### Local Testing (Without Secrets Manager)

```bash
# Set development mode
export FLASK_ENV=development
export GITHUB_TOKEN=ghp_your_token_here

# Build image
docker build -t action-spec:dev .

# Run container
docker run -p 8080:8080 \
  -e FLASK_ENV=development \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  action-spec:dev

# Test health endpoint
curl http://localhost:8080/health

# Test app
open http://localhost:8080
```

### Local Testing (With Secrets Manager)

```bash
# Create test secret (one time)
aws secretsmanager create-secret \
  --name mediaco/github-token \
  --secret-string "ghp_your_token_here" \
  --region us-east-1

# Build image
docker build -t action-spec:prod .

# Run with AWS credentials
docker run -p 8080:8080 \
  -e AWS_REGION=us-east-1 \
  -e SECRET_NAME=mediaco/github-token \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  action-spec:prod

# Test health endpoint
curl http://localhost:8080/health
```

### Validation Checklist

- [ ] Docker build completes without errors
- [ ] Image size is reasonable (<500MB)
- [ ] Container starts successfully
- [ ] Health endpoint returns 200
- [ ] Vue app loads in browser
- [ ] Can fetch blueprint from GitHub
- [ ] Can list AWS resources (subnets, AMIs, snapshots)
- [ ] Can trigger workflow dispatch
- [ ] Logs show Gunicorn workers
- [ ] No secrets in container environment variables

---

## Implementation Notes

### Build Order
1. Create `.dockerignore` first
2. Update `requirements.txt` with gunicorn and boto3
3. Add Secrets Manager integration to `app.py`
4. Add `/health` endpoint to `app.py`
5. Create root `Dockerfile`
6. Test build locally
7. Test with dev environment variables
8. Test with Secrets Manager (if available)
9. Document IAM permissions

### Edge Cases
- **Secrets Manager unavailable**: Fail fast with clear error message
- **Invalid token format**: Validate token format before use
- **Port conflicts**: Ensure 8080 is exposed and bound correctly
- **Vue build missing**: Verify frontend build copied to correct location

### Security Considerations
- ✅ Token never in Dockerfile or image layers
- ✅ Token fetched at runtime from Secrets Manager
- ✅ IAM role permissions scoped to specific secret
- ✅ Production mode disables Flask debug
- ✅ Gunicorn runs with limited workers (resource constraint)

---

## Acceptance Criteria

### Definition of Done
- [ ] Dockerfile builds successfully
- [ ] Container runs on port 8080
- [ ] `/health` returns 200 OK
- [ ] GitHub token fetched from Secrets Manager
- [ ] Vue app accessible at root path
- [ ] All API endpoints working
- [ ] IAM permissions documented
- [ ] `.dockerignore` excludes dev files
- [ ] Local testing validated (both modes)
- [ ] PR merged to main

### Demo Script
```bash
# 1. Show the Dockerfile
cat Dockerfile

# 2. Build the image
docker build -t action-spec .

# 3. Run the container
docker run -d -p 8080:8080 --name action-spec-test \
  -e FLASK_ENV=development \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  action-spec

# 4. Check health
curl http://localhost:8080/health

# 5. Open in browser
open http://localhost:8080

# 6. Show logs
docker logs action-spec-test

# 7. Cleanup
docker stop action-spec-test && docker rm action-spec-test
```

---

## Dependencies

- **Blocks**: D2A-30 (App Runner deployment)
- **Blocked By**: None
- **Related**: D2A-17 (repo refactoring), D2A-28 (Vue migration)

---

## Notes

- Using Node 22 and Python 3.14 as specified
- Multi-stage build keeps final image size small
- Gunicorn with 2 workers for App Runner's resource limits
- Health check is simple but extensible
- Secrets Manager integration is production-only (dev uses env vars)
