#!/bin/bash
set -e

# E2E Test: Build and test production Docker container locally
# This validates that the container can start and respond to health checks

echo "🧪 E2E Test: Production Docker Container"
echo "=========================================="
echo ""

# Configuration
IMAGE_NAME="action-spec-test"
CONTAINER_NAME="action-spec-e2e-test"
PORT=8080
TIMEOUT=30

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo "✓ Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT

echo "📦 Step 1: Building Docker image..."
docker build -t "$IMAGE_NAME:test" . || {
    echo "❌ Docker build failed"
    exit 1
}
echo "✓ Image built successfully"
echo ""

echo "🚀 Step 2: Starting container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8080" \
    -e FLASK_ENV=production \
    "$IMAGE_NAME:test"
echo "✓ Container started: $CONTAINER_NAME"
echo ""

echo "⏳ Step 3: Waiting for container to be healthy..."
ELAPSED=0
HEALTHY=false

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check container status
    STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not_found")

    if [ "$STATUS" != "running" ]; then
        echo "❌ Container is not running (status: $STATUS)"
        echo ""
        echo "📋 Container logs:"
        docker logs "$CONTAINER_NAME" 2>&1 | tail -50
        exit 1
    fi

    # Try health check endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/health 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
        HEALTHY=true
        break
    fi

    echo "  ⏱️  Waiting... ($ELAPSED/${TIMEOUT}s) - HTTP $HTTP_CODE"
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ "$HEALTHY" = false ]; then
    echo "❌ Container failed to become healthy within ${TIMEOUT}s"
    echo ""
    echo "📋 Container logs:"
    docker logs "$CONTAINER_NAME" 2>&1 | tail -50
    exit 1
fi

echo "✓ Container is healthy (${ELAPSED}s)"
echo ""

echo "🔍 Step 4: Testing endpoints..."

# Test 1: Health check (detailed)
echo "  Test 1: GET /health"
HEALTH_RESPONSE=$(curl -s http://localhost:$PORT/health)
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status' 2>/dev/null || echo "error")

if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo "    ✓ Health check passed"
    echo "    Response: $HEALTH_RESPONSE" | head -c 200
    echo ""
else
    echo "    ❌ Health check failed"
    echo "    Response: $HEALTH_RESPONSE"
    exit 1
fi
echo ""

# Test 2: Root endpoint (SPA)
echo "  Test 2: GET / (SPA index.html)"
ROOT_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/)
if [ "$ROOT_CODE" = "200" ]; then
    echo "    ✓ Root endpoint returns 200"
    # Check for Vue app in HTML
    ROOT_CONTENT=$(curl -s http://localhost:$PORT/)
    if echo "$ROOT_CONTENT" | grep -q "div id=\"app\""; then
        echo "    ✓ Vue SPA detected in HTML"
    else
        echo "    ⚠️  Vue SPA not detected (might be an issue)"
    fi
else
    echo "    ❌ Root endpoint returned $ROOT_CODE"
    exit 1
fi
echo ""

# Test 3: Static assets
echo "  Test 3: Static assets"
ASSETS_RESPONSE=$(curl -s http://localhost:$PORT/ | grep -o 'src="[^"]*\.js"' | head -1 || echo "")
if [ -n "$ASSETS_RESPONSE" ]; then
    ASSET_PATH=$(echo "$ASSETS_RESPONSE" | sed 's/src="//g' | sed 's/"//g')
    echo "    Testing asset: $ASSET_PATH"
    ASSET_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT$ASSET_PATH")
    if [ "$ASSET_CODE" = "200" ]; then
        echo "    ✓ Static asset loads: $ASSET_PATH"
    else
        echo "    ❌ Static asset failed: $ASSET_PATH (HTTP $ASSET_CODE)"
        exit 1
    fi
else
    echo "    ⚠️  No JS assets found in HTML"
fi
echo ""

# Test 4: Favicon
echo "  Test 4: GET /favicon.ico"
FAVICON_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/favicon.ico)
if [ "$FAVICON_CODE" = "200" ]; then
    echo "    ✓ Favicon loads (HTTP 200)"
elif [ "$FAVICON_CODE" = "404" ]; then
    echo "    ⚠️  Favicon not found (HTTP 404) - this is OK"
else
    echo "    ❌ Favicon returned unexpected code: $FAVICON_CODE"
    # Don't fail on favicon issues
fi
echo ""

echo "  Test 5: OAuth authentication"
echo "    ⚠️  API endpoints require OAuth login (expected 401)"
PODS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/api/pods)
if [ "$PODS_CODE" = "401" ]; then
    echo "    ✓ API correctly requires authentication (HTTP 401)"
else
    echo "    ⚠️  Unexpected response: HTTP $PODS_CODE"
fi
echo ""

echo "📊 Step 5: Container stats"
docker stats "$CONTAINER_NAME" --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -2
echo ""

echo "📋 Step 6: Recent container logs (last 20 lines)"
echo "─────────────────────────────────────────────"
docker logs "$CONTAINER_NAME" 2>&1 | tail -20
echo "─────────────────────────────────────────────"
echo ""

echo "✅ All tests passed!"
echo ""
echo "🎉 Production Docker container is working correctly"
echo ""
echo "To manually test the running container:"
echo "  curl http://localhost:$PORT/health"
echo "  curl http://localhost:$PORT/"
echo ""
echo "To view logs:"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
echo "(Container will be cleaned up on exit)"
