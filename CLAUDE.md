# action-spec

Demo POC (v0.1.0) for YAML-driven infrastructure deployment via GitHub Actions. A web UI for editing YAML pod specifications that commits to Git and triggers Terraform via GitHub Actions.

## Stack

- **Backend**: Python 3.12 / Flask 3.0 (port 5000)
- **Frontend**: Vue 3 + Vite 5 + Tailwind CSS 4 (port 5173)
- **IaC**: Terraform / OpenTofu on AWS
- **Schema**: JSON Schema Draft-07 (`specs/schema/actionspec-v1.schema.json`)
- **Auth**: GitHub OAuth (repo + workflow scopes)

## Commands (justfile)

```bash
just dev                  # Docker Compose (frontend + backend)
just down                 # Stop Docker services
just lint                 # Lint all workspaces
just test                 # Test all workspaces
just build                # Build all workspaces
just validate             # Run lint, test, build
just frontend [cmd]       # Delegate to frontend justfile
just backend [cmd]        # Delegate to backend justfile
just test-docker-quick    # Fast Docker E2E test (~30s)
```

## Package Managers

- **Frontend**: pnpm exclusively (never npm/npx; use `pnpm dlx` not `npx`)
- **Backend**: uv for venv management, pip for packages

## Git Workflow

- Never push directly to main - always feature branches + PRs
- Never squash merge - use `--merge` to preserve commit history
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
- Branch naming: `feature/add-xyz`, `fix/broken-xyz`, `docs/update-xyz`

## Environment

- `.env.local` for secrets (git-ignored, loaded by direnv)
- `.envrc` with `dotenv_if_exists .env.local`
- Required: `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, `FLASK_SECRET_KEY`

## Project Structure

```
backend/           # Flask app (app.py, auth.py, api/)
frontend/          # Vue 3 SPA (src/components/, src/stores/)
infra/             # Terraform modules and pod specs
specs/             # JSON Schema + example YAML specs
scripts/           # Pre-commit hooks, test scripts
.github/workflows/ # CI/CD (deploy, security scan, CodeQL)
```

## Key Patterns

- Pod specs are YAML files at `infra/{customer}/{env}/spec.yml`
- GitOps: UI creates branch, commits spec, opens PR
- All GitHub API calls use the user's OAuth token (no app-level credentials)
- Input validation: path components (`^[a-zA-Z0-9_-]+$`), instance names (`^[a-z0-9-]+$`)

## Testing

- **Frontend**: Playwright E2E (headless only - no X windows on this system)
- **Backend**: pytest (placeholder - not fully configured)
- Always run headless: never use `--headed` flag with Playwright

## AI Behavior Rules

- Never assume missing context - ask if uncertain
- Never hallucinate libraries - only use verified packages
- Run tests before claiming completion
- Report actual status - no false optimism
