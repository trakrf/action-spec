# Implementation Plan: Docker Packaging & Deployment (Demo Phase D6)
Generated: 2025-01-24
Specification: spec.md

## Understanding

Phase D6 packages the working Flask spec-editor application (completed in D1-D5) into Docker containers for production deployment. The application currently runs locally with `flask run` and needs containerization for consistent EC2 deployment.

**Key Requirements**:
- Dockerfile for Flask app (python:3.12-slim base)
- docker-compose.yml with spec-editor + demo-app services
- GitHub Action for automated image builds on merge to main
- Environment variable configuration via .env file
- Deployment documentation

**User Decisions from Clarifying Questions**:
1. Use Flask built-in server (not gunicorn) for simplicity
2. Include commented-out volume mounts for dev workflow
3. Auto-trigger only on push to main (no workflow_dispatch - YAGNI)
4. .env.example with working values where safe + detailed generation comments

## Relevant Files

**Reference Patterns** (existing code to follow):
- `.github/workflows/deploy-pod.yml` (lines 1-50) - GitHub Actions workflow structure, uses `actions/checkout@v5`
- `demo/backend/app.py` (lines 28-31) - Environment variable configuration pattern
- `demo/backend/app.py` (lines 520-521) - Flask app startup: `app.run(debug=True, host='0.0.0.0', port=5000)`
- `demo/backend/requirements.txt` - Dependencies: flask==3.0.0, PyGithub==2.1.1, pyyaml==6.0.1, gunicorn==21.2.0

**Files to Create**:
- `demo/backend/Dockerfile` - Python 3.12-slim container with Flask app
- `demo/docker-compose.yml` - Orchestrates spec-editor + demo-app services
- `demo/.env.example` - Environment variable template with examples and comments
- `.github/workflows/build-spec-editor.yml` - CI/CD for Docker image builds
- `demo/DEPLOY.md` - Deployment guide for local and EC2

**Files to Modify**:
- `.gitignore` (if needed) - Verify .env exclusion (already present at line 24)

## Architecture Impact

- **Subsystems affected**: Docker/Containerization, GitHub Actions CI/CD
- **New dependencies**: None (uses existing Flask stack)
- **Breaking changes**: None (additive packaging only)

## Task Breakdown

### Task 1: Create Dockerfile
**File**: `demo/backend/Dockerfile`
**Action**: CREATE
**Pattern**: Standard Python container pattern

**Implementation**:
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

# Health check using /health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Run Flask (uses app.py's if __name__ == '__main__' block)
CMD ["python", "app.py"]
```

**Key Points**:
- Based on python:3.12-slim (matches local development from app.py comments)
- Copies requirements.txt first (Docker layer caching for dependencies)
- Health check uses existing /health endpoint from demo/backend/app.py:487
- Runs Flask directly via `python app.py` (app.py:520 has `app.run(debug=True, host='0.0.0.0', port=5000)`)
- Note: gunicorn is available in requirements.txt but not used per user decision

**Validation**:
```bash
cd demo/backend
docker build -t spec-editor:test .
# Should complete without errors
# Image size should be < 500 MB
```

---

### Task 2: Create docker-compose.yml
**File**: `demo/docker-compose.yml`
**Action**: CREATE
**Pattern**: Multi-service Docker Compose

**Implementation**:
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
    # Uncomment for development (live code reload)
    # volumes:
    #   - ./backend/app.py:/app/app.py
    #   - ./backend/templates:/app/templates

  demo-app:
    image: mendhak/http-https-echo:latest
    container_name: demo-app
    ports:
      - "8080:8080"
    restart: unless-stopped
    environment:
      - HTTP_PORT=8080
```

**Key Points**:
- Environment variables match app.py:28-31 pattern (GH_TOKEN, GH_REPO, SPECS_PATH, WORKFLOW_BRANCH)
- Uses image name `ghcr.io/trakrf/spec-editor:latest` for GitHub Container Registry
- Health check via /health endpoint
- Volume mounts commented out per user decision (option b - dev workflow support)
- demo-app uses same image as EC2 user_data scripts (mendhak/http-https-echo)

**Validation**:
```bash
cd demo
# Create .env file with GH_TOKEN
echo "GH_TOKEN=ghp_xxx" > .env

docker-compose up -d
# Should start both containers

docker ps
# Should show both containers healthy

curl http://localhost:5000/health
# Should return: {"status": "healthy", ...}

curl http://localhost:8080/
# Should return HTTP echo response
```

---

### Task 3: Create .env.example
**File**: `demo/.env.example`
**Action**: CREATE
**Pattern**: Environment variable template

**Implementation**:
```bash
# GitHub Personal Access Token
# Required scopes: repo, workflow
# Generate at: https://github.com/settings/tokens/new
# - Select "repo" (Full control of private repositories)
# - Select "workflow" (Update GitHub Action workflows)
# Token format: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GH_TOKEN=ghp_your_token_here

# GitHub repository (owner/repo format)
# Default: trakrf/action-spec
GH_REPO=trakrf/action-spec

# Path to specs directory within repository
# Default: demo/infra
SPECS_PATH=demo/infra

# Git branch for workflow operations
# Default: main
# Override for testing: feature/your-branch-name
WORKFLOW_BRANCH=main
```

**Key Points**:
- Working example values for GH_REPO, SPECS_PATH, WORKFLOW_BRANCH (user decision b)
- Detailed comments on how to generate GH_TOKEN (user decision c)
- Shows token format for validation
- Explains required scopes (from demo/backend/app.py functionality)

**Validation**:
```bash
cd demo
cp .env.example .env
# Edit .env with real GH_TOKEN

# Test that spec-editor starts with these values
docker-compose up -d
docker-compose logs spec-editor | grep "Successfully connected"
# Should show: "✓ Successfully connected to GitHub repo: trakrf/action-spec"
```

---

### Task 4: Create GitHub Action for Docker Builds
**File**: `.github/workflows/build-spec-editor.yml`
**Action**: CREATE
**Pattern**: Reference `.github/workflows/deploy-pod.yml` structure

**Implementation**:
```yaml
name: Build Spec-Editor

on:
  push:
    branches: [ main ]
    paths:
      - 'demo/backend/**'
      - 'demo/docker-compose.yml'
      - '.github/workflows/build-spec-editor.yml'

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
        uses: actions/checkout@v5

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
            type=sha,prefix=main-

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./demo/backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

**Key Points**:
- Triggers only on push to main (no workflow_dispatch per user decision - YAGNI)
- Paths filter: only builds when demo/backend/**, docker-compose.yml, or workflow itself changes
- Uses actions/checkout@v5 pattern from deploy-pod.yml:48
- Pushes to ghcr.io/trakrf/spec-editor with tags: `latest` and `main-<sha>`
- Uses GITHUB_TOKEN (automatically provided, no manual secrets needed)
- Permissions: packages:write for GHCR push

**Validation**:
After merging to main, check:
```bash
# Verify workflow ran
gh run list --workflow=build-spec-editor.yml

# Verify image published
docker pull ghcr.io/trakrf/spec-editor:latest

# Test pulled image
docker run -p 5000:5000 \
  -e GH_TOKEN=$GH_TOKEN \
  -e GH_REPO=trakrf/action-spec \
  ghcr.io/trakrf/spec-editor:latest

curl http://localhost:5000/health
# Should return healthy status
```

---

### Task 5: Create Deployment Documentation
**File**: `demo/DEPLOY.md`
**Action**: CREATE
**Pattern**: Deployment guide with troubleshooting

**Implementation**:
```markdown
# Spec-Editor Deployment Guide

## Prerequisites
- Docker Engine 20.10+ (install via `curl -fsSL https://get.docker.com | sh`)
- Docker Compose (included with Docker Engine)
- GitHub Personal Access Token with `repo` and `workflow` scopes

## Quick Start (Local Development)

1. **Clone repository**:
   ```bash
   git clone https://github.com/trakrf/action-spec.git
   cd action-spec/demo
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   nano .env  # Add your GH_TOKEN
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Verify health**:
   ```bash
   curl http://localhost:5000/health
   # Should return: {"status": "healthy", "github": "connected", ...}
   ```

5. **Access UI**:
   - Spec-editor: http://localhost:5000
   - Demo app: http://localhost:8080

## EC2 Deployment

### Prerequisites
- EC2 instance with public IP (t3.small minimum, t3.medium recommended)
- Security group allows inbound TCP 5000 (or 80 if using reverse proxy)
- SSH access to EC2 instance

### Deployment Steps

1. **Install Docker on EC2**:
   ```bash
   # SSH to EC2
   ssh ec2-user@your-ec2-ip

   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker ec2-user

   # Log out and back in for group to take effect
   exit
   ssh ec2-user@your-ec2-ip

   # Verify Docker
   docker --version
   ```

2. **Deploy spec-editor**:
   ```bash
   # Create deployment directory
   mkdir -p ~/spec-editor
   cd ~/spec-editor

   # Download docker-compose.yml
   curl -O https://raw.githubusercontent.com/trakrf/action-spec/main/demo/docker-compose.yml

   # Create .env file
   cat > .env <<EOF
   GH_TOKEN=ghp_your_token_here
   GH_REPO=trakrf/action-spec
   SPECS_PATH=demo/infra
   WORKFLOW_BRANCH=main
   EOF

   # Start services
   docker-compose up -d
   ```

3. **Verify deployment**:
   ```bash
   docker ps
   # Should show spec-editor and demo-app running

   curl http://localhost:5000/health
   # Should return healthy status
   ```

4. **Access via browser**:
   - Open http://your-ec2-public-ip:5000

## Development Workflow

### Enable Live Code Reload

Uncomment volume mounts in `docker-compose.yml`:
```yaml
volumes:
  - ./backend/app.py:/app/app.py
  - ./backend/templates:/app/templates
```

Restart containers:
```bash
docker-compose restart spec-editor
```

Now edits to `app.py` or templates automatically reload (Flask debug mode).

## Monitoring

**View logs**:
```bash
docker-compose logs -f spec-editor
docker-compose logs -f demo-app
```

**Check health**:
```bash
docker ps  # Should show "healthy" status
curl http://localhost:5000/health
```

**Restart services**:
```bash
docker-compose restart spec-editor
docker-compose restart demo-app
```

## Updates

**Pull latest image**:
```bash
docker-compose pull
docker-compose up -d
```

**Rebuild from source**:
```bash
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Container won't start
**Symptom**: `docker ps` shows container exited

**Debug**:
```bash
docker-compose logs spec-editor
```

**Common fixes**:
- Missing GH_TOKEN: Add to .env file
- Invalid GH_TOKEN: Generate new token at https://github.com/settings/tokens/new
- Port conflict: Change port in docker-compose.yml (5000:5000 → 8000:5000)

### Health check failing
**Symptom**: `docker ps` shows "unhealthy" status

**Debug**:
```bash
docker-compose exec spec-editor curl http://localhost:5000/health
docker-compose logs spec-editor
```

**Common fixes**:
- GitHub connectivity: Test with `curl https://api.github.com/repos/trakrf/action-spec`
- Rate limits: Check /health endpoint response for rate limit info
- Token permissions: Verify token has `repo` and `workflow` scopes

### Can't access UI from browser
**Symptom**: Connection refused when accessing http://ec2-ip:5000

**Debug**:
```bash
# Check container is running
docker ps | grep spec-editor

# Check port binding
docker port spec-editor

# Check EC2 security group
# Ensure inbound rule allows TCP 5000 from your IP
```

**Common fixes**:
- Security group: Add inbound rule for TCP 5000
- Container not running: `docker-compose up -d`
- Firewall: Check EC2 firewall settings

### "Permission denied" errors
**Symptom**: Cannot run docker commands

**Fix**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
exit
ssh ec2-user@your-ec2-ip
```

## Architecture

```
┌─────────────────────────────────┐
│  Browser                        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Docker Compose                 │
│  ┌──────────────────────────┐   │
│  │  spec-editor:5000        │   │
│  │  - Flask app             │   │
│  │  - GitHub API client     │   │
│  │  - Health check          │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  demo-app:8080           │   │
│  │  - HTTP echo server      │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

## Security Notes

- **Never commit .env files** - They contain GitHub tokens
- **.env is gitignored** - Already excluded in .gitignore
- **Token scopes**: Only grant `repo` and `workflow` (principle of least privilege)
- **Token rotation**: Regenerate tokens periodically
- **EC2 security**: Restrict port 5000 to trusted IPs only

## Production Hardening (Future)

For production deployments beyond demo, consider:
- NGINX reverse proxy with TLS termination
- Gunicorn WSGI server (already in requirements.txt)
- AWS Secrets Manager for GH_TOKEN
- CloudWatch Logs integration
- Multi-stage Docker builds (smaller images)
- Horizontal scaling with ECS/EKS
```

**Key Points**:
- Covers local development and EC2 deployment
- Troubleshooting section for common issues
- Security notes about .env files and token scopes
- Development workflow section (volume mounts)
- Architecture diagram for clarity

**Validation**:
```bash
# Follow guide end-to-end on fresh EC2 instance
# Verify all commands work
# Test troubleshooting steps
```

---

### Task 6: Verify .gitignore Coverage
**File**: `.gitignore`
**Action**: VERIFY (likely no changes needed)
**Pattern**: Check existing .env exclusion

**Implementation**:
Check that .gitignore already covers:
- `.env` (line 24)
- `.env.local` (line 25)
- `.env.*.local` (line 26)

If demo/.env is not covered, add:
```gitignore
# Docker environment files
demo/.env
demo/backend/.env
```

But existing `.env` pattern should already match `demo/.env`.

**Validation**:
```bash
# Create demo/.env file
cd demo
echo "GH_TOKEN=test" > .env

# Verify it's ignored
git status
# Should NOT show demo/.env as untracked

# Clean up test file
rm .env
```

---

### Task 7: Test Local Docker Build
**File**: N/A (testing task)
**Action**: VALIDATE
**Pattern**: Docker build workflow

**Implementation**:
```bash
cd demo/backend
docker build -t spec-editor:local .

# Verify build succeeded
docker images | grep spec-editor

# Verify image size < 500 MB
docker images spec-editor:local --format "{{.Size}}"

# Test run container
docker run --rm -d \
  -p 5000:5000 \
  -e GH_TOKEN=$GH_TOKEN \
  -e GH_REPO=trakrf/action-spec \
  --name spec-editor-test \
  spec-editor:local

# Wait for health check
sleep 15

# Test health endpoint
curl http://localhost:5000/health
# Should return: {"status": "healthy", ...}

# Test UI loads
curl -I http://localhost:5000/
# Should return: HTTP/1.1 200 OK

# Stop test container
docker stop spec-editor-test
```

**Success Criteria**:
- Build completes without errors
- Image size < 500 MB
- Container starts successfully
- Health check passes
- UI accessible on port 5000

---

### Task 8: Test Docker Compose Locally
**File**: N/A (testing task)
**Action**: VALIDATE
**Pattern**: Docker Compose workflow

**Implementation**:
```bash
cd demo

# Create .env from .env.example
cp .env.example .env
# Edit .env with real GH_TOKEN

# Start services
docker-compose up -d

# Wait for services to start
sleep 20

# Check both containers running
docker ps | grep spec-editor
docker ps | grep demo-app

# Test spec-editor health
curl http://localhost:5000/health
# Should return healthy status

# Test spec-editor UI
curl -I http://localhost:5000/
# Should return 200 OK

# Test demo-app
curl http://localhost:8080/
# Should return HTTP echo response

# Check logs for errors
docker-compose logs spec-editor | grep ERROR
# Should be empty

# Test form submission (optional - full e2e)
# Open http://localhost:5000 in browser
# Select advworks/dev
# Verify form loads with current values

# Clean up
docker-compose down
```

**Success Criteria**:
- Both containers start successfully
- spec-editor shows healthy status
- demo-app responds on port 8080
- No errors in logs
- Can access UI and view pods

---

### Task 9: Commit and Push for GitHub Action Testing
**File**: N/A (git task)
**Action**: COMMIT
**Pattern**: Git workflow for CI/CD testing

**Implementation**:
```bash
# Stage all new files
git add demo/backend/Dockerfile
git add demo/docker-compose.yml
git add demo/.env.example
git add .github/workflows/build-spec-editor.yml
git add demo/DEPLOY.md
git add .gitignore  # Only if modified

# Commit with conventional commit format
git commit -m "feat(demo): add Docker packaging and CI/CD (D6)

Add Docker containerization for spec-editor Flask app:
- Dockerfile with Python 3.12-slim base
- docker-compose.yml with spec-editor and demo-app services
- GitHub Action for automated image builds on merge to main
- Deployment documentation for local and EC2
- .env.example template with detailed token generation instructions

Image published to: ghcr.io/trakrf/spec-editor:latest

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push feature branch
git push -u origin feature/active-demo-phase-d6
```

**Note**: GitHub Action won't run on feature branch (only on main). We'll test it after merge via /ship.

---

### Task 10: Validate GitHub Action (After Merge)
**File**: N/A (post-merge validation)
**Action**: VALIDATE
**Pattern**: CI/CD verification

**Implementation**:
After merging PR to main via `/ship`:

```bash
# Check workflow run
gh run list --workflow=build-spec-editor.yml --limit 1

# View workflow logs
gh run view --log

# Verify image published
docker pull ghcr.io/trakrf/spec-editor:latest

# Test pulled image
docker run --rm -d \
  -p 5000:5000 \
  -e GH_TOKEN=$GH_TOKEN \
  -e GH_REPO=trakrf/action-spec \
  --name spec-editor-ghcr \
  ghcr.io/trakrf/spec-editor:latest

# Wait for health check
sleep 15

# Test health
curl http://localhost:5000/health

# Test UI
curl -I http://localhost:5000/

# Clean up
docker stop spec-editor-ghcr
```

**Success Criteria**:
- Workflow triggered automatically on merge to main
- Build completed successfully
- Image pushed to ghcr.io
- Image tagged with both `latest` and `main-<sha>`
- Pulled image works identically to local build
- Health check passes

---

## Risk Assessment

**Risk**: Docker image size exceeds 500 MB target
**Mitigation**: Python 3.12-slim base is ~150 MB, Flask stack is ~50 MB, app is ~1 MB. Total should be ~200-250 MB. If larger, investigate with `docker history spec-editor:local`.

**Risk**: GitHub Action fails to push to GHCR due to permissions
**Mitigation**: Workflow uses GITHUB_TOKEN with packages:write permission. If fails, verify repo settings allow GHCR package publishing.

**Risk**: Container health check fails on EC2 due to slow startup
**Mitigation**: Health check has 10s start period. If needed, increase to 30s in docker-compose.yml.

**Risk**: Port 5000 conflicts with existing services on EC2
**Mitigation**: Documentation shows how to remap ports in docker-compose.yml (e.g., 8000:5000).

**Risk**: Missing GH_TOKEN causes cryptic errors
**Mitigation**: app.py:34-37 already has fail-fast check. Container logs will show clear error.

## Integration Points

**Docker Build**:
- Copies app.py and templates/ from demo/backend/
- Uses requirements.txt (flask, PyGithub, pyyaml, gunicorn)
- Exposes port 5000 (matches app.py:520)

**Docker Compose**:
- Passes environment variables to Flask app (GH_TOKEN, GH_REPO, SPECS_PATH, WORKFLOW_BRANCH)
- Health check uses /health endpoint (app.py:487)
- demo-app on port 8080 (matches EC2 user_data pattern)

**GitHub Action**:
- Triggers on changes to demo/backend/** or docker-compose.yml
- Builds from demo/backend/Dockerfile
- Pushes to ghcr.io/trakrf/spec-editor
- Tags: latest, main-<sha>

**Deployment**:
- EC2 pulls image from ghcr.io
- Configures via .env file (copied from .env.example)
- Accesses via public IP on port 5000

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

Since this is a Docker/infrastructure feature, validation differs from code features:

**After Each Task**:
- Gate 1: Docker Build Success
  ```bash
  cd demo/backend && docker build -t spec-editor:test .
  # Must complete without errors
  ```

- Gate 2: Syntax Validation (YAML files)
  ```bash
  # GitHub Action YAML
  yamllint .github/workflows/build-spec-editor.yml
  # docker-compose YAML
  yamllint demo/docker-compose.yml
  ```

- Gate 3: Functional Testing
  ```bash
  # Container must start and pass health check
  docker run --rm -d -p 5000:5000 -e GH_TOKEN=$GH_TOKEN spec-editor:test
  sleep 10
  curl http://localhost:5000/health
  # Must return {"status": "healthy"}
  ```

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

After Task 1 (Dockerfile):
```bash
cd demo/backend
docker build -t spec-editor:test .
```

After Task 2 (docker-compose.yml):
```bash
cd demo
docker-compose config  # Validate YAML syntax
```

After Task 4 (GitHub Action):
```bash
yamllint .github/workflows/build-spec-editor.yml
# Or use GitHub Action syntax checker
```

After Task 7 (Local Build Test):
```bash
# Full build and run test
cd demo/backend
docker build -t spec-editor:local .
docker run --rm -d -p 5000:5000 -e GH_TOKEN=$GH_TOKEN spec-editor:local
sleep 10
curl http://localhost:5000/health
docker stop $(docker ps -q --filter ancestor=spec-editor:local)
```

After Task 8 (Compose Test):
```bash
cd demo
docker-compose up -d
sleep 15
curl http://localhost:5000/health
curl http://localhost:8080/
docker-compose logs | grep ERROR  # Should be empty
docker-compose down
```

Final validation (Task 10 - after merge to main):
```bash
gh run list --workflow=build-spec-editor.yml --limit 1
docker pull ghcr.io/trakrf/spec-editor:latest
docker run --rm -d -p 5000:5000 -e GH_TOKEN=$GH_TOKEN ghcr.io/trakrf/spec-editor:latest
sleep 10
curl http://localhost:5000/health
```

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM-LOW)

**Breakdown**:
- File Impact: 5 new files, 0-1 modified = 2pts
- Subsystems: Docker + CI/CD = 2 subsystems = 1pt
- Tasks: 10 tasks = 2pts
- Dependencies: 0 new packages = 0pts
- Pattern Novelty: Standard Docker patterns = 0pts

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Standard Docker patterns (python:3.12-slim + Flask)
✅ Existing GitHub Actions workflow to reference (.github/workflows/deploy-pod.yml)
✅ All clarifying questions answered (Flask vs gunicorn, volumes, trigger, .env format)
✅ App.py startup pattern already defined (app.run on port 5000)
✅ Environment variables documented in app.py:28-31
✅ No new dependencies or complex integrations
✅ Health check endpoint already exists (/health)

**Assessment**: Straightforward Docker packaging following standard Python container patterns. High confidence due to existing Flask app maturity and clear deployment requirements.

**Estimated one-pass success probability**: 90%

**Reasoning**: Standard Docker workflow with well-defined application behavior. Main risks are minor (port conflicts, GHCR permissions) with clear mitigation. Flask app already runs successfully locally, so containerization is primarily packaging work. GitHub Action follows existing workflow patterns. Only uncertainty is post-merge GHCR push testing, which can be validated quickly.
