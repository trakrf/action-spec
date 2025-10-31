# Feature: GitHub OAuth Authentication - Phase 1.5

## Origin
This is **Phase 1.5 of 3** for the App Runner deployment from Linear issue **D2A-30**.

**Prerequisites**: Phase 1 must be completed (App Runner deployed with Secrets Manager)

**Phase Strategy**:
- **Phase 1** (completed): Core infrastructure with Secrets Manager
- **Phase 1.5** (this): Replace Secrets Manager with GitHub OAuth
- **Phase 2** (next): Monitoring, alarms, and comprehensive documentation

## Outcome
Replace single-tenant Secrets Manager authentication with multi-tenant GitHub OAuth:
- Professional "Sign in with GitHub" experience
- Each user authenticates with their own GitHub account
- User-specific GitHub tokens for API calls
- Session management for authenticated users
- Remove AWS Secrets Manager dependency

## User Story
As a **user of the action-spec demo**
I want **to sign in with my GitHub account**
So that **the tool uses my credentials and identity for GitHub API operations**

## Context

### Why OAuth After Infrastructure?
- **Phase 1 proves deployment**: Infrastructure works, app is running
- **Known App Runner URL**: Need callback URL for OAuth app registration
- **Incremental improvement**: Replace auth without touching infrastructure
- **Better architecture**: Multi-tenant from the start

### What Phase 1 Delivered
✅ Working App Runner deployment
✅ Infrastructure as code
✅ Secrets Manager with shared token (single-tenant)
✅ Health check validation

### What Phase 1.5 Adds
🎯 GitHub OAuth App registration
🎯 "Sign in with GitHub" UI
🎯 OAuth callback handling (Flask)
🎯 Server-side session management
🎯 User-specific token storage
🎯 Remove Secrets Manager (Terraform cleanup)

### What Phase 1.5 Removes
❌ AWS Secrets Manager resources
❌ Secrets Manager IAM policies
❌ Shared GitHub token
❌ `TF_VAR_github_token` requirement

## Technical Requirements

### GitHub OAuth App Setup (Manual, One-Time)

**Register OAuth App**:
1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create new OAuth App:
   - **Application name**: `Action Spec - [Your Name]`
   - **Homepage URL**: `https://<app-runner-url>/`
   - **Authorization callback URL**: `https://<app-runner-url>/auth/github/callback`
   - **Enable Device Flow**: No
3. Generate client secret
4. Save Client ID and Client Secret

**Required OAuth Scopes**:
- `repo` - Access repositories
- `workflow` - Trigger GitHub Actions workflows

### Backend Changes (Flask)

#### 1. Add Dependencies (backend/requirements.txt)
```txt
# Add to existing requirements.txt
requests-oauthlib==1.3.1  # OAuth flow handling
Flask-Session==0.5.0       # Server-side sessions
```

#### 2. Environment Variables (App Runner)
**Add to Terraform** (`infra/tools/main.tf`):
```hcl
runtime_environment_variables = {
  AWS_REGION            = var.aws_region
  GH_REPO               = var.github_repo
  SPECS_PATH            = "infra"
  WORKFLOW_BRANCH       = var.github_branch
  GITHUB_CLIENT_ID      = var.github_oauth_client_id      # New
  GITHUB_CLIENT_SECRET  = var.github_oauth_client_secret  # New (sensitive)
  SESSION_SECRET        = var.session_secret              # New (for Flask sessions)
}

# Remove this block (no more Secrets Manager)
# runtime_environment_secrets = {
#   GH_TOKEN = aws_secretsmanager_secret.github_token.arn
# }
```

#### 3. Session Configuration (backend/app.py)
```python
import os
from flask import Flask, session, redirect, url_for, request, jsonify
from flask_session import Session
from requests_oauthlib import OAuth2Session

app = Flask(__name__)

# Session configuration
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET')
app.config['SESSION_TYPE'] = 'filesystem'  # or 'redis' for production
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
GITHUB_AUTHORIZATION_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_API_BASE_URL = 'https://api.github.com'
```

#### 4. OAuth Routes (backend/auth.py - new file)
```python
from flask import Blueprint, redirect, request, session, url_for
from requests_oauthlib import OAuth2Session
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
GITHUB_AUTHORIZATION_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'

@auth_bp.route('/github/login')
def github_login():
    """Initiate GitHub OAuth flow"""
    github = OAuth2Session(
        GITHUB_CLIENT_ID,
        redirect_uri=url_for('auth.github_callback', _external=True),
        scope=['repo', 'workflow']
    )
    authorization_url, state = github.authorization_url(GITHUB_AUTHORIZATION_URL)

    # Store state for CSRF protection
    session['oauth_state'] = state

    return redirect(authorization_url)

@auth_bp.route('/github/callback')
def github_callback():
    """Handle GitHub OAuth callback"""
    github = OAuth2Session(
        GITHUB_CLIENT_ID,
        state=session.get('oauth_state'),
        redirect_uri=url_for('auth.github_callback', _external=True)
    )

    # Exchange authorization code for access token
    token = github.fetch_token(
        GITHUB_TOKEN_URL,
        client_secret=GITHUB_CLIENT_SECRET,
        authorization_response=request.url
    )

    # Store token in session
    session['github_token'] = token['access_token']

    # Get user info
    github = OAuth2Session(GITHUB_CLIENT_ID, token=token)
    user_data = github.get('https://api.github.com/user').json()

    session['github_user'] = {
        'login': user_data['login'],
        'name': user_data.get('name'),
        'avatar_url': user_data.get('avatar_url')
    }

    return redirect('/')

@auth_bp.route('/logout')
def logout():
    """Clear session"""
    session.clear()
    return redirect('/')

@auth_bp.route('/user')
def current_user():
    """Get current authenticated user"""
    if 'github_user' in session:
        return jsonify(session['github_user'])
    return jsonify(None), 401
```

#### 5. Protected API Routes (backend/api.py - modify)
**Add authentication check**:
```python
from flask import session, jsonify
from functools import wraps

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'github_token' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Apply to existing routes
@app.route('/api/blueprints')
@require_auth
def get_blueprints():
    token = session['github_token']
    # Use token for GitHub API calls
    # ... existing logic
```

### Frontend Changes (Vue)

#### 1. Login Component (frontend/src/components/Login.vue - new)
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const user = ref(null)

async function checkAuth() {
  try {
    const response = await fetch('/auth/user')
    if (response.ok) {
      user.value = await response.json()
    }
  } catch (error) {
    console.error('Auth check failed:', error)
  }
}

function login() {
  window.location.href = '/auth/github/login'
}

function logout() {
  window.location.href = '/auth/logout'
}

onMounted(checkAuth)
</script>

<template>
  <div class="login-container">
    <div v-if="!user" class="login-prompt">
      <h2>Welcome to Action Spec</h2>
      <p>Sign in with GitHub to manage your infrastructure specs</p>
      <button @click="login" class="github-login-btn">
        <svg class="github-icon" viewBox="0 0 16 16" width="20" height="20">
          <path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
        </svg>
        Sign in with GitHub
      </button>
    </div>

    <div v-else class="user-info">
      <img :src="user.avatar_url" :alt="user.name" class="avatar" />
      <div>
        <p class="user-name">{{ user.name || user.login }}</p>
        <button @click="logout" class="logout-btn">Sign out</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  padding: 2rem;
}

.login-prompt {
  text-align: center;
  max-width: 400px;
  margin: 0 auto;
}

.github-login-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #24292e;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.github-login-btn:hover {
  background: #1b1f23;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.logout-btn {
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;
}
</style>
```

#### 2. Update Main App (frontend/src/App.vue)
```vue
<script setup lang="ts">
import Login from './components/Login.vue'
// ... existing imports
</script>

<template>
  <div id="app">
    <header>
      <h1>Action Spec</h1>
      <Login />
    </header>
    <!-- ... rest of app -->
  </div>
</template>
```

#### 3. Add Auth Interceptor (frontend/src/api/client.ts)
```typescript
// Redirect to login if 401
async function fetchWithAuth(url: string, options = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: 'same-origin' // Include cookies
  })

  if (response.status === 401) {
    window.location.href = '/auth/github/login'
  }

  return response
}

export default fetchWithAuth
```

### Terraform Changes

#### 1. Update Variables (infra/tools/variables.tf)
**Add**:
```hcl
variable "github_oauth_client_id" {
  description = "GitHub OAuth App Client ID"
  type        = string
  sensitive   = true
}

variable "github_oauth_client_secret" {
  description = "GitHub OAuth App Client Secret"
  type        = string
  sensitive   = true
}

variable "session_secret" {
  description = "Flask session secret key"
  type        = string
  sensitive   = true
  default     = ""  # Will be auto-generated if not provided
}
```

**Remove**:
```hcl
# Delete this variable
# variable "github_token" { ... }
```

#### 2. Update Environment (.env.local)
**Add**:
```bash
TF_VAR_github_oauth_client_id=Iv1.xxxxxxxxxxxx
TF_VAR_github_oauth_client_secret=xxxxxxxxxxxx
TF_VAR_session_secret=$(openssl rand -hex 32)
```

**Remove**:
```bash
# Delete this line
# TF_VAR_github_token=$GH_TOKEN
```

#### 3. Remove Secrets Manager (infra/tools/secrets.tf)
**Delete entire file** or comment out:
```hcl
# File can be deleted - no longer needed
```

#### 4. Update IAM (infra/tools/iam.tf)
**Remove Secrets Manager policy**:
```hcl
# Delete this resource
# resource "aws_iam_role_policy" "app_runner_secrets" { ... }
```

#### 5. Update Main (infra/tools/main.tf)
See "Environment Variables (App Runner)" section above.

## Validation Criteria

Phase 1.5 is complete when:

- [ ] GitHub OAuth App registered with correct callback URL
- [ ] Backend dependencies installed (`requests-oauthlib`, `Flask-Session`)
- [ ] OAuth routes implemented and tested
- [ ] Session management working
- [ ] Login UI component created
- [ ] "Sign in with GitHub" button works
- [ ] OAuth callback redirects correctly
- [ ] User info displayed after login
- [ ] API routes protected with `@require_auth`
- [ ] Logout clears session
- [ ] Terraform updated (variables, main.tf, remove secrets.tf)
- [ ] `tofu plan` shows Secrets Manager resources to be destroyed
- [ ] `tofu apply` successfully removes Secrets Manager
- [ ] Application works with OAuth (can load blueprints, trigger workflows)
- [ ] Multiple users can sign in with different GitHub accounts
- [ ] Frontend tests pass (`just frontend test`)
- [ ] Backend tests pass (`just backend test`)

## Success Metrics

- Login flow: < 3 clicks (Sign in → Authorize → Redirected)
- OAuth callback: < 2 seconds
- Session persistence: Survives page refresh
- Multi-tenancy: Different users see their own repos
- Zero AWS Secrets Manager costs

## Security Considerations

- **Session security**: Use secure, httpOnly cookies
- **CSRF protection**: OAuth state parameter validates callbacks
- **Token storage**: Server-side sessions (not localStorage)
- **HTTPS only**: App Runner provides HTTPS automatically
- **Scope minimization**: Only request `repo` and `workflow` scopes

## Out of Scope (Future Enhancements)

- Token refresh (OAuth tokens don't expire by default for GitHub)
- Database-backed sessions (using filesystem for now)
- Rate limiting per user
- Admin/user roles
- Organization-level authentication

## References

- Phase 1 spec: `spec/active/app-runner-phase1-deployment/spec.md`
- Phase 2 spec: `spec/active/app-runner-phase2-observability/spec.md`
- Linear issue: [D2A-30](https://linear.app/trakrf/issue/D2A-30)
- GitHub OAuth docs: https://docs.github.com/en/developers/apps/building-oauth-apps
- Flask-Session docs: https://flask-session.readthedocs.io/
- requests-oauthlib docs: https://requests-oauthlib.readthedocs.io/
