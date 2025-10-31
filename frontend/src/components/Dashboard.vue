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
            class="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition font-medium shadow-md hover:shadow-lg"
            @click="refreshCache"
          >
            🔄 Refresh
          </button>
          <button
            class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-md hover:shadow-lg"
            @click="router.push('/pod/new')"
          >
            + Create New Pod
          </button>
        </div>
      </div>
    </header>

    <!-- Pod List -->
    <main>
      <div
        v-if="loading"
        class="text-center py-12"
      >
        <p class="text-gray-600">
          Loading pods...
        </p>
      </div>

      <div
        v-else-if="error"
        class="bg-red-50 border-l-4 border-red-400 p-4"
      >
        <p class="text-red-700">
          {{ error }}
        </p>
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
        <div
          v-if="pods.length === 0"
          class="bg-yellow-50 border-l-4 border-yellow-400 p-4"
        >
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
