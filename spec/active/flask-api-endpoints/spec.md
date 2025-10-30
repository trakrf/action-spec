# Feature: Flask REST API Endpoints for Frontend Decoupling

## Origin
This specification is extracted from Linear issue D2A-27, part of a phased migration strategy to decouple the Flask backend from Jinja templates and enable Vue.js frontend development.

## Outcome
The Flask application will expose REST API endpoints that provide the same data currently embedded in Jinja templates, enabling parallel development of a Vue.js frontend while maintaining backward compatibility with existing template-based routes.

## User Story
As a **frontend developer migrating to Vue.js**
I want **REST API endpoints that provide pod listing, blueprint YAML, and deployment data**
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

Based on the current Flask application which uses GitHub API and YAML parsing (NO AWS integration exists):

#### 1. `GET /api/pods`
- List all pods (customer/environment combinations) discovered from GitHub repository structure
- Returns: Array of `{customer: string, env: string}` objects
- Uses existing `list_all_pods()` function logic
- Error handling: 500 for GitHub API errors

#### 2. `GET /api/pod/<customer>/<env>`
- Fetch spec.yml for a specific pod from GitHub
- Returns: Parsed YAML structure with blueprint configuration
- Uses existing `fetch_spec(customer, env)` function logic
- Error handling: 404 if pod not found, 500 for GitHub API errors

#### 3. `POST /api/pod`
- Create or update a pod specification
- Request body: `{customer: string, env: string, spec: object, commit_message?: string}`
- Creates GitHub branch and pull request using existing deployment logic
- Response: `{branch: string, pr_url: string}`
- Error handling: 400 for invalid input, 500 for GitHub API errors

#### 4. `GET /api/health`
- Health check endpoint (already exists but may need JSON response)
- Returns: `{status: "ok", github_connected: boolean}`
- Verify GitHub API connectivity
- Error handling: 500 if GitHub unreachable

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
- GitHub token from environment variable (GH_TOKEN), never hardcoded
- Input validation for all POST endpoints
- No sensitive data in error messages
- YAML validation to prevent injection attacks

#### Performance
- Consider caching for pod listing (GitHub API rate limits)
- GitHub PR creation is async by nature (returns immediately)
- YAML parsing should be fast for typical spec sizes

## Implementation Notes

### Code Organization
```python
# Option 1: Minimal - Add API routes directly to backend/app.py
# Since we only have 4 endpoints and they reuse existing functions

# Option 2: Organized - Extract to blueprint (recommended for maintainability)
/backend
  /api
    __init__.py          # API blueprint registration
    /routes
      pods.py            # Pod listing and CRUD endpoints
      health.py          # Health check endpoint
```

### API Implementation Pattern
```python
# Example: Reuse existing logic for API endpoints
from flask import Blueprint, jsonify, request

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/pods', methods=['GET'])
def get_pods():
    try:
        pods = list_all_pods()  # Reuse existing function
        return jsonify(pods), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/pod/<customer>/<env>', methods=['GET'])
def get_pod(customer, env):
    try:
        spec = fetch_spec(customer, env)  # Reuse existing function
        if spec is None:
            return jsonify({'error': 'Pod not found'}), 404
        return jsonify(spec), 200
    except Exception as e:
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
- [ ] `GET /api/pods` returns array of all customer/environment combinations
- [ ] `GET /api/pod/<customer>/<env>` returns parsed spec.yml for valid pod
- [ ] `POST /api/pod` creates GitHub branch and PR successfully
- [ ] `GET /api/health` returns JSON status with GitHub connectivity check
- [ ] All endpoints return proper JSON responses

### Error Handling Tests
- [ ] `GET /api/pod/<customer>/<env>` returns 404 for non-existent pod
- [ ] GitHub API failures are handled gracefully with 500 status
- [ ] Invalid POST input is rejected with 400 status
- [ ] Error responses include helpful messages in consistent format

### Compatibility Tests
- [ ] All existing Jinja routes still work (`/`, `/pod/<c>/<e>`, `/pod/new`, `/deploy`)
- [ ] No breaking changes to current functionality
- [ ] Jinja routes can coexist with API routes
- [ ] Existing functions (fetch_spec, list_all_pods, etc.) work unchanged

### Security Tests
- [ ] CORS only enabled for allowed origins (localhost in dev)
- [ ] No sensitive data (GH_TOKEN) in error messages
- [ ] GitHub token not exposed in responses
- [ ] YAML input validation prevents injection attacks
- [ ] POST endpoint validates customer/env naming patterns

### Performance Tests
- [ ] Pod listing completes within reasonable time (<2s typical)
- [ ] GitHub API rate limits considered (caching strategy)
- [ ] Concurrent requests handled correctly

### Integration Tests
- [ ] Test with curl/Postman (manual verification)
- [ ] Test from Vue dev server with CORS enabled
- [ ] Test error scenarios end-to-end
- [ ] Verify PR creation workflow from API

## Success Criteria

**This feature is complete when:**
1. All 4 API endpoints are implemented and tested
2. Vue.js frontend can fetch pod data and create/update pods via API
3. Existing Jinja functionality is unaffected (backward compatibility verified)
4. CORS works for local development (Vue dev server can connect)
5. Error handling is consistent and helpful (JSON format, proper status codes)
6. Manual API testing completed with curl/Postman

## Future Considerations

**After this PR:**
- Build Vue.js frontend consuming these APIs (Phase 3b)
- Add API authentication/authorization if needed (currently relies on network security)
- Implement caching layer for pod listing (GitHub API rate limits)
- Deprecate Jinja routes once Vue frontend is complete
- Consider API versioning strategy (`/api/v1/...`) before public release
- **Potential future AWS integration** (if needed - not in current scope)

## Questions to Resolve

1. **Pod listing format**: Should `/api/pods` return just `{customer, env}` or include additional metadata?
2. **Authentication**: Do API endpoints need authentication, or rely on network security? (Current app has no auth)
3. **Rate limiting**: Should we add rate limiting to prevent abuse?
4. **Caching**: Should we cache pod listing results, and if so, for how long?
5. **POST response**: Should `/api/pod` wait for PR creation or return immediately?

## References

- Linear Issue: [D2A-27](https://linear.app/trakrf/issue/D2A-27/pr-3a-add-flask-api-endpoints-keep-jinja)
- PR Branch: `feature/flask-api-endpoints`
- Estimate: 15-20 minutes (revised down - only 4 simple endpoints reusing existing functions)
- Priority: High
- Project: MediaCo spec editor phase 2

## Revision History

- **2025-10-30**: Rescoped from 7 endpoints (including AWS integration) to 4 endpoints matching actual application functionality (GitHub API + YAML only). Removed all AWS-related requirements that don't exist in current codebase.
