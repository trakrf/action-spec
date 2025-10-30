<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

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
  } catch {
    // Silently fail - this is best effort
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
          <div class="text-6xl mb-4">
            {{ errorIcon }}
          </div>
          <h2 class="text-3xl font-bold text-gray-900 mb-2">
            {{ errorTitle }}
          </h2>
          <p class="text-lg text-gray-600">
            {{ errorMessage }}
          </p>
        </div>

        <!-- Valid Pods List (if available) -->
        <div
          v-if="showPods && pods.length > 0"
          class="border-t pt-6"
        >
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
