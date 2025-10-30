# Implementation Plan: Promote Demo to Backend (Industry Standard Structure)

Generated: 2025-10-30
Specification: spec.md

## Understanding

This is a mechanical refactoring to promote the working Flask backend from `/demo` to `/backend` following industry-standard monorepo structure (POLS). The task completes the pivot narrative started with D2A-25 (archive overengineered) by promoting the simple solution to its proper place.

**Key Decision**: Moving to `/backend` (not `/src`) because:
- Industry standard for multi-service projects (MERN, Django+React, microservices)
- Clear peer structure ready for `/frontend` (Phase 3.4)
- Semantic clarity: "backend" describes WHAT, not just "source"

**Validation Strategy**: Lightweight per user confirmation
- Smoke tests: Flask imports, Docker config validation
- Full test suite intentionally deferred to D2A-27/D2A-28
- Rationale: Pure structure refactor, no logic changes

## Relevant Files

**Current Structure** (to be moved):
```
demo/
├── backend/
│   ├── app.py (line 30: SPECS_PATH='demo/infra')
│   ├── Dockerfile
│   ├── requirements.txt
│   └── templates/
├── infra/
│   ├── advworks/dev/, advworks/stg/
│   └── northwind/dev/
├── tfmodules/pod/
├── docker-compose.yml (lines 6, 15: references ./backend, demo/infra)
├── justfile
├── SPEC.md
├── README.md
└── .env.example

root/
├── .github/workflows/
│   ├── deploy-pod.yml (references demo paths)
│   ├── build-spec-editor.yml (references demo/backend)
│   ├── terraform-plan.yml (references demo/infra)
│   └── terraform-apply.yml
└── README.md (references demo)
```

**Target Structure**:
```
backend/
├── app.py (SPECS_PATH='infra')
├── Dockerfile
├── requirements.txt
├── templates/
└── README.md

infra/
├── advworks/
├── northwind/
└── modules/pod/

docker-compose.yml (at root, references ./backend)
justfile (at root)
.env.example (at root)
docs/SPEC.md
```

**Files to Move** (with git mv):
- `demo/backend/` → `backend/`
- `demo/infra/` → `infra/`
- `demo/tfmodules/pod/` → `infra/modules/pod/`
- `demo/docker-compose.yml` → `docker-compose.yml`
- `demo/justfile` → `justfile`
- `demo/SPEC.md` → `docs/SPEC.md`
- `demo/README.md` → `backend/README.md`
- `demo/.env.example` → `.env.example`

**Files to Modify**:
- `backend/app.py` (line 30: SPECS_PATH default)
- `docker-compose.yml` (lines 6, 15, 26-27: paths)
- `infra/*/dev/main.tf` (3 files: module source paths)
- `infra/*/stg/main.tf` (1 file: module source path)
- `.github/workflows/*.yml` (4 files: demo path references)
- Root `README.md` (demo → backend references)
- `backend/README.md` (reframe from demo to production)
- `.env.example` (SPECS_PATH default, add .env.local note)

## Architecture Impact

- **Subsystems affected**: Application (Flask), Infrastructure (Terraform), CI/CD (GitHub Actions), Docker, Documentation
- **New dependencies**: None
- **Breaking changes**: None (paths change but functionality identical)
- **Git history**: Fully preserved via `git mv`

## Task Breakdown

### Task 1: Create Target Directories
**Action**: CREATE
**Path**: `infra/modules/`, `docs/`

**Implementation**:
```bash
mkdir -p infra/modules
mkdir -p docs
```

**Validation**:
```bash
ls -la infra/modules/ docs/
# Should show empty directories
```

**Success Criteria**:
- [ ] `infra/modules/` directory exists
- [ ] `docs/` directory exists

---

### Task 2: Move Application Code to /backend
**Action**: MOVE (with git history)
**Pattern**: Use `git mv` to preserve full commit history

**Implementation**:
```bash
git mv demo/backend backend
```

**Validation**:
```bash
# Verify files moved
ls -la backend/app.py backend/Dockerfile backend/templates/

# Verify original gone
! ls demo/backend 2>/dev/null

# Verify git history preserved
git log --follow --oneline backend/ | head -3
```

**Success Criteria**:
- [ ] `backend/` contains app.py, Dockerfile, templates/, requirements.txt
- [ ] Original `demo/backend/` removed
- [ ] Git status shows "renamed:" not "deleted/added"

---

### Task 3: Move Infrastructure to Root
**Action**: MOVE (with git history)

**Implementation**:
```bash
# Move pod specs to root
git mv demo/infra infra

# Move Terraform modules under infra
git mv demo/tfmodules/pod infra/modules/pod

# Clean up empty tfmodules directory
rmdir demo/tfmodules 2>/dev/null || true
```

**Validation**:
```bash
# Verify infrastructure moved
ls -la infra/advworks/ infra/northwind/ infra/modules/pod/

# Verify originals gone
! ls demo/infra demo/tfmodules 2>/dev/null

# Verify git history preserved
git log --follow --oneline infra/ | head -3
```

**Success Criteria**:
- [ ] `infra/advworks/` and `infra/northwind/` exist with pod specs
- [ ] `infra/modules/pod/` contains Terraform module files
- [ ] Original demo/infra and demo/tfmodules removed
- [ ] Git status shows "renamed:"

---

### Task 4: Move Project Tooling to Root
**Action**: MOVE (with git history)

**Implementation**:
```bash
git mv demo/docker-compose.yml docker-compose.yml
git mv demo/justfile justfile
```

**Validation**:
```bash
# Verify files moved
ls -la docker-compose.yml justfile

# Verify originals gone
! ls demo/docker-compose.yml demo/justfile 2>/dev/null
```

**Success Criteria**:
- [ ] `docker-compose.yml` at root
- [ ] `justfile` at root
- [ ] Original demo files removed
- [ ] Git status shows "renamed:"

---

### Task 5: Move Documentation
**Action**: MOVE (with git history)

**Implementation**:
```bash
git mv demo/SPEC.md docs/SPEC.md
git mv demo/README.md backend/README.md
git mv demo/.env.example .env.example
```

**Validation**:
```bash
# Verify moved
ls -la docs/SPEC.md backend/README.md .env.example

# Verify originals gone
! ls demo/SPEC.md demo/README.md demo/.env.example 2>/dev/null
```

**Success Criteria**:
- [ ] `docs/SPEC.md` exists
- [ ] `backend/README.md` exists
- [ ] `.env.example` at root
- [ ] Original demo files removed
- [ ] Git status shows "renamed:"

---

### Task 6: Update Flask App Path References
**Action**: MODIFY
**File**: `backend/app.py`
**Line**: 30

**Implementation**:
Update hardcoded path from demo to new location:

```python
# OLD (line 30):
SPECS_PATH = os.environ.get('SPECS_PATH', 'demo/infra')

# NEW:
SPECS_PATH = os.environ.get('SPECS_PATH', 'infra')
```

**Validation**:
```bash
# Verify change
grep "SPECS_PATH.*infra" backend/app.py
! grep "demo/infra" backend/app.py

# Smoke test (lightweight validation)
cd backend && python -c "import app; print('✓ Imports work')" 2>&1 | head -5
```

**Success Criteria**:
- [ ] `SPECS_PATH` default updated to `infra`
- [ ] No references to `demo/infra` in app.py
- [ ] Python imports still work (no ImportError)

---

### Task 7: Update Docker Compose Paths
**Action**: MODIFY
**File**: `docker-compose.yml` (now at root)

**Implementation**:
Update paths to reference new locations:

```yaml
# OLD (line 6):
    build:
      context: ./backend

# NEW:
    build:
      context: ./backend
# (Already correct after move!)

# OLD (line 15):
      - SPECS_PATH=${SPECS_PATH:-demo/infra}

# NEW:
      - SPECS_PATH=${SPECS_PATH:-infra}

# OLD (lines 26-27, commented):
    #   - ./backend/app.py:/app/app.py
    #   - ./backend/templates:/app/templates

# (Already correct after move!)
```

**Validation**:
```bash
# Verify SPECS_PATH change
grep "SPECS_PATH.*:-infra" docker-compose.yml

# Verify no demo references
! grep "demo/infra" docker-compose.yml

# Smoke test Docker config
docker compose config >/dev/null && echo "✓ Docker config valid"
```

**Success Criteria**:
- [ ] SPECS_PATH default updated to `infra`
- [ ] No active references to demo/infra
- [ ] `docker compose config` succeeds

---

### Task 8: Update Terraform Module Paths
**Action**: MODIFY
**Files**: `infra/advworks/dev/main.tf`, `infra/advworks/stg/main.tf`, `infra/northwind/dev/main.tf`

**Implementation**:
Update module source paths in all pod specs:

```hcl
# OLD:
module "pod" {
  source = "../../../tfmodules/pod"

# NEW:
module "pod" {
  source = "../../modules/pod"
```

**Validation**:
```bash
# Update all main.tf files
find infra -name "main.tf" ! -path "*/modules/*" -exec sed -i 's|../../../tfmodules/pod|../../modules/pod|g' {} \;

# Verify changes
grep "source.*modules/pod" infra/*/dev/main.tf infra/*/stg/main.tf

# Verify no tfmodules references
! grep -r "tfmodules" infra/ --include="*.tf"
```

**Success Criteria**:
- [ ] All 4 main.tf files updated (advworks/dev, advworks/stg, northwind/dev)
- [ ] Module source paths point to `../../modules/pod`
- [ ] No references to `tfmodules` in infrastructure code

---

### Task 9: Update GitHub Actions Workflows
**Action**: MODIFY
**Files**: `.github/workflows/deploy-pod.yml`, `build-spec-editor.yml`, `terraform-plan.yml`, `terraform-apply.yml`

**Implementation**:
Update demo path references in workflows:

```bash
# Batch update all workflows
find .github/workflows -name "*.yml" -exec sed -i \
  -e 's|demo/infra|infra|g' \
  -e 's|demo/backend|backend|g' \
  -e 's|demo/docker-compose\.yml|docker-compose.yml|g' \
  -e 's|demo/tfmodules|infra/modules|g' \
  {} \;
```

**Note**: Intentionally preserve S3 state key "demo/" prefix in deploy-pod.yml - those are S3 paths, not file paths.

**Validation**:
```bash
# Verify path updates (expect only S3 state keys to have "demo/")
grep "demo" .github/workflows/*.yml
```

**Success Criteria**:
- [ ] File path references updated in all 4 workflows
- [ ] S3 state keys intentionally kept with "demo/" prefix
- [ ] Workflows reference correct paths (infra, backend, etc.)

---

### Task 10: Update Root README
**Action**: MODIFY
**File**: `README.md` (root)

**Implementation**:
Update demo references to backend:

```markdown
# Search for these patterns and update:
/demo → /backend (in paths)
demo/ → backend/ (in instructions)

# Specific line to find and update:
"See the demo: The `demo/` directory..." → "See the implementation: The `backend/` directory..."
```

**Validation**:
```bash
# Check for remaining demo path references (should be minimal)
grep -n "/demo" README.md

# Verify backend references added
grep -n "/backend" README.md
```

**Success Criteria**:
- [ ] Path references updated from demo/ to backend/
- [ ] Only contextual "demo" mentions remain (demo account, demonstration project)
- [ ] Quick Start reflects new structure

---

### Task 11: Update Backend README (Reframe from Demo to Production)
**Action**: MODIFY
**File**: `backend/README.md` (was demo/README.md)

**Implementation**:
Remove experimental language and update paths:

```markdown
# Changes to make:
1. Title: "ActionSpec Demo" → "ActionSpec Backend"
2. Intro: "proof-of-concept" → "production backend"
3. All demo/ paths → backend/ or infra/
4. Architecture diagrams: update all paths
5. Remove phrases: "demo", "POC", "proof of concept", "experimental"
6. Keep technical content but adjust framing to production tone
```

**Validation**:
```bash
# Check for demo/POC language
grep -i "demo\|poc\|proof.of.concept\|experimental" backend/README.md

# Should only remain in historical context (if any)
```

**Success Criteria**:
- [ ] Title reflects "Backend" or "Main Implementation"
- [ ] Architecture diagrams show new paths
- [ ] Production tone (not experimental)
- [ ] Technical accuracy maintained

---

### Task 12: Update .env.example
**Action**: MODIFY
**File**: `.env.example` (now at root)

**Implementation**:
Update SPECS_PATH and add .env.local guidance:

```bash
# OLD:
SPECS_PATH=demo/infra

# NEW:
SPECS_PATH=infra

# Add note about .env.local:
# Local Configuration
# Copy this file to .env.local and update with your values
# .env.local is gitignored and safe for secrets
```

**Validation**:
```bash
# Verify SPECS_PATH updated
grep "SPECS_PATH=infra" .env.example

# Verify .env.local mentioned
grep ".env.local" .env.example
```

**Success Criteria**:
- [ ] SPECS_PATH updated to `infra`
- [ ] Documentation mentions .env.local pattern
- [ ] File location at root (not in demo/)

---

### Task 13: Smoke Test Flask Application
**Action**: TEST
**Purpose**: Lightweight validation that Flask app starts

**Implementation**:
```bash
cd backend

# Test import
python -c "from app import app; print('✓ App imports successfully')"

# Optional: Test Flask runs (if dependencies installed)
# flask run --port 5001 &
# sleep 2
# curl http://localhost:5001/health
# kill %1
```

**Validation**:
- App imports without errors
- No ImportError or path issues

**Success Criteria**:
- [ ] Python can import app module
- [ ] No import errors related to paths
- [ ] (Optional) Flask starts successfully

---

### Task 14: Smoke Test Docker Compose
**Action**: TEST
**Purpose**: Lightweight validation that docker-compose builds

**Implementation**:
```bash
# From project root
docker compose config

# Optional: Full build test
# docker compose build spec-editor
```

**Validation**:
- docker-compose.yml parses correctly
- Build context paths resolve
- Environment variables correct

**Success Criteria**:
- [ ] `docker compose config` succeeds
- [ ] No path resolution errors
- [ ] (Optional) Docker build succeeds

---

### Task 15: Verify No Demo References Remain
**Action**: VERIFY
**Purpose**: Final check for missed references

**Implementation**:
```bash
# Search for demo references (excluding git history, archived docs)
grep -r "demo/" . \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=venv \
  --exclude-dir=overengineered \
  --include="*.py" \
  --include="*.yml" \
  --include="*.yaml" \
  --include="*.tf" \
  --include="*.md"
```

**Validation**:
Only acceptable demo references:
- S3 Terraform state keys (infra/*/backend.tf)
- GitHub workflow state key generation
- Historical explanations in docs (SECURITY.md, CONTRIBUTING.md: "demo/portfolio project")
- overengineered/README.md (explains the journey)

**Success Criteria**:
- [ ] No active code references to demo paths
- [ ] Configuration files updated
- [ ] Only S3 keys and historical/explanatory references remain

---

### Task 16: Remove Empty Demo Directory
**Action**: DELETE
**Purpose**: Clean up empty demo directory

**Implementation**:
```bash
# Verify demo is mostly empty (only DEPLOY.md may remain)
ls -la demo/

# Remove demo directory
rm -rf demo/

# Or use git rm if any tracked files remain
git rm -r demo/ 2>/dev/null || rm -rf demo/
```

**Validation**:
```bash
# Verify demo removed
! ls demo/ 2>/dev/null

# Check git status
git status | grep demo
```

**Success Criteria**:
- [ ] `demo/` directory removed
- [ ] Git shows deletion or clean status
- [ ] Clean working directory

---

## Risk Assessment

**Risk**: Import errors from missed path updates
- **Likelihood**: Very Low (only environment variables, not Python imports)
- **Mitigation**: Smoke test imports in Task 13

**Risk**: Docker build fails due to path misconfigurations
- **Likelihood**: Low (simple path updates)
- **Mitigation**: Task 14 validates docker compose config

**Risk**: Terraform module paths incorrect
- **Likelihood**: Very Low (sed replacement is straightforward)
- **Mitigation**: Task 8 validates with grep check

**Risk**: Missed demo references in workflows
- **Likelihood**: Low (systematic sed replacement)
- **Mitigation**: Task 9 validates with grep

**Risk**: Git history loss
- **Likelihood**: Very Low (using git mv consistently)
- **Mitigation**: Verify git log --follow after each move

## Integration Points

- **Flask App**: Environment variable `SPECS_PATH` changes default from `demo/infra` to `infra`
- **Docker Compose**: Build context and paths updated to reference `backend/`
- **Terraform**: Module source paths updated to nested structure `infra/modules/pod`
- **CI/CD**: GitHub Actions workflows updated to new file paths
- **Documentation**: All docs updated to reflect new canonical structure

## VALIDATION GATES (LIGHTWEIGHT FOR THIS REFACTOR)

**User Decision**: Lightweight validation acceptable - comprehensive testing deferred to D2A-27/D2A-28

**Per-Task Validation** (smoke tests only):
- After moves: Verify files in new location, originals removed
- After path updates: Grep to confirm changes applied
- After Flask changes: Test import works
- After Docker changes: docker compose config validates

**Final Validation** (basic checks):
```bash
# 1. Python imports work
cd backend && python -c "from app import app; print('✓')"

# 2. Docker compose parses
docker compose config >/dev/null && echo "✓"

# 3. No stray demo references in code
! grep -r "demo/" . --include="*.py" --include="*.yml" --include="*.tf" \
  --exclude-dir=.git --exclude-dir=venv --exclude-dir=overengineered

# 4. Git history preserved
git log --follow backend/ | head -1
```

**Full test suite INTENTIONALLY SKIPPED**:
- Lint: Skip (mechanical refactor, no logic changes)
- Tests: Skip (no functionality changes)
- Build: Skip (validated in D2A-27/D2A-28)

**Rationale**: This is pure housekeeping. Real validation happens when features (D2A-27/D2A-28) exercise the refactored paths.

## Plan Quality Assessment

**Complexity Score**: 9/10 (HIGH - but mechanical)
**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ User confirmed lightweight validation approach
- ✅ All clarifying questions answered (.env.example → root, .env.local pattern)
- ✅ Similar pattern from D2A-25 (used git mv successfully)
- ✅ User confirmed Flask app has no Python imports to update
- ✅ All files identified in codebase research
- ✅ Mechanical refactor - deterministic steps
- ✅ Easy to validate (paths work or they don't)

**Assessment**: High confidence for mechanical execution. This is straightforward file moves and path string replacements. Primary risk is missing demo references in scattered documentation, but comprehensive grep (Task 15) mitigates this. Deferred validation to D2A-27/D2A-28 is pragmatic - those features will immediately reveal any path issues.

**Estimated one-pass success probability**: 92%

**Reasoning**: The 8% risk accounts for potentially missed documentation references or edge cases in workflow configs. However, these are low-impact issues (docs only, not functional) that are easily discovered and fixed. The mechanical nature of this refactor (move files, update strings) has very high success probability. User's decision to reset and redo with correct structure shows thoughtful commitment to getting it right.
