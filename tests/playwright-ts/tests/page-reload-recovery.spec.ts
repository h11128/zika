import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// Priority 1: Page reload state recovery for layout and auto-fill

test.describe('Page Reload State Recovery @priority1', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
  });

  test('should maintain consistent UI after reload', async () => {
    await app.goto();
    await app.setupCards();

    await app.expandAdvancedOptions();

    // Disable auto-fill
    const disableBtn = app.page.getByText('关闭自动填充以手动调整大小');
    await disableBtn.click();
    await app.page.waitForTimeout(500);

    // Set rows/cols to a non-default value
    await app.setRowsCols(3, 4);

    // Verify current state: manual mode
    await expect(disableBtn).toBeHidden();
    const sizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    await expect(sizeSlider).toBeVisible();

    // Reload the page
    await app.reloadAndWait();
    await app.setupCards(); // regenerate cards if needed

    // After reload, ensure UI remains consistent (either auto-fill kept disabled or defaults applied)
    // We don't assert persistence; we assert consistency of final UI
    const hasDisable = await disableBtn.isVisible().catch(() => false);
    const sliderVisible = await sizeSlider.isVisible().catch(() => false);
    const consistent = (hasDisable && !sliderVisible) || (!hasDisable && sliderVisible);
    expect(consistent).toBe(true);

    // Preview should still be available
    expect(await app.verifyPreviewUpdated()).toBe(true);

    // Current color display should show a hex
    const displayHex = await app.getCurrentColorFromDisplay();
    expect(displayHex).not.toBeNull();
  });
});

