# Implementation Plan: Promote Demo to Main Implementation

Generated: 2025-10-30
Specification: spec.md

## Understanding

This is a mechanical refactoring to promote the working Flask POC from `/demo` to `/src` as the official main implementation. The task completes the pivot narrative started with D2A-25 (archive overengineered) by promoting the simple solution that actually shipped.

**Key insight**: This is primarily file moves and path updates - no logic changes. User has confirmed lightweight validation is acceptable since D2A-27/D2A-28 will provide comprehensive testing.

**User confirmations**:
- Flask app is self-contained (minimal imports)
- Terraform specs reference `../../../tfmodules/pod` (need path updates)
- GitHub Actions don't reference demo paths

## Relevant Files

**Reference Pattern** (from D2A-25):
- Previous archive PR used `git mv` to preserve history
- Same approach: move with git, preserve full history

**Files Found in Demo**:
- `demo/backend/app.py` - Single Flask app file
- `demo/backend/Dockerfile` - Container build
- `demo/backend/templates/` - Jinja templates
- `demo/docker-compose.yml` - Service orchestration
- `demo/justfile` - Task runner (WAF testing, Terraform)
- `demo/README.md` - Demo documentation
- `demo/SPEC.md` - Infrastructure spec documentation
- `demo/infra/northwind/`, `demo/infra/advworks/`, `demo/infra/advworks/stg/` - Pod specs
- `demo/tfmodules/pod/` - Terraform module

**Files to Move**:
- `demo/backend/` → `src/backend/`
- `demo/Dockerfile` → `src/Dockerfile`
- `demo/README.md` → `src/README.md`
- `demo/infra/` → `infra/`
- `demo/tfmodules/pod/` → `infra/modules/pod/`
- `demo/docker-compose.yml` → `docker-compose.yml`
- `demo/justfile` → `justfile`
- `demo/SPEC.md` → `docs/SPEC.md`

**Files to Modify**:
- `demo/backend/app.py` (line 33: `SPECS_PATH = 'demo/infra'`) → Update to `infra/`
- `demo/docker-compose.yml` (line 5: `context: ./backend`) → Update to `./src/backend`
- `demo/docker-compose.yml` (line 13: `SPECS_PATH=demo/infra`) → Update to `infra/`
- `demo/infra/*/main.tf` (3 files: `source = "../../../tfmodules/pod"`) → Update to `../../modules/pod`
- Main `README.md` - Update references from `/demo` to `/src`
- `.gitignore` - Add src-specific entries if needed

## Architecture Impact

- **Subsystems affected**: Application (Flask), Infrastructure (Terraform), Tooling (Docker/justfile), Documentation
- **New dependencies**: None
- **Breaking changes**: None (paths change but functionality identical)
- **Git history**: Fully preserved via `git mv`

## Task Breakdown

### Task 1: Create Target Directories
**Action**: CREATE
**Path**: `src/`, `infra/modules/`, `docs/`

**Implementation**:
```bash
mkdir -p src
mkdir -p infra/modules
mkdir -p docs
```

**Validation**:
```bash
ls -la src/ infra/modules/ docs/
# Should show empty directories
```

**Success Criteria**:
- [ ] `src/` directory exists
- [ ] `infra/modules/` directory exists
- [ ] `docs/` directory exists

---

### Task 2: Move Application Code to /src
**Action**: MOVE (with git history)
**Pattern**: Reference D2A-25 archive PR (used git mv)

**Implementation**:
```bash
git mv demo/backend src/backend
git mv demo/Dockerfile src/Dockerfile
git mv demo/README.md src/README.md
```

**Validation**:
```bash
# Verify files moved
ls -la src/backend/app.py
ls -la src/Dockerfile
ls -la src/README.md

# Verify originals gone
ls demo/backend 2>&1 | grep "No such file"
ls demo/Dockerfile 2>&1 | grep "No such file"

# Verify git history preserved
git log --follow --oneline src/backend/ | head -3
```

**Success Criteria**:
- [ ] `src/backend/` contains app.py, templates/, venv/
- [ ] `src/Dockerfile` exists
- [ ] `src/README.md` exists
- [ ] Original demo files removed
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
ls -la infra/northwind/
ls -la infra/advworks/
ls -la infra/modules/pod/

# Verify originals gone
ls demo/infra 2>&1 | grep "No such file"
ls demo/tfmodules 2>&1 | grep "No such file"

# Verify git history preserved
git log --follow --oneline infra/ | head -3
```

**Success Criteria**:
- [ ] `infra/northwind/`, `infra/advworks/` exist with pod specs
- [ ] `infra/modules/pod/` contains Terraform module
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
ls -la docker-compose.yml
ls -la justfile

# Verify originals gone
ls demo/docker-compose.yml 2>&1 | grep "No such file"
ls demo/justfile 2>&1 | grep "No such file"
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
```

**Validation**:
```bash
# Verify moved
ls -la docs/SPEC.md

# Verify original gone
ls demo/SPEC.md 2>&1 | grep "No such file"
```

**Success Criteria**:
- [ ] `docs/SPEC.md` exists
- [ ] Original demo/SPEC.md removed
- [ ] Git status shows "renamed:"

---

### Task 6: Update Flask App Path References
**Action**: MODIFY
**File**: `src/backend/app.py`
**Line**: 33

**Implementation**:
Update hardcoded path from demo to new location:

```python
# OLD (line 33):
SPECS_PATH = os.environ.get('SPECS_PATH', 'demo/infra')

# NEW:
SPECS_PATH = os.environ.get('SPECS_PATH', 'infra')
```

**Validation**:
```bash
# Verify change
grep "SPECS_PATH.*infra" src/backend/app.py
grep -v "demo/infra" src/backend/app.py | grep SPECS_PATH

# Smoke test (optional - lightweight validation)
cd src/backend && python -c "import app; print('✓ Imports work')"
```

**Success Criteria**:
- [ ] `SPECS_PATH` default updated to `infra`
- [ ] No references to `demo/infra` in app.py
- [ ] Python imports still work

---

### Task 7: Update Docker Compose Paths
**Action**: MODIFY
**File**: `docker-compose.yml` (now at root)

**Implementation**:
Update paths to reference new locations:

```yaml
# OLD (line 5):
    build:
      context: ./backend

# NEW:
    build:
      context: ./src/backend

# OLD (line 13):
      - SPECS_PATH=${SPECS_PATH:-demo/infra}

# NEW:
      - SPECS_PATH=${SPECS_PATH:-infra}
```

**Validation**:
```bash
# Verify changes
grep "context: ./src/backend" docker-compose.yml
grep "SPECS_PATH.*:-infra" docker-compose.yml

# Verify no demo references
grep -c "demo" docker-compose.yml
# Should be 0 or only in comments
```

**Success Criteria**:
- [ ] Build context updated to `./src/backend`
- [ ] `SPECS_PATH` default updated to `infra`
- [ ] No active references to demo paths

---

### Task 8: Update Terraform Module Paths
**Action**: MODIFY
**Files**: `infra/northwind/dev/main.tf`, `infra/advworks/dev/main.tf`, `infra/advworks/stg/main.tf`

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
find infra -name "main.tf" -exec sed -i 's|../../../tfmodules/pod|../../modules/pod|g' {} \;

# Verify changes
grep "source.*modules/pod" infra/*/dev/main.tf
grep "source.*modules/pod" infra/*/stg/main.tf

# Verify no tfmodules references
grep -r "tfmodules" infra/ --include="*.tf"
# Should return no results
```

**Success Criteria**:
- [ ] All 3 main.tf files updated
- [ ] Module source paths point to `../../modules/pod`
- [ ] No references to `tfmodules` in infrastructure code

---

### Task 9: Update Main README Documentation
**Action**: MODIFY
**File**: `README.md` (root)

**Implementation**:
Search and replace demo references:
- `/demo` → `/src`
- `demo/` → `src/` (in paths)
- Remove "POC" or "demo" framing language
- Update Quick Start instructions

**Validation**:
```bash
# Check for remaining demo references (should be minimal)
grep -n "demo" README.md

# Verify src references added
grep -n "/src" README.md
grep -n "src/backend" README.md
```

**Success Criteria**:
- [ ] `/demo` paths updated to `/src`
- [ ] "Demo" framing removed or clarified
- [ ] Quick Start reflects new structure
- [ ] Only historical/explanatory demo references remain

---

### Task 10: Update Src README (Reframe from Demo to Production)
**Action**: MODIFY
**File**: `src/README.md` (was demo/README.md)

**Implementation**:
Remove experimental language:
- Change "Demo POC" → "Main Implementation"
- Update architecture diagrams with `/src` and `/infra` paths
- Remove phrases like "proof of concept", "experimental", "demo"
- Keep technical content but adjust framing

**Validation**:
```bash
# Check for demo/POC language
grep -i "demo\|poc\|proof.of.concept\|experimental" src/README.md

# Should only remain in historical context
```

**Success Criteria**:
- [ ] Title reflects "Main Implementation" not "Demo"
- [ ] Architecture diagrams show new paths
- [ ] Production tone (not experimental)
- [ ] Technical accuracy maintained

---

### Task 11: Update .gitignore (if needed)
**Action**: MODIFY
**File**: `.gitignore`

**Implementation**:
Check for demo-specific entries and add src-specific:

```gitignore
# If these exist, consider updating:
# demo/backend/venv/ → src/backend/venv/
# demo/backend/__pycache__/ → src/backend/__pycache__/
```

**Validation**:
```bash
# Check current gitignore
grep "demo" .gitignore

# Add src entries if needed
grep "src" .gitignore
```

**Success Criteria**:
- [ ] No orphaned demo-specific rules
- [ ] Src paths ignored if needed (venv, __pycache__, etc.)
- [ ] .gitignore still functions correctly

---

### Task 12: Smoke Test Flask Application
**Action**: TEST
**Purpose**: Basic validation that Flask app starts

**Implementation**:
```bash
cd src/backend

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

### Task 13: Smoke Test Docker Compose
**Action**: TEST
**Purpose**: Verify docker-compose builds with new paths

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

### Task 14: Verify No Demo References Remain
**Action**: VERIFY
**Purpose**: Final check for missed references

**Implementation**:
```bash
# Search for demo references (excluding git history, docs, changelog)
grep -r "demo/" . \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=venv \
  --include="*.py" \
  --include="*.yml" \
  --include="*.yaml" \
  --include="*.tf" \
  --include="*.md"

# Check specifically for demo/infra and demo/backend
grep -r "demo/infra\|demo/backend" . \
  --exclude-dir=.git \
  --exclude-dir=venv
```

**Validation**:
Only acceptable demo references:
- Historical explanations in docs
- Git commit messages (in history)
- Comments explaining the refactor
- overengineered/README.md (explains the journey)

**Success Criteria**:
- [ ] No active code references to demo paths
- [ ] Configuration files updated
- [ ] Only historical/explanatory references remain

---

### Task 15: Remove Empty Demo Directory
**Action**: DELETE
**Purpose**: Clean up empty demo directory

**Implementation**:
```bash
# Verify demo is empty (should only have .env.example and DEPLOY.md at most)
ls -la demo/

# Remove demo directory
rm -rf demo/

# Or use git rm if any tracked files remain
git rm -r demo/ 2>/dev/null || rm -rf demo/
```

**Validation**:
```bash
# Verify demo removed
ls demo/ 2>&1 | grep "No such file"

# Check git status
git status | grep demo
```

**Success Criteria**:
- [ ] `demo/` directory removed
- [ ] Git shows deletion or reports "nothing to commit"
- [ ] Clean working directory

---

## Risk Assessment

**Risk**: Import errors from missed path updates
- **Likelihood**: Low (Flask app is self-contained)
- **Mitigation**: Smoke test imports in Task 12

**Risk**: Docker build fails due to path misconfigurations
- **Likelihood**: Medium (multiple path references in docker-compose.yml)
- **Mitigation**: Task 13 validates docker compose config

**Risk**: Terraform module paths incorrect
- **Likelihood**: Low (sed replacement is straightforward)
- **Mitigation**: Task 8 validates with grep check

**Risk**: Missed demo references in docs
- **Likelihood**: Medium (documentation is scattered)
- **Mitigation**: Task 14 comprehensive grep search

**Risk**: Git history loss
- **Likelihood**: Very Low (using git mv consistently)
- **Mitigation**: Verify git log --follow after each move

## Integration Points

- **Flask App**: Environment variable `SPECS_PATH` changes default from `demo/infra` to `infra`
- **Docker Compose**: Build context and volume mounts updated to reference `src/`
- **Terraform**: Module source paths updated to new nested structure
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
cd src/backend && python -c "from app import app; print('✓')"

# 2. Docker compose parses
docker compose config >/dev/null && echo "✓"

# 3. No stray demo references in code
! grep -r "demo/" . --include="*.py" --include="*.yml" --include="*.tf" --exclude-dir=.git --exclude-dir=venv

# 4. Git history preserved
git log --follow src/backend/ | head -1
```

**Full test suite SKIPPED** (intentional):
- Lint: Skip (mechanical refactor)
- Tests: Skip (no logic changes)
- Build: Skip (validated in D2A-27/D2A-28)

**Rationale**: This is pure housekeeping. Real validation happens when features (D2A-27/D2A-28) exercise the refactored paths.

## Plan Quality Assessment

**Complexity Score**: 10/10 (HIGH - but mechanical)
**Confidence Score**: 8/10 (HIGH for execution, questions about missed references)

**Confidence Factors**:
- ✅ Clear requirements from spec
- ✅ Similar pattern from D2A-25 (archive PR used same git mv approach)
- ✅ User confirmed self-contained Flask app (minimal imports)
- ✅ User confirmed lightweight validation acceptable
- ✅ All files identified in codebase research
- ⚠️ Documentation scattered - may miss some demo references
- ⚠️ No test coverage to validate changes (intentional skip)

**Assessment**: High confidence for mechanical execution. Primary risk is missing demo references in documentation, but impact is low (docs only, not functional). Deferred validation to D2A-27/D2A-28 is pragmatic - those features will exercise all paths and reveal any issues.

**Estimated one-pass success probability**: 85%

**Reasoning**: This is straightforward file moves and path string replacements. The user's decision to defer comprehensive validation is appropriate - if any paths break, D2A-27/D2A-28 will immediately reveal them with clear error messages. The 15% risk accounts for potentially missed documentation references or edge cases in justfile/docker-compose configs, but these are low-impact issues easily fixed when discovered.
