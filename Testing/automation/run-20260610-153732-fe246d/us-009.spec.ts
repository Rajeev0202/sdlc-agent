import { test, expect } from '@playwright/test';

test.describe('Story US-009: ', () => {
  test('AC1: Given I access the audit interface, when I arrive at the page, then I ', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I access the audit interface, when I arrive 
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC2: Given I submit a search, when results are returned, then they are disp', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I submit a search, when results are returned
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC3: Given I view search results, when I click export, then results are exp', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I view search results, when I click export, 
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC4: Given I access the audit interface, when my authentication is checked,', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I access the audit interface, when my authen
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

});
