#!/bin/bash
# Quick Docker E2E test - minimal version for fast iteration

set -e

IMAGE="action-spec-test"
CONTAINER="action-spec-quick"
PORT="${TEST_PORT:-8081}"

# Cleanup
docker stop $CONTAINER 2>/dev/null || true
docker rm $CONTAINER 2>/dev/null || true

echo "Building..."
docker build -t $IMAGE:latest . -q

echo "Starting container..."
docker run -d --name $CONTAINER -p $PORT:8080 \
    -e GH_TOKEN="${GH_TOKEN:-}" \
    $IMAGE:latest

echo "Waiting for health check..."
sleep 5

# Test health endpoint
for i in {1..10}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/health 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Health check passed!"
        curl -s http://localhost:$PORT/health | jq .

        echo ""
        echo "Testing root endpoint..."
        ROOT_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/)
        echo "Root endpoint: HTTP $ROOT_CODE"

        echo ""
        echo "Testing favicon..."
        FAV_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/favicon.ico)
        echo "Favicon: HTTP $FAV_CODE"

        echo ""
        echo "📋 Recent logs:"
        docker logs $CONTAINER 2>&1 | tail -15

        echo ""
        echo "Container running at http://localhost:$PORT"
        echo "To stop: docker stop $CONTAINER && docker rm $CONTAINER"
        exit 0
    fi
    echo "Attempt $i: HTTP $HTTP_CODE, retrying..."
    sleep 2
done

echo "❌ Health check failed after 20s"
echo "📋 Container logs:"
docker logs $CONTAINER 2>&1
docker stop $CONTAINER
docker rm $CONTAINER
exit 1
