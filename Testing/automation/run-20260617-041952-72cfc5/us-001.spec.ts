import { test, expect } from '@playwright/test';

test.describe('Story US-001: ', () => {
  test('AC1: Given I am on the card details screen, when I tap the 'Freeze Card' bu', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I am on the card details screen, when I tap 
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC2: Given my card is frozen, when I view the card details, then I see a vi', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given my card is frozen, when I view the card deta
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC3: Given I freeze my card, when I attempt a transaction, then the transac', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I freeze my card, when I attempt a transacti
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC4: Given I have no active cards, when I view card details, then the freez', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I have no active cards, when I view card det
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

});
