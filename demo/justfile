# Flask Development Commands for Demo Backend

# Default recipe - show available commands
default:
    @just --list

# Start Flask development server
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend

    # Load environment variables from root .env.local
    if [ -f "../.env.local" ]; then
        set -a
        source ../.env.local
        set +a
        echo "✓ Loaded environment from .env.local"
    else
        echo "⚠️  Warning: .env.local not found in root directory"
    fi

    # Activate venv
    if [ ! -d "venv" ]; then
        echo "❌ Virtual environment not found. Run: just setup"
        exit 1
    fi

    source venv/bin/activate
    echo "✓ Virtual environment activated"
    echo ""
    echo "🚀 Starting Flask development server..."
    echo "   Open http://localhost:5000 in your browser"
    echo "   Press Ctrl+C to stop"
    echo ""
    flask --app app run --debug --host 0.0.0.0

# Set up virtual environment and install dependencies
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend

    echo "Creating virtual environment..."
    python3 -m venv venv

    echo "Installing dependencies..."
    venv/bin/pip install -q -r requirements.txt

    echo "✓ Setup complete!"
    echo "  Run 'just dev' to start the Flask server"

# Clean up virtual environment and cache
clean:
    #!/usr/bin/env bash
    cd backend
    rm -rf venv __pycache__ templates/__pycache__ .pytest_cache
    echo "✓ Cleaned up venv and cache files"

# Run health check (requires server to be running)
health:
    @curl -s http://localhost:5000/health | python3 -m json.tool

# Test pod discovery (requires server to be running)
test-home:
    @curl -s http://localhost:5000/ | head -30

# Run Flask with custom port
dev-port PORT:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend

    if [ -f "../.env.local" ]; then
        set -a
        source ../.env.local
        set +a
    fi

    source venv/bin/activate
    echo "🚀 Starting Flask on port {{PORT}}..."
    flask --app app run --debug --host 0.0.0.0 --port {{PORT}}

# Show Flask logs (if running in background)
logs-flask:
    @tail -f /tmp/flask_run.log 2>/dev/null || echo "No Flask logs found at /tmp/flask_run.log"

# Check if all environment variables are set
check-env:
    #!/usr/bin/env bash
    if [ -f ".env.local" ]; then
        source .env.local
    fi

    echo "Checking required environment variables..."

    if [ -z "${GH_TOKEN:-}" ]; then
        echo "❌ GH_TOKEN not set"
    else
        echo "✓ GH_TOKEN is set"
    fi

    echo "✓ GH_REPO=${GH_REPO:-trakrf/action-spec}"
    echo "✓ SPECS_PATH=${SPECS_PATH:-demo/infra}"

# === Docker Compose Commands ===

# Start docker compose services (detached)
up:
    #!/usr/bin/env bash
    set -euo pipefail

    if [ ! -f ".env" ]; then
        echo "⚠️  Warning: .env file not found"
        echo "   Copy .env.example and add your GH_TOKEN:"
        echo "   cp .env.example .env"
        echo ""
    fi

    echo "🚀 Starting docker compose services..."
    docker compose up -d
    echo ""
    echo "✓ Services started"
    echo "  Spec-editor: http://localhost:5000"
    echo "  Demo app: http://localhost:8080"
    echo ""
    echo "Run 'just logs' to view logs"
    echo "Run 'just ps' to check status"

# Stop docker compose services
down:
    #!/usr/bin/env bash
    echo "🛑 Stopping docker compose services..."
    docker compose down
    echo "✓ Services stopped"

# View logs from all services
logs:
    docker compose logs -f

# View logs from spec-editor only
logs-spec:
    docker compose logs -f spec-editor

# View logs from demo-app only
logs-demo:
    docker compose logs -f demo-app

# Restart docker compose services
restart:
    #!/usr/bin/env bash
    echo "🔄 Restarting docker compose services..."
    docker compose restart
    echo "✓ Services restarted"

# Restart only spec-editor
restart-spec:
    docker compose restart spec-editor

# Rebuild docker images (no cache)
build:
    #!/usr/bin/env bash
    echo "🔨 Building docker images..."
    docker compose build --no-cache
    echo "✓ Build complete"

# Rebuild and restart services
rebuild: build
    just down
    just up

# Show running containers
ps:
    docker compose ps

# Check health of spec-editor
health-docker:
    @echo "Checking spec-editor health..."
    @curl -s http://localhost:5000/health | python3 -m json.tool || echo "❌ Service not responding"

# Pull latest published image from GHCR
pull:
    #!/usr/bin/env bash
    echo "📥 Pulling latest image from GHCR..."
    docker compose pull
    echo "✓ Pull complete. Run 'just up' to use the latest image"

# Clean up docker volumes and orphaned containers
clean-docker:
    #!/usr/bin/env bash
    echo "🧹 Cleaning up docker resources..."
    docker compose down -v --remove-orphans
    echo "✓ Cleanup complete"

# === WAF Testing Commands ===

# Test WAF path-based filtering (requires ALB_URL env var or argument)
waf-test-paths ALB_URL="":
    #!/usr/bin/env bash
    set -euo pipefail

    URL="${1:-${ALB_URL:-}}"
    if [ -z "$URL" ]; then
        echo "❌ Error: ALB_URL not provided"
        echo "Usage: just waf-test-paths <alb-url>"
        echo "   or: ALB_URL=http://... just waf-test-paths"
        exit 1
    fi

    # Remove trailing slash
    URL="${URL%/}"

    echo "🔒 Testing WAF Path-Based Filtering"
    echo "Target: $URL"
    echo ""

    echo "✅ Testing ALLOWED paths (should return 200):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo -n "  /spec ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/spec")
    if [ "$STATUS" = "200" ]; then
        echo "✅ $STATUS"
    else
        echo "❌ $STATUS (expected 200)"
    fi

    echo -n "  /health ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/health")
    if [ "$STATUS" = "200" ]; then
        echo "✅ $STATUS"
    else
        echo "❌ $STATUS (expected 200)"
    fi

    echo -n "  /api/v1/test ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/api/v1/test")
    if [ "$STATUS" = "200" ]; then
        echo "✅ $STATUS"
    else
        echo "❌ $STATUS (expected 200)"
    fi

    echo -n "  / (root) ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/")
    if [ "$STATUS" = "200" ]; then
        echo "✅ $STATUS"
    else
        echo "❌ $STATUS (expected 200)"
    fi

    echo ""
    echo "❌ Testing BLOCKED paths (should return 403):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo -n "  /admin ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/admin")
    if [ "$STATUS" = "403" ]; then
        echo "✅ $STATUS (blocked)"
    else
        echo "❌ $STATUS (expected 403)"
    fi

    echo -n "  /malicious ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/malicious")
    if [ "$STATUS" = "403" ]; then
        echo "✅ $STATUS (blocked)"
    else
        echo "❌ $STATUS (expected 403)"
    fi

    echo -n "  /../../etc/passwd ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/../../etc/passwd")
    if [ "$STATUS" = "403" ]; then
        echo "✅ $STATUS (blocked)"
    else
        echo "❌ $STATUS (expected 403)"
    fi

    echo -n "  /api/v2/test ... "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/api/v2/test")
    if [ "$STATUS" = "403" ]; then
        echo "✅ $STATUS (blocked - only /api/v1/* allowed)"
    else
        echo "❌ $STATUS (expected 403)"
    fi

    echo ""
    echo "✓ Path filtering test complete"

# Test WAF rate-based filtering (fire 200 requests to trigger rate limit)
waf-test-rate ALB_URL="" PATH="/health":
    #!/usr/bin/env bash
    set -euo pipefail

    URL="${1:-${ALB_URL:-}}"
    TEST_PATH="${2:-/health}"

    if [ -z "$URL" ]; then
        echo "❌ Error: ALB_URL not provided"
        echo "Usage: just waf-test-rate <alb-url> [path]"
        echo "   or: ALB_URL=http://... just waf-test-rate"
        exit 1
    fi

    # Remove trailing slash
    URL="${URL%/}"
    FULL_URL="$URL$TEST_PATH"

    echo "🔒 Testing WAF Rate-Based Filtering"
    echo "Target: $FULL_URL"
    echo "Limit: 10 requests per 60 seconds"
    echo "Test: Firing 200 requests to trigger rate limit"
    echo ""

    SUCCESS_COUNT=0
    BLOCKED_COUNT=0
    FIRST_BLOCK=""

    echo "Sending requests (watching for 200→403 transition):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    for i in {1..200}; do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FULL_URL")

        if [ "$STATUS" = "200" ]; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            printf "."
        elif [ "$STATUS" = "403" ]; then
            if [ -z "$FIRST_BLOCK" ]; then
                FIRST_BLOCK=$i
                echo ""
                echo "⚠️  Rate limit triggered at request #$i"
                echo "   Now showing blocked requests..."
            fi
            BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
            printf "X"
        else
            printf "?"
        fi

        # Show progress every 50 requests
        if [ $((i % 50)) -eq 0 ]; then
            echo " [$i/200]"
        fi
    done

    echo ""
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Results:"
    echo "  Total requests: 200"
    echo "  Successful (200): $SUCCESS_COUNT"
    echo "  Blocked (403): $BLOCKED_COUNT"

    if [ -n "$FIRST_BLOCK" ]; then
        echo "  First block at request: #$FIRST_BLOCK"
        echo ""
        echo "✅ Rate limiting is WORKING"
        echo "   WAF blocked requests after threshold reached"
    else
        echo ""
        echo "⚠️  Rate limiting NOT triggered"
        echo "   All 200 requests returned 200 OK"
        echo "   Check WAF configuration"
    fi

    echo ""
    echo "💡 Note: Wait 60+ seconds for rate limit to reset"

# Run both WAF tests sequentially
waf-test-all ALB_URL="":
    #!/usr/bin/env bash
    URL="${1:-${ALB_URL:-}}"

    if [ -z "$URL" ]; then
        echo "❌ Error: ALB_URL not provided"
        echo "Usage: just waf-test-all <alb-url>"
        exit 1
    fi

    just waf-test-paths "$URL"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    just waf-test-rate "$URL"
