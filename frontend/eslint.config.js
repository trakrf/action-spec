import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'

export default [
  // Ignore build artifacts and dependencies
  {
    ignores: ['dist/**', 'node_modules/**', 'test-results/**', 'playwright-report/**']
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        // Browser globals
        console: 'readonly',
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        fetch: 'readonly',
        getComputedStyle: 'readonly',
        // Node.js globals (for config files)
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
      }
    },
    rules: {
      // Allow console for development
      'no-console': 'off',
      // Vue-specific rules
      'vue/multi-word-component-names': 'off'
    }
  }
]
