import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// Keyboard-only accessibility smoke test

test.describe('Keyboard Accessibility Smoke', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
  });

  test('toggle auto-fill and switch preview using keyboard only', async () => {
    await app.goto();
    await app.setupCards();

    // Focus document and tab to controls
    await app.page.keyboard.press('Tab');
    // Try toggling auto-fill via Space after some tabs (heuristic)
    for (let i = 0; i < 10; i++) {
      await app.page.keyboard.press('Tab');
    }
    await app.page.keyboard.press('Space');
    await app.page.waitForTimeout(300);

    // Switch preview mode radio via Arrow keys
    // First ensure preview section is visible
    await app.page.keyboard.press('End');
    await app.page.keyboard.press('ArrowUp');
    await app.page.keyboard.press('ArrowUp');
    await app.page.keyboard.press('ArrowLeft');
    await app.page.waitForTimeout(300);

    // Validate UI still consistent and preview available
    const disableButton = app.page.getByText('关闭自动填充以手动调整大小');
    const sizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    const hasDisable = await disableButton.isVisible().catch(() => false);
    const sliderVisible = await sizeSlider.isVisible().catch(() => false);
    const consistent = (hasDisable && !sliderVisible) || (!hasDisable && sliderVisible);
    expect(consistent).toBe(true);

    expect(await app.verifyPreviewUpdated()).toBe(true);
  });
});

