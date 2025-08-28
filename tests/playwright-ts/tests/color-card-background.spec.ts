import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// 精准校验：卡片背景颜色确实变为选中的颜色

test.describe('Preview - Card Background Color', () => {
  let zikaApp: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    zikaApp = new ZikaAppPage(page);
    await zikaApp.goto();
  });

  test('Page 模式：自定义颜色应应用到卡片背景', async ({ page }) => {
    await zikaApp.setupCards();
    await zikaApp.expandAdvancedOptions();

    const target = '#00ff00';
    await zikaApp.selectCustomColorOrVerifyDisplay(target);
    await zikaApp.waitForCurrentColorDisplay(target);
    const expected = (await zikaApp.getCurrentColorFromDisplay()) || target;

    // 切换到完整页面模式确保选择器路径（也可触发一次稳定的 rerender）
    await zikaApp.switchPreviewModeFast('📄 完整页面');

    // 精确断言卡片背景色
    await zikaApp.expectCardBackgroundHex(expected, 'page');
  });

  test('Simple Grid 模式：自定义颜色应应用到卡片背景', async ({ page }) => {
    await zikaApp.setupCards();
    await zikaApp.expandAdvancedOptions();

    const target = '#ff0000';
    await zikaApp.selectCustomColorOrVerifyDisplay(target);
    await zikaApp.waitForCurrentColorDisplay(target);
    const expected = (await zikaApp.getCurrentColorFromDisplay()) || target;

    await zikaApp.switchPreviewModeFast('🔲 简单网格');

    // 精确断言卡片背景色
    await zikaApp.expectCardBackgroundHex(expected, 'grid');
  });
});

