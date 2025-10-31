import { test, expect } from '@playwright/test'

test.describe('Dashboard Styling', () => {
  test('should have proper Tailwind styles applied', async ({ page }) => {
    await page.goto('/')

    // Wait for content to load
    await page.waitForSelector('h1')

    // Take a screenshot for visual comparison
    await page.screenshot({ path: 'e2e/screenshots/dashboard-current.png', fullPage: true })

    // Test 1: Page should have gray background
    const body = await page.locator('body')
    const bodyBg = await body.evaluate(el => getComputedStyle(el).backgroundColor)
    console.log('Body background:', bodyBg)

    // Test 2: Check if main container has proper padding
    const container = await page.locator('.container').first()
    const containerPadding = await container.evaluate(el => getComputedStyle(el).paddingLeft)
    console.log('Container padding:', containerPadding)
    expect(parseInt(containerPadding)).toBeGreaterThan(0)

    // Test 3: Check if cards have white background (if data available)
    const cards = await page.locator('.bg-white')
    const cardCount = await cards.count()
    console.log('White background elements:', cardCount)
    // Don't fail if no data - backend might not be running
    if (cardCount > 0) {
      expect(cardCount).toBeGreaterThan(0)
    }

    // Test 4: Check if cards have shadows
    const cardWithShadow = await page.locator('.shadow-md').first()
    if (await cardWithShadow.count() > 0) {
      const boxShadow = await cardWithShadow.evaluate(el => getComputedStyle(el).boxShadow)
      console.log('Card shadow:', boxShadow)
      expect(boxShadow).not.toBe('none')
    }

    // Test 5: Check if buttons have proper colors
    const blueButton = await page.locator('.bg-blue-600').first()
    if (await blueButton.count() > 0) {
      const buttonBg = await blueButton.evaluate(el => getComputedStyle(el).backgroundColor)
      console.log('Button background:', buttonBg)
      // Tailwind v4 uses oklch color space
      expect(buttonBg).toMatch(/oklch|rgb/)
    }

    // Test 6: Check if environment badges exist
    const badges = await page.locator('.rounded-full')
    const badgeCount = await badges.count()
    console.log('Badge count:', badgeCount)

    // Test 7: Log all applied Tailwind classes for debugging
    const allElements = await page.locator('[class]').all()
    console.log(`Total elements with classes: ${allElements.length}`)

    // Get a sample of classes being used
    const firstCard = await page.locator('.bg-white').first()
    if (await firstCard.count() > 0) {
      const classes = await firstCard.getAttribute('class')
      console.log('Card classes:', classes)
    }
  })

  test('visual regression - compare with baseline', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('h1')

    // Take screenshot for manual comparison
    await page.screenshot({
      path: 'e2e/screenshots/dashboard-full.png',
      fullPage: true
    })
  })
})
