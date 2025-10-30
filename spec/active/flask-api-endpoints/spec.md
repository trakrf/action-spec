# Feature: Flask REST API Endpoints for Frontend Decoupling

## Origin
This specification is extracted from Linear issue D2A-27, part of a phased migration strategy to decouple the Flask backend from Jinja templates and enable Vue.js frontend development.

## Outcome
The Flask application will expose REST API endpoints that provide the same data currently embedded in Jinja templates, enabling parallel development of a Vue.js frontend while maintaining backward compatibility with existing template-based routes.

## User Story
As a **frontend developer migrating to Vue.js**
I want **REST API endpoints that provide blueprint, AWS resource, and deployment data**
So that **I can build a Vue frontend without modifying backend logic or breaking existing Jinja functionality**

## Context

**Discovery**: The current Flask application tightly couples data fetching with template rendering, making frontend migration require backend changes.

**Current State**:
- Flask app uses Jinja templates for all UI rendering
- Backend logic embedded in route handlers that return rendered HTML
- No separation between data layer and presentation layer

**Desired State**:
- Flask exposes JSON API endpoints for all data operations
- Jinja routes continue to work (backward compatibility)
- Vue frontend can be developed in parallel without backend changes
- Clear migration path to fully replace Jinja templates

**Strategic Context**:
- This is PR-3a in a multi-phase Vue migration
- Phase 3a: Add API endpoints (this spec)
- Future phases: Build Vue frontend, deprecate Jinja
- Enables parallel team workflows

## Technical Requirements

### API Endpoints

#### 1. `GET /api/blueprint`
- Fetch blueprint.yml from GitHub repository
- Return raw YAML content or parsed JSON structure
- Handle GitHub API authentication securely
- Error handling: 404 if file not found, 401 if auth fails, 500 for GitHub API errors

#### 2. `GET /api/config`
- Return parsed YAML structure from blueprint.yml
- Validate YAML structure before returning
- Error handling: 400 if YAML is malformed, 404 if file missing

#### 3. `GET /api/aws/subnets`
- List EC2 subnets with VPC context
- Include: subnet ID, CIDR, VPC ID, availability zone, tags
- Consider pagination for large AWS accounts
- Error handling: 401 for credential issues, 500 for AWS API errors

#### 4. `GET /api/aws/amis`
- List AMIs sorted by creation date (newest first)
- Filter criteria: owner, name pattern (query params)
- Include: AMI ID, name, creation date, state
- Error handling: Similar to subnets endpoint

#### 5. `GET /api/aws/snapshots`
- List EBS snapshots with status
- Include: snapshot ID, volume ID, state, progress, start time
- Consider pagination
- Error handling: Similar to subnets endpoint

#### 6. `POST /api/validate`
- Validate that CIDRs and AMIs exist in AWS
- Request body: `{"cidrs": [...], "ami_ids": [...]}`
- Response: Validation results with specific errors per resource
- Error handling: 400 for invalid input format, detailed validation errors in 200 response

#### 7. `POST /api/deploy`
- Trigger GitHub Actions workflow_dispatch
- Request body: Deployment parameters
- Response: Workflow run ID or confirmation
- Error handling: 401 for auth, 400 for invalid params, 500 for GitHub API errors

### Cross-Cutting Requirements

#### CORS Configuration
- Enable CORS for local development (http://localhost:*)
- Configurable via environment variable to disable in production
- Proper handling of preflight OPTIONS requests
- **Security note**: Do not use `*` wildcard in production

#### Backward Compatibility
- All existing Jinja template routes must continue working
- No breaking changes to current functionality
- Existing route handlers can call new API logic internally (DRY principle)

#### Error Handling
- Consistent JSON error responses: `{"error": "message", "details": {...}}`
- Appropriate HTTP status codes:
  - 200: Success
  - 400: Bad request (validation errors)
  - 401: Authentication failure
  - 404: Resource not found
  - 500: Server error (AWS/GitHub API failures)

#### Security Considerations
- AWS credentials via boto3 default credential chain
- GitHub token from environment variable, never hardcoded
- Input validation for all POST endpoints
- No sensitive data in error messages

#### Performance
- Consider caching for AWS resource queries (AMIs change infrequently)
- Handle AWS pagination to avoid timeouts on large datasets
- Async operations for long-running tasks (deployment)

## Implementation Notes

### Code Organization
```python
# Suggested structure
/backend
  /api
    __init__.py          # API blueprint registration
    /routes
      blueprint.py       # Blueprint/config endpoints
      aws.py            # AWS resource endpoints
      deploy.py         # Deployment endpoint
    /services
      github_service.py  # GitHub API client
      aws_service.py     # AWS API client
      validator.py       # Validation logic
```

### AWS Service Pattern
```python
# Example pattern for AWS endpoints
def get_subnets():
    try:
        ec2 = boto3.client('ec2')
        response = ec2.describe_subnets()
        subnets = []
        for subnet in response['Subnets']:
            subnets.append({
                'id': subnet['SubnetId'],
                'cidr': subnet['CidrBlock'],
                'vpc_id': subnet['VpcId'],
                'az': subnet['AvailabilityZone'],
                'tags': subnet.get('Tags', [])
            })
        return jsonify(subnets), 200
    except ClientError as e:
        return jsonify({'error': str(e)}), 500
```

### CORS Setup
```python
# Conditional CORS for development
if os.getenv('FLASK_ENV') == 'development':
    from flask_cors import CORS
    CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])
```

## Validation Criteria

### Functional Tests
- [ ] `/api/blueprint` returns valid blueprint.yml content
- [ ] `/api/config` returns correctly parsed YAML structure
- [ ] `/api/aws/subnets` returns subnets with VPC context
- [ ] `/api/aws/amis` returns AMIs sorted by date (newest first)
- [ ] `/api/aws/snapshots` returns snapshots with status
- [ ] `/api/validate` correctly identifies invalid CIDRs/AMIs
- [ ] `/api/deploy` triggers workflow_dispatch successfully
- [ ] All endpoints return proper JSON responses

### Error Handling Tests
- [ ] Endpoints return appropriate error codes for missing resources
- [ ] AWS credential failures are handled gracefully
- [ ] GitHub API failures are handled gracefully
- [ ] Invalid input is rejected with 400 status
- [ ] Error responses include helpful messages

### Compatibility Tests
- [ ] All existing Jinja routes still work
- [ ] No breaking changes to current functionality
- [ ] Jinja routes can coexist with API routes

### Security Tests
- [ ] CORS only enabled for allowed origins
- [ ] No sensitive data in error messages
- [ ] GitHub token not exposed in responses
- [ ] Input validation prevents injection attacks

### Performance Tests
- [ ] AWS queries complete within reasonable time (<5s)
- [ ] Large result sets don't cause timeouts
- [ ] Concurrent requests handled correctly

### Integration Tests
- [ ] Test with curl/Postman (manual verification)
- [ ] Test from Vue dev server with CORS
- [ ] Test error scenarios end-to-end

## Success Criteria

**This feature is complete when:**
1. All 7 API endpoints are implemented and tested
2. Vue.js frontend can fetch all necessary data via API
3. Existing Jinja functionality is unaffected
4. CORS works for local development
5. Error handling is consistent and helpful
6. Documentation exists for each endpoint

## Future Considerations

**After this PR:**
- Build Vue.js frontend consuming these APIs (Phase 3b)
- Add API authentication/authorization if needed
- Implement caching layer for AWS queries
- Deprecate Jinja routes once Vue is complete
- Consider API versioning strategy (`/api/v1/...`)

## Questions to Resolve

1. **Data format**: Should `/api/blueprint` return raw YAML or parsed JSON?
2. **Pagination**: Do we need pagination for AWS endpoints now, or acceptable to implement later?
3. **Authentication**: Do API endpoints need authentication, or rely on network security?
4. **Rate limiting**: Should we add rate limiting to prevent abuse?
5. **Async deployment**: Should `/api/deploy` be synchronous or return immediately with job ID?

## References

- Linear Issue: [D2A-27](https://linear.app/trakrf/issue/D2A-27/pr-3a-add-flask-api-endpoints-keep-jinja)
- PR Branch: `feature/flask-api-endpoints`
- Estimate: 30 minutes (from Linear)
- Priority: High
- Project: MediaCo spec editor phase 2
