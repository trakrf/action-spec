# Implementation Plan: GitHub OAuth Frontend - User Interface
Generated: 2025-10-31
Specification: spec.md

## Understanding

This is Phase 2 of the GitHub OAuth implementation. The backend OAuth endpoints are already functional (Phase 1 complete). This phase adds the frontend UI components that enable users to authenticate with GitHub through a clean interface.

**Core Requirements**:
- Login button for unauthenticated users
- User menu with avatar/name when authenticated
- Lazy validation (non-blocking page load, async auth check)
- Logout functionality
- Auth state management using Vue reactivity
- Minimal E2E tests (happy path coverage)

**Key Architectural Decisions** (from clarifying questions):
1. Create missing `router.js` file (currently broken import in main.js)
2. Auth UI in App.vue header (global, visible on all pages)
3. Redirect all unauthenticated users to login (app requires auth)
4. No authFetch wrapper - keep simple, handle 401s in validation only
5. Include basic loading spinner and error messages
6. Minimal E2E tests - just happy path

## Relevant Files

### Reference Patterns (existing code to follow)

**Component Structure**:
- `frontend/src/components/Dashboard.vue` (lines 1-56) - Vue 3 Composition API pattern with `<script setup>`
- `frontend/src/components/PodForm.vue` (lines 1-168) - State management with `ref()`, async operations

**Error Handling**:
- `frontend/src/components/Dashboard.vue` (lines 100-106) - Error display pattern (red bordered div)
- `frontend/src/components/PodForm.vue` (lines 151-163) - Try/catch with error state

**Loading States**:
- `frontend/src/components/Dashboard.vue` (lines 91-96) - Simple loading message
- `frontend/src/components/PodForm.vue` (lines 380-398) - SVG spinner for async operations

**Router Usage**:
- `frontend/src/components/Dashboard.vue` (lines 3-5) - Import and use `useRouter()`
- `frontend/src/components/PodForm.vue` (lines 4-6) - Import `useRoute()` and `useRouter()`

**Styling**:
- All components use Tailwind CSS utility classes
- Follow existing button styles from Dashboard.vue (lines 72-83)

### Files to Create

**Core Implementation**:
- `frontend/src/router.js` - Missing router configuration (fixes broken import in main.js:4)
- `frontend/src/stores/auth.js` - Auth state management (reactive refs)
- `frontend/src/components/LoginButton.vue` - GitHub login button
- `frontend/src/components/UserMenu.vue` - Avatar dropdown with logout

**Testing**:
- `frontend/tests/auth.spec.js` - Minimal E2E test (happy path only)
- `frontend/playwright.config.js` - Playwright configuration (if not exists)

### Files to Modify

- `frontend/src/App.vue` - Add header with auth components, lazy validation on mount

## Architecture Impact

- **Subsystems affected**: Frontend UI only
- **New dependencies**: None (using existing Vue 3 + Tailwind CSS + Playwright)
- **Breaking changes**: None (purely additive)

## Task Breakdown

### Task 1: Create Missing Router Configuration
**File**: `frontend/src/router.js`
**Action**: CREATE
**Pattern**: Standard Vue Router setup

**Implementation**:
```javascript
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './components/Dashboard.vue'
import PodForm from './components/PodForm.vue'
import SuccessPage from './components/SuccessPage.vue'
import ErrorPage from './components/ErrorPage.vue'

const routes = [
  { path: '/', name: 'home', component: Dashboard },
  { path: '/pod/new', name: 'new-pod', component: PodForm },
  { path: '/pod/:customer/:env', name: 'edit-pod', component: PodForm },
  { path: '/success', name: 'success', component: SuccessPage },
  { path: '/error', name: 'error', component: ErrorPage }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

**Rationale**: main.js:4 imports `./router` but file doesn't exist, causing app to fail. This creates basic routing for existing components.

**Validation**:
```bash
just frontend lint
```

---

### Task 2: Create Auth State Store
**File**: `frontend/src/stores/auth.js`
**Action**: CREATE
**Pattern**: Match existing pattern of using `ref()` directly (no Pinia/Vuex in project)

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

**Rationale**:
- Uses Vue reactive refs (matches Dashboard.vue pattern at lines 6-8)
- Backend contract: `/api/auth/user` returns `{login, name, avatar_url}` or 401 (see backend/auth.py:172-204)
- Redirect to `/auth/login` on 401 (per user decision: app requires auth)

**Validation**:
```bash
just frontend lint
```

---

### Task 3: Create Login Button Component
**File**: `frontend/src/components/LoginButton.vue`
**Action**: CREATE
**Pattern**: Match Dashboard.vue button styling (lines 72-83)

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
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
    </svg>
    <span>Login with GitHub</span>
  </button>
</template>
```

**Rationale**:
- Backend endpoint `/auth/login` redirects to GitHub OAuth (backend/auth.py:34-65)
- GitHub branding (dark button, GitHub logo)
- Follows existing button style from Dashboard.vue

**Validation**:
```bash
just frontend lint
```

---

### Task 4: Create User Menu Component
**File**: `frontend/src/components/UserMenu.vue`
**Action**: CREATE
**Pattern**: Match Dashboard.vue structure and Tailwind styling

**Implementation**:
```vue
<script setup>
import { ref } from 'vue'
import { user, logout } from '@/stores/auth'

const isOpen = ref(false)
const isLoggingOut = ref(false)

const handleLogout = async () => {
  isLoggingOut.value = true
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
        :alt="user.name || user.login"
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
      class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 z-50"
    >
      <div class="px-4 py-2 text-sm text-gray-700 border-b">
        <div class="font-medium">{{ user.name }}</div>
        <div class="text-gray-500">@{{ user.login }}</div>
      </div>

      <button
        @click="handleLogout"
        :disabled="isLoggingOut"
        class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
      >
        <span v-if="!isLoggingOut">Logout</span>
        <span v-else>Logging out...</span>
      </button>
    </div>
  </div>
</template>
```

**Rationale**:
- User object shape: `{login, name, avatar_url}` (backend/auth.py:198-203)
- Logout endpoint: `POST /auth/logout` returns `{success: true}` (backend/auth.py:156-169)
- After logout, redirect to `/auth/login` (per user decision)
- Loading state for logout button (follows existing pattern)

**Validation**:
```bash
just frontend lint
```

---

### Task 5: Update App.vue with Auth Integration
**File**: `frontend/src/App.vue`
**Action**: MODIFY
**Pattern**: Add header similar to Dashboard.vue (lines 61-86)

**Current content** (App.vue:1-10):
```vue
<script setup>
// No state needed - components handle their own data
</script>

<template>
  <div class="bg-gray-50 min-h-screen">
    <RouterView />
  </div>
</template>
```

**Changes**:
1. Import auth store and components
2. Add `onMounted` to trigger lazy validation
3. Add header with conditional auth UI
4. Add loading spinner during validation
5. Add error display if validation fails

**New implementation**:
```vue
<script setup>
import { onMounted } from 'vue'
import { validateAuth, isValidating, user, isAuthenticated, error } from '@/stores/auth'
import LoginButton from '@/components/LoginButton.vue'
import UserMenu from '@/components/UserMenu.vue'

// Validate auth on page load (non-blocking)
onMounted(() => {
  validateAuth()
})
</script>

<template>
  <div class="bg-gray-50 min-h-screen">
    <!-- Header with auth components -->
    <header class="bg-white border-b border-gray-200 px-4 py-3 flex justify-between items-center">
      <h1 class="text-xl font-bold text-gray-900">Action Spec</h1>

      <!-- Loading indicator during validation -->
      <div v-if="isValidating" class="flex items-center gap-2 text-sm text-gray-500">
        <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>Checking authentication...</span>
      </div>

      <!-- Show login button or user menu -->
      <LoginButton v-else-if="!isAuthenticated" />
      <UserMenu v-else-if="isAuthenticated" />
    </header>

    <!-- Error display (if validation fails non-401) -->
    <div v-if="error" class="bg-red-50 border-l-4 border-red-400 p-4 m-4">
      <p class="text-red-700">{{ error }}</p>
    </div>

    <!-- Main content (loads immediately) -->
    <main>
      <RouterView />
    </main>
  </div>
</template>
```

**Rationale**:
- Lazy validation: `onMounted` doesn't block render (Dashboard.vue pattern at lines 53-55)
- Spinner SVG: Matches PodForm.vue spinner (lines 380-398)
- Error display: Matches Dashboard.vue error pattern (lines 100-106)
- Auth UI placement: Global header visible on all pages (per user decision)
- Note: `<RouterView />` uses capital R (current App.vue convention)

**Validation**:
```bash
just frontend lint
just frontend build
```

---

### Task 6: Create Minimal E2E Tests
**File**: `frontend/tests/auth.spec.js`
**Action**: CREATE
**Pattern**: Playwright test structure (happy path only per user decision)

**Implementation**:
```javascript
import { test, expect } from '@playwright/test'

test.describe('GitHub OAuth Authentication', () => {
  test('shows login button when not authenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Login with GitHub')).toBeVisible()
  })

  test('shows user menu after authentication', async ({ page, context }) => {
    // Set auth cookie (simulating successful login)
    await context.addCookies([{
      name: 'github_token',
      value: 'test_token_12345',
      domain: 'localhost',
      path: '/'
    }])

    // Mock /api/auth/user endpoint
    await page.route('/api/auth/user', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          login: 'testuser',
          name: 'Test User',
          avatar_url: 'https://github.com/identicons/testuser.png'
        })
      })
    })

    await page.goto('/')

    // Should show user menu after validation
    await expect(page.getByText('Test User')).toBeVisible()
    await expect(page.getByRole('img', { name: 'Test User' })).toBeVisible()
  })
})
```

**Rationale**:
- Happy path only (per user decision: minimal tests)
- Tests core flow: unauthenticated shows login, authenticated shows user menu
- Mocks API endpoint to avoid real GitHub API calls
- Uses `context.addCookies()` to simulate authenticated state

**Note**: If `frontend/playwright.config.js` doesn't exist, create basic config:
```javascript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

**Validation**:
```bash
just frontend test
```

---

## Risk Assessment

### Risk: Router configuration doesn't match existing usage
**Likelihood**: Low
**Impact**: Medium (app won't load)
**Mitigation**: Verified existing components already use `useRouter()` and expect named routes. Router config matches observed usage patterns.

### Risk: Cookie-based auth doesn't work in E2E tests
**Likelihood**: Low
**Impact**: Medium (tests fail)
**Mitigation**: Use Playwright's `context.addCookies()` API which is designed for this. Mock the validation endpoint to avoid real API calls.

### Risk: Auth validation causes redirect loops
**Likelihood**: Low
**Impact**: High (app unusable)
**Mitigation**: Only redirect on 401. Successful validation sets user state without redirect. Error state displays message without redirect.

### Risk: App.vue already has header structure
**Likelihood**: Low (verified current content)
**Impact**: Low (merge conflict)
**Mitigation**: Read current App.vue first (already done - it's minimal). Current version has no header.

## Integration Points

### Store Updates
- New auth store at `frontend/src/stores/auth.js`
- Exports: `user`, `isValidating`, `error`, `isAuthenticated`, `validateAuth()`, `logout()`

### Component Integration
- App.vue imports LoginButton and UserMenu components
- App.vue imports auth store for state/actions
- UserMenu imports auth store for user data and logout action

### Route Changes
- New router.js file created (fixes broken import)
- No changes to existing route definitions
- Routes: `/` (Dashboard), `/pod/new`, `/pod/:customer/:env`, `/success`, `/error`

### Backend API Contract
- `GET /api/auth/user` → `{login, name, avatar_url}` or 401
- `POST /auth/logout` → `{success: true}`
- `GET /auth/login` → 302 redirect to GitHub
- `GET /auth/callback` → 302 redirect to `/` with cookie set

## VALIDATION GATES (MANDATORY)

**CRITICAL**: These are not suggestions - they are GATES that block progress.

After EVERY code change:
- **Gate 1: Syntax & Style** → `just frontend lint`
- **Gate 2: Build** → `just frontend build`

After completing all tasks:
- **Gate 3: E2E Tests** → `just frontend test`

**Enforcement Rules**:
- If ANY gate fails → Fix immediately
- Re-run validation after fix
- Loop until ALL gates pass
- After 3 failed attempts → Stop and ask for help

**Do not proceed to next task until current task passes all applicable gates.**

## Validation Sequence

**After each task (1-5)**:
```bash
just frontend lint
```

**After Task 5 (App.vue complete)**:
```bash
just frontend build
```

**After Task 6 (tests complete)**:
```bash
just frontend test
```

**Final validation**:
```bash
just validate
```

## Plan Quality Assessment

**Complexity Score**: 3/10 (LOW)

**Confidence Score**: 8/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec
✅ Backend API contract verified (backend/auth.py exists and documented)
✅ Similar patterns found in codebase (Dashboard.vue, PodForm.vue)
✅ All clarifying questions answered
✅ No new NPM packages required
✅ Existing test framework (Playwright) already installed
⚠️ Router file missing but pattern is standard
⚠️ No existing tests to reference (creating first test)

**Assessment**: High confidence implementation. All patterns are well-established in the codebase. The missing router.js is straightforward to create. Backend API is already functional (Phase 1 complete). Only unknown is E2E test execution environment, but Playwright is configured in package.json.

**Estimated one-pass success probability**: 85%

**Reasoning**:
- Strong existing patterns to follow
- Backend already working (Phase 1 shipped)
- No complex state management (simple reactive refs)
- Minimal scope (6 tasks, all well-defined)
- Main risk is E2E test environment setup, but Playwright is already in devDependencies
- User decisions eliminated architectural ambiguity
