# Feature: Promote Demo POC to Main Implementation

## Origin
This specification follows from D2A-25 (archiving overengineered implementation). After archiving the complex Lambda/API Gateway code, we now promote the working POC from `/demo` to `/backend` as the official main implementation.

**Linear Issue**: D2A-26
**Branch**: `refactor/promote-demo-to-src`

## Outcome
The `/demo` directory will be moved to `/backend`, making the working Flask/Jinja POC the official main implementation. All references, imports, and configurations will be updated to reflect this promotion.

## User Story
As a **portfolio reviewer or future contributor**
I want **the main implementation to live in `/backend` not `/demo`**
So that **it's immediately clear this is production code, not experimental POC**

## Context

**Discovery**: The `/demo` POC proved the concept faster and more effectively than the enterprise implementation. It became the working solution.

**Current Problem**:
- Working implementation lives in `/demo/`, signaling "temporary" or "experimental"
- Portfolio narrative incomplete - archived old code but didn't promote new code
- Contributors might miss that `/demo` is the actual implementation
- Import paths have "demo" in them, suggesting non-production code

**Desired State**:
- Working implementation at `/backend/` signals "main application codebase"
- Infrastructure organized under `/infra/` (pod specs + modules) - standard Terraform convention
- Project tooling at root (`docker-compose.yml`, `justfile`) - standard convention
- Documentation in `/docs` (not scattered in demo)
- Clear separation: `/overengineered/` (archived), `/backend/` (app), `/infra/` (IaC), `/demo/` (removed)
- Clean import paths: `from backend` not `from demo.backend`
- Completes pivot narrative: "archived complex, promoted simple"

## Technical Requirements

### File Moves (Structure Preservation)

**Application Code** (moves to `/backend/`):
- [ ] Move `/demo/backend/` → `/backend/`
- [ ] Move `/demo/Dockerfile` → `/backend/Dockerfile`
- [ ] Move `/demo/README.md` → `/backend/README.md` (app-specific docs with app)
- [ ] Already in `/demo/backend/requirements.txt` (if not already there)

**Infrastructure Code** (organized under `/infra/`):
- [ ] Move `/demo/infra/` → `/infra/` (pod specifications - advworks, contoso, fabrikam)
- [ ] Move `/demo/tfmodules/` → `/infra/modules/` (Terraform modules with infra)

**Project Tooling** (moves to root):
- [ ] Move `/demo/docker-compose.yml` → `/docker-compose.yml` (orchestrates services from root)
- [ ] Move `/demo/justfile` → `/justfile` (task runner operates at project level)

**Documentation**:
- [ ] Move `/demo/SPEC.md` → `/docs/SPEC.md` (project documentation)

### Code Updates (Import Paths)
- [ ] Update Python imports in all `.py` files:
  - `from backend` → `from backend`
  - Any relative imports referencing demo
- [ ] Update any hardcoded path references in Python code
- [ ] Search for string literals containing "/demo/" or "demo/"

### Terraform Updates (Module Paths)
- [ ] Update module source paths in pod specs:
  - `source = "../../../tfmodules/pod"` → `source = "../../modules/pod"`
  - Check all `main.tf` files in infra/advworks/dev, infra/contoso/staging, etc.
- [ ] Verify Terraform init/plan still works after path changes

### Configuration Updates
- [ ] Update `docker-compose.yml` (now at root):
  - Volume mounts from `./demo/backend` → `./backend`
  - Build context from `./demo` → `./backend`
  - Working directories
  - Any environment variables referencing demo paths
- [ ] Update `.gitignore`:
  - Remove demo-specific entries if any
  - Add src-specific entries if needed
- [ ] Update GitHub Actions workflows:
  - Path filters (if any watch `/demo`)
  - Working directories in jobs
  - Any demo-specific steps

### Documentation Updates
- [ ] Update main `README.md`:
  - References to `/demo` → `/backend`
  - Remove "POC" or "demo" framing
  - Update Quick Start instructions
- [ ] Update `/demo/README.md` → `/backend/README.md`:
  - Reframe from "demo POC" to "main implementation"
  - Update architecture diagrams with new paths
  - Remove temporary/experimental language
- [ ] Update any other docs referencing demo paths

### Quality Gates
- [ ] Flask app runs: `cd backend && flask run`
- [ ] Docker compose works: `cd src && docker compose up`
- [ ] All Python imports resolve correctly (no ImportError)
- [ ] GitHub Actions/CI passes
- [ ] No grep results for `/demo/` in code (except git history and docs explaining the move)
- [ ] Git history preserved (use `git mv` for all moves)

## Implementation Order

**Critical**: Order matters to avoid breaking references

1. **Prepare**: Document current state (what's in /demo, what references it)
2. **Move application code**: Backend, Dockerfile → `/backend/`
3. **Move infrastructure code**: infra → root, tfmodules → `/infra/modules/`
4. **Move project tooling**: docker-compose.yml, justfile → root level
5. **Move documentation**: SPEC.md → `/docs/`, README.md → `/backend/`
6. **Update imports**: Python files referencing demo.backend
7. **Update Terraform references**: Module source paths in pod specs
8. **Update configs**: docker-compose.yml paths (now at root), .gitignore, justfile paths
9. **Update docs**: Main README.md references to demo paths
10. **Test locally**: Flask app, Docker compose (from root)
11. **Update CI/CD**: GitHub Actions workflows (if they reference demo/tfmodules paths)
12. **Final verification**: Full test suite, CI passes

## Why This Structure?

**Why `/backend` instead of `/src`?**
- POLS (Principle of Least Surprise): Industry-standard monorepo pattern
- Peer structure ready for `/frontend` when React UI ships (Phase 3.4)
- Clear semantic: "backend" describes WHAT, not just "source code"
- 90% of web projects with multiple services use this pattern
- Examples: MERN stack, Django+React, microservices all use service names at root

**Application code at `/backend/`**:
- Flask backend, Dockerfile, app-specific README
- Self-contained: application source code only
- Standard convention for multi-service projects

**Infrastructure organized under `/infra/`**:
- `/infra/advworks/`, `/infra/contoso/`, `/infra/fabrikam/` - Pod specifications
- `/infra/modules/pod/` - Reusable Terraform modules
- Follows standard Terraform convention (`modules/` subdirectory)
- Separate lifecycle from application code
- Less root-level clutter (POLS: everything infrastructure is under `/infra`)
- Supports multiple applications if needed later

**Project tooling at root level**:
- `/docker-compose.yml` - Service orchestration (run from project root)
- `/justfile` - Task runner with project-wide commands (WAF testing, Terraform, deployments)
- Standard convention: tooling that operates on the whole project lives at root
- You run `docker compose up` and `just <command>` from root, not from `/backend`

**Documentation under `/docs/`**:
- `/docs/SPEC.md` - Infrastructure specification documentation
- Standard convention: project docs separate from code

## Validation Criteria

**Success Metrics**:
- [ ] Flask app starts successfully from `/backend/`
- [ ] Docker compose up works (from root)
- [ ] All Python imports work (no ImportError exceptions)
- [ ] GitHub Actions CI passes
- [ ] No references to `/demo/` in active code (only git history)
- [ ] Main README clearly describes `/backend` as main implementation

**Test Cases**:
```bash
# Test Flask app
cd backend && flask run
# Should start without errors

# Test Docker compose (from root)
docker compose up
# Should build and start services

# Test imports
cd backend && python -c "from backend.app import app; print('✓ Imports work')"

# Test CI
git push origin refactor/promote-demo-to-src
# GitHub Actions should pass
```

**Edge Cases**:
- [ ] Environment variables in `.env` (if they reference demo paths)
- [ ] Terraform backend configs (if they have demo in state keys)
- [ ] Terraform module source paths in pod specs (must update to new location)
- [ ] GitHub Actions cache keys (if they include demo or tfmodules paths)
- [ ] Any shell scripts in justfile or elsewhere with hardcoded paths
- [ ] README references to tfmodules (should now reference infra/modules)

## Git Approach

**Use git mv to preserve history**:
```bash
# Application code to /backend
git mv demo/backend backend

# Infrastructure (organized under /infra)
git mv demo/infra infra
mkdir -p infra/modules
git mv demo/tfmodules/pod infra/modules/pod
rmdir demo/tfmodules  # Should be empty now

# Project tooling to root
git mv demo/docker-compose.yml docker-compose.yml
git mv demo/justfile justfile

# Documentation to docs
git mv demo/SPEC.md docs/SPEC.md
```

**Verification**:
```bash
# Verify history preserved
git log --follow --oneline src/backend/ | head -5
```

## Time Estimate
**Original estimate**: 15 minutes
**Realistic estimate**: 30-45 minutes
- 10 min: File moves (git mv)
- 15 min: Update imports and configs
- 10 min: Documentation updates
- 10 min: Testing and verification

## Portfolio Narrative

This PR completes the pivot story started with D2A-25:

**D2A-25**: "Here's what I overengineered (archived with explanation)"
**D2A-26**: "Here's the simple solution I shipped instead (promoted to main)"

Together they demonstrate:
- Course correction based on evidence
- Maturity to document mistakes
- Pragmatism to ship simple solutions
- Confidence to make big architectural decisions

## Anti-patterns to Avoid

- ❌ Don't just rename - this is a promotion, update framing in docs
- ❌ Don't forget import paths (will cause runtime errors)
- ❌ Don't skip testing after move (imports can silently break)
- ❌ Don't leave stale /demo references in docs
- ❌ Don't copy files (use git mv for history tracking)

## Related Work

- **D2A-25**: Archive overengineered implementation (completed)
- **Portfolio story**: Together these PRs tell a compelling narrative of engineering judgment

## Conversation References

**From Linear D2A-26**:
- Goal: "Promote working POC from `/demo` to `/backend` as the main implementation"
- What's moving: "The working Jinja-based demo that proved the concept"
- Estimate: 15 minutes (likely 30-45 with thorough testing)

**Key Decision**: Not just moving files - reframing from "demo/POC" to "production implementation"
