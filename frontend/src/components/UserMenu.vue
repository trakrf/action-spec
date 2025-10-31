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
  <div
    v-if="user"
    class="relative"
  >
    <!-- Avatar button -->
    <button
      class="flex items-center gap-2 hover:opacity-80 transition-opacity"
      @click="isOpen = !isOpen"
    >
      <img
        :src="user.avatar_url"
        :alt="user.name || user.login"
        class="w-8 h-8 rounded-full"
      >
      <span class="text-sm font-medium">{{ user.name || user.login }}</span>
      <svg
        class="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M19 9l-7 7-7-7"
        />
      </svg>
    </button>

    <!-- Dropdown menu -->
    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 z-50"
    >
      <div class="px-4 py-2 text-sm text-gray-700 border-b">
        <div class="font-medium">
          {{ user.name }}
        </div>
        <div class="text-gray-500">
          @{{ user.login }}
        </div>
      </div>

      <button
        class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
        :disabled="isLoggingOut"
        @click="handleLogout"
      >
        <span v-if="!isLoggingOut">Logout</span>
        <span v-else>Logging out...</span>
      </button>
    </div>
  </div>
</template>
