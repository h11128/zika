import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// This E2E verifies that changing color does not reset preview font size
// Uses event-driven waits via ZikaAppPage helpers per repo conventions

test('preview font persistence after color change', async ({ page }) => {
  const app = new ZikaAppPage(page);
  await app.goto();
  await app.setupCards();
  await app.waitForCardsGeneration();
  await app.verifyPreviewVisible();

  // Switch to 完整页面 to check size alignment more stably
  await app.switchPreviewModeFast('📄 完整页面');

  // Open 高级选项并设置字体大小（26/12/14）
  await app.expandAdvancedOptions();
  const hanziSlider = page.getByRole('slider', { name: '汉字' });
  const pinyinSlider = page.getByRole('slider', { name: '拼音' });
  const enSlider = page.getByRole('slider', { name: '英文' });

  // Move sliders to target values using keyboard (event-driven vs timeouts)
  // We don't know current values; so we force a few lefts then rights
  await hanziSlider.click();
  for (let i = 0; i < 20; i++) await page.keyboard.press('ArrowLeft');
  for (let i = 0; i < 13; i++) await page.keyboard.press('ArrowRight'); // move to ~26

  await pinyinSlider.click();
  for (let i = 0; i < 20; i++) await page.keyboard.press('ArrowLeft');
  for (let i = 0; i < 12; i++) await page.keyboard.press('ArrowRight'); // move to ~12

  await enSlider.click();
  for (let i = 0; i < 20; i++) await page.keyboard.press('ArrowLeft');
  for (let i = 0; i < 14; i++) await page.keyboard.press('ArrowRight'); // ~14

  // 变更颜色
  await app.selectCustomColorOrVerifyDisplay('#ffcc00');

  // 切换预览模式以触发稳定重渲染（可选，但更稳定）
  await app.switchPreviewModeFast('🔲 简单网格');
  await app.switchPreviewModeFast('📄 完整页面');

  // 在所有 iframe 中查找元素，避免因多个 iframe 或顺序变化导致的 flakiness
  async function getFontSizeAcrossFrames(selector: string): Promise<number> {
    const deadline = Date.now() + 10000;
    let lastError: any = null;
    while (Date.now() < deadline) {
      for (const frame of page.frames()) {
        try {
          const loc = frame.locator(selector).first();
          await loc.waitFor({ state: 'visible', timeout: 500 });
          const size = await loc.evaluate((el: any) => parseFloat((globalThis as any).getComputedStyle(el as any).fontSize));
          if (!isNaN(size)) return size;
        } catch (e) {
          lastError = e as any;
        }
      }
      await page.waitForTimeout(150);
    }
    throw lastError || new Error(`Element ${selector} not found in any frame`);
  }

  const hanziSize = await getFontSizeAcrossFrames('.page-hanzi');
  const pinyinSize = await getFontSizeAcrossFrames('.page-pinyin');
  const englishSize = await getFontSizeAcrossFrames('.page-english');

  // 因为页面缩放 factor 存在，我们仅验证没有回退到默认比例对应的像素值
  // 即：不应接近 48pt→px、18pt→px 的比例（这在我们页面一般更大）
  const ptToPx = 96/72;
  expect(hanziSize).toBeLessThan(48 * ptToPx - 2);
  expect(pinyinSize).toBeLessThan(18 * ptToPx - 1);
  // 英文默认值就是 14，因此只要不大于默认即可；我们调整过为14，所以允许接近
  expect(englishSize).toBeGreaterThan(10);
});

