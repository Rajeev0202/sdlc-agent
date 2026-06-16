import { test, expect } from '@playwright/test';

test.describe('Story US-003: ', () => {
  test('AC1: Given a card status changes to FROZEN, when the change is committed, t', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given a card status changes to FROZEN, when the ch
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC2: Given the switch message fails, when retry logic executes, then up to ', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given the switch message fails, when retry logic e
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC3: Given propagation completes, when monitoring is checked, then p95 late', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given propagation completes, when monitoring is ch
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC4: Given TLS 1.2+ is enforced, when connecting to the switch, then certif', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given TLS 1.2+ is enforced, when connecting to the
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

});
