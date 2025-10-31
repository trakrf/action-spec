# Feature: GitHub OAuth Backend - Authentication API

## Metadata
**Phase**: 1 of 3
**Type**: feature
**Estimated Time**: 45-60 minutes

## Origin
This specification emerged from discussing how to transition from service account authentication (PAT) to user-based authentication for GitHub API operations. Currently, all GitHub API calls use a shared service account token (`GH_TOKEN`), which prevents audit trails and doesn't respect individual user permissions.

**This is Phase 1**: Backend OAuth endpoints and token handling infrastructure.

## Outcome
Backend provides OAuth authentication endpoints that enable users to authenticate with GitHub. User tokens are securely stored in HttpOnly cookies and used for all GitHub API operations. This phase focuses purely on the API layer - no UI changes visible yet.

**Enables**:
- OAuth login flow (redirect to GitHub, handle callback)
- Secure token storage (HttpOnly cookies)
- Token validation and user info retrieval
- GitHub API wrapper using user tokens
- Access control for public/private repos

## User Story
As a **backend service**
I want **OAuth authentication endpoints**
So that **users can authenticate with GitHub and I can make API calls on their behalf**

## Context

### Current State
- All GitHub API operations use service account PAT stored in Secrets Manager (`GH_TOKEN`)
- No user authentication mechanism
- Single shared token for all operations
- No way to distinguish between users

### Desired State (Phase 1)
- OAuth endpoints available at `/auth/*`
- Users can authenticate via GitHub OAuth
- Tokens stored securely in HttpOnly cookies
- GitHub API wrapper uses user tokens from cookies
- Access control logic validates repo permissions

**Note**: Frontend UI (Phase 2) and Infrastructure deployment (Phase 3) come after this.

### Architectural Decisions

**HttpOnly Cookies**:
- Immune to XSS attacks (JavaScript can't read)
- Automatically sent with requests
- Natural multi-tab sync

**Stateless Backend**:
- No Redis/database needed for sessions
- Simpler infrastructure
- Auto-scales without session migration

**Lazy Validation**:
- Fast page load (validation happens async)
- Good user experience
- Token validated on-demand

## Technical Requirements

### 1. GitHub OAuth App Setup

**Manual Prerequisites** (one-time, before development):
- Register OAuth App at https://github.com/settings/developers
- Obtain Client ID (public identifier)
- Obtain Client Secret (sensitive credential)
- Configure Callback URL: `https://<app-runner-url>/auth/callback`
- Request Scopes:
  - `repo` - Read repository files/directories, launch workflows
  - `workflow` - Dispatch workflow runs

**For local development**: Use `http://localhost:8080/auth/callback`

**Note**: Client ID/Secret stored as environment variables (added in Phase 3).

### 2. Backend API Endpoints (Flask)

#### Authentication Endpoints

**`GET /auth/login`**

Purpose: Initiate OAuth flow

Implementation:
```python
@app.route('/auth/login')
def login():
    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    # Build GitHub OAuth URL
    params = {
        'client_id': os.environ['GITHUB_OAUTH_CLIENT_ID'],
        'redirect_uri': f"{request.host_url}auth/callback",
        'scope': 'repo workflow',
        'state': state
    }

    github_auth_url = 'https://github.com/login/oauth/authorize'
    redirect_url = f"{github_auth_url}?{urlencode(params)}"

    return redirect(redirect_url)
```

Response: HTTP 302 redirect to GitHub

---

**`GET /auth/callback`**

Purpose: Handle OAuth callback from GitHub

Implementation:
```python
@app.route('/auth/callback')
def callback():
    # Validate state (CSRF protection)
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        abort(400, "Invalid state parameter")

    # Get authorization code
    code = request.args.get('code')
    if not code:
        abort(400, "No authorization code")

    # Exchange code for access token
    token_url = 'https://github.com/login/oauth/access_token'
    data = {
        'client_id': os.environ['GITHUB_OAUTH_CLIENT_ID'],
        'client_secret': os.environ['GITHUB_OAUTH_CLIENT_SECRET'],
        'code': code,
        'redirect_uri': f"{request.host_url}auth/callback"
    }

    response = requests.post(token_url, data=data,
                           headers={'Accept': 'application/json'})
    token_data = response.json()
    access_token = token_data.get('access_token')

    if not access_token:
        abort(400, "Failed to get access token")

    # Validate token with GitHub API
    user_response = requests.get('https://api.github.com/user',
                                headers={'Authorization': f'token {access_token}'})

    if user_response.status_code != 200:
        abort(400, "Invalid token")

    # Set HttpOnly cookie
    response = make_response(redirect('/'))
    response.set_cookie(
        'github_token',
        value=access_token,
        max_age=2592000,  # 30 days
        secure=True,       # HTTPS only
        httponly=True,     # Not accessible to JavaScript
        samesite='Lax'     # CSRF protection
    )

    return response
```

Response: HTTP 302 redirect to app root with cookie set

---

**`POST /auth/logout`**

Purpose: Clear authentication cookie

Implementation:
```python
@app.route('/auth/logout', methods=['POST'])
def logout():
    response = make_response({'success': True})
    response.set_cookie('github_token', '', max_age=0)
    return response
```

Response: `{"success": true}` with cookie cleared

---

**`GET /api/auth/user`**

Purpose: Return current authenticated user info

Implementation:
```python
@app.route('/api/auth/user')
def get_user():
    token = request.cookies.get('github_token')

    if not token:
        abort(401, "Not authenticated")

    # Validate token with GitHub
    response = requests.get('https://api.github.com/user',
                          headers={'Authorization': f'token {token}'})

    if response.status_code == 401:
        # Token invalid/revoked, clear cookie
        resp = make_response({'error': 'Token invalid'}, 401)
        resp.set_cookie('github_token', '', max_age=0)
        return resp

    if response.status_code != 200:
        abort(500, "GitHub API error")

    user_data = response.json()
    return {
        'login': user_data['login'],
        'name': user_data['name'],
        'avatar_url': user_data['avatar_url']
    }
```

Response: User info JSON or 401 if not authenticated

### 3. GitHub API Wrapper

Helper functions for making authenticated GitHub API calls:

```python
def get_github_token():
    """Get user's GitHub token from cookie."""
    token = request.cookies.get('github_token')
    if not token:
        abort(401, "Not authenticated")
    return token

def github_api_call(endpoint, method='GET', **kwargs):
    """Make GitHub API call with user's token."""
    token = get_github_token()
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'token {token}'

    response = requests.request(
        method,
        f'https://api.github.com{endpoint}',
        headers=headers,
        **kwargs
    )

    if response.status_code == 401:
        # Token revoked, clear cookie
        abort(401, "Token invalid")

    return response

def check_repo_access(owner, repo):
    """Verify user has access to repository."""
    # Check repo exists and user has access
    repo_response = github_api_call(f'/repos/{owner}/{repo}')

    if repo_response.status_code == 404:
        abort(403, "No access to repository")

    repo_data = repo_response.json()

    # For private repos in trakrf org, verify membership
    if owner == 'trakrf' and repo_data.get('private'):
        user = github_api_call('/user').json()
        org_response = github_api_call(f'/orgs/trakrf/members/{user["login"]}')

        if org_response.status_code == 404:
            abort(403, "Must be trakrf org member for private repos")

    return True
```

### 4. Update Existing API Endpoints

**Example**: Update file reading endpoint

Before (using service account):
```python
@app.route('/api/repos/<owner>/<repo>/contents/<path:file_path>')
def get_file_contents(owner, repo, file_path):
    # Uses GH_TOKEN from environment
    token = os.environ['GH_TOKEN']
    # ... rest of implementation
```

After (using user token):
```python
@app.route('/api/repos/<owner>/<repo>/contents/<path:file_path>')
def get_file_contents(owner, repo, file_path):
    # Verify access first
    check_repo_access(owner, repo)

    # Use user's token from cookie
    response = github_api_call(f'/repos/{owner}/{repo}/contents/{file_path}')

    if response.status_code != 200:
        abort(response.status_code, response.json().get('message', 'API error'))

    return response.json()
```

**Apply this pattern to**:
- `/api/repos/<owner>/<repo>/contents/<path:file_path>` - Read file
- `/api/repos/<owner>/<repo>/contents` - List directory
- `/api/repos/<owner>/<repo>/actions/workflows/<workflow_id>/dispatches` - Trigger workflow
- Any other GitHub API endpoints

### 5. Security Considerations

#### CSRF Protection
- Generate random `state` parameter for OAuth flow
- Store in server-side session during redirect
- Validate `state` matches in callback
- Use Flask sessions with secure secret key

#### Cookie Security
- `HttpOnly=True` - Not accessible to JavaScript (XSS protection)
- `Secure=True` - HTTPS only (App Runner provides this)
- `SameSite=Lax` - CSRF protection for cross-site requests
- 30-day expiration (manual re-auth acceptable)

#### Token Handling
- Never expose token to JavaScript
- Clear cookie immediately on logout or invalid token
- No token in localStorage (vulnerable to XSS)
- No token in URL parameters

#### Session Security
- Flask secret key from environment variable
- Secure session cookies
- Session only used for OAuth state parameter

### 6. Access Control Logic

#### Public Repositories
- Any authenticated GitHub user can access
- Verify via GitHub API: `GET /repos/{owner}/{repo}`
- 404 response = no access

#### Private Repositories
- User must be member of `trakrf` organization (if owner is trakrf)
- Verify via GitHub API: `GET /orgs/trakrf/members/{username}`
- 204 response = member, 404 = not member

### 7. Error Handling

**401 Unauthorized**:
- No token in cookie
- Token invalid/revoked
- Token expired
- **Action**: Clear cookie, return 401 (frontend will redirect)

**403 Forbidden**:
- User lacks access to repository
- User not trakrf org member for private repo
- **Action**: Return clear error message

**500 Internal Server Error**:
- GitHub API unavailable
- Unexpected error during OAuth flow
- **Action**: Return error message, log details

## Validation Criteria

### Functional Requirements
- [ ] `GET /auth/login` redirects to GitHub with correct params
- [ ] `GET /auth/callback` exchanges code for token successfully
- [ ] HttpOnly cookie set with 30-day expiration after callback
- [ ] `POST /auth/logout` clears cookie
- [ ] `GET /api/auth/user` returns user info when authenticated
- [ ] `GET /api/auth/user` returns 401 when not authenticated
- [ ] Invalid/revoked token triggers cookie clear and 401 response

### Access Control
- [ ] Public repo access works for any authenticated user
- [ ] Private trakrf repo access requires org membership
- [ ] 403 error returned when user lacks access
- [ ] Repo existence verified before operations

### Security
- [ ] Cookie is HttpOnly (not accessible to JavaScript)
- [ ] Cookie is Secure (HTTPS only)
- [ ] Cookie is SameSite=Lax
- [ ] CSRF state parameter validated in OAuth callback
- [ ] Token never exposed in URLs or responses

### API Integration
- [ ] File reading endpoints use user token
- [ ] Directory listing endpoints use user token
- [ ] Workflow dispatch endpoints use user token
- [ ] All GitHub API calls use `github_api_call()` wrapper
- [ ] 401 responses handled gracefully (clear cookie)

## Success Metrics

- All backend OAuth endpoints functional
- 100% of GitHub API calls use user tokens (in this branch)
- Zero security issues in token handling
- CSRF state validation working correctly
- Access control logic enforcing org membership

## Testing Strategy

### Unit Tests (pytest)

**Test OAuth flow**:
```python
def test_login_redirects_to_github(client):
    response = client.get('/auth/login', follow_redirects=False)
    assert response.status_code == 302
    assert 'github.com/login/oauth/authorize' in response.location

def test_callback_validates_state(client):
    # Missing state
    response = client.get('/auth/callback?code=test')
    assert response.status_code == 400

def test_callback_sets_cookie(client, mock_github):
    # Mock GitHub API responses
    response = client.get('/auth/callback?code=test&state=valid')
    assert 'github_token' in response.headers.get('Set-Cookie', '')
```

**Test token handling**:
```python
def test_github_api_call_uses_cookie(client):
    # Set cookie
    client.set_cookie('github_token', 'test_token')

    # Mock GitHub API
    response = github_api_call('/user')
    assert response.request.headers['Authorization'] == 'token test_token'

def test_invalid_token_clears_cookie(client):
    # Set invalid token
    client.set_cookie('github_token', 'invalid')

    # Should clear cookie and return 401
    response = client.get('/api/auth/user')
    assert response.status_code == 401
    assert 'github_token=;' in response.headers.get('Set-Cookie', '')
```

**Test access control**:
```python
def test_public_repo_access_allowed(client, mock_github):
    # Any authenticated user
    response = check_repo_access('octocat', 'Hello-World')
    assert response == True

def test_private_repo_requires_org_membership(client, mock_github):
    # Non-member tries to access private trakrf repo
    with pytest.raises(Forbidden):
        check_repo_access('trakrf', 'private-repo')
```

### Manual Testing

1. **OAuth Flow**:
   - Visit `/auth/login`
   - Complete GitHub authorization
   - Verify redirected back to app
   - Check cookie set in browser devtools

2. **Token Validation**:
   - Call `/api/auth/user`
   - Verify user info returned
   - Clear cookie manually
   - Verify 401 response

3. **Access Control**:
   - Try accessing public repo (should work)
   - Try accessing private trakrf repo as non-member (should 403)
   - Try accessing private trakrf repo as member (should work)

## Dependencies

### Environment Variables (added in Phase 3)
- `GITHUB_OAUTH_CLIENT_ID` - OAuth App Client ID
- `GITHUB_OAUTH_CLIENT_SECRET` - OAuth App Client Secret
- `FLASK_SECRET_KEY` - Session secret for CSRF state

### Python Libraries
- `requests` - Already installed
- `flask` - Already installed
- No new dependencies needed

### External Services
- GitHub OAuth App (must be registered manually)
- GitHub API (must be accessible from App Runner)

## Out of Scope

**Not in Phase 1**:
- Frontend UI components (Phase 2)
- Infrastructure deployment (Phase 3)
- Service account PAT removal (Phase 3)
- Token refresh mechanism (future enhancement)

## Next Steps

After Phase 1 complete:
1. **Phase 2**: Frontend UI - Login button, user menu, auth state
2. **Phase 3**: Infrastructure - Add secrets, deploy, cutover

## Related

- **Linear**: D2A-31
- **Next Phase**: `spec/active/github-oauth-frontend/spec.md`
- **Infrastructure**: Multi-cloud restructure (complete)
