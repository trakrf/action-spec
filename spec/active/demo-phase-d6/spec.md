# Feature: Docker Packaging & Deployment (Demo Phase D6)

## Origin
Phases D1-D5 delivered a working Flask spec-editor application that can read specs from GitHub, render forms, and trigger workflow_dispatch to deploy infrastructure. The app currently runs locally with `flask run` for development. Phase D6 packages the application in Docker containers for production deployment on EC2.

## Outcome
A containerized spec-editor application that:
- Runs in Docker on EC2 with docker-compose
- Automatically builds and publishes to ghcr.io on push to main
- Includes both spec-editor and demo-app services
- Uses environment variables for configuration (no hardcoded secrets)
- Provides health checks and graceful restarts
- Can be deployed via Ansible/Portainer or manually with docker-compose

**Shippable**: Yes - delivers production-ready deployment of the spec-editor demo.

## User Story
**As a** DevOps engineer
**I want** the spec-editor packaged as Docker containers
**So that** I can deploy it consistently to EC2 without managing Python dependencies

**As a** demo presenter
**I want** the spec-editor and demo app running together
**So that** I can show the full end-to-end workflow from one URL

**As a** developer
**I want** automated Docker image builds on every merge
**So that** deployments always use the latest tested code

## Context

**Discovery**:
- D1-D5 prove the application works (end-to-end tested in D5B)
- Flask app requires Python 3.12, Flask, PyGithub, PyYAML
- Needs GitHub token (GH_TOKEN) and repo path (GH_REPO) at runtime
- Health check endpoint exists at /health for monitoring

**Current State** (after D5):
- Flask app runs locally: `cd demo/backend && flask run`
- Manual dependency management: `pip install -r requirements.txt`
- Environment variables set manually in shell
- No production deployment method
- No CI/CD for building images

**Desired State**:
- Dockerfile packages Flask app with all dependencies
- docker-compose.yml orchestrates spec-editor + demo-app
- GitHub Action builds and publishes to ghcr.io on merge
- Simple EC2 deployment: `docker-compose up -d`
- Environment variables passed via .env file or docker-compose
- Health checks for container orchestration

## Technical Requirements

### 1. Dockerfile for spec-editor

**Create `demo/backend/Dockerfile`**:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY templates/ templates/

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Run Flask with production server (gunicorn)
CMD ["python", "app.py"]
```

**Requirements**:
- Based on `python:3.12-slim` (matches current development)
- Installs from requirements.txt (Flask, PyGithub, PyYAML)
- Copies app.py and templates/
- Exposes port 5000
- Health check using /health endpoint
- Runs Flask directly (or gunicorn if added to requirements.txt)

**Note**: Flask's built-in server is acceptable for demo MVP. For production hardening, consider adding gunicorn:
```txt
# requirements.txt
Flask==3.0.0
PyGithub==2.1.1
PyYAML==6.0.1
gunicorn==21.2.0  # Optional for production
```

### 2. docker-compose.yml

**Create `demo/docker-compose.yml`**:

```yaml
version: '3.8'

services:
  spec-editor:
    build:
      context: ./backend
      dockerfile: Dockerfile
    image: ghcr.io/trakrf/spec-editor:latest
    container_name: spec-editor
    ports:
      - "5000:5000"
    environment:
      - GH_TOKEN=${GH_TOKEN}
      - GH_REPO=${GH_REPO:-trakrf/action-spec}
      - SPECS_PATH=${SPECS_PATH:-demo/infra}
      - WORKFLOW_BRANCH=${WORKFLOW_BRANCH:-main}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s

  demo-app:
    image: mendhak/http-https-echo:latest
    container_name: demo-app
    ports:
      - "8080:8080"
    restart: unless-stopped
    environment:
      - HTTP_PORT=8080
```

**Services**:
- **spec-editor**: Flask app (builds from ./backend/Dockerfile)
  - Port 5000 exposed
  - Environment variables for GitHub integration
  - Health check via /health endpoint
  - Auto-restart on failure

- **demo-app**: Simple HTTP echo server for testing
  - Port 8080 exposed
  - Shows request details (useful for WAF demo)
  - Same image used in EC2 user_data scripts

**Environment Variable Configuration**:
Users provide via `.env` file:
```bash
# demo/.env (not committed to git)
GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GH_REPO=trakrf/action-spec
SPECS_PATH=demo/infra
WORKFLOW_BRANCH=main
```

### 3. GitHub Action - Build and Publish

**Create `.github/workflows/build-spec-editor.yml`**:

```yaml
name: Build Spec-Editor

on:
  push:
    branches: [ main ]
    paths:
      - 'demo/backend/**'
      - 'demo/docker-compose.yml'
      - '.github/workflows/build-spec-editor.yml'
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository_owner }}/spec-editor

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata (tags, labels)
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest
            type=sha,prefix={{branch}}-

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./demo/backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

**Behavior**:
- Triggers on push to main when demo/backend/** changes
- Builds Docker image from demo/backend/Dockerfile
- Pushes to ghcr.io/trakrf/spec-editor:latest
- Tags with both `latest` and `main-<sha>` for rollback capability
- Uses GITHUB_TOKEN (automatically provided, no manual setup)

**Image URL**: `ghcr.io/trakrf/spec-editor:latest`

### 4. Update .gitignore

**Add to `.gitignore`**:
```
# Docker environment files
demo/.env
demo/backend/.env

# Docker volumes
demo/data/
```

Prevents accidental commit of GitHub tokens.

### 5. Deployment Documentation

**Create `demo/DEPLOY.md`**:

```markdown
# Spec-Editor Deployment Guide

## Prerequisites
- Docker Engine installed (via `get.docker.com` script)
- Docker Compose installed (included with Docker Engine)
- GitHub Personal Access Token with `repo` and `workflow` scopes

## Local Deployment

1. **Clone repository**:
   ```bash
   git clone https://github.com/trakrf/action-spec.git
   cd action-spec/demo
   ```

2. **Create environment file**:
   ```bash
   cat > .env <<EOF
   GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   GH_REPO=trakrf/action-spec
   SPECS_PATH=demo/infra
   WORKFLOW_BRANCH=main
   EOF
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Verify health**:
   ```bash
   curl http://localhost:5000/health
   # Should return: {"status": "healthy", ...}
   ```

5. **Access UI**:
   - Spec-editor: http://localhost:5000
   - Demo app: http://localhost:8080

## EC2 Deployment

### Option A: Manual (Quick)

1. **Install Docker on EC2**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   # Log out and back in for group to take effect
   ```

2. **Deploy compose file**:
   ```bash
   mkdir -p ~/spec-editor
   cd ~/spec-editor

   # Download compose file
   curl -O https://raw.githubusercontent.com/trakrf/action-spec/main/demo/docker-compose.yml

   # Create .env file
   nano .env
   # Paste GH_TOKEN and other vars

   # Start services
   docker-compose up -d
   ```

3. **Access via EC2 public IP**:
   - http://ec2-xx-xx-xx-xx.compute.amazonaws.com:5000

### Option B: Ansible (Recommended for multiple hosts)

TODO: Create Ansible playbook in Phase D7 if needed for multi-host demo.

## Monitoring

**Check logs**:
```bash
docker-compose logs -f spec-editor
docker-compose logs -f demo-app
```

**Check health**:
```bash
docker ps  # Should show both containers healthy
curl http://localhost:5000/health
```

**Restart services**:
```bash
docker-compose restart spec-editor
```

## Updates

**Pull latest image**:
```bash
docker-compose pull
docker-compose up -d
```

## Troubleshooting

**Container won't start**:
- Check logs: `docker-compose logs spec-editor`
- Verify .env file has GH_TOKEN
- Test token: `curl -H "Authorization: token $GH_TOKEN" https://api.github.com/user`

**Health check failing**:
- Check Flask app logs
- Verify GitHub connectivity: `curl https://api.github.com/repos/trakrf/action-spec`
- Check rate limits: Visit /health endpoint in browser

**Port conflicts**:
- Change ports in docker-compose.yml if 5000 or 8080 are in use
```

## Implementation Punch List

### Docker Packaging (3 tasks)
- [ ] Create `demo/backend/Dockerfile` with Python 3.12-slim base
- [ ] Test local build: `docker build -t spec-editor demo/backend/`
- [ ] Test local run: `docker run -p 5000:5000 -e GH_TOKEN=... spec-editor`

### Docker Compose (3 tasks)
- [ ] Create `demo/docker-compose.yml` with spec-editor and demo-app
- [ ] Create `.env.example` template (without real token)
- [ ] Test compose: `docker-compose up -d && curl http://localhost:5000/health`

### GitHub Action (3 tasks)
- [ ] Create `.github/workflows/build-spec-editor.yml`
- [ ] Configure GHCR permissions (public read for image)
- [ ] Test build: Merge to main, verify image at ghcr.io

### Documentation (2 tasks)
- [ ] Create `demo/DEPLOY.md` with deployment instructions
- [ ] Update `.gitignore` to exclude .env files

### Testing (4 tasks)
- [ ] Local: docker-compose up, access http://localhost:5000
- [ ] Local: Submit form, verify workflow triggers
- [ ] GHCR: Pull published image, verify it works
- [ ] EC2 (optional): Deploy to EC2, access via public IP

**Total: 15 tasks**

## Validation Criteria

**Must Pass Before Shipping D6**:

**Local Docker**:
- [ ] `docker build` succeeds without errors
- [ ] Image size reasonable (< 500 MB)
- [ ] Container starts and passes health check
- [ ] Flask app accessible on port 5000
- [ ] Can list pods, view forms, submit deployments

**Docker Compose**:
- [ ] `docker-compose up -d` starts both services
- [ ] spec-editor shows healthy status
- [ ] demo-app responds on port 8080
- [ ] Environment variables passed correctly
- [ ] Can submit form and trigger workflow

**GitHub Action**:
- [ ] Action triggers on push to main
- [ ] Docker build succeeds
- [ ] Image pushed to ghcr.io successfully
- [ ] Image tagged with both `latest` and `main-<sha>`
- [ ] Published image is publicly pullable

**Deployment**:
- [ ] Can pull image: `docker pull ghcr.io/trakrf/spec-editor:latest`
- [ ] Can deploy on fresh EC2 with just docker-compose.yml and .env
- [ ] Health check endpoint returns 200
- [ ] UI loads correctly via EC2 public IP
- [ ] All D5 functionality works in containerized environment

## Success Metrics

**Quantitative**:
- Docker image build time < 2 minutes
- Image size < 500 MB (Python 3.12-slim + Flask stack)
- Container startup time < 10 seconds
- Health check passes within 10 seconds
- Zero environment variable leaks (no tokens in logs)

**Qualitative**:
- One-command deployment (`docker-compose up -d`)
- No manual dependency management
- Automated CI/CD (merge → build → publish)
- Easy rollback via tagged images
- Clear deployment documentation

**Customer Value**:
- Consistent deployment across environments
- No Python version conflicts
- Fast deployment (docker-compose vs manual setup)
- Automated image updates on merge
- Production-ready packaging

## Dependencies

**Blocked By**:
- D5 must be complete (workflow_dispatch integration) ✅
- Flask app must have /health endpoint ✅
- requirements.txt must be current ✅

**Blocks**:
- D7 (Integration Testing & Scale to 9 Pods) - needs deployed app

**Requires**:
- Docker Engine 20.10+ (for BuildKit features)
- GitHub Container Registry access
- EC2 with port 5000 accessible (or reverse proxy)

## Constraints

**Docker Image Size**:
- Base: python:3.12-slim (~150 MB)
- Dependencies: ~50 MB (Flask, PyGithub, PyYAML)
- Application: ~1 MB (app.py + templates)
- **Target**: < 500 MB total

**Environment Variables**:
- GH_TOKEN: Required (GitHub PAT with repo + workflow scopes)
- GH_REPO: Optional (defaults to trakrf/action-spec)
- SPECS_PATH: Optional (defaults to demo/infra)
- WORKFLOW_BRANCH: Optional (defaults to main)

**Port Requirements**:
- 5000: spec-editor Flask app
- 8080: demo-app HTTP echo server
- Both must be available or remapped in docker-compose.yml

**Scope Boundaries**:
- No Kubernetes/orchestration (EC2 + docker-compose only)
- No secrets management (uses .env file)
- No TLS/HTTPS (behind reverse proxy if needed)
- No multi-stage builds (simple single-stage for clarity)

## Edge Cases Handled

**Docker Build**:
1. Missing requirements.txt → Build fails with clear error
2. Invalid Dockerfile syntax → docker build fails at parse time
3. Python version mismatch → Explicitly use python:3.12-slim

**Docker Compose**:
1. Missing .env file → Services start but Flask returns 500 (no token)
2. Invalid GH_TOKEN → Health check shows GitHub API error
3. Port conflicts → docker-compose fails with port binding error

**GitHub Action**:
1. GITHUB_TOKEN expired → Action fails, use default GITHUB_TOKEN
2. Image push fails → Action fails, check GHCR permissions
3. Dockerfile changes outside demo/backend/ → Action skips build (paths filter)

**Deployment**:
1. EC2 port 5000 blocked → Health check fails, update security group
2. Out of memory → Container crashes, check EC2 instance size (min t3.small)
3. GitHub rate limit → /health endpoint shows rate limit error

## Next Steps After D6

1. **Ship D6** - Docker packaging complete
2. **Verify Deployment** - Test on EC2 with docker-compose
3. **Phase D7** - Scale to 9 pods and integration testing
4. **Demo Preparation** - Practice walkthrough with containerized app

## Out of Scope (Future Enhancements)

**Production Hardening** (defer to post-demo):
- Multi-stage Docker builds (builder + runtime stages)
- Gunicorn WSGI server (currently using Flask dev server)
- NGINX reverse proxy with TLS termination
- Secret management via AWS Secrets Manager
- Horizontal scaling with load balancer
- Container orchestration (ECS, EKS, Nomad)

**CI/CD Improvements** (defer to production):
- Image vulnerability scanning (Trivy, Snyk)
- Automated tests in Docker build
- Staging deployment before production
- Rollback automation
- Blue/green deployments

**Monitoring** (defer to production):
- Prometheus metrics export
- CloudWatch Logs integration
- Distributed tracing (OpenTelemetry)
- Uptime monitoring (UptimeRobot, Pingdom)
- Performance profiling

---

**Specification Status**: Ready for Planning
**Estimated Effort**: 1-2 hours
**Target PR Size**: ~150 LoC (3 new files: Dockerfile, docker-compose.yml, build-spec-editor.yml, plus DEPLOY.md)
**Complexity**: 3/10 (Low - standard Docker packaging)
