import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

test.describe('Pagination Navigation', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
    await app.goto();
    
    // Generate multi-page content for testing
    await app.generateMultiPageContent();
    
    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);
  });

  // Clean up after each test
  test.afterEach(async ({ page, context }) => {
    console.log('🧹 Cleaning up test page and context...');
    try {
      const pages = context.pages();
      for (const p of pages) {
        if (!p.isClosed()) {
          await p.close();
        }
      }
      await context.close();
      console.log('✅ Test page and context closed');
    } catch (error) {
      console.log('ℹ️ Page/context already closed');
    }
  });

  test('should display correct page information for multi-page content @critical', async () => {
    console.log('🧪 Testing multi-page content display...');

    // Get initial page info
    const initialPageInfo = await app.getPageInfo();
    expect(initialPageInfo.total).toBeGreaterThan(1);
    expect(initialPageInfo.current).toBe(1);

    console.log(`📊 Total pages: ${initialPageInfo.total}`);

    // Verify page info is displayed correctly
    const pageInfoText = await app.page.locator('text=/总计 \\d+ 张卡片，共 \\d+ 页/').textContent();
    expect(pageInfoText).toContain('总计');
    expect(pageInfoText).toContain('张卡片');
    expect(pageInfoText).toContain('页');

    console.log('✅ Page information display test completed');
  });

  test('should maintain content consistency when cards are generated', async () => {
    console.log('🧪 Testing content consistency...');

    // Get initial page info
    const pageInfo = await app.getPageInfo();
    expect(pageInfo.total).toBeGreaterThan(1);

    // Verify cards are visible initially
    const cardsVisible = await app.verifyCardsGenerated();
    expect(cardsVisible).toBe(true);

    // Wait a bit and verify cards are still there
    await app.page.waitForTimeout(2000);
    const cardsStillVisible = await app.verifyCardsGenerated();
    expect(cardsStillVisible).toBe(true);

    console.log('✅ Content consistency test completed');
  });

  test('should display navigation buttons when multiple pages exist @critical', async () => {
    console.log('🧪 Testing navigation button presence...');

    const pageInfo = await app.getPageInfo();
    expect(pageInfo.total).toBeGreaterThan(1);

    // Verify navigation buttons exist (use role to avoid strict mode conflicts)
    const firstPageButton = app.page.getByRole('button', { name: '⏮️ 首页' }).last();
    const prevPageButton = app.page.getByRole('button', { name: '◀️ 上页' }).last();
    const nextPageButton = app.page.getByRole('button', { name: '▶️ 下页' }).last();
    const lastPageButton = app.page.getByRole('button', { name: '⏭️ 末页' }).last();

    await expect(firstPageButton).toBeVisible();
    await expect(prevPageButton).toBeVisible();
    await expect(nextPageButton).toBeVisible();
    await expect(lastPageButton).toBeVisible();

    console.log('✅ Navigation buttons are visible');
    console.log('✅ Navigation button presence test completed');
  });

  test('should display page selector when multiple pages exist', async () => {
    console.log('🧪 Testing page selector presence...');

    const pageInfo = await app.getPageInfo();
    expect(pageInfo.total).toBeGreaterThan(1);

    // Verify page selector exists (disambiguate from 编辑页码)
    const pageSelector = app.page.getByRole('combobox', { name: / 页码$/ }).last();
    await expect(pageSelector).toBeVisible();

    // Verify it shows some page information
    const selectorValue = await pageSelector.inputValue();
    expect(selectorValue).toBeDefined();

    console.log('✅ Page selector is visible and functional');
    console.log('✅ Page selector test completed');
  });

  test('should handle pagination with different content amounts', async () => {
    console.log('🧪 Testing pagination with different content...');

    // Get initial page info with template content
    const initialPageInfo = await app.getPageInfo();
    console.log(`📊 Template content: ${initialPageInfo.current}/${initialPageInfo.total} pages`);

    // Switch to manual input with less content
    const manualRadio = app.page.getByText('手动输入');
    await manualRadio.click();
    await app.page.waitForTimeout(1000);

    const textInput = app.page.getByLabel('输入汉字（空格分隔）');
    await textInput.clear();
    await textInput.fill('爱 家 朋友'); // Only 3 cards
    await app.page.waitForTimeout(2000);

    // Get new page info
    const newPageInfo = await app.getPageInfo();
    console.log(`📊 Manual content: ${newPageInfo.current}/${newPageInfo.total} pages`);

    // Should have fewer or equal pages with less content
    expect(newPageInfo.total).toBeLessThanOrEqual(initialPageInfo.total);
    expect(newPageInfo.current).toBe(1);

    console.log('✅ Pagination content test completed');
  });

  test('should handle minimal content pagination correctly', async () => {
    console.log('🧪 Testing minimal content pagination...');

    // Test with minimal content
    const manualRadio = app.page.getByText('手动输入');
    await manualRadio.click();

    const textInput = app.page.getByLabel('输入汉字（空格分隔）');
    await textInput.clear();
    await textInput.fill('爱 家'); // Only 2 cards
    await app.page.waitForTimeout(2000);

    // Get page info for minimal content
    const minimalPageInfo = await app.getPageInfo();
    expect(minimalPageInfo.current).toBe(1);
    expect(minimalPageInfo.total).toBeGreaterThanOrEqual(1);

    console.log(`📊 Minimal content: ${minimalPageInfo.current}/${minimalPageInfo.total} pages`);

    // Verify cards are still generated
    const cardsVisible = await app.verifyCardsGenerated();
    expect(cardsVisible).toBe(true);

    console.log('✅ Minimal content pagination test completed');
  });
});
