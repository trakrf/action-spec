# Implementation Plan: Production Dockerfile + Secrets Manager Integration
Generated: 2025-10-31T00:55:00Z
Specification: spec.md

## Understanding

Create a production-ready multi-stage Docker image that:
1. Builds the Vue 3 frontend with Vite
2. Serves the built frontend via Flask backend with Gunicorn
3. Exposes health check endpoint for App Runner
4. Runs on port 8080 (App Runner default)

**Key simplifications from original spec**:
- `/health` endpoint already exists (backend/app.py:617-672) - no changes needed
- GitHub token will be injected via App Runner's Secrets Manager integration (no boto3 code needed)
- IAM permissions documentation deferred to D2A-30 (App Runner deployment PR)

**Critical path dependency**: Update Flask static_folder path BEFORE creating Dockerfile (Dockerfile copies frontend/dist to backend/static/)

**Local development strategy**: Create symlink `backend/static -> ../frontend/dist` so local dev continues to work after changing static_folder path. Symlink is git-ignored and not used in Docker build.

## Relevant Files

**Reference Patterns** (existing code to follow):
- `frontend/Dockerfile` (lines 1-40) - Multi-stage build pattern with Node + nginx
- `backend/Dockerfile` (lines 1-27) - Python container pattern with health check
- `backend/app.py` (line 27) - Static folder configuration
- `backend/app.py` (lines 617-672) - Existing /health endpoint (keep as-is)
- `backend/app.py` (lines 736-770) - SPA serving logic (keep as-is)

**Files to Create**:
- `.dockerignore` (root) - Exclude development files from build context
- `Dockerfile` (root) - Multi-stage production image (Vue build + Flask serve)

**Files to Modify**:
- `backend/app.py` (line 27) - Update static_folder from `"../frontend/dist"` to `"static"` (POLS for production)
- `.gitignore` (root) - Add `backend/static` to ignore symlink

## Architecture Impact

- **Subsystems affected**: Frontend (Vue build), Backend (Flask static path), Infrastructure (Docker)
- **New dependencies**: None (gunicorn already in requirements.txt)
- **Breaking changes**: None (static_folder path works for both dev and production)

## Task Breakdown

### Task 1: Create .dockerignore
**File**: `.dockerignore`
**Action**: CREATE
**Pattern**: Standard Docker ignore patterns for Python + Node monorepo

**Implementation**:
```dockerignore
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

# Infrastructure (not needed in container)
infra/
overengineered/
spec/
```

**Validation**:
```bash
# Verify file created
ls -la .dockerignore

# No validation commands needed (static file)
```

### Task 2: Update Flask static_folder path
**File**: `backend/app.py`
**Action**: MODIFY
**Pattern**: Flask static_folder configuration (line 27)

**Implementation**:
```python
# OLD (line 27):
app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")

# NEW (line 27):
app = Flask(__name__, static_folder="static", static_url_path="")
```

**Rationale**:
- Production Dockerfile copies frontend/dist to backend/static/
- Using `"static"` follows POLS (Principle of Least Surprise)
- Path resolves relative to WORKDIR (/app in Dockerfile)

**Validation**:
```bash
just backend lint
just backend test
```

### Task 3: Create symlink for local dev
**File**: `backend/static` (symlink)
**Action**: CREATE
**Pattern**: Symlink to maintain local dev compatibility

**Implementation**:
```bash
# Create symlink from backend/static to frontend/dist
ln -sf ../frontend/dist backend/static

# Verify symlink created
ls -la backend/static
```

**Rationale**:
- After changing static_folder to `"static"`, local dev needs backend/static/ to exist
- Symlink points to frontend/dist (the actual build output)
- Docker ignores this symlink (copies frontend/dist directly to backend/static/)
- Git ignores this symlink (added to .gitignore)

**Validation**:
```bash
# Verify symlink exists and points to correct target
test -L backend/static && echo "✓ Symlink exists" || echo "✗ Symlink missing"
readlink backend/static  # Should output: ../frontend/dist
```

### Task 4: Update .gitignore
**File**: `.gitignore`
**Action**: MODIFY
**Pattern**: Ignore symlink in backend/

**Implementation**:
```gitignore
# Add to .gitignore:
backend/static
```

**Rationale**:
- Symlink is environment-specific (local dev only)
- Should not be committed to git
- Production Docker creates its own backend/static/ directory

**Validation**:
```bash
# Verify git ignores the symlink
git status | grep -q "backend/static" && echo "✗ Not ignored" || echo "✓ Ignored"
```

### Task 5: Create production Dockerfile
**File**: `Dockerfile`
**Action**: CREATE
**Pattern**: Multi-stage build combining frontend/Dockerfile (lines 1-19) and backend/Dockerfile patterns

**Implementation**:
```dockerfile
# Stage 1: Build Vue frontend
FROM node:22-slim AS frontend-builder

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app/frontend

# Copy dependency files
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Build for production
RUN pnpm run build

# Stage 2: Python runtime with Flask + Gunicorn
FROM python:3.14-slim

WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies (gunicorn already in requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy Vue build from stage 1 to backend/static/
COPY --from=frontend-builder /app/frontend/dist ./backend/static/

# Environment variables (defaults, override at runtime via App Runner)
ENV FLASK_ENV=production \
    PORT=8080 \
    GH_REPO=trakrf/action-spec \
    SPECS_PATH=infra \
    WORKFLOW_BRANCH=main

# Expose port
EXPOSE 8080

# Health check using existing /health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run with Gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "--chdir", "backend", "app:app"]
```

**Critical details**:
- `--chdir backend` - Changes working directory to backend/ before importing app
- `app:app` - Imports `app` object from `app.py` module
- `--workers 2` - Suitable for App Runner's resource limits
- `--timeout 60` - Prevents worker timeout on slow GitHub API calls
- Port 8080 - App Runner default port

**Validation**:
```bash
# Build the image
docker build -t action-spec:test .

# Check image size (should be <500MB)
docker images action-spec:test

# Verify layers
docker history action-spec:test
```

### Task 6: Test Docker build locally (development mode)
**File**: N/A (testing)
**Action**: TEST
**Pattern**: Local Docker run with development environment variables

**Implementation**:
```bash
# Build image
docker build -t action-spec:dev .

# Run container with dev env vars
docker run -d -p 8080:8080 --name action-spec-test \
  -e GH_TOKEN=${GH_TOKEN} \
  -e GH_REPO=trakrf/action-spec \
  action-spec:dev

# Wait for startup
sleep 3

# Test health endpoint
curl http://localhost:8080/health

# Test Vue app loads
curl -I http://localhost:8080/

# Check logs
docker logs action-spec-test

# Cleanup
docker stop action-spec-test
docker rm action-spec-test
```

**Expected results**:
- ✅ Health check returns 200 OK with JSON
- ✅ Root path returns 200 OK (index.html)
- ✅ Logs show Gunicorn workers started
- ✅ No Python errors in logs

**Validation**:
```bash
# If tests pass, proceed to final validation
# If tests fail, debug and fix before proceeding
```

### Task 7: Verify static file serving
**File**: N/A (testing)
**Action**: TEST
**Pattern**: Verify Vue SPA assets are served correctly

**Implementation**:
```bash
# Container should still be running from Task 4
# If not, restart:
# docker run -d -p 8080:8080 --name action-spec-test \
#   -e GH_TOKEN=${GH_TOKEN} \
#   action-spec:dev

# Test static assets load
curl -I http://localhost:8080/assets/index.js  # Should return 200
curl -I http://localhost:8080/assets/index.css  # Should return 200

# Test SPA fallback (non-existent route should serve index.html)
curl -I http://localhost:8080/nonexistent-page  # Should return 200 (index.html)

# Test API routes still work
curl http://localhost:8080/api/health  # Should return API response

# Cleanup
docker stop action-spec-test
docker rm action-spec-test
```

**Expected results**:
- ✅ Static assets (.js, .css) return 200 OK
- ✅ Non-existent routes return index.html (SPA fallback)
- ✅ API routes are not affected by SPA fallback

**Validation**:
```bash
# Manual verification of curl responses
```

### Task 8: Run full validation suite
**File**: N/A (validation)
**Action**: VALIDATE
**Pattern**: Run all validation commands from spec/stack.md

**Implementation**:
```bash
# Lint all code
just lint

# Run all tests
just test

# Build all workspaces
just build

# Run full validation
just validate
```

**Expected results**:
- ✅ Backend lint passes (black, mypy)
- ✅ Frontend lint passes (eslint)
- ✅ Backend tests pass (pytest)
- ✅ Frontend tests pass (playwright)
- ✅ Backend build succeeds
- ✅ Frontend build succeeds

**Validation**:
```bash
# Exit code 0 for all commands
echo $?
```

## Risk Assessment

- **Risk**: Static folder path breaks local development
  **Mitigation**: The path `"static"` works for both dev (when run from backend/) and production (when WORKDIR is /app)

- **Risk**: pnpm install fails in Docker
  **Mitigation**: Using `--frozen-lockfile` ensures deterministic builds, fail fast if lock file out of sync

- **Risk**: Gunicorn worker timeout on slow GitHub API calls
  **Mitigation**: Set `--timeout 60` (matches typical GitHub API response time)

- **Risk**: Docker build fails due to large context
  **Mitigation**: Comprehensive .dockerignore excludes node_modules, venv, tests, docs

- **Risk**: Port 8080 conflicts with local services
  **Mitigation**: Document clearly, use `-p 8081:8080` if needed for local testing

## Integration Points

- **Flask static_folder**: Updated from `"../frontend/dist"` to `"static"` (production path)
- **Gunicorn WSGI**: Runs Flask app in production mode with 2 workers
- **Health endpoint**: Already exists at `/health` (no changes needed)
- **Environment variables**: Defaults in Dockerfile, override via App Runner

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY code change:
- Gate 1: Syntax & Style → `just backend lint` (Task 2)
- Gate 2: Unit Tests → `just backend test` (Task 2)
- Gate 3: Docker Build → `docker build -t action-spec:test .` (Task 3)

After Task 4 (Docker run):
- Gate 4: Health Check → `curl http://localhost:8080/health` must return 200
- Gate 5: SPA Serving → `curl http://localhost:8080/` must return HTML

After Task 6 (final validation):
- Gate 6: Full Lint → `just lint` must pass
- Gate 7: Full Tests → `just test` must pass
- Gate 8: Full Build → `just build` must pass

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all gates.**

## Validation Sequence

After each task:
```bash
# Task 1: No validation needed (.dockerignore is static)

# Task 2: Validate Python changes
just backend lint
just backend test

# Task 3: Verify symlink created
test -L backend/static && readlink backend/static

# Task 4: Verify git ignores symlink
git status | grep -v "backend/static"

# Task 5: Validate Docker build
docker build -t action-spec:test .

# Task 6: Validate runtime
docker run -d -p 8080:8080 --name action-spec-test -e GH_TOKEN=${GH_TOKEN} action-spec:test
curl http://localhost:8080/health
docker stop action-spec-test && docker rm action-spec-test

# Task 7: Validate static serving
docker run -d -p 8080:8080 --name action-spec-test -e GH_TOKEN=${GH_TOKEN} action-spec:test
curl -I http://localhost:8080/assets/index.js
curl -I http://localhost:8080/nonexistent-page
docker stop action-spec-test && docker rm action-spec-test

# Task 8: Final validation
just validate
```

## Plan Quality Assessment

**Complexity Score**: 5/10 (MEDIUM)

**Complexity Factors**:
- 📁 File Impact: Creating 3 files (.dockerignore, Dockerfile, symlink), modifying 2 files (app.py, .gitignore) = 5 files total
- 🔗 Subsystems: Touching 3 subsystems (Frontend/Vue, Backend/Flask, Infrastructure/Docker)
- 🔢 Task Estimate: 8 subtasks (well within manageable range)
- 📦 Dependencies: 0 new packages (gunicorn already present)
- 🆕 Pattern Novelty: Existing patterns (multi-stage Docker from frontend/Dockerfile)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ Similar patterns found in codebase at frontend/Dockerfile (lines 1-40), backend/Dockerfile (lines 1-27)
- ✅ All clarifying questions answered
- ✅ Existing test patterns to follow (just lint, just test, just build)
- ✅ Health endpoint already exists (no new code needed)
- ⚠️ Static folder path change requires testing both dev and production modes

**Assessment**: High confidence implementation. The multi-stage Docker pattern already exists in the codebase, and the only code change is a simple path update. Main risk is ensuring the static folder path works correctly in both development and production contexts.

**Estimated one-pass success probability**: 85%

**Reasoning**: Straightforward Docker build with existing patterns. The static_folder path change is low-risk (resolves relative to current working directory). Main uncertainty is verifying that Docker build layers are optimized and that static serving works correctly. Testing strategy includes incremental validation gates to catch issues early.
