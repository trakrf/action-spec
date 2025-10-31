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
