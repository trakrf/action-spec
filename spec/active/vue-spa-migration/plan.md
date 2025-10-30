# Implementation Plan: Jinja → Vue 3 SPA Migration (Parity Release)
Generated: 2025-10-30
Specification: spec.md

## Understanding

This is a **1:1 migration** of existing Jinja templates to Vue 3 SPA. The goal is architectural modernization (SSR → CSR) while maintaining exact functional parity. No feature additions, no AWS resource pickers, no nested YAML editors - just translate the 4 existing templates into Vue components.

**Current Architecture:**
- Flask serves Jinja templates (SSR)
- Forms POST to Flask routes
- JavaScript only for live preview
- Full page reloads on navigation
- TailwindCSS via CDN

**Target Architecture:**
- Flask serves Vue SPA + REST API
- Vue components fetch/post to `/api/*` endpoints
- Client-side routing (Vue Router)
- No page reloads
- TailwindCSS via CDN (matching current design exactly)

**Existing REST API (PR #35):**
- `GET /api/pods` - List all pods
- `GET /api/pod/<customer>/<env>` - Get specific pod spec
- `POST /api/pod` - Create or update pod (returns PR details)

**Key Constraint:** POLS (Principle of Least Surprise) - keep it simple, no bells/whistles, engineers should understand everything immediately.

---

## Relevant Files

### Reference Patterns (existing code to follow)

**Jinja Templates** (translate these):
- `/home/mike/action-spec/backend/templates/index.html.j2` (lines 1-95) - Dashboard layout, pod grouping by customer, environment badges
- `/home/mike/action-spec/backend/templates/form.html.j2` (lines 1-237) - Dual-mode form (create/edit), real-time preview JavaScript, loading state on submit
- `/home/mike/action-spec/backend/templates/success.html.j2` (lines 1-133) - PR link display, workflow inputs summary
- `/home/mike/action-spec/backend/templates/error.html.j2` (lines 1-111) - Dynamic error icons, conditional pod list display

**Flask API Endpoints** (existing, use these):
- `/home/mike/action-spec/backend/api/routes.py` (lines 15-41) - `GET /api/pods` endpoint
- `/home/mike/action-spec/backend/api/routes.py` (lines 43-90) - `GET /api/pod/<customer>/<env>` endpoint
- `/home/mike/action-spec/backend/api/routes.py` (lines 93-193) - `POST /api/pod` endpoint

**Flask App Configuration**:
- `/home/mike/action-spec/backend/app.py` (lines 82-108) - Validation functions (`validate_path_component`, `validate_instance_name`)
- `/home/mike/action-spec/backend/app.py` (lines 282-288) - Cache refresh route pattern

### Files to Create

**Vue Project Structure**:
- `src/frontend/` - Vue 3 project root (created by scaffold command)
- `src/frontend/src/components/Dashboard.vue` - Replicate index.html.j2
- `src/frontend/src/components/PodForm.vue` - Replicate form.html.j2
- `src/frontend/src/components/SuccessPage.vue` - Replicate success.html.j2
- `src/frontend/src/components/ErrorPage.vue` - Replicate error.html.j2
- `src/frontend/src/router/index.js` - Vue Router config matching Flask routes
- `src/frontend/src/App.vue` - Root component with router-view
- `src/frontend/src/main.js` - Vue app initialization
- `src/frontend/src/assets/main.css` - Custom styles matching Jinja templates
- `src/frontend/vite.config.js` - Vite proxy config for `/api/*` → `localhost:5000`

### Files to Modify

**Flask Backend**:
- `/home/mike/action-spec/backend/app.py` - Add static file serving for Vue SPA build, add SPA fallback route handler

**Jinja Templates** (to be removed after Vue works):
- `/home/mike/action-spec/backend/templates/index.html.j2` - Delete
- `/home/mike/action-spec/backend/templates/form.html.j2` - Delete
- `/home/mike/action-spec/backend/templates/success.html.j2` - Delete
- `/home/mike/action-spec/backend/templates/error.html.j2` - Delete

---

## Architecture Impact

- **Subsystems affected**: Frontend (new Vue SPA), Backend (Flask static file serving)
- **New dependencies**:
  - `vue@3` (Vue 3 framework)
  - `vue-router@4` (Client-side routing)
  - `vite@5` (Build tool and dev server)
- **Breaking changes**: None (REST API already exists, just changing frontend)
- **Deployment changes**: Flask must serve `src/frontend/dist/` in production

---

## Task Breakdown

### Task 1: Scaffold Vue 3 Project
**Action**: CREATE
**Pattern**: Use Vue 3 official scaffold tool

**Implementation**:
```bash
# Run from project root
npm create vue@latest src/frontend

# Interactive prompts - select:
# - Project name: frontend
# - Add TypeScript? No
# - Add JSX Support? No
# - Add Vue Router? Yes
# - Add Pinia? No (YAGNI - no state management needed)
# - Add Vitest? No (no tests for parity migration)
# - Add End-to-End Testing? No
# - Add ESLint? Yes (code quality)
# - Add Prettier? No (keep it simple)

cd src/frontend
npm install
```

**Validation**:
```bash
cd src/frontend
npm run dev
# Should see "Vite + Vue" at http://localhost:5173
```

**Success Criteria**:
- Vue 3 project created at `src/frontend/`
- Dependencies installed
- Dev server runs without errors
- Can access default Vue welcome page

---

### Task 2: Configure Vite Proxy
**File**: `src/frontend/vite.config.js`
**Action**: MODIFY
**Pattern**: Add server.proxy config to forward `/api/*` to Flask backend

**Implementation**:
```javascript
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
```

**Validation**:
```bash
# Terminal 1: Start Flask backend
cd backend
python app.py

# Terminal 2: Start Vue dev server
cd src/frontend
npm run dev

# Test proxy: curl http://localhost:5173/api/pods
# Should return JSON pod list from Flask
```

**Success Criteria**:
- `/api/*` requests from Vue dev server forward to Flask
- No CORS errors in browser console
- Can fetch pod list from Vue dev server URL

---

### Task 3: Create Dashboard Component
**File**: `src/frontend/src/components/Dashboard.vue`
**Action**: CREATE
**Pattern**: Reference `/home/mike/action-spec/backend/templates/index.html.j2`

**Implementation**:
```vue
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const pods = ref([])
const loading = ref(true)
const error = ref(null)

// Group pods by customer (matching Jinja template logic)
const customers = ref({})

async function fetchPods() {
  loading.value = true
  error.value = null

  try {
    const response = await fetch('/api/pods')
    if (!response.ok) throw new Error('Failed to fetch pods')

    const data = await response.json()
    pods.value = data

    // Group by customer
    customers.value = {}
    data.forEach(pod => {
      if (!customers.value[pod.customer]) {
        customers.value[pod.customer] = []
      }
      customers.value[pod.customer].push(pod.env)
    })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function refreshCache() {
  await fetch('/api/refresh', { method: 'POST' })
  await fetchPods()
}

function getEnvBadgeClass(env) {
  const colors = {
    dev: 'bg-green-100 text-green-800',
    stg: 'bg-yellow-100 text-yellow-800',
    prd: 'bg-red-100 text-red-800'
  }
  return colors[env] || 'bg-gray-100 text-gray-800'
}

onMounted(() => {
  fetchPods()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <!-- Header -->
    <header class="mb-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-4xl font-bold text-gray-900 mb-2">
            Spec Editor - Pod Management
          </h1>
          <p class="text-lg text-gray-600">
            View and manage infrastructure pod configurations
          </p>
        </div>
        <div class="flex gap-3">
          <button
            @click="refreshCache"
            class="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition font-medium shadow-md hover:shadow-lg"
          >
            🔄 Refresh
          </button>
          <button
            @click="router.push('/pod/new')"
            class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-md hover:shadow-lg"
          >
            + Create New Pod
          </button>
        </div>
      </div>
    </header>

    <!-- Pod List -->
    <main>
      <div v-if="loading" class="text-center py-12">
        <p class="text-gray-600">Loading pods...</p>
      </div>

      <div v-else-if="error" class="bg-red-50 border-l-4 border-red-400 p-4">
        <p class="text-red-700">{{ error }}</p>
      </div>

      <div v-else>
        <!-- Customer Groups -->
        <div
          v-for="(envs, customer) in customers"
          :key="customer"
          class="bg-white rounded-lg shadow-md p-6 mb-6"
        >
          <h2 class="text-2xl font-semibold text-gray-800 mb-4 capitalize">
            {{ customer }}
          </h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <router-link
              v-for="env in envs"
              :key="env"
              :to="`/pod/${customer}/${env}`"
              class="block p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:shadow-lg transition-all"
            >
              <div class="flex items-center justify-between">
                <span class="text-lg font-medium text-gray-700">
                  {{ customer }} / {{ env }}
                </span>
                <span
                  :class="['px-3 py-1 text-sm font-medium rounded-full', getEnvBadgeClass(env)]"
                >
                  {{ env }}
                </span>
              </div>
            </router-link>
          </div>
        </div>

        <!-- No Pods Warning -->
        <div v-if="pods.length === 0" class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <p class="text-yellow-700">
            No pods found in infra/. Check your repository structure.
          </p>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="mt-12 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
      <p>
        Spec Editor -
        <a
          href="https://github.com/trakrf/action-spec"
          class="text-blue-600 hover:underline"
        >
          trakrf/action-spec
        </a>
      </p>
      <p class="mt-2">
        ActionSpec v0.1.0 - Infrastructure Deployment via Spec Editor
      </p>
    </footer>
  </div>
</template>
```

**Validation**:
- Navigate to http://localhost:5173 (Vue dev server)
- Should see pod list grouped by customer
- Environment badges should match colors (dev=green, stg=yellow, prd=red)
- Clicking pod card should navigate to edit form
- Refresh button should work

**Success Criteria**:
- Visually identical to index.html.j2
- Pod grouping works correctly
- Navigation to form works
- Refresh clears cache and reloads

---

### Task 4: Create PodForm Component
**File**: `src/frontend/src/components/PodForm.vue`
**Action**: CREATE
**Pattern**: Reference `/home/mike/action-spec/backend/templates/form.html.j2`

**Implementation**:
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// Form state
const customer = ref('')
const env = ref('')
const instanceName = ref('')
const wafEnabled = ref(false)
const loading = ref(false)
const submitting = ref(false)
const error = ref(null)

// Mode detection
const mode = computed(() => {
  return route.params.customer && route.params.env ? 'edit' : 'new'
})

// Computed instance name preview
const computedName = computed(() => {
  const c = mode.value === 'edit' ? route.params.customer : (customer.value || '?')
  const e = mode.value === 'edit' ? route.params.env : (env.value || '?')
  const n = instanceName.value || '?'
  return `${c}-${e}-${n}`
})

// Environment badge color
function getEnvBadgeClass(envName) {
  const colors = {
    dev: 'bg-green-100 text-green-800',
    stg: 'bg-yellow-100 text-yellow-800',
    prd: 'bg-red-100 text-red-800'
  }
  return colors[envName] || 'bg-gray-100 text-gray-800'
}

// Fetch pod spec in edit mode
async function fetchPodSpec() {
  if (mode.value !== 'edit') return

  loading.value = true
  error.value = null

  try {
    const response = await fetch(`/api/pod/${route.params.customer}/${route.params.env}`)
    if (!response.ok) throw new Error('Pod not found')

    const data = await response.json()

    // Populate form from spec
    customer.value = data.metadata.customer
    env.value = data.metadata.environment
    instanceName.value = data.spec.compute.instance_name
    wafEnabled.value = data.spec.security.waf.enabled
  } catch (e) {
    error.value = e.message
    router.push({
      name: 'error',
      query: {
        type: 'not_found',
        title: 'Pod Not Found',
        message: `Could not find spec for ${route.params.customer}/${route.params.env}`
      }
    })
  } finally {
    loading.value = false
  }
}

// Client-side validation
function validateForm() {
  // Instance name pattern: [a-z0-9-]+, 1-30 chars, no start/end hyphen
  const pattern = /^[a-z0-9-]+$/

  if (!instanceName.value || instanceName.value.length > 30) {
    return 'Instance name must be 1-30 characters'
  }

  if (!pattern.test(instanceName.value)) {
    return 'Instance name must be lowercase letters, numbers, and hyphens only'
  }

  if (instanceName.value.startsWith('-') || instanceName.value.endsWith('-')) {
    return 'Instance name cannot start or end with hyphen'
  }

  if (mode.value === 'new') {
    if (!customer.value) return 'Customer is required'
    if (!env.value) return 'Environment is required'
  }

  return null
}

// Submit form
async function handleSubmit() {
  // Validate
  const validationError = validateForm()
  if (validationError) {
    router.push({
      name: 'error',
      query: {
        type: 'validation',
        title: 'Invalid Input',
        message: validationError
      }
    })
    return
  }

  submitting.value = true

  try {
    const payload = {
      customer: mode.value === 'edit' ? route.params.customer : customer.value,
      env: mode.value === 'edit' ? route.params.env : env.value,
      spec: {
        instance_name: instanceName.value,
        waf_enabled: wafEnabled.value
      }
    }

    const response = await fetch('/api/pod', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || 'Deployment failed')
    }

    // Navigate to success page with PR details
    router.push({
      name: 'success',
      query: {
        mode: mode.value,
        customer: payload.customer,
        env: payload.env,
        instance_name: instanceName.value,
        waf_enabled: wafEnabled.value,
        pr_url: data.pr_url,
        pr_number: data.pr_number
      }
    })
  } catch (e) {
    router.push({
      name: 'error',
      query: {
        type: 'api_error',
        title: 'Deployment Failed',
        message: e.message
      }
    })
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchPodSpec()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <!-- Breadcrumb (edit mode only) -->
    <nav v-if="mode === 'edit'" class="mb-6 text-sm">
      <router-link to="/" class="text-blue-600 hover:underline">Home</router-link>
      <span class="text-gray-400 mx-2">/</span>
      <span class="text-gray-700 font-medium">{{ route.params.customer }}</span>
      <span class="text-gray-400 mx-2">/</span>
      <span class="text-gray-700 font-medium">{{ route.params.env }}</span>
    </nav>

    <!-- Header -->
    <header class="mb-8">
      <!-- Edit Mode: Customer/env badges -->
      <div v-if="mode === 'edit'" class="flex items-center justify-between mb-4">
        <h1 class="text-3xl font-bold text-gray-900 capitalize">
          {{ route.params.customer }}
        </h1>
        <span
          :class="['px-4 py-2 text-lg font-medium rounded-full', getEnvBadgeClass(route.params.env)]"
        >
          {{ route.params.env }}
        </span>
      </div>

      <!-- Create Mode: Simple title -->
      <h1 v-else class="text-3xl font-bold text-gray-900 mb-4">
        Create New Pod
      </h1>
    </header>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <p class="text-gray-600">Loading pod spec...</p>
    </div>

    <!-- Form -->
    <main v-else>
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-xl font-semibold text-gray-800 mb-4">
          Pod Configuration
        </h2>

        <form @submit.prevent="handleSubmit" class="space-y-6">
          <!-- Customer and Environment (create mode only) -->
          <div v-if="mode === 'new'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label for="customer" class="block text-sm font-medium text-gray-700 mb-2">
                Customer *
              </label>
              <select
                id="customer"
                v-model="customer"
                required
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">-- Select Customer --</option>
                <option value="advworks">advworks</option>
                <option value="northwind">northwind</option>
                <option value="contoso">contoso</option>
              </select>
            </div>

            <div>
              <label for="environment" class="block text-sm font-medium text-gray-700 mb-2">
                Environment *
              </label>
              <select
                id="environment"
                v-model="env"
                required
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">-- Select Environment --</option>
                <option value="dev">dev (Development)</option>
                <option value="stg">stg (Staging)</option>
                <option value="prd">prd (Production)</option>
              </select>
            </div>
          </div>

          <!-- Computed Instance Name Preview -->
          <div class="bg-gray-50 p-4 rounded border border-gray-200">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Full Instance Name Preview
            </label>
            <p class="text-lg font-mono text-gray-900">
              {{ computedName }}
            </p>
            <p class="text-xs text-gray-500 mt-1">
              Format: {customer}-{environment}-{instance_name}
            </p>
          </div>

          <!-- Compute Section -->
          <div class="border-t pt-6">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">Compute</h3>

            <div>
              <label for="instance_name" class="block text-sm font-medium text-gray-700 mb-2">
                Instance Name *
              </label>
              <input
                id="instance_name"
                v-model="instanceName"
                type="text"
                required
                pattern="[a-z0-9-]+"
                placeholder="e.g., web1, app1"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <small class="text-gray-600 text-xs">Lowercase letters, numbers, hyphens only</small>
              <small class="text-gray-500 text-xs block mt-1">
                Note: Instance type is managed in spec.yml, not via this form
              </small>
            </div>
          </div>

          <!-- Security Section -->
          <div class="border-t pt-6">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">Security</h3>

            <div class="flex items-center">
              <input
                id="waf_enabled"
                v-model="wafEnabled"
                type="checkbox"
                class="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              />
              <label for="waf_enabled" class="ml-3 text-sm font-medium text-gray-700">
                Web Application Firewall (WAF) Enabled
              </label>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="border-t pt-6 flex justify-between">
            <router-link
              to="/"
              class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
            >
              ← Back to Home
            </router-link>

            <button
              type="submit"
              :disabled="submitting"
              class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-70 disabled:cursor-wait"
            >
              <span v-if="submitting" class="flex items-center">
                <svg
                  class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Deploying...
              </span>
              <span v-else>Deploy Changes</span>
            </button>
          </div>
        </form>
      </div>
    </main>

    <!-- Footer -->
    <footer class="mt-12 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
      <p>
        Spec Editor -
        <a
          href="https://github.com/trakrf/action-spec"
          class="text-blue-600 hover:underline"
        >
          trakrf/action-spec
        </a>
      </p>
      <p class="mt-2">
        ActionSpec v0.1.0 - Infrastructure Deployment via Spec Editor
      </p>
    </footer>
  </div>
</template>
```

**Validation**:
- Create mode: Navigate to `/pod/new`, fill form, verify preview updates in real-time
- Edit mode: Navigate to `/pod/<customer>/<env>`, verify form pre-populated
- Submit: Verify loading state appears (button shows spinner)
- Validation: Try invalid instance names, verify inline error navigation

**Success Criteria**:
- Visually identical to form.html.j2
- Dual-mode (create/edit) works correctly
- Real-time preview updates as user types
- Client-side validation matches server rules
- Submit shows loading state

---

### Task 5: Create SuccessPage Component
**File**: `src/frontend/src/components/SuccessPage.vue`
**Action**: CREATE
**Pattern**: Reference `/home/mike/action-spec/backend/templates/success.html.j2`

**Implementation**:
```vue
<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const mode = computed(() => route.query.mode || 'edit')
const customer = computed(() => route.query.customer)
const env = computed(() => route.query.env)
const instanceName = computed(() => route.query.instance_name)
const wafEnabled = computed(() => route.query.waf_enabled === 'true')
const prUrl = computed(() => route.query.pr_url)
const prNumber = computed(() => route.query.pr_number)
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <header class="mb-8">
      <h1 class="text-4xl font-bold text-gray-900 mb-2">
        Spec Editor
      </h1>
    </header>

    <main>
      <div class="bg-white rounded-lg shadow-md p-8">
        <!-- Success Icon -->
        <div class="text-center mb-6">
          <div class="text-6xl mb-4">✅</div>
          <h2 class="text-3xl font-bold text-gray-900 mb-2">
            Deployment Started
          </h2>
        </div>

        <!-- Mode-specific message -->
        <p class="text-lg text-gray-700 mb-4">
          <span v-if="mode === 'new'">
            Creating new pod: <strong class="font-mono">{{ customer }}/{{ env }}</strong>
          </span>
          <span v-else>
            Updating pod: <strong class="font-mono">{{ customer }}/{{ env }}</strong>
          </span>
        </p>

        <!-- Workflow Inputs -->
        <div class="bg-gray-50 p-6 rounded-lg border border-gray-200 mb-6">
          <h3 class="text-lg font-semibold text-gray-800 mb-4">
            Workflow Inputs (Sent)
          </h3>
          <dl class="space-y-2">
            <div class="flex">
              <dt class="font-medium text-gray-700 w-40">Customer:</dt>
              <dd class="font-mono text-gray-900">{{ customer }}</dd>
            </div>
            <div class="flex">
              <dt class="font-medium text-gray-700 w-40">Environment:</dt>
              <dd class="font-mono text-gray-900">{{ env }}</dd>
            </div>
            <div class="flex">
              <dt class="font-medium text-gray-700 w-40">Instance Name:</dt>
              <dd class="font-mono text-gray-900">{{ instanceName }}</dd>
            </div>
            <div class="flex">
              <dt class="font-medium text-gray-700 w-40">WAF Enabled:</dt>
              <dd class="font-mono text-gray-900">{{ wafEnabled }}</dd>
            </div>
          </dl>
        </div>

        <!-- PR Link -->
        <p class="mb-4">
          <template v-if="prUrl">
            View PR:
            <a
              :href="prUrl"
              target="_blank"
              class="text-blue-600 hover:underline font-medium"
            >
              #{{ prNumber }} →
            </a>
          </template>
          <template v-else>
            View progress:
            <a
              href="https://github.com/trakrf/action-spec/actions"
              target="_blank"
              class="text-blue-600 hover:underline font-medium"
            >
              GitHub Actions Tab →
            </a>
          </template>
        </p>
        <p class="text-gray-600 mb-6">
          The deployment typically takes 3-5 minutes to complete.
        </p>

        <!-- Navigation -->
        <div class="flex gap-4">
          <router-link
            :to="`/pod/${customer}/${env}`"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            View Pod
          </router-link>
          <router-link
            to="/"
            class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
          >
            Back to Home
          </router-link>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="mt-12 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
      <p>
        Spec Editor -
        <a
          href="https://github.com/trakrf/action-spec"
          class="text-blue-600 hover:underline"
        >
          trakrf/action-spec
        </a>
      </p>
      <p class="mt-2">
        ActionSpec v0.1.0 - Infrastructure Deployment via Spec Editor
      </p>
    </footer>
  </div>
</template>
```

**Validation**:
- Navigate from form submission
- Verify PR link displays correctly
- Verify workflow inputs match form data
- Test "View Pod" and "Back to Home" navigation

**Success Criteria**:
- Visually identical to success.html.j2
- Displays PR link and number
- Shows workflow inputs correctly
- Navigation buttons work

---

### Task 6: Create ErrorPage Component
**File**: `src/frontend/src/components/ErrorPage.vue`
**Action**: CREATE
**Pattern**: Reference `/home/mike/action-spec/backend/templates/error.html.j2`

**Implementation**:
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const pods = ref([])

const errorType = computed(() => route.query.type || 'default')
const errorTitle = computed(() => route.query.title || 'Error')
const errorMessage = computed(() => route.query.message || 'An error occurred')
const showPods = computed(() => route.query.show_pods === 'true')

const errorIcon = computed(() => {
  const icons = {
    not_found: '🔍',
    validation: '⚠️',
    conflict: '⚠️',
    forbidden: '🔒',
    api_error: '🔌',
    server_error: '💥',
    service_unavailable: '🚫'
  }
  return icons[errorType.value] || '❌'
})

function getEnvBadgeClass(env) {
  const colors = {
    dev: 'bg-green-100 text-green-800',
    stg: 'bg-yellow-100 text-yellow-800',
    prd: 'bg-red-100 text-red-800'
  }
  return colors[env] || 'bg-gray-100 text-gray-800'
}

async function fetchPods() {
  if (!showPods.value) return

  try {
    const response = await fetch('/api/pods')
    if (response.ok) {
      pods.value = await response.json()
    }
  } catch (e) {
    console.error('Failed to fetch pods for error page:', e)
  }
}

onMounted(() => {
  fetchPods()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <header class="mb-8">
      <h1 class="text-4xl font-bold text-gray-900 mb-2">
        Spec Editor
      </h1>
    </header>

    <main>
      <div class="bg-white rounded-lg shadow-md p-8 mb-6">
        <!-- Error Icon and Title -->
        <div class="text-center mb-6">
          <div class="text-6xl mb-4">{{ errorIcon }}</div>
          <h2 class="text-3xl font-bold text-gray-900 mb-2">
            {{ errorTitle }}
          </h2>
          <p class="text-lg text-gray-600">
            {{ errorMessage }}
          </p>
        </div>

        <!-- Valid Pods List (if available) -->
        <div v-if="showPods && pods.length > 0" class="border-t pt-6">
          <h3 class="text-xl font-semibold text-gray-800 mb-4">
            Available Pods
          </h3>
          <p class="text-gray-600 mb-4">
            Try one of these valid pods instead:
          </p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <router-link
              v-for="pod in pods"
              :key="`${pod.customer}-${pod.env}`"
              :to="`/pod/${pod.customer}/${pod.env}`"
              class="block p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:shadow-lg transition-all"
            >
              <div class="flex items-center justify-between">
                <span class="font-medium text-gray-700">
                  {{ pod.customer }} / {{ pod.env }}
                </span>
                <span
                  :class="['px-3 py-1 text-sm font-medium rounded-full', getEnvBadgeClass(pod.env)]"
                >
                  {{ pod.env }}
                </span>
              </div>
            </router-link>
          </div>
        </div>

        <!-- Navigation -->
        <div class="border-t pt-6 mt-6">
          <router-link
            to="/"
            class="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            ← Back to Home
          </router-link>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="mt-12 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
      <p>
        Spec Editor -
        <a
          href="https://github.com/trakrf/action-spec"
          class="text-blue-600 hover:underline"
        >
          trakrf/action-spec
        </a>
      </p>
    </footer>
  </div>
</template>
```

**Validation**:
- Navigate with different error types: `?type=validation&title=Test&message=Error`
- Verify correct icon displays for each error type
- Test with `show_pods=true` to verify pod list appears
- Test navigation back to home

**Success Criteria**:
- Visually identical to error.html.j2
- Correct icon for each error type
- Conditionally shows pod list
- Back to home navigation works

---

### Task 7: Configure Vue Router
**File**: `src/frontend/src/router/index.js`
**Action**: MODIFY
**Pattern**: Match existing Flask routes

**Implementation**:
```javascript
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../components/Dashboard.vue'
import PodForm from '../components/PodForm.vue'
import SuccessPage from '../components/SuccessPage.vue'
import ErrorPage from '../components/ErrorPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/pod/new',
      name: 'new-pod',
      component: PodForm
    },
    {
      path: '/pod/:customer/:env',
      name: 'edit-pod',
      component: PodForm
    },
    {
      path: '/success',
      name: 'success',
      component: SuccessPage
    },
    {
      path: '/error',
      name: 'error',
      component: ErrorPage
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/error?type=not_found&title=Page Not Found&message=The page you are looking for does not exist'
    }
  ]
})

export default router
```

**Validation**:
- Test all routes:
  - `/` → Dashboard
  - `/pod/new` → PodForm (create mode)
  - `/pod/advworks/dev` → PodForm (edit mode)
  - `/success?mode=new&customer=test&env=dev` → SuccessPage
  - `/error?type=validation&title=Test&message=Error` → ErrorPage
  - `/invalid-route` → ErrorPage (404)

**Success Criteria**:
- All routes work correctly
- Browser back/forward buttons work
- Direct URL access works for all routes
- 404s redirect to error page

---

### Task 8: Update App.vue Root Component
**File**: `src/frontend/src/App.vue`
**Action**: MODIFY
**Pattern**: Simple router-view wrapper, Tailwind CDN in index.html

**Implementation**:
```vue
<script setup>
// No state needed - components handle their own data
</script>

<template>
  <div class="bg-gray-50 min-h-screen">
    <RouterView />
  </div>
</template>

<style>
/* Remove default styles, let Tailwind handle everything */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
</style>
```

**Validation**:
- Run dev server, verify components render
- Verify background color matches (bg-gray-50)

**Success Criteria**:
- RouterView renders active component
- No layout issues
- Matches Jinja template body background

---

### Task 9: Update index.html with Tailwind CDN
**File**: `src/frontend/index.html`
**Action**: MODIFY
**Pattern**: Add Tailwind CDN matching Jinja templates

**Implementation**:
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spec Editor - Pod Management</title>
    <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

**Validation**:
- Verify Tailwind classes work (check console for Tailwind loaded)
- Verify title matches Jinja template

**Success Criteria**:
- Tailwind CDN loads correctly
- No console errors
- Page title correct

---

### Task 10: Add API Refresh Endpoint
**File**: `backend/api/routes.py`
**Action**: MODIFY
**Pattern**: Add POST endpoint matching Flask `/refresh` route

**Implementation**:
Add after `get_pods()` function:

```python
@api_blueprint.route('/refresh', methods=['POST'])
def refresh_cache():
    """
    POST /api/refresh

    Clear the pod cache and return success.

    Returns:
        200: {"message": "Cache cleared"}
    """
    # Clear cache using main app's cache mechanism
    main_app._cache.clear()
    main_app.logger.info("Cache cleared via API")
    return json_success({"message": "Cache cleared"})
```

**Validation**:
```bash
# Test refresh endpoint
curl -X POST http://localhost:5000/api/refresh

# Should return: {"message": "Cache cleared"}
```

**Success Criteria**:
- Endpoint clears cache
- Returns success message
- Dashboard refresh button works

---

### Task 11: Configure Flask to Serve Vue SPA
**File**: `backend/app.py`
**Action**: MODIFY
**Pattern**: Serve static files from `src/frontend/dist/`, add SPA fallback

**Implementation**:
Add after `app = Flask(__name__)` line (around line 24):

```python
import os.path

# Flask app
app = Flask(__name__,
            static_folder='../src/frontend/dist',
            static_url_path='')
app.config['SECRET_KEY'] = os.urandom(24)
```

Add SPA fallback route at the end of the file, before `if __name__ == '__main__'`:

```python
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    """
    Serve Vue SPA for all non-API routes.

    If path is a file (e.g., .js, .css), serve it.
    Otherwise, serve index.html (SPA fallback).
    """
    # API routes are handled by blueprint, don't catch them here
    if path.startswith('api/'):
        abort(404)

    # If path points to a static file, serve it
    static_file = os.path.join(app.static_folder, path)
    if os.path.exists(static_file) and os.path.isfile(static_file):
        return app.send_static_file(path)

    # Otherwise, serve index.html (SPA fallback)
    return app.send_static_file('index.html')
```

**Validation**:
```bash
# Build Vue app first
cd src/frontend
npm run build

# Start Flask
cd ../../backend
python app.py

# Test:
# - http://localhost:5000/ → Serves Vue SPA
# - http://localhost:5000/pod/new → Serves index.html (Vue Router handles routing)
# - http://localhost:5000/api/pods → Returns JSON (API still works)
```

**Success Criteria**:
- Flask serves Vue SPA from `/`
- SPA routes work (refreshing `/pod/new` serves index.html)
- API routes still work at `/api/*`
- Static assets (JS, CSS) load correctly

---

### Task 12: Build Production Vue App
**File**: N/A (command only)
**Action**: RUN
**Pattern**: Vite production build

**Implementation**:
```bash
cd src/frontend
npm run build
```

**Validation**:
- Check `src/frontend/dist/` folder created
- Contains `index.html`, `assets/*.js`, `assets/*.css`
- No build errors

**Success Criteria**:
- Build completes successfully
- dist/ folder contains optimized assets
- File sizes reasonable (JS < 500KB, CSS < 50KB)

---

### Task 13: Remove Jinja Templates
**Files**: All templates in `backend/templates/*.j2`
**Action**: DELETE
**Pattern**: Clean cutover, remove old SSR templates

**Implementation**:
```bash
rm backend/templates/index.html.j2
rm backend/templates/form.html.j2
rm backend/templates/success.html.j2
rm backend/templates/error.html.j2
```

**Validation**:
- Flask app still runs without errors
- All routes serve Vue SPA
- No Jinja template references remain in app.py

**Success Criteria**:
- Templates deleted
- Flask serves only SPA + API
- No broken references in code

---

### Task 14: Remove Jinja-specific Flask routes
**File**: `backend/app.py`
**Action**: MODIFY
**Pattern**: Remove routes that rendered Jinja templates

**Implementation**:
Delete or comment out these routes (they're replaced by SPA):
- `@app.route('/')` function `index()` (lines ~260-280)
- `@app.route('/refresh')` function `refresh()` (lines ~282-288) - KEEP THIS, it's used by API
- `@app.route('/pod/<customer>/<env>')` function `view_pod()` (lines ~290-326)
- `@app.route('/pod/new')` function `new_pod()` (lines ~328-358)
- `@app.route('/deploy', methods=['POST'])` function `deploy()` (lines ~360-564)

**IMPORTANT**: Keep these routes:
- `/health` - Health check endpoint
- Error handlers (`@app.errorhandler`)
- API blueprint registration

Actually, upon reflection: **DO NOT DELETE THESE ROUTES YET**. The API endpoints in `api/routes.py` provide similar functionality, but we need to verify the SPA works first. Instead, we'll test with both systems running in parallel initially.

**Revised approach**: Leave old routes intact for now. The SPA fallback route will only catch requests that don't match existing routes. After successful testing, we can remove old routes in a follow-up commit.

**Implementation**:
Skip this task - leave old routes for safety. They won't interfere with SPA since SPA fallback is lowest priority.

**Validation**:
N/A - skipped for safety

**Success Criteria**:
- Both systems can coexist
- SPA takes precedence for `/` route
- Old routes available as fallback if needed

---

### Task 15: Test End-to-End Workflows
**Action**: MANUAL TESTING
**Pattern**: Validate all 3 workflows from spec

**Test Cases**:

**Workflow 1: View and Edit Existing Pod**
1. Navigate to http://localhost:5000/
2. Click on a pod card (e.g., advworks/dev)
3. Verify form pre-populated with existing data
4. Change instance name
5. Submit form
6. Verify success page appears with PR link
7. Click "View Pod" to return to edit form
8. Verify changes not yet applied (still shows old data - correct, PR not merged yet)

**Workflow 2: Create New Pod**
1. Navigate to http://localhost:5000/
2. Click "+ Create New Pod"
3. Select customer and environment
4. Enter instance name
5. Check WAF checkbox
6. Verify preview updates in real-time
7. Submit form
8. Verify success page appears
9. Click "Back to Home"
10. Verify new pod NOT in list yet (correct - PR not merged)

**Workflow 3: Error Handling**
1. Navigate to http://localhost:5000/pod/new
2. Enter invalid instance name (e.g., "TEST123" with uppercase)
3. Submit form
4. Verify error page appears with validation message
5. Click "Back to Home"
6. Navigate to non-existent pod: /pod/invalid/invalid
7. Verify error page with pod suggestions appears

**Additional Tests**:
- Refresh button clears cache
- Browser back/forward buttons work
- Direct URL access works for all routes
- Mobile responsive layout works (resize browser)

**Validation**:
All test cases pass without errors

**Success Criteria**:
- All workflows function identically to Jinja app
- No console errors
- No broken links
- Visual design matches exactly

---

## Risk Assessment

### Risk: Validation logic mismatch between client and server
**Impact**: Users might bypass client validation, hit server errors
**Mitigation**: Copy exact regex patterns from Flask validators, test with invalid inputs
**Probability**: Low (patterns are simple and well-documented in spec)

### Risk: API response format changes
**Impact**: Vue components fail to parse API responses
**Mitigation**: API already exists from PR #35, format is stable
**Probability**: Very Low (no backend changes)

### Risk: CSS styling differences (CDN Tailwind vs production build)
**Impact**: Layout breaks in production build
**Mitigation**: Use same Tailwind CDN in both dev and prod (no build-time Tailwind)
**Probability**: Very Low (CDN is consistent)

### Risk: SPA routing conflicts with Flask routes
**Impact**: Some URLs don't work in production
**Mitigation**: Flask SPA fallback only catches unmatched routes, API routes preserved
**Probability**: Low (clear route separation)

### Risk: Missing refresh endpoint in API
**Impact**: Dashboard refresh button doesn't work
**Mitigation**: Add `/api/refresh` POST endpoint (Task 10)
**Probability**: Low (straightforward addition)

---

## Integration Points

- **API Integration**: Vue components call existing REST endpoints at `/api/*`
- **Route Mapping**: Vue Router paths match Flask routes exactly (`/`, `/pod/new`, `/pod/:customer/:env`, etc.)
- **Static File Serving**: Flask serves Vue build from `src/frontend/dist/`
- **SPA Fallback**: Flask catches all non-API routes and serves `index.html`
- **No State Management**: Components fetch data independently, no shared store needed

---

## VALIDATION GATES (MANDATORY)

**CRITICAL**: After EVERY task, validate before proceeding.

### Per-Task Validation
After each component creation (Tasks 3-6):
```bash
cd src/frontend
npm run lint
# Must pass with 0 errors
```

### Integration Validation
After Task 11 (Flask SPA serving):
```bash
# Terminal 1: Flask backend
cd backend
python app.py

# Terminal 2: Build Vue app
cd src/frontend
npm run build

# Test in browser:
# - http://localhost:5000/ → Vue SPA loads
# - http://localhost:5000/api/pods → JSON response
# - Console has 0 errors
```

### Final Validation
After Task 15 (E2E testing):
```bash
# Run through all 3 workflows manually
# Document any issues found
# Fix before marking complete
```

**Enforcement Rules**:
- If ANY validation fails → Fix immediately
- Re-run validation after fix
- Do not proceed to next task until current task passes validation
- After 3 failed attempts → Stop and report issue

---

## Validation Sequence

### After Each Component Task (3-6):
```bash
npm run lint
```

### After Router Config (Task 7):
```bash
npm run dev
# Test all routes manually in browser
```

### After Flask Integration (Task 11):
```bash
npm run build
cd ../../backend
python app.py
# Test production build in browser
```

### Final Validation (Task 15):
- Manual testing of all 3 workflows
- No console errors
- Visual comparison with Jinja templates (screenshot side-by-side if needed)

---

## Plan Quality Assessment

**Complexity Score**: 8/10 (MEDIUM-HIGH)
- 11 files to create, 3 files to modify
- 2 subsystems (Frontend, Backend)
- 15 subtasks
- 3 new packages
- Adapting existing patterns (not inventing new)

**Confidence Score**: 9/10 (HIGH)

**Confidence Factors**:
✅ Clear requirements from spec (exact parity migration)
✅ REST API already exists from PR #35 (`backend/api/routes.py`)
✅ All clarifying questions answered (POLS, inline errors, no state management, etc.)
✅ Existing templates provide clear reference patterns
✅ TailwindCSS via CDN (same as Jinja templates)
✅ Vue 3 + Vue Router are mature, stable technologies
✅ No new backend logic required
⚠️ First Vue SPA in this project (no existing patterns to follow)
⚠️ Dual Flask routes (old + new) during transition could cause confusion

**Assessment**: High confidence in implementation success. The spec is crystal clear about parity requirements, existing API endpoints eliminate backend work, and Jinja templates provide exact visual reference. Main risk is over-engineering (adding features not in spec), which is mitigated by strict parity checklist.

**Estimated one-pass success probability**: 85%

**Reasoning**:
- Clear scope (1:1 translation) reduces ambiguity risk
- Existing API eliminates integration uncertainty
- TailwindCSS matching is straightforward (same CDN)
- Main challenge is ensuring absolute visual parity (may need minor CSS tweaks)
- User emphasized POLS, which aligns with simple implementation approach
- No test writing required (parity migration, manual testing sufficient)

---

## Notes for Implementation

1. **POLS Principle**: If you're tempted to add a feature, don't. Stick to exact parity.

2. **Inline vs ErrorPage**: Use inline errors for validation (user sees immediately), ErrorPage for server errors (navigation required).

3. **No State Management**: Each component fetches its own data. Don't add Pinia/Vuex.

4. **TailwindCSS**: Use CDN exactly as Jinja templates do. Don't install Tailwind as npm package.

5. **Commit Strategy**: Commit after every 2-3 tasks:
   - Commit 1: Scaffold + Vite config (Tasks 1-2)
   - Commit 2: Dashboard + PodForm (Tasks 3-4)
   - Commit 3: Success + Error + Router (Tasks 5-7)
   - Commit 4: App.vue + index.html + API refresh (Tasks 8-10)
   - Commit 5: Flask integration + build (Tasks 11-12)
   - Commit 6: Remove templates + final testing (Tasks 13-15)

6. **Testing Strategy**: Manual testing only. No unit tests for parity migration (can add later if needed).

7. **Rollback Plan**: If SPA fails in production, revert to commit before Task 13 (templates still exist).

8. **Future Enhancements** (NOT in this PR):
   - SubnetPicker, AMIPicker, SnapshotPicker
   - Nested YAML editor
   - Additional form fields
   - Animations or fancy UI
