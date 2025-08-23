import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// Priority 1: Complex custom color transitions under state changes

test.describe('Complex Custom Color Transitions @priority1', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
  });

  test('should handle preset→custom→preset with state switches', async () => {
    await app.goto();
    await app.setupCards();

    // Ensure color control is present
    await app.expandAdvancedOptions();
    const colorLabel = app.page.getByText('选择颜色', { exact: true });
    await expect(colorLabel).toBeVisible({ timeout: 10000 });
    const anchor = app.page.locator('[data-testid="color-picker-anchor"]');
    await expect(anchor).toHaveCount(1, { timeout: 10000 });

    // 1) Select a preset color from palette (if available)
    const preset1 = await app.selectPresetColorFromPalette(2);
    const display1 = await app.getCurrentColorFromDisplay();
    if (preset1 && display1) {
      console.log(`✅ Preset selected: ${preset1}, display shows: ${display1}`);
    } else {
      console.log('ℹ️ Preset palette not found or display not parsed; continue');
    }

    // 2) Switch preview modes and toggle auto-fill during color transitions
    await app.switchPreviewMode('🔲 简单网格');
    await app.switchPreviewMode('📄 完整页面');

    const disableBtn = app.page.getByText('关闭自动填充以手动调整大小');
    const hasDisable = await disableBtn.isVisible().catch(() => false);
    if (hasDisable) {
      await disableBtn.click();
      await app.page.waitForTimeout(500);
    }

    // 3) Try custom color (native input if present)
    await app.selectCustomColorOrVerifyDisplay('#ff5722');

    // Verify preview keeps showing cards
    expect(await app.verifyPreviewUpdated()).toBe(true);

    // 4) Re-enable auto-fill via checkbox
    await app.expandAdvancedOptions();
    // Re-query to avoid stale handles after reruns
    let autoFillCheckbox = app.page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');
    let labelText = app.page.getByText('自动填充（按边距与间距自动计算卡片大小）', { exact: true });
    let isChecked = await autoFillCheckbox.isChecked().catch(() => false);
    if (!isChecked) {
      // Ensure expander is open and elements are scrolled into view
      await app.expandAdvancedOptions();
      labelText = app.page.getByText('自动填充（按边距与间距自动计算卡片大小）', { exact: true });
      autoFillCheckbox = app.page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');

      if (await labelText.isVisible().catch(() => false)) {
        await labelText.scrollIntoViewIfNeeded().catch(() => {});
        await labelText.click({ timeout: 5000 });
      } else {
        await autoFillCheckbox.scrollIntoViewIfNeeded().catch(() => {});
        await autoFillCheckbox.click({ timeout: 5000, force: true });
      }
      await app.page.waitForTimeout(1000);
    }

    // 5) Select another preset and ensure UI is still stable
    const preset2 = await app.selectPresetColorFromPalette(5);
    const display2 = await app.getCurrentColorFromDisplay();
    if (preset2 && display2) {
      console.log(`✅ Second preset selected: ${preset2}, display shows: ${display2}`);
    }

    // Final: UI consistency on auto-fill vs slider
    const slider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    const finalHasDisable = await disableBtn.isVisible().catch(() => false);
    const finalSliderVisible = await slider.isVisible().catch(() => false);
    const consistent = (finalHasDisable && !finalSliderVisible) || (!finalHasDisable && finalSliderVisible);
    expect(consistent).toBe(true);

    expect(await app.verifyPreviewUpdated()).toBe(true);
  });
});

