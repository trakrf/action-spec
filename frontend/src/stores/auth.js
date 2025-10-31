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
    return false
  } finally {
    isValidating.value = false
  }
}

export async function logout() {
  try {
    await fetch('/auth/logout', { method: 'POST' })
    user.value = null
  } catch {
    // Clear local state anyway
    user.value = null
  }
}
