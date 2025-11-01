<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { version } from '../../package.json'

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
    <nav
      v-if="mode === 'edit'"
      class="mb-6 text-sm"
    >
      <router-link
        to="/"
        class="text-blue-600 hover:underline"
      >
        Home
      </router-link>
      <span class="text-gray-400 mx-2">/</span>
      <span class="text-gray-700 font-medium">{{ route.params.customer }}</span>
      <span class="text-gray-400 mx-2">/</span>
      <span class="text-gray-700 font-medium">{{ route.params.env }}</span>
    </nav>

    <!-- Header -->
    <header class="mb-8">
      <!-- Edit Mode: Customer/env badges -->
      <div
        v-if="mode === 'edit'"
        class="flex items-center justify-between mb-4"
      >
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
      <h1
        v-else
        class="text-3xl font-bold text-gray-900 mb-4"
      >
        Create New Pod
      </h1>
    </header>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="text-center py-12"
    >
      <p class="text-gray-600">
        Loading pod spec...
      </p>
    </div>

    <!-- Form -->
    <main v-else>
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-xl font-semibold text-gray-800 mb-4">
          Pod Configuration
        </h2>

        <form
          class="space-y-6"
          @submit.prevent="handleSubmit"
        >
          <!-- Customer and Environment (create mode only) -->
          <div
            v-if="mode === 'new'"
            class="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            <div>
              <label
                for="customer"
                class="block text-sm font-medium text-gray-700 mb-2"
              >
                Customer *
              </label>
              <select
                id="customer"
                v-model="customer"
                required
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">
                  -- Select Customer --
                </option>
                <option value="advworks">
                  advworks
                </option>
                <option value="northwind">
                  northwind
                </option>
                <option value="contoso">
                  contoso
                </option>
              </select>
            </div>

            <div>
              <label
                for="environment"
                class="block text-sm font-medium text-gray-700 mb-2"
              >
                Environment *
              </label>
              <select
                id="environment"
                v-model="env"
                required
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">
                  -- Select Environment --
                </option>
                <option value="dev">
                  dev (Development)
                </option>
                <option value="stg">
                  stg (Staging)
                </option>
                <option value="prd">
                  prd (Production)
                </option>
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
            <h3 class="text-lg font-semibold text-gray-800 mb-4">
              Compute
            </h3>

            <div>
              <label
                for="instance_name"
                class="block text-sm font-medium text-gray-700 mb-2"
              >
                Instance Name *
              </label>
              <input
                id="instance_name"
                v-model="instanceName"
                type="text"
                required
                pattern="[a-z0-9\-]+"
                placeholder="e.g., web1, app1"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
              <small class="text-gray-600 text-xs">Lowercase letters, numbers, hyphens only</small>
              <small class="text-gray-500 text-xs block mt-1">
                Note: Instance type is managed in spec.yml, not via this form
              </small>
            </div>
          </div>

          <!-- Security Section -->
          <div class="border-t pt-6">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">
              Security
            </h3>

            <div class="flex items-center">
              <input
                id="waf_enabled"
                v-model="wafEnabled"
                type="checkbox"
                class="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              >
              <label
                for="waf_enabled"
                class="ml-3 text-sm font-medium text-gray-700"
              >
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
              <span
                v-if="submitting"
                class="flex items-center"
              >
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
                  />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
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
        ActionSpec v{{ version }} - Infrastructure Deployment via Spec Editor
      </p>
    </footer>
  </div>
</template>
