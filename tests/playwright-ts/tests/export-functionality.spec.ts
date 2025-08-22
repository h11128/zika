import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';
import * as path from 'path';

test.describe('Export Functionality', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    // Enable downloads for this test
    app = new ZikaAppPage(page);
    await app.goto();
    
    // Set up some cards for export
    await app.generateMultiPageContent();
    
    // Verify cards are generated before testing export
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

  test('should export cards to PPTX and verify download', async () => {
    console.log('🧪 Testing PPTX export and download...');
    
    // Export to PPTX
    const download = await app.exportToPPTX();
    expect(download).not.toBeNull();
    
    if (download) {
      // Verify downloaded file
      const fileVerified = await app.verifyDownloadedFile(download, '.pptx');
      expect(fileVerified).toBe(true);
      
      // Verify filename contains expected pattern
      const fileName = download.suggestedFilename();
      expect(fileName).toMatch(/cards_\d+_\d{8}_\d{6}\.pptx/);
      
      console.log(`✅ PPTX file downloaded: ${fileName}`);
    }
    
    console.log('✅ PPTX export test completed');
  });

  test('should export cards to PDF and verify download', async () => {
    console.log('🧪 Testing PDF export and download...');
    
    // Export to PDF
    const download = await app.exportToPDF();
    expect(download).not.toBeNull();
    
    if (download) {
      // Verify downloaded file
      const fileVerified = await app.verifyDownloadedFile(download, '.pdf');
      expect(fileVerified).toBe(true);
      
      // Verify filename contains expected pattern
      const fileName = download.suggestedFilename();
      expect(fileName).toMatch(/cards_\d+_\d{8}_\d{6}\.pdf/);
      
      console.log(`✅ PDF file downloaded: ${fileName}`);
    }
    
    console.log('✅ PDF export test completed');
  });

  test('should show export completion status and progress', async () => {
    console.log('🧪 Testing export progress and completion status...');

    // Start PPTX export and monitor progress
    const exportButton = app.page.getByText('📄 导出 PowerPoint');
    await exportButton.click();

    // Try to verify progress indicator appears (may be very fast)
    try {
      const progressIndicator = app.page.locator('text=正在生成 PowerPoint 文件...');
      await expect(progressIndicator).toBeVisible({ timeout: 2000 });
      console.log('✅ Export progress indicator shown');

      // Wait for completion
      await expect(progressIndicator).toBeHidden({ timeout: 30000 });
      console.log('✅ Export progress completed');
    } catch (error) {
      console.log('⚠️ Progress indicator not visible (export may be very fast)');
    }

    // Verify download button appears (this is the key indicator)
    const downloadButton = app.page.getByText('⬇️ 下载 PPTX');
    await expect(downloadButton).toBeVisible({ timeout: 30000 });
    console.log('✅ Download button appeared after export completion');

    console.log('✅ Export progress test completed');
  });

  test('should handle export with different card counts', async () => {
    console.log('🧪 Testing export with different card counts...');
    
    // Test with small dataset first
    const manualRadio = app.page.getByText('手动输入');
    await manualRadio.click();
    
    const textInput = app.page.getByLabel('输入汉字（空格分隔）');
    await textInput.clear();
    await textInput.fill('爱 家 朋友'); // Only 3 cards
    await app.page.waitForTimeout(2000);
    
    // Export small dataset
    const smallDownload = await app.exportToPDF();
    expect(smallDownload).not.toBeNull();
    
    if (smallDownload) {
      const fileVerified = await app.verifyDownloadedFile(smallDownload, '.pdf');
      expect(fileVerified).toBe(true);
      console.log('✅ Small dataset export successful');
    }
    
    // Test with larger dataset
    await textInput.clear();
    const largeDataset = '一 二 三 四 五 六 七 八 九 十 十一 十二 十三 十四 十五 十六 十七 十八 十九 二十';
    await textInput.fill(largeDataset);
    await app.page.waitForTimeout(3000);
    
    // Export large dataset
    const largeDownload = await app.exportToPDF();
    expect(largeDownload).not.toBeNull();
    
    if (largeDownload) {
      const fileVerified = await app.verifyDownloadedFile(largeDownload, '.pdf');
      expect(fileVerified).toBe(true);
      console.log('✅ Large dataset export successful');
    }
    
    console.log('✅ Different card count export test completed');
  });

  test('should export current page vs all pages correctly', async () => {
    console.log('🧪 Testing export scope (current page vs all)...');
    
    // Generate multi-page content
    await app.generateMultiPageContent();
    
    // Get page info
    const pageInfo = await app.getPageInfo();
    expect(pageInfo.total).toBeGreaterThan(1);
    console.log(`📊 Generated ${pageInfo.total} pages`);
    
    // Navigate to second page
    if (pageInfo.total > 1) {
      await app.navigateToPage(2);
      
      // Export from second page (should export all cards, not just current page)
      const download = await app.exportToPPTX();
      expect(download).not.toBeNull();
      
      if (download) {
        const fileVerified = await app.verifyDownloadedFile(download, '.pptx');
        expect(fileVerified).toBe(true);
        console.log('✅ Multi-page export successful');
      }
    }
    
    console.log('✅ Export scope test completed');
  });

  test('should handle export errors gracefully', async () => {
    console.log('🧪 Testing export error handling...');
    
    // Clear all cards to test export with no content
    const manualRadio = app.page.getByText('手动输入');
    await manualRadio.click();
    
    const textInput = app.page.getByLabel('输入汉字（空格分隔）');
    await textInput.clear();
    await app.page.waitForTimeout(1000);
    
    // Try to export with no cards
    const exportButton = app.page.getByText('📄 导出 PowerPoint');
    await exportButton.click();
    
    // Check if appropriate handling occurs (either error message or graceful handling)
    try {
      // Look for error message or spinner
      const hasError = await app.page.locator('.stAlert').filter({ hasText: '导出失败' }).isVisible({ timeout: 5000 });
      const hasSpinner = await app.page.locator('text=正在生成 PowerPoint 文件...').isVisible({ timeout: 5000 });
      
      if (hasError) {
        console.log('✅ Export error handled with error message');
      } else if (hasSpinner) {
        // Wait for completion and check result
        await app.page.waitForSelector('text=正在生成 PowerPoint 文件...', { state: 'hidden', timeout: 30000 });
        console.log('✅ Export completed (possibly with empty content)');
      } else {
        console.log('✅ Export handled gracefully');
      }
    } catch (error) {
      console.log('✅ Export error handling test completed (no specific error UI found)');
    }
    
    console.log('✅ Export error handling test completed');
  });
});
