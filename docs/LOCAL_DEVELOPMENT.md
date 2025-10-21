# Local Development Guide

Guide for developing and testing the ActionSpec backend locally.

## Prerequisites

### Required
- **Python 3.11+**
  ```bash
  python3 --version  # Should be 3.11 or higher
  ```

- **AWS CLI**
  ```bash
  aws --version
  aws configure  # Set up credentials
  ```

- **AWS SAM CLI**
  ```bash
  # Install SAM CLI
  # macOS
  brew install aws-sam-cli

  # Linux
  pip3 install aws-sam-cli

  # Verify
  sam --version  # Should be >= 1.100.0
  ```

- **Docker** (for `sam local start-api`)
  ```bash
  docker --version
  ```

### Optional
- **pytest** (for running tests)
  ```bash
  pip3 install -r backend/tests/requirements.txt
  ```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/trakrf/action-spec.git
cd action-spec

# Copy environment template
cp env.json.example env.json

# Edit env.json if needed (defaults work for local)
```

### 2. Build SAM Application

```bash
sam build
```

This compiles the Lambda functions and packages dependencies.

### 3. Start Local API

```bash
sam local start-api
```

API will be available at `http://localhost:3000`

### 4. Test Endpoints

```bash
# Test form endpoint
curl http://localhost:3000/api/form

# Test discover endpoint
curl http://localhost:3000/api/discover

# Test parse endpoint
curl -X POST http://localhost:3000/api/parse

# Test submit endpoint
curl -X POST http://localhost:3000/api/submit
```

All endpoints should return 200 with stub JSON responses.

## Testing Options

### Option 1: SAM Local (Docker Required)

```bash
# Start API
sam local start-api &

# Run smoke tests
export API_ENDPOINT=http://localhost:3000
pytest backend/tests/test_smoke.py -v

# Stop API
killall sam
```

### Option 2: Standalone Test Harness (No Docker)

```bash
# Test handlers directly
./scripts/test-local.sh
```

This runs each Lambda handler in-process without Docker.

### Option 3: Unit Tests Only

```bash
# Test security wrapper
pytest backend/tests/test_security_wrapper.py -v

# Test with coverage
pytest backend/tests/ --cov=backend/lambda/shared --cov-report=html
```

## Development Workflow

### Modify Lambda Function

1. Edit handler: `backend/lambda/functions/{function}/handler.py`
2. Rebuild: `sam build`
3. Test: `sam local start-api` or `./scripts/test-local.sh`

### Modify SAM Template

1. Edit: `template.yaml`
2. Validate: `sam validate --lint`
3. Build: `sam build`
4. Deploy: `./scripts/deploy-backend.sh`

### Modify Security Wrapper

1. Edit: `backend/lambda/shared/security_wrapper.py`
2. Test: `pytest backend/tests/test_security_wrapper.py`
3. Rebuild layer: `sam build`

## Troubleshooting

### "Module not found" error

**Problem**: Lambda can't import `security_wrapper`

**Solution**: Check Lambda layer configuration in `template.yaml`:
```yaml
Layers:
  - !Ref SharedDependenciesLayer
```

Rebuild: `sam build`

### SAM local not starting

**Problem**: `sam local start-api` hangs or fails

**Solutions**:
1. Check Docker is running: `docker ps`
2. Clear SAM cache: `rm -rf .aws-sam/`
3. Rebuild: `sam build`
4. Use standalone test harness: `./scripts/test-local.sh`

### API returns 403 Forbidden

**Problem**: API Gateway requires API key

**Solution**: SAM local may not enforce API keys in development mode. This is expected. In deployed environment, use:
```bash
export API_KEY=$(aws apigateway get-api-key --api-key $API_KEY_ID --include-value --query 'value' --output text)
curl -H "x-api-key: $API_KEY" $API_ENDPOINT/api/form
```

### Tests fail with connection error

**Problem**: `pytest backend/tests/test_smoke.py` fails

**Solution**:
1. Ensure SAM local is running: `sam local start-api`
2. Verify endpoint: `curl http://localhost:3000/api/form`
3. Check Docker: `docker ps` should show Lambda containers

### Import errors in tests

**Problem**: `ModuleNotFoundError: No module named 'security_wrapper'`

**Solution**:
```bash
# Add to PYTHONPATH
export PYTHONPATH="${PWD}/backend/lambda/shared:${PYTHONPATH:-}"

# Or use standalone test harness
./scripts/test-local.sh
```

## Environment Variables

### Local Development (env.json)

```json
{
  "Parameters": {
    "ENVIRONMENT": "local",
    "SPECS_BUCKET": "actionspec-backend-specs-local",
    "GITHUB_TOKEN_SSM_PARAM": "/actionspec/github-token"
  }
}
```

### Deployment (Environment Variables)

```bash
export AWS_REGION=us-west-2
export ENVIRONMENT=demo
export GITHUB_TOKEN_SSM_PARAM=/actionspec/github-token

./scripts/deploy-backend.sh
```

## Debugging

### Enable Verbose Logging

```bash
# SAM local with debug
sam local start-api --debug

# Lambda with debug logging
export SAM_CLI_TELEMETRY=0
export SAM_CLI_DEBUG=1
```

### View Lambda Logs

```bash
# SAM local shows logs in terminal

# Deployed Lambda
aws logs tail /aws/lambda/actionspec-backend-form-generator --follow
```

### Invoke Lambda Directly

```bash
# Test single function
echo '{}' | sam local invoke FormGeneratorFunction

# With event file
sam local invoke SpecParserFunction -e events/test-event.json
```

## Performance Tips

### Speed Up Builds

```bash
# Use cached builds
sam build --cached --parallel

# Skip dependency installation if unchanged
sam build --use-container --skip-pull-image
```

### Warm Containers

In `samconfig.toml`:
```toml
[default.local_start_api.parameters]
warm_containers = "EAGER"
```

## Next Steps

After local development works:

1. **Deploy to AWS**: `./scripts/deploy-backend.sh`
2. **Setup SSM Parameter**: `./scripts/setup-ssm-params.sh`
3. **Run deployed tests**:
   ```bash
   export API_ENDPOINT=https://xxx.execute-api.us-west-2.amazonaws.com/demo
   export API_KEY=your-api-key
   pytest backend/tests/test_smoke.py
   ```
4. **Move to Phase 3.2**: Implement actual spec parsing logic

## Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [SAM CLI Reference](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-command-reference.html)
- [Lambda Python Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
- [API Gateway Local Testing](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-start-api.html)
