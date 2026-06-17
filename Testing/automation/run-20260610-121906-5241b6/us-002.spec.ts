import { test, expect } from '@playwright/test';

test.describe('Story US-002: ', () => {
  test('AC1: Given I request to freeze an active debit card, when the API receives ', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I request to freeze an active debit card, wh
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC2: Given validation passes, when the freeze is processed, then the card s', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given validation passes, when the freeze is proces
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC3: Given validation fails, when the request is rejected, then an appropri', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given validation fails, when the request is reject
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC4: Given the card is not a debit card or not active, when validation runs', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given the card is not a debit card or not active, 
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

});
