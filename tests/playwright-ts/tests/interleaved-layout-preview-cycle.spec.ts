import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// Priority 1: Interleave layout changes and preview switches within auto-fill cycle

test.describe('Interleaved Layout/Preview within Auto-fill Cycle @priority1', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
  });

  test('should remain consistent when interleaving layout changes and preview mode switches', async () => {
    await app.goto();
    await app.setupCards();

    // Expand advanced options
    await app.expandAdvancedOptions();

    // Initial expectations: auto-fill enabled
    const disableButton = app.page.getByText('关闭自动填充以手动调整大小');
    await expect(disableButton).toBeVisible();
    const sizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    await expect(sizeSlider).toBeHidden();

    // Disable auto-fill and verify
    await disableButton.click();
    await app.page.waitForTimeout(800);
    await expect(disableButton).toBeHidden();
    await expect(sizeSlider).toBeVisible();

    // Interleave: change layout params and preview mode while in manual mode
    await app.setRowsCols(2, 3);
    await app.setGapMargin(1, 1);

    await app.switchPreviewMode('🔲 简单网格');
    expect(await app.verifyPreviewUpdated()).toBe(true);

    await app.switchPreviewMode('📄 完整页面');
    expect(await app.verifyPreviewUpdated()).toBe(true);

    // Adjust card size extremes (manual mode)
    await sizeSlider.click();
    // drive towards min
    for (let i = 0; i < 10; i++) await app.page.keyboard.press('ArrowLeft');
    // drive towards max
    for (let i = 0; i < 20; i++) await app.page.keyboard.press('ArrowRight');
    // small back to center-ish
    for (let i = 0; i < 5; i++) await app.page.keyboard.press('ArrowLeft');
    expect(await app.verifyPreviewUpdated()).toBe(true);

    // Re-enable auto-fill via checkbox (expander may collapse after reruns)
    await app.expandAdvancedOptions();
    // Re-query elements after potential rerender
    const autoFillCheckbox = app.page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');
    const labelText = app.page.getByText('自动填充（按边距与间距自动计算卡片大小）', { exact: true });

    const isChecked = await autoFillCheckbox.isChecked().catch(() => false);
    if (!isChecked) {
      await app.expandAdvancedOptions(); // ensure visible
      if (await labelText.isVisible().catch(() => false)) {
        await labelText.scrollIntoViewIfNeeded().catch(() => {});
        await labelText.click();
      } else {
        await autoFillCheckbox.scrollIntoViewIfNeeded().catch(() => {});
        await autoFillCheckbox.click({ timeout: 5000 });
      }
      await app.page.waitForTimeout(1000);
    }

    // Final assertions: auto-fill enabled => button visible, size slider hidden
    await expect(disableButton).toBeVisible();
    await expect(sizeSlider).toBeHidden();

    // Preview still available
    expect(await app.verifyPreviewUpdated()).toBe(true);
  });
});

