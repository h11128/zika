import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

test.describe('Stress Rapid State Switches @stress', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
  });

  test('should remain consistent after 10 rapid cycles', async () => {
    await app.goto();
    await app.setupCards();

    const disableButton = app.page.getByText('关闭自动填充以手动调整大小');
    const sizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });

    for (let i = 0; i < 10; i++) {
      // ensure options visible
      await app.expandAdvancedOptions();
      const labelText = app.page.getByText('自动填充（按边距与间距自动计算卡片大小）', { exact: true });
      const checkbox = app.page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');

      // toggle auto-fill using robust fallbacks
      const hasDisable = await disableButton.isVisible().catch(() => false);
      if (hasDisable) {
        await disableButton.click();
      } else {
        if (await labelText.isVisible().catch(() => false)) {
          await labelText.scrollIntoViewIfNeeded().catch(() => {});
          // Page can overlay; prefer clicking the label container via getByText
          await labelText.click({ timeout: 5000 });
        } else {
          // As a robust fallback: toggle by pressing Space while focused on the body
          await app.page.keyboard.press('Tab');
          await app.page.keyboard.press('Space');
        }
      }

      // switch preview mode back and forth
      await app.switchPreviewMode('🔲 简单网格');
      await app.switchPreviewMode('📄 完整页面');

      // wait briefly for rerun stabilization and requery elements next loop
      await app.page.waitForTimeout(150);
    }

    // Final consistency check
    const hasDisable = await disableButton.isVisible().catch(() => false);
    const sliderVisible = await sizeSlider.isVisible().catch(() => false);
    const consistent = (hasDisable && !sliderVisible) || (!hasDisable && sliderVisible);
    expect(consistent).toBe(true);

    expect(await app.verifyPreviewUpdated()).toBe(true);
  });
});

