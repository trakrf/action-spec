# ActionSpec - Task Runner
# https://just.systems/

# List all available recipes
default:
    @just --list

# ============================================================================
# Workspace Delegation
# ============================================================================

frontend *args:
    cd frontend && just {{args}}

backend *args:
    cd backend && just {{args}}

alias fe := frontend
alias be := backend

# ============================================================================
# Development
# ============================================================================

# Start development environment (Docker Compose)
dev:
    @echo "🐳 Starting development environment..."
    @echo "📱 Frontend: http://localhost:5173"
    @echo "🔧 Backend: http://localhost:5000"
    @echo ""
    @echo "Press Ctrl+C to stop"
    docker compose up --build

# Stop development environment
down:
    docker compose down

# View development logs
logs:
    docker compose logs -f

# Local development without Docker (not recommended)
dev-local:
    #!/usr/bin/env bash
    set -m
    echo "🚀 Starting local development servers..."
    echo "📱 Frontend: http://localhost:5173"
    echo "🔧 Backend: http://localhost:5000"
    echo ""
    cleanup() {
        echo ""
        echo "🛑 Stopping servers..."
        for pid in $(jobs -p); do
            pkill -15 -P $pid 2>/dev/null || true
            kill -15 $pid 2>/dev/null || true
        done
        sleep 1
        for pid in $(jobs -p); do
            pkill -9 -P $pid 2>/dev/null || true
            kill -9 $pid 2>/dev/null || true
        done
        exit 0
    }
    trap cleanup INT TERM
    (cd frontend && just dev </dev/null) &
    (cd backend && just dev </dev/null) &
    wait

# ============================================================================
# Setup & Cleanup
# ============================================================================

# Setup all workspaces
setup:
    @echo "📦 Setting up all workspaces..."
    @just backend setup
    @just frontend install
    @echo "✅ Setup complete!"

# Clean all workspaces
clean:
    @just backend clean
    @just frontend clean

# Check environment variables
check-env:
    #!/usr/bin/env bash
    [ -f ".env.local" ] && source .env.local
    echo "Checking required environment variables..."
    [ -z "${GH_TOKEN:-}" ] && echo "❌ GH_TOKEN not set" || echo "✓ GH_TOKEN is set"
    echo "✓ GH_REPO=${GH_REPO:-trakrf/action-spec}"
    echo "✓ SPECS_PATH=${SPECS_PATH:-infra}"

# ============================================================================
# Validation
# ============================================================================

# Lint all workspaces
lint: (frontend "lint") (backend "lint")

# Test all workspaces
test: (frontend "test") (backend "test")

# Build all workspaces
build: (frontend "build") (backend "build")

# Run all validation checks
validate: lint test build

# Alias for CI/CD
check: validate

# ============================================================================
# Docker E2E Testing
# ============================================================================

# Quick Docker test - fast iteration (~30s)
test-docker-quick:
    @echo "🧪 Running quick Docker E2E test..."
    @./scripts/test-docker-quick.sh

# Comprehensive Docker test - full validation (~60s)
test-docker:
    @echo "🧪 Running comprehensive Docker E2E test..."
    @./scripts/test-docker-local.sh

# Alias for quick test
test-e2e: test-docker-quick

# Run all tests including Docker E2E
test-all: test test-docker

