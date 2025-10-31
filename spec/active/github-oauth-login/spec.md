# Feature: GitHub OAuth Login for User Authentication

## Origin
This specification emerged from discussing how to transition from service account authentication (PAT) to user-based authentication for GitHub API operations. Currently, all GitHub API calls use a shared service account token (`GH_TOKEN`), which prevents audit trails and doesn't respect individual user permissions.

## Outcome
Users authenticate with their GitHub account via OAuth, and all GitHub API operations (reading files, launching workflows) use the authenticated user's token. This enables:
- Audit trail capability (track who performs what operations)
- User-level permissions (respect individual GitHub access)
- Elimination of shared service account token
- Better rate limit distribution (per-user vs shared)

## User Story
As a **developer using action-spec**
I want **to authenticate with my GitHub account**
So that **I can access repos I have permission for and my actions are tracked under my identity**

## Context

### Current State
- All GitHub API operations use service account PAT stored in Secrets Manager (`GH_TOKEN`)
- No user authentication required
- No audit trail of who performed operations
- Single rate limit pool shared across all users
- All operations limited to service account's permissions

### Desired State
- Users authenticate via GitHub OAuth
- Each user's token used for their operations
- Actions attributed to specific users (audit trail ready)
- Individual rate limits per user
- Users can only access repos they have GitHub permissions for
- Service account PAT (`GH_TOKEN`) eliminated

### Discovery
Through architectural discussion, determined:
- HttpOnly cookies provide best security for token storage
- Stateless backend avoids Redis/session storage complexity
- Lazy validation during page load provides good UX
- Cookie-based auth naturally syncs across browser tabs
- OAuth App credentials never expire (manual rotation only)

## Technical Requirements

### 1. GitHub OAuth App Setup

**Manual Prerequisites** (one-time):
- Register OAuth App at https://github.com/settings/developers
- Obtain Client ID (public identifier)
- Obtain Client Secret (sensitive credential)
- Configure Callback URL: `https://<app-runner-url>/auth/callback`
- Request Scopes:
  - `repo` - Read repository files/directories, launch workflows
  - `workflow` - Dispatch workflow runs

**Note**: `repo` scope includes write access, but this is acceptable for simplicity. Future enhancement could explore fine-grained permissions.

### 2. Backend API Endpoints (Flask)

#### Authentication Endpoints

**`GET /auth/login`**
- Redirects to GitHub OAuth authorization URL
- Includes `state` parameter for CSRF protection
- Includes `client_id` and requested scopes
- Response: HTTP 302 redirect to GitHub

**`GET /auth/callback`**
- Receives authorization code from GitHub
- Validates `state` parameter (CSRF protection)
- Exchanges code for access token (server-side)
- Validates token with GitHub API (`GET /user`)
- **Access control**:
  - For private repos: Verify org membership (`trakrf`)
  - For public repos: Verify repo access
- Sets HttpOnly cookie with token
- Response: HTTP 302 redirect to app root

**`POST /auth/logout`**
- Clears authentication cookie
- Response: `{"success": true}`

**`GET /api/auth/user`**
- Returns current authenticated user info
- Validates token with GitHub API
- If token invalid (401), clears cookie and returns error
- Response: `{"login": "username", "avatar_url": "...", "name": "..."}`

#### Token Handling

**Token Storage**:
- HttpOnly cookie named `github_token`
- Secure flag: `true` (HTTPS only)
- SameSite: `Lax` (CSRF protection)
- Max-Age: 2592000 seconds (30 days)
- Path: `/` (site-wide)

**Token Validation Strategy**:
- Lazy validation on page load (non-blocking)
- Validate on-demand when API calls fail
- Clear cookie and redirect to login on 401 responses

**GitHub API Wrapper**:
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
    headers = {'Authorization': f'token {token}'}
    response = requests.request(method, f'https://api.github.com{endpoint}',
                                headers=headers, **kwargs)

    if response.status_code == 401:
        # Token revoked, clear cookie
        abort(401, "Token invalid")

    return response
```

### 3. Frontend Changes (Vue)

#### New Components

**`LoginButton.vue`**:
- Shown when user not authenticated
- Redirects to `/auth/login` on click
- GitHub branding/styling

**`UserMenu.vue`**:
- Shown when user authenticated
- Displays user avatar and name
- Dropdown with logout option

**`AuthGuard.vue` (composable)**:
- Lazy validation on mount
- Fetches `/api/auth/user` asynchronously
- Redirects to `/auth/login` if validation fails
- Stores user info in Vue state

#### Authentication State Management

```javascript
// stores/auth.js
import { ref } from 'vue'

export const user = ref(null)
export const isAuthenticated = computed(() => !!user.value)
export const isValidating = ref(false)

export async function validateAuth() {
  isValidating.value = true
  try {
    const response = await fetch('/api/auth/user')
    if (response.ok) {
      user.value = await response.json()
    } else {
      window.location.href = '/auth/login'
    }
  } finally {
    isValidating.value = false
  }
}
```

#### Page Load Behavior

```vue
<script setup>
import { onMounted } from 'vue'
import { validateAuth, isValidating, user } from '@/stores/auth'

onMounted(() => {
  validateAuth() // Non-blocking, async
})
</script>

<template>
  <div v-if="!isValidating">
    <!-- App content loads immediately -->
    <UserMenu v-if="user" :user="user" />
    <!-- UI appears while validation happens in background -->
  </div>
</template>
```

### 4. Infrastructure Changes

#### Secrets Manager (Terraform)

**Add OAuth credentials** (`infra/tools/aws/secrets.tf`):
```hcl
resource "aws_secretsmanager_secret" "github_oauth_client_secret" {
  name                    = "action-spec/github-oauth-client-secret"
  description             = "GitHub OAuth App client secret"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "github_oauth_client_secret" {
  secret_id     = aws_secretsmanager_secret.github_oauth_client_secret.id
  secret_string = var.github_oauth_client_secret
}
```

**Remove after OAuth ships**:
```hcl
# DELETE: Service account PAT no longer needed
# resource "aws_secretsmanager_secret" "github_token" { ... }
```

#### App Runner Configuration (Terraform)

**Add environment variables** (`infra/tools/aws/main.tf`):
```hcl
runtime_environment_variables = {
  AWS_REGION               = var.aws_region
  GH_REPO                  = var.github_repo
  SPECS_PATH               = "infra"
  WORKFLOW_BRANCH          = var.github_branch
  GITHUB_OAUTH_CLIENT_ID   = var.github_oauth_client_id  # Public, can be env var
}

runtime_environment_secrets = {
  GITHUB_OAUTH_CLIENT_SECRET = aws_secretsmanager_secret.github_oauth_client_secret.arn
  # DELETE after OAuth ships: GH_TOKEN = ...
}
```

**Add variables** (`infra/tools/aws/variables.tf`):
```hcl
variable "github_oauth_client_id" {
  description = "GitHub OAuth App Client ID (public identifier)"
  type        = string
}

variable "github_oauth_client_secret" {
  description = "GitHub OAuth App Client Secret (from environment)"
  type        = string
  sensitive   = true
}
```

### 5. Access Control Logic

#### Public Repositories
- Any authenticated GitHub user can access
- Verify user has read access to repo via GitHub API
- Endpoint: `GET /repos/{owner}/{repo}` (will 404 if no access)

#### Private Repositories
- User must be member of `trakrf` organization
- Verify via GitHub API: `GET /orgs/trakrf/members/{username}`
- Returns 204 if member, 404 if not

**Implementation**:
```python
def check_access(repo_owner, repo_name):
    """Verify user has access to repository."""
    token = get_github_token()

    # Check repo access
    repo_response = github_api_call(f'/repos/{repo_owner}/{repo_name}')
    if repo_response.status_code == 404:
        abort(403, "No access to repository")

    # For private repos in trakrf org, verify membership
    if repo_owner == 'trakrf' and repo_response.json().get('private'):
        user = github_api_call('/user').json()
        org_response = github_api_call(f'/orgs/trakrf/members/{user["login"]}')
        if org_response.status_code == 404:
            abort(403, "Must be trakrf org member for private repos")

    return True
```

### 6. Security Considerations

#### CSRF Protection
- Use `state` parameter in OAuth flow (random token)
- Store `state` in server-side session during redirect
- Validate `state` matches in callback
- Flask-WTF for form CSRF protection

#### Cookie Security
- `HttpOnly=True` - Not accessible to JavaScript (XSS protection)
- `Secure=True` - HTTPS only (App Runner provides this)
- `SameSite=Lax` - CSRF protection for cross-site requests
- 30-day expiration

#### Token Handling
- Never expose token to JavaScript (HttpOnly cookie)
- Clear cookie immediately on logout or invalid token
- No token in localStorage (vulnerable to XSS)
- No token in URL parameters or query strings

#### Rate Limiting
- GitHub API: 5,000 requests/hour per authenticated user
- Expected usage: < 500 requests/day per user
- Handle 403 rate limit responses gracefully
- No additional rate limiting needed at app level

### 7. Session and Token Lifecycle

#### Token Expiration
- **GitHub tokens**: Never expire automatically
- **App session**: 30-day cookie expiration
- **Refresh strategy**: Manual re-authentication (acceptable)
- **Alternative**: Could refresh weekly by validating + issuing new cookie (future enhancement)

#### Token Revocation Handling
- User revokes access in GitHub settings
- Next API call returns 401
- Backend clears cookie and returns 401
- Frontend redirects to `/auth/login`
- User must re-authenticate

#### Multi-Tab Behavior
- HttpOnly cookies are browser-level (shared across tabs)
- Logout in one tab clears cookie for all tabs
- Other tabs auto-logout on next API request (natural sync)
- No need for BroadcastChannel or real-time sync

#### Deployment Impact
- App Runner redeploy doesn't affect cookies (browser-side storage)
- No server-side session state to lose
- Stateless backend = zero session migration needed

### 8. Migration Strategy

#### Phase 1: Add OAuth (Parallel)
- Deploy OAuth endpoints alongside existing PAT auth
- Keep `GH_TOKEN` service account as fallback
- Test OAuth flow with subset of users
- All operations still work via service account

#### Phase 2: Require OAuth (Cutover)
- Remove service account fallback
- Require login for all operations
- Remove `GH_TOKEN` from Secrets Manager
- Update Terraform to remove old secret

#### Rollback Plan
- Re-add `GH_TOKEN` to Secrets Manager
- Update Terraform to restore service account auth
- Redeploy with old configuration

## Validation Criteria

### Functional Requirements
- [ ] User can click "Login with GitHub" and complete OAuth flow
- [ ] User redirected to GitHub authorization page with correct scopes
- [ ] OAuth callback exchanges code for token successfully
- [ ] User info displayed in UI after authentication
- [ ] HttpOnly cookie set with 30-day expiration
- [ ] User can logout and cookie is cleared
- [ ] Lazy validation on page load works without blocking UI
- [ ] Invalid token triggers logout and redirect to login
- [ ] Multi-tab logout syncs on next request

### Access Control
- [ ] Public repo access works for any authenticated user
- [ ] Private repo access requires trakrf org membership
- [ ] 403 error shown when user lacks access
- [ ] Token revocation detected and handled gracefully

### Security
- [ ] Cookie is HttpOnly (not accessible to JavaScript)
- [ ] Cookie is Secure (HTTPS only)
- [ ] Cookie is SameSite=Lax (CSRF protected)
- [ ] CSRF state parameter validated in OAuth callback
- [ ] Token never exposed in URLs or localStorage
- [ ] 401 responses clear cookie automatically

### API Operations
- [ ] Read repository files using user token works
- [ ] Read directory listing using user token works
- [ ] Dispatch workflow using user token works
- [ ] User respects GitHub permissions (can't access unauthorized repos)
- [ ] Rate limits are per-user (not shared service account)

### User Experience
- [ ] Page loads immediately with skeleton/loading state
- [ ] Validation happens asynchronously in background
- [ ] User sees avatar/name after authentication
- [ ] Logout is instant and clears all state
- [ ] Error messages are clear and actionable

### Infrastructure
- [ ] OAuth client secret stored in Secrets Manager
- [ ] OAuth client ID in environment variables
- [ ] Service account PAT (`GH_TOKEN`) removed after cutover
- [ ] Terraform apply succeeds with new configuration
- [ ] App Runner deployment works with new env vars

## Success Metrics

### Measurable Outcomes
- 100% of GitHub API calls use user tokens (not service account)
- Zero security incidents related to token exposure
- < 100ms overhead for lazy validation on page load
- Zero user complaints about authentication UX
- GitHub API rate limits not hit (< 5,000 req/hr per user)

### Future Capabilities Enabled
- Audit trail of operations (track by GitHub username)
- User-level permissions respected (can't access unauthorized repos)
- Fine-grained access control (future: role-based permissions)
- Better security posture (no shared service account)

## Out of Scope

**Not included in this feature**:
- GitHub App authentication (using OAuth App instead)
- Fine-grained permissions (using standard OAuth scopes)
- Token refresh mechanism (relying on long-lived tokens)
- Session storage backend (using stateless cookies)
- Real-time multi-tab sync (using natural sync on request)
- Admin operations with service account (all user-driven)
- Rate limit tracking UI (usage too low to matter)

**Potential future enhancements**:
- Weekly token refresh for added security
- Fine-grained permission scopes (read-only access)
- Admin dashboard with elevated permissions
- Audit log viewer (query by user/operation)
- Session timeout warnings before expiration

## Technical Debt and Tradeoffs

### Accepted Tradeoffs

**Using `repo` scope (includes write)**:
- ✅ Simpler implementation (fewer scopes to manage)
- ✅ Matches GitHub's coarse-grained permissions
- ❌ Over-permissioned (users get write when only need read)
- **Decision**: Acceptable for MVP, can refine later

**30-day token expiration without refresh**:
- ✅ Simple implementation (no refresh logic)
- ✅ GitHub tokens don't expire anyway
- ❌ Users must manually re-authenticate every 30 days
- **Decision**: Acceptable, can add weekly refresh later

**Stateless backend**:
- ✅ No Redis/database needed (simpler infrastructure)
- ✅ Auto-scales without session migration
- ❌ Token lives in browser (more XSS risk, mitigated by HttpOnly)
- **Decision**: HttpOnly cookie provides sufficient security

**Lazy validation**:
- ✅ Fast page load (no blocking auth check)
- ✅ Good UX (UI appears immediately)
- ❌ Brief window where UI shows before redirect
- **Decision**: Acceptable tradeoff for performance

### Technical Debt to Address

**Before shipping**:
- None identified (design is production-ready)

**After shipping** (future enhancements):
- Consider fine-grained permissions (read-only scope)
- Consider token refresh mechanism for added security
- Consider audit log storage (track operations by user)
- Consider session timeout warnings

## Dependencies

### External Services
- GitHub OAuth App (must be registered manually)
- GitHub API (must be accessible from App Runner)

### Internal Dependencies
- Flask backend (existing)
- Vue frontend (existing)
- AWS Secrets Manager (existing)
- App Runner (existing)

### New Libraries Required
- `requests` (already used) - GitHub API calls
- `flask-session` or similar for CSRF state management
- No additional AWS services needed

## Conversation References

### Key Decisions

**Token Storage**:
> "1. http cookie"
> "HttpOnly cookie (secure, auto-sent)"

**Session Policy**:
> "2. expire in say 30 days, refresh daily or weekly. not critical, your suggested manual would be OK too"

**Validation Strategy**:
> "3. could you use a lazy load component to validate async during/after page load? or just redirect if call fails works too"
> "Yes, this works beautifully... Page loads instantly... Async validation happens in background"

**Backend Architecture**:
> "4. stateless"

**Permissions**:
> "5. repo + workflow will be fine"
> "6. both: public for demo, private for client"
> "7. repo check for public, org member for private"

**Revocation Handling**:
> "8. logout and redirect"

**Multi-Tab Sync**:
> "9. how does cookie based play into that? sync if needed"
> "Cookie naturally syncs on next request... The natural sync-on-next-request is fine"

**Rate Limits**:
> "10. usage should never be more than a few hundred requests per day. could all be within an hour but still < 10% limit"

### Key Insights

**Eliminating Service Account PAT**:
> "and this would mean that we dont need a PAT in secrets manager"
> "Yes, you can eliminate GH_TOKEN entirely"
> "All GitHub operations are user-initiated... Cleaner security model (users use their own permissions)"

**OAuth Credentials Lifecycle**:
> "what's lifecycle/expiration on the oauth id/secret?"
> "Client ID: Never changes, never expires... Client Secret: Never expires automatically... Rotate annually or on security events"

**User Token Lifecycle**:
> "GitHub OAuth tokens don't expire... Persist until: user revokes, app revokes, user changes password, or OAuth app deleted"

### Architectural Concerns Raised

**Security**:
- HttpOnly cookies chosen for XSS protection
- CSRF protection via `state` parameter
- Token never exposed to JavaScript
- Secure + SameSite flags on cookies

**Simplicity**:
- Stateless backend avoids Redis complexity
- Cookie-based auth naturally handles multi-tab
- Lazy validation avoids blocking page load
- Natural sync-on-request vs real-time events

**Scalability**:
- Per-user rate limits (5,000/hr each)
- Expected usage < 500 req/day per user
- No rate limiting needed at app level

## Related Work

- **Parent Feature**: App Runner Phase 1 Deployment (PR #39)
- **Infrastructure**: `infra/tools/aws/` Terraform configuration
- **Future Work**: App Runner Phase 2 (Observability)
