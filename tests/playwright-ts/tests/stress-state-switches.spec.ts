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

    // Expand advanced options once at the beginning
    await app.expandAdvancedOptions();
    await app.page.waitForTimeout(100); // Minimal wait for initial expansion

    for (let i = 0; i < 10; i++) {
      // Check current state and toggle auto-fill appropriately
      const disableButton = app.page.getByText('关闭自动填充以手动调整大小');
      const enableText = app.page.getByText('自动填充（按边距与间距自动计算卡片大小）', { exact: true });
      const enableCheckbox = app.page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');

      // Quick parallel visibility checks
      const [hasDisableButton, hasEnableText, hasEnableCheckbox] = await Promise.all([
        disableButton.isVisible().catch(() => false),
        enableText.isVisible().catch(() => false),
        enableCheckbox.isVisible().catch(() => false)
      ]);

      // Toggle auto-fill state with event-driven waiting
      if (hasDisableButton) {
        await disableButton.click();

        // ✅ EVENT-DRIVEN: Wait for UI to change to manual mode (slider appears)
        try {
          const sizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
          await sizeSlider.waitFor({ state: 'visible', timeout: 1500 });
        } catch {
          // Fallback: wait for enable text to appear
          await app.page.getByText('自动填充（按边距与间距自动计算卡片大小）').waitFor({ state: 'visible', timeout: 1000 }).catch(() => {});
        }

      } else if (hasEnableText) {
        await enableText.click({ timeout: 1000 });

        // ✅ EVENT-DRIVEN: Wait for UI to change to auto mode (disable button appears)
        await app.page.getByText('关闭自动填充以手动调整大小').waitFor({ state: 'visible', timeout: 1500 }).catch(() => {});

      } else if (hasEnableCheckbox) {
        await enableCheckbox.click({ timeout: 1000 });

        // ✅ EVENT-DRIVEN: Wait for disable button to appear
        await app.page.getByText('关闭自动填充以手动调整大小').waitFor({ state: 'visible', timeout: 1500 }).catch(() => {});

      } else {
        // Quick fallback - try first available auto-fill element
        const fallbackElement = app.page.getByText('自动填充').first();
        await fallbackElement.click({ timeout: 1000 }).catch(() => {});
        await app.page.waitForTimeout(100); // Minimal fallback wait
      }

      // Fast preview mode switches
      await app.switchPreviewModeFast('🔲 简单网格');
      await app.switchPreviewModeFast('📄 完整页面');

      // Minimal stabilization wait
      await app.page.waitForTimeout(50);
    }

    // Final consistency check - verify UI is in a consistent state
    await app.expandAdvancedOptions();
    await app.page.waitForTimeout(300);

    const finalDisableButton = app.page.getByText('关闭自动填充以手动调整大小');
    const finalSizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });

    const hasDisable = await finalDisableButton.isVisible().catch(() => false);
    const sliderVisible = await finalSizeSlider.isVisible().catch(() => false);
    const consistent = (hasDisable && !sliderVisible) || (!hasDisable && sliderVisible);
    expect(consistent).toBe(true);

    expect(await app.verifyPreviewUpdated()).toBe(true);
  });
});

