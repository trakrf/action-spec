# Docker E2E Testing

Local end-to-end testing scripts for validating the production Docker container before deployment.

## Quick Start

### Quick Test (Fast)
```bash
./test-docker-quick.sh
```
- Builds image
- Starts container
- Tests health endpoint
- Tests root and favicon
- Leaves container running for manual testing
- ~30 seconds

### Comprehensive Test (Recommended)
```bash
./test-docker-local.sh
```
- Builds image
- Starts container with proper cleanup
- Tests all endpoints (health, SPA, static assets, API)
- Shows container stats and logs
- Auto-cleanup on exit
- ~60 seconds

## Prerequisites

- Docker installed and running
- (Optional) `GH_TOKEN` environment variable for GitHub API access
- `jq` for JSON parsing (comprehensive test only)

## Setting GitHub Token

For full functionality testing:

```bash
export GH_TOKEN="your_github_token_here"
./test-docker-local.sh
```

Without `GH_TOKEN`, the app will start but GitHub-dependent features won't work.

## What Gets Tested

### Quick Test (`test-docker-quick.sh`)
1. ✅ Docker build succeeds
2. ✅ Container starts
3. ✅ `/health` endpoint returns 200
4. ✅ Root `/` endpoint returns 200
5. ✅ `/favicon.ico` endpoint check
6. 📋 Shows recent logs

### Comprehensive Test (`test-docker-local.sh`)
1. ✅ Docker build succeeds
2. ✅ Container starts and stays healthy
3. ✅ `/health` endpoint returns healthy status JSON
4. ✅ Root `/` serves Vue SPA with `<div id="app">`
5. ✅ Static JavaScript assets load (HTTP 200)
6. ✅ Favicon handling (200 or 404 acceptable)
7. ✅ `/api/pods` endpoint (if GH_TOKEN available)
8. 📊 Container resource stats (CPU, memory)
9. 📋 Full container logs

## Troubleshooting

### Container fails to start
```bash
# Check logs
docker logs action-spec-e2e-test

# Or with quick test
docker logs action-spec-quick
```

### Health check fails
Common causes:
- Flask app not binding to 0.0.0.0:8080
- Gunicorn workers crashing
- Missing environment variables
- Static file serving errors

### Static assets return 500
This indicates the `serve_spa()` function in `app.py` has issues:
- Check Flask static folder configuration
- Verify `send_static_file()` returns properly
- Check for path traversal validation issues

### Port already in use
```bash
# Find process using port 8080
lsof -i :8080

# Or change port in script
PORT=8081 ./test-docker-quick.sh
```

## Manual Testing

After running `test-docker-quick.sh`, the container stays running:

```bash
# Test endpoints manually
curl http://localhost:8080/health
curl http://localhost:8080/
curl http://localhost:8080/api/pods

# View live logs
docker logs -f action-spec-quick

# Shell into container
docker exec -it action-spec-quick /bin/bash

# Stop and remove
docker stop action-spec-quick && docker rm action-spec-quick
```

## CI/CD Integration

Add to `.github/workflows/`:

```yaml
- name: Run E2E Docker tests
  run: ./test-docker-local.sh
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Known Issues

- Favicon 404 is acceptable (not critical)
- Without `GH_TOKEN`, API endpoints will return auth errors
- First build may take 2-3 minutes (subsequent builds are cached)

## Success Criteria

Both scripts should exit with code 0 and show:
- ✅ All tests passed
- 🎉 Production Docker container is working correctly

Any failures indicate issues that will occur in production deployment.
