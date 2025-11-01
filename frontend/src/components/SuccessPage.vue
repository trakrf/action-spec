<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { version } from '../../package.json'

const route = useRoute()

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
          <div class="text-6xl mb-4">
            ✅
          </div>
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
              <dt class="font-medium text-gray-700 w-40">
                Customer:
              </dt>
              <dd class="font-mono text-gray-900">
                {{ customer }}
              </dd>
            </div>
            <div class="flex">
              <dt class="font-medium text-gray-700 w-40">
                Environment:
              </dt>
              <dd class="font-mono text-gray-900">
                {{ env }}
              </dd>
            </div>
            <div class="flex">
              <dt class="font-medium text-gray-700 w-40">
                Instance Name:
              </dt>
              <dd class="font-mono text-gray-900">
                {{ instanceName }}
              </dd>
            </div>
            <div class="flex">
              <dt class="font-medium text-gray-700 w-40">
                WAF Enabled:
              </dt>
              <dd class="font-mono text-gray-900">
                {{ wafEnabled }}
              </dd>
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
        ActionSpec v{{ version }} - Infrastructure Deployment via Spec Editor
      </p>
    </footer>
  </div>
</template>
