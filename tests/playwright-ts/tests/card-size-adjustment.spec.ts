import { test, expect, Page, Locator } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

interface CardSize {
  width: number;
  height: number;
}

interface SliderInfo {
  value: string;
  min: string;
  max: string;
}

test.describe('Card Size Adjustment', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
  });

  // Clean up after each test
  test.afterEach(async ({ page, context }) => {
    console.log('🧹 Cleaning up test page and context...');
    try {
      await page.close();
      await context.close();
    } catch (error) {
      console.log('⚠️ Cleanup error (non-critical):', error);
    }
    console.log('✅ Test page and context closed');
  });

  // Helper function to get card size from preview
  async function getCardSizeFromPreview(page: Page): Promise<CardSize> {
    // Prefer a direct frameLocator if it resolves quickly
    const fastCard = page.frameLocator('iframe').locator('.page-grid .page-card').first();
    try {
      await expect(fastCard).toBeVisible({ timeout: 2000 });
      const fastBox = await fastCard.boundingBox();
      if (fastBox) return { width: fastBox.width, height: fastBox.height };
    } catch {}

    // Fallback: actively search all frames a few times
    for (let attempt = 0; attempt < 5; attempt++) {
      for (const frame of page.frames()) {
        try {
          const card = frame.locator('.page-grid .page-card').first();
          if (await card.isVisible({ timeout: 500 })) {
            const box = await card.boundingBox();
            if (box) return { width: box.width, height: box.height };
          }
        } catch {}
      }
      await page.waitForTimeout(300);
    }

    throw new Error('Preview card not found in any iframe');
  }

  // Helper for simple grid: measure a card inside the iframe
  async function getSimpleGridCardSize(page: Page): Promise<CardSize> {
    // Helper to read size from a locator if visible
    const sizeOf = async (loc: Locator) => {
      if (await loc.isVisible({ timeout: 500 }).catch(() => false)) {
        const b = await loc.boundingBox();
        if (b) return { width: b.width, height: b.height } as CardSize;
      }
      return null;
    };

    // 1) Try main page common selectors
    const mainSelectors = [
      '.simple-grid .simple-card',
      '[class*="simple"] [class*="card"]',
      '.simple-grid [class*="card"]',
    ];
    for (const sel of mainSelectors) {
      const res = await sizeOf(page.locator(sel).first());
      if (res) return res;
    }

    // 2) Try direct frameLocator common selectors
    const frameLoc = page.frameLocator('iframe').first();
    for (const sel of mainSelectors) {
      const res = await sizeOf(frameLoc.locator(sel).first());
      if (res) return res;
    }

    // 3) Fallback: scan all frames with broader heuristics
    const fallbackSelectors = [
      '.simple-grid .simple-card',
      '[class*="simple-grid"] [class*="card"]',
      '[class*="simple"] [class*="card"]',
      'div:has-text("一"), div:has-text("二"), div:has-text("三")',
    ];
    for (let attempt = 0; attempt < 6; attempt++) {
      for (const frame of page.frames()) {
        for (const sel of fallbackSelectors) {
          const res = await sizeOf(frame.locator(sel).first());
          if (res) return res;
        }
      }
      await page.waitForTimeout(250);
    }

    throw new Error('Simple grid card not found in any iframe');
  }


  // Ensure Simple Grid mode is active and visible
  async function ensureSimpleGridMode(page: Page, app: ZikaAppPage): Promise<void> {
    // Quick probe using any frame
    const quickVisible = async () => {
      for (const frame of page.frames()) {
        const card = frame.locator('.simple-grid .simple-card').first();
        if (await card.isVisible({ timeout: 300 }).catch(() => false)) return true;
      }
      return false;
    };

    if (await quickVisible()) return;

    // Re-select the mode and then poll all frames for visibility
    await app.switchPreviewModeFast('🔲 简单网格');

    const deadline = Date.now() + 6000;
    while (Date.now() < deadline) {
      if (await quickVisible()) return;
      await page.waitForTimeout(150);
    }
    throw new Error('Simple grid mode not visible after switching');
  }


  async function disableAutoFill(page: Page) {
    console.log('🔧 Disabling auto fill...');

    // Try button first (more reliable)
    try {
      const disableButton = page.getByText('关闭自动填充以手动调整大小');
      await disableButton.click({ timeout: 5000 });
      console.log('✅ Clicked disable auto fill button');
      await page.waitForTimeout(1000);
      return;
    } catch (error) {
      console.log('⚠️ Button method failed, trying advanced options');
    }

    // Fallback: Try checkbox in advanced options
    try {
      const advancedToggle = page.getByText('🔧 高级选项', { exact: true });
      await advancedToggle.click({ timeout: 5000 });
      await page.waitForTimeout(500);

      const autoFillCheckbox = page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');
      if (await autoFillCheckbox.isChecked({ timeout: 2000 })) {
        await autoFillCheckbox.uncheck();
        console.log('✅ Unchecked auto fill checkbox');
        await page.waitForTimeout(1000);
      }
    } catch (error) {
      console.log('⚠️ Could not disable auto fill:', error);
    }
  }

  // Clean up after each test
  test.afterEach(async ({ page, context }) => {
    console.log('🧹 Cleaning up test page and context...');
    try {
      await page.close();
      await context.close();
    } catch (error) {
      console.log('⚠️ Cleanup error (non-critical):', error);
    }
    console.log('✅ Test page and context closed');
  });

  test('should update preview when card size is manually adjusted in full page mode', async () => {
    // Setup
    await app.goto();
    await app.setupCards();

    // Use full page mode (default)
    console.log('📄 Using full page mode...');

    // Disable auto-fill to enable manual size adjustment
    await disableAutoFill(app.page);

    // Get initial card size from preview
    const initialSize = await getCardSizeFromPreview(app.page);
    console.log(`📏 Initial card size: ${initialSize.width}x${initialSize.height}`);

    // Find and adjust the card size slider
    const slider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    await slider.waitFor({ state: 'visible', timeout: 5000 });

    // Get initial slider value
    const initialValue = await slider.getAttribute('aria-valuenow') || '5';
    console.log(`🎚️ Initial slider value: ${initialValue}`);

    // Adjust slider using keyboard navigation (works for Streamlit div sliders)
    await slider.focus();
    await app.page.keyboard.press('ArrowRight'); // Increase value
    await app.page.keyboard.press('ArrowRight'); // Increase value again
    await app.page.keyboard.press('ArrowRight'); // Increase value more for visible change

    // Wait for Streamlit to process the change
    await app.page.waitForTimeout(2000);

    // Verify slider value changed
    const newValue = await slider.getAttribute('aria-valuenow') || '5';
    console.log(`🎚️ New slider value: ${newValue}`);

    // Ensure the value actually changed significantly
    const valueChange = Math.abs(parseFloat(newValue) - parseFloat(initialValue));
    if (valueChange < 0.3) {
      // Fallback: try mouse drag for more significant change
      const box = await slider.boundingBox();
      if (box) {
        const startX = box.x + box.width * 0.3;
        const endX = box.x + box.width * 0.8;
        const y = box.y + box.height / 2;

        await app.page.mouse.move(startX, y);
        await app.page.mouse.down();
        await app.page.mouse.move(endX, y, { steps: 15 });
        await app.page.mouse.up();


        await app.page.waitForTimeout(2000);
        console.log('🖱️ Used mouse drag for larger change');

        const finalValue = await slider.getAttribute('aria-valuenow') || '5';
        console.log(`🎚️ Final slider value after drag: ${finalValue}`);
      }
    }

    // Wait until the card size inside iframe actually changes (event-driven)
    await expect.poll(async () => {
      const now = await getCardSizeFromPreview(app.page);
      return Math.round(now.width);
    }, { timeout: 10000, intervals: [300, 500, 1000] }).not.toBe(Math.round(initialSize.width));

    const newSize = await getCardSizeFromPreview(app.page);

    // Verify that the card size actually changed (use smaller threshold for more sensitivity)
    const widthChange = Math.abs(newSize.width - initialSize.width);
    const heightChange = Math.abs(newSize.height - initialSize.height);
    const sizeChanged = widthChange > 2 || heightChange > 2;

    console.log(`📊 Size changes: width Δ${widthChange.toFixed(1)}px, height Δ${heightChange.toFixed(1)}px`);
    console.log(`🎯 Size change threshold: >2px, actual change: ${sizeChanged ? 'PASS' : 'FAIL'}`);

    expect(sizeChanged).toBe(true);
    console.log(`✅ Card size changed successfully in full page mode!`);
  });

  test('should update preview when card size is manually adjusted in simple grid mode', async () => {
    await app.goto();
    await app.setupCards();

    // Switch to simple grid mode and ensure grid is visible
    await app.switchPreviewModeFast('🔲 简单网格');
    await ensureSimpleGridMode(app.page, app);

    // Disable auto-fill to enable manual size adjustment
    await disableAutoFill(app.page);

    // Measure initial simple grid card size
    const initial = await getSimpleGridCardSize(app.page);

    // Adjust card size slider using keyboard
    const slider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    await slider.waitFor({ state: 'visible', timeout: 5000 });
    await slider.focus();
    await app.page.keyboard.press('ArrowRight');
    await app.page.keyboard.press('ArrowRight');

    // Wait until the simple grid card size changes (event-driven)
    await expect.poll(async () => {
      const now = await getSimpleGridCardSize(app.page);
      return Math.round(now.width);
    }, { timeout: 10000, intervals: [300, 500, 1000] }).not.toBe(Math.round(initial.width));
  });


});
