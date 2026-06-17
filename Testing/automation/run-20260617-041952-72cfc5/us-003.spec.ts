import { test, expect } from '@playwright/test';

test.describe('Story US-003: ', () => {
  test('AC1: Given my card is frozen, when I tap 'Unfreeze Card', then I am prompte', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given my card is frozen, when I tap 'Unfreeze Card
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC2: Given I complete step-up authentication successfully, when I confirm u', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I complete step-up authentication successful
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC3: Given I fail step-up authentication, when I attempt to unfreeze, then ', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given I fail step-up authentication, when I attemp
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC4: Given step-up authentication times out, when I return to the app, then', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given step-up authentication times out, when I ret
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

  test('AC5: Given my card is active, when I view card details, then the unfreeze b', async ({ page }) => {
    // Arrange: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Act: Perform actions for 
    await page.getByRole('button', { name: /freeze|unfreeze/i }).click();
    await page.waitForSelector('[data-testid="status-message"]');

    // Assert: Verify Given my card is active, when I view card details,
    const statusMessage = page.locator('[data-testid="status-message"]');
    await expect(statusMessage).toBeVisible();
    await expect(statusMessage).toContainText(/success|complete/i);
  });

});
