<script setup>
import { onMounted } from 'vue'
import { validateAuth, isValidating, isAuthenticated, error } from '@/stores/auth'
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
      <h1 class="text-xl font-bold text-gray-900">
        Action Spec
      </h1>

      <!-- Loading indicator during validation -->
      <div
        v-if="isValidating"
        class="flex items-center gap-2 text-sm text-gray-500"
      >
        <svg
          class="animate-spin h-4 w-4"
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
        <span>Checking authentication...</span>
      </div>

      <!-- Show login button or user menu -->
      <LoginButton v-else-if="!isAuthenticated" />
      <UserMenu v-else-if="isAuthenticated" />
    </header>

    <!-- Error display (if validation fails non-401) -->
    <div
      v-if="error"
      class="bg-red-50 border-l-4 border-red-400 p-4 m-4"
    >
      <p class="text-red-700">
        {{ error }}
      </p>
    </div>

    <!-- Main content (loads immediately) -->
    <main>
      <RouterView />
    </main>
  </div>
</template>

