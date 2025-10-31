# Feature: GitHub OAuth Frontend - User Interface

## Metadata
**Phase**: 2 of 3
**Type**: feature
**Estimated Time**: 45-60 minutes
**Prerequisites**: Phase 1 (Backend) must be complete

## Origin
Building on the OAuth backend (Phase 1), this phase adds the user-facing components that enable authentication via GitHub. Users will see a login button, complete the OAuth flow, and see their avatar/name in the UI.

**This is Phase 2**: Frontend UI components and authentication state management.

## Outcome
Users can authenticate with their GitHub account through the UI. The app displays user information (avatar, name) and provides logout functionality. Authentication state is managed cleanly with lazy validation on page load.

**Delivers**:
- Login button component (GitHub branding)
- User menu with avatar and logout
- Authentication state management (Vue store)
- Lazy validation during page load
- Error handling and redirects
- End-to-end tests with Playwright

## User Story
As a **user of action-spec**
I want **to login with my GitHub account**
So that **I can access repositories I have permission for**

## Context

### Current State (After Phase 1)
- Backend OAuth endpoints functional (`/auth/login`, `/auth/callback`, `/auth/logout`)
- Token storage working (HttpOnly cookies)
- GitHub API wrapper using user tokens
- **But**: No UI for authentication, users can't actually login

### Desired State (Phase 2)
- Login button visible when not authenticated
- User menu showing avatar/name when authenticated
- Logout functionality working
- Smooth auth flow with good UX
- Lazy validation (page loads fast, validation async)

**Note**: Infrastructure deployment (Phase 3) comes after this.

### Architectural Decisions

**Lazy Validation**:
- Page loads immediately with skeleton UI
- Validation happens asynchronously in background
- If invalid, redirect to login (users see brief flash)
- Good UX: fast page load > perfect loading state

**Cookie-Based Auth**:
- HttpOnly cookies automatically sent with requests
- No need to pass tokens explicitly
- Natural multi-tab sync (cookies are browser-level)

**Stateless Frontend**:
- No localStorage (tokens stay in secure cookies)
- Vue store for temporary user info only
- Logout clears store + cookie

## Technical Requirements

### 1. New Vue Components

#### `LoginButton.vue`

**Purpose**: Call-to-action for unauthenticated users

**Location**: `frontend/src/components/LoginButton.vue`

**Implementation**:
```vue
<script setup>
const handleLogin = () => {
  window.location.href = '/auth/login'
}
</script>

<template>
  <button
    @click="handleLogin"
    class="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
  >
    <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <!-- GitHub logo SVG path -->
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
    </svg>
    <span>Login with GitHub</span>
  </button>
</template>
```

**Styling**: Match GitHub's button style (dark bg, white text)

---

#### `UserMenu.vue`

**Purpose**: Display authenticated user info with logout option

**Location**: `frontend/src/components/UserMenu.vue`

**Implementation**:
```vue
<script setup>
import { ref } from 'vue'
import { user, logout } from '@/stores/auth'

const isOpen = ref(false)

const handleLogout = async () => {
  await logout()
  window.location.href = '/auth/login'
}
</script>

<template>
  <div class="relative" v-if="user">
    <!-- Avatar button -->
    <button
      @click="isOpen = !isOpen"
      class="flex items-center gap-2 hover:opacity-80 transition-opacity"
    >
      <img
        :src="user.avatar_url"
        :alt="user.name"
        class="w-8 h-8 rounded-full"
      />
      <span class="text-sm font-medium">{{ user.name || user.login }}</span>
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Dropdown menu -->
    <div
      v-if="isOpen"
      @click="isOpen = false"
      class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 z-50"
    >
      <div class="px-4 py-2 text-sm text-gray-700 border-b">
        <div class="font-medium">{{ user.name }}</div>
        <div class="text-gray-500">@{{ user.login }}</div>
      </div>

      <button
        @click="handleLogout"
        class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
      >
        Logout
      </button>
    </div>
  </div>
</template>
```

**Features**:
- Avatar image from GitHub
- Username display
- Dropdown menu
- Logout button

---

### 2. Authentication State Management

#### `stores/auth.js`

**Purpose**: Centralized auth state using Vue reactivity

**Location**: `frontend/src/stores/auth.js`

**Implementation**:
```javascript
import { ref, computed } from 'vue'

// State
export const user = ref(null)
export const isValidating = ref(false)
export const error = ref(null)

// Computed
export const isAuthenticated = computed(() => !!user.value)

// Actions
export async function validateAuth() {
  isValidating.value = true
  error.value = null

  try {
    const response = await fetch('/api/auth/user')

    if (response.ok) {
      user.value = await response.json()
      return true
    } else if (response.status === 401) {
      // Not authenticated, redirect to login
      window.location.href = '/auth/login'
      return false
    } else {
      throw new Error('Validation failed')
    }
  } catch (err) {
    error.value = err.message
    console.error('Auth validation failed:', err)
    return false
  } finally {
    isValidating.value = false
  }
}

export async function logout() {
  try {
    await fetch('/auth/logout', { method: 'POST' })
    user.value = null
  } catch (err) {
    console.error('Logout failed:', err)
    // Clear local state anyway
    user.value = null
  }
}
```

**Features**:
- Reactive user state
- Async validation
- Error handling
- Logout action

---

### 3. Page Load Integration

#### Update `App.vue`

**Purpose**: Add lazy auth validation on mount

**Changes**:
```vue
<script setup>
import { onMounted } from 'vue'
import { validateAuth, isValidating, user, isAuthenticated } from '@/stores/auth'
import LoginButton from '@/components/LoginButton.vue'
import UserMenu from '@/components/UserMenu.vue'

// Validate auth on page load (non-blocking)
onMounted(() => {
  validateAuth()
})
</script>

<template>
  <div id="app">
    <!-- Header with auth components -->
    <header class="border-b p-4 flex justify-between items-center">
      <h1 class="text-xl font-bold">Action Spec</h1>

      <!-- Show login button or user menu -->
      <LoginButton v-if="!isAuthenticated && !isValidating" />
      <UserMenu v-if="isAuthenticated" />

      <!-- Loading indicator during validation -->
      <div v-if="isValidating" class="text-sm text-gray-500">
        Validating...
      </div>
    </header>

    <!-- Main content (loads immediately) -->
    <main class="p-4">
      <router-view />
    </main>
  </div>
</template>
```

**Behavior**:
- Page loads immediately
- Validation happens in background
- Login button appears briefly if not authenticated
- User menu appears after validation succeeds
- Redirect to login if validation fails

---

### 4. Error Handling

#### 401 Unauthorized Handling

**Global fetch wrapper** (optional enhancement):
```javascript
// utils/fetch.js
export async function authFetch(url, options = {}) {
  const response = await fetch(url, options)

  if (response.status === 401) {
    // Token invalid, redirect to login
    window.location.href = '/auth/login'
    throw new Error('Authentication required')
  }

  return response
}
```

**Use in existing API calls**:
```javascript
// Before
const response = await fetch('/api/repos/...')

// After
const response = await authFetch('/api/repos/...')
```

#### Network Error Handling

```javascript
try {
  const response = await authFetch('/api/auth/user')
  // ...
} catch (error) {
  if (error.message === 'Authentication required') {
    // Already redirecting
    return
  }

  // Other errors
  console.error('Network error:', error)
  showNotification('Connection error. Please try again.')
}
```

---

### 5. User Experience Enhancements

#### Loading States

**During validation**:
```vue
<div v-if="isValidating" class="flex items-center gap-2">
  <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
    <!-- Spinner icon -->
  </svg>
  <span class="text-sm">Checking authentication...</span>
</div>
```

**During logout**:
```vue
<button
  @click="handleLogout"
  :disabled="isLoggingOut"
  class="..."
>
  <span v-if="!isLoggingOut">Logout</span>
  <span v-else>Logging out...</span>
</button>
```

#### Error Messages

```vue
<div v-if="error" class="bg-red-50 text-red-800 p-3 rounded">
  {{ error }}
  <button @click="error = null" class="ml-2 underline">Dismiss</button>
</div>
```

---

### 6. End-to-End Tests

#### Playwright Tests

**Location**: `frontend/tests/e2e/auth.spec.js`

**Tests**:
```javascript
import { test, expect } from '@playwright/test'

test.describe('GitHub OAuth Authentication', () => {
  test('shows login button when not authenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Login with GitHub')).toBeVisible()
  })

  test('redirects to GitHub on login click', async ({ page, context }) => {
    await page.goto('/')

    // Click login button
    const loginButton = page.getByText('Login with GitHub')
    await loginButton.click()

    // Should redirect to GitHub
    await page.waitForURL(/github\.com/)
    expect(page.url()).toContain('github.com/login/oauth/authorize')
  })

  test('shows user menu after authentication', async ({ page, context }) => {
    // Set auth cookie (simulating successful login)
    await context.addCookies([{
      name: 'github_token',
      value: 'test_token',
      domain: 'localhost',
      path: '/'
    }])

    // Mock /api/auth/user endpoint
    await page.route('/api/auth/user', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          login: 'testuser',
          name: 'Test User',
          avatar_url: 'https://github.com/identicons/testuser.png'
        })
      })
    })

    await page.goto('/')

    // Should show user menu
    await expect(page.getByText('Test User')).toBeVisible()
    await expect(page.getByRole('img', { name: 'Test User' })).toBeVisible()
  })

  test('logout clears session', async ({ page, context }) => {
    // Setup authenticated state
    await context.addCookies([{
      name: 'github_token',
      value: 'test_token',
      domain: 'localhost',
      path: '/'
    }])

    // Mock endpoints
    await page.route('/api/auth/user', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ login: 'testuser', name: 'Test User', avatar_url: 'test.png' })
      })
    })

    await page.route('/auth/logout', route => {
      route.fulfill({ status: 200, body: JSON.stringify({ success: true }) })
    })

    await page.goto('/')

    // Click user menu
    await page.getByText('Test User').click()

    // Click logout
    await page.getByText('Logout').click()

    // Should redirect to login
    await page.waitForURL(/\/auth\/login/)
  })

  test('handles 401 gracefully', async ({ page }) => {
    // Mock 401 response
    await page.route('/api/auth/user', route => {
      route.fulfill({ status: 401 })
    })

    await page.goto('/')

    // Should redirect to login
    await page.waitForURL(/\/auth\/login/)
  })
})
```

---

## Validation Criteria

### UI Components
- [ ] Login button visible when not authenticated
- [ ] Login button redirects to `/auth/login`
- [ ] User menu shows avatar and name when authenticated
- [ ] User menu dropdown opens/closes correctly
- [ ] Logout button clears session

### Authentication Flow
- [ ] Page loads immediately (no blocking)
- [ ] Lazy validation happens in background
- [ ] User info displayed after validation succeeds
- [ ] Redirect to login if validation fails
- [ ] 401 responses trigger redirect to login

### State Management
- [ ] User state updates after successful validation
- [ ] Logout clears user state
- [ ] isAuthenticated computed works correctly
- [ ] Error state handled and displayed

### User Experience
- [ ] No flash of unauthenticated content (except brief on invalid)
- [ ] Loading indicators during async operations
- [ ] Smooth transitions between states
- [ ] Error messages are clear and actionable

### End-to-End Tests
- [ ] All E2E tests pass
- [ ] Login flow tested
- [ ] Logout flow tested
- [ ] 401 handling tested
- [ ] UI states tested

## Success Metrics

- Users can authenticate via UI (no manual URL navigation)
- < 100ms overhead for lazy validation
- Zero visible errors during normal flow
- Smooth UX with no blocking operations
- All E2E tests passing

## Testing Strategy

### Manual Testing

1. **Unauthenticated State**:
   - Clear cookies in browser
   - Visit app root
   - Verify login button visible
   - Click login button
   - Complete GitHub OAuth flow
   - Verify redirected back with user menu visible

2. **Authenticated State**:
   - With valid cookie, reload page
   - Verify page loads immediately
   - Verify user menu appears after validation
   - Click user menu
   - Verify dropdown opens
   - Click logout
   - Verify redirected to login

3. **Error Scenarios**:
   - Set invalid token in cookie
   - Reload page
   - Verify redirected to login after brief flash

### Automated Testing

Run E2E tests:
```bash
cd frontend
pnpm test:e2e
```

Expected: All tests pass

## Dependencies

### Prerequisites
- **Phase 1 (Backend)**: Must be complete and deployed
- Backend endpoints must be functional:
  - `GET /auth/login`
  - `GET /auth/callback`
  - `POST /auth/logout`
  - `GET /api/auth/user`

### Vue Components
- Existing: `App.vue` (modify)
- New: `LoginButton.vue`
- New: `UserMenu.vue`

### No New NPM Packages
- All using existing Vue 3 + Tailwind CSS

## Out of Scope

**Not in Phase 2**:
- Infrastructure deployment (Phase 3)
- Service account PAT removal (Phase 3)
- Token refresh UI (future enhancement)
- Multi-account switching (future enhancement)

## Next Steps

After Phase 2 complete:
1. **Phase 3**: Infrastructure deployment - Add OAuth secrets to Secrets Manager, deploy to production, remove service account PAT

## Related

- **Linear**: D2A-31
- **Previous Phase**: `spec/active/github-oauth-backend/spec.md` (must be complete)
- **Next Phase**: `spec/active/github-oauth-infrastructure/spec.md`
