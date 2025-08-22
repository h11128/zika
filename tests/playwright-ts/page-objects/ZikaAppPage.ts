import { Page, expect, Download } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

export class ZikaAppPage {
  constructor(private page: Page) {}

  async goto() {
    console.log('🌐 Navigating to app...');
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForSelector('text=Chinese Learning Cards Generator', { timeout: 10000 });

    // Check for Streamlit errors
    await this.checkForStreamlitErrors();

    console.log('✅ App loaded successfully');
  }

  async checkForStreamlitErrors(allowedErrors: string[] = []): Promise<void> {
    console.log('🔍 Checking for Streamlit errors...');

    // Check for common Streamlit error messages
    const errorSelectors = [
      '.stAlert[data-baseweb="notification"]',  // Streamlit error alerts
      '.stException',  // Streamlit exceptions
      'text=/.*错误.*/',  // Chinese error messages
      'text=/.*Error.*/',  // English error messages
      'text=/Columns can only be placed inside other columns/',  // Specific column nesting error
    ];

    for (const selector of errorSelectors) {
      try {
        const errorElement = this.page.locator(selector);
        const isVisible = await errorElement.isVisible({ timeout: 1000 });
        if (isVisible) {
          const errorText = await errorElement.textContent();

          // Check if this error is in the allowed list
          const isAllowedError = allowedErrors.some(allowedError =>
            errorText?.includes(allowedError)
          );

          if (isAllowedError) {
            console.log(`⚠️ Expected error detected: ${errorText}`);
            return;
          }

          console.log(`❌ Unexpected Streamlit error detected: ${errorText}`);
          throw new Error(`Streamlit error found: ${errorText}`);
        }
      } catch (error) {
        if (error.message.includes('Streamlit error found:')) {
          throw error;
        }
        // Ignore timeout errors for error checking
      }
    }

    console.log('✅ No Streamlit errors detected');
  }

  // CSV Upload methods
  async selectCSVUploadMethod() {
    console.log('📁 Selecting CSV upload method...');
    const csvRadio = this.page.getByText('上传CSV文件');
    await csvRadio.click();
    console.log('✅ CSV upload method selected');
  }

  async uploadCSVFile(filePath: string): Promise<boolean> {
    console.log(`📤 Uploading CSV file: ${filePath}`);
    try {
      // First select CSV upload method
      await this.selectCSVUploadMethod();

      // Wait for the file uploader to appear
      await this.page.waitForTimeout(1000);

      // Try multiple strategies to find the file input
      let fileUploader = null;

      // Strategy 1: Look for file input by type
      try {
        fileUploader = this.page.locator('input[type="file"]').first();
        await fileUploader.waitFor({ state: 'visible', timeout: 5000 });
      } catch (error) {
        console.log('Strategy 1 failed, trying strategy 2...');
      }

      // Strategy 2: Look for Streamlit file uploader structure
      if (!fileUploader) {
        try {
          fileUploader = this.page.locator('[data-testid="stFileUploader"] input[type="file"]').first();
          await fileUploader.waitFor({ state: 'attached', timeout: 5000 });
        } catch (error) {
          console.log('Strategy 2 failed, trying strategy 3...');
        }
      }

      // Strategy 3: Look for any file input in the page
      if (!fileUploader) {
        try {
          fileUploader = this.page.locator('input[type="file"]').first();
          await fileUploader.waitFor({ state: 'attached', timeout: 5000 });
        } catch (error) {
          console.log('All strategies failed to find file uploader');
          return false;
        }
      }

      // Upload the file
      await fileUploader.setInputFiles(filePath);

      // Wait for processing
      await this.page.waitForTimeout(3000);

      console.log('✅ CSV file uploaded successfully');
      return true;
    } catch (error) {
      console.log(`❌ CSV upload failed: ${error.message}`);
      return false;
    }
  }

  async validateCSVUploadError(expectedError: string): Promise<boolean> {
    console.log(`🔍 Checking for expected error: ${expectedError}`);
    try {
      // Look for error message
      const errorElement = this.page.locator('.stAlert').filter({ hasText: expectedError });
      await errorElement.waitFor({ state: 'visible', timeout: 5000 });
      console.log('✅ Expected error message found');
      return true;
    } catch (error) {
      console.log(`❌ Expected error not found: ${error.message}`);
      return false;
    }
  }

  async validateCSVUploadSuccess(expectedCardCount: number): Promise<boolean> {
    console.log(`🔍 Validating successful CSV upload with ${expectedCardCount} cards`);
    try {
      // Look for success message
      const successElement = this.page.locator('.stAlert').filter({ hasText: `成功读取 ${expectedCardCount} 张卡片` });
      await successElement.waitFor({ state: 'visible', timeout: 5000 });
      console.log('✅ CSV upload success message found');
      return true;
    } catch (error) {
      console.log(`❌ Success message not found: ${error.message}`);
      return false;
    }
  }

  // Export methods
  async exportToPPTX(): Promise<Download | null> {
    console.log('📄 Exporting to PPTX...');
    try {
      // Click export PPTX button
      const exportButton = this.page.getByText('📄 导出 PowerPoint');
      await exportButton.click();

      // Wait for generation - try different selectors
      try {
        await this.page.waitForSelector('text=正在生成 PowerPoint 文件...', { state: 'visible', timeout: 5000 });
        await this.page.waitForSelector('text=正在生成 PowerPoint 文件...', { state: 'hidden', timeout: 30000 });
      } catch (error) {
        console.log('⚠️ Progress indicator not found, waiting for download button...');
        // Wait for download button to appear instead
        await this.page.waitForSelector('text=⬇️ 下载 PPTX', { timeout: 30000 });
      }

      // Click download button and wait for download
      const downloadPromise = this.page.waitForEvent('download');
      const downloadButton = this.page.getByText('⬇️ 下载 PPTX');
      await downloadButton.click();

      const download = await downloadPromise;
      console.log('✅ PPTX export completed');
      return download;
    } catch (error) {
      console.log(`❌ PPTX export failed: ${error.message}`);
      return null;
    }
  }

  async exportToPDF(): Promise<Download | null> {
    console.log('📑 Exporting to PDF...');
    try {
      // Click export PDF button
      const exportButton = this.page.getByText('📑 导出 PDF');
      await exportButton.click();

      // Wait for generation - try different selectors
      try {
        await this.page.waitForSelector('text=正在生成 PDF 文件...', { state: 'visible', timeout: 5000 });
        await this.page.waitForSelector('text=正在生成 PDF 文件...', { state: 'hidden', timeout: 30000 });
      } catch (error) {
        console.log('⚠️ Progress indicator not found, waiting for download button...');
        // Wait for download button to appear instead
        await this.page.waitForSelector('text=⬇️ 下载 PDF', { timeout: 30000 });
      }

      // Click download button and wait for download
      const downloadPromise = this.page.waitForEvent('download');
      const downloadButton = this.page.getByText('⬇️ 下载 PDF');
      await downloadButton.click();

      const download = await downloadPromise;
      console.log('✅ PDF export completed');
      return download;
    } catch (error) {
      console.log(`❌ PDF export failed: ${error.message}`);
      return null;
    }
  }

  async verifyDownloadedFile(download: Download, expectedExtension: string): Promise<boolean> {
    console.log(`🔍 Verifying downloaded file with extension: ${expectedExtension}`);
    try {
      const fileName = download.suggestedFilename();
      const fileSize = await download.path().then(path => path ? fs.statSync(path).size : 0);
      
      console.log(`📁 Downloaded file: ${fileName}, size: ${fileSize} bytes`);
      
      // Verify file extension
      if (!fileName.endsWith(expectedExtension)) {
        console.log(`❌ Wrong file extension. Expected: ${expectedExtension}, got: ${fileName}`);
        return false;
      }
      
      // Verify file size is reasonable (> 1KB)
      if (fileSize < 1024) {
        console.log(`❌ File too small: ${fileSize} bytes`);
        return false;
      }
      
      console.log('✅ Downloaded file verified');
      return true;
    } catch (error) {
      console.log(`❌ File verification failed: ${error.message}`);
      return false;
    }
  }

  // Pagination methods
  async generateMultiPageContent(): Promise<void> {
    console.log('📚 Generating multi-page content...');

    // Use manual input method
    const manualRadio = this.page.getByText('手动输入');
    await manualRadio.click();
    await this.page.waitForTimeout(1000);

    // Use template to ensure reliable card generation
    try {
      const templateSelect = this.page.getByLabel('选择模板');
      await templateSelect.click();
      await this.page.waitForTimeout(500);
      await this.page.getByText('数字', { exact: true }).click();
      console.log('✅ Selected 数字 template for multi-page content');
      await this.page.waitForTimeout(2000);
    } catch (error) {
      console.log('⚠️ Template selection failed, using manual input');

      // Fallback to manual input
      const textInput = this.page.getByLabel('输入汉字（空格分隔）');
      await textInput.clear();

      // Create 15 cards to ensure multiple pages (assuming 3x3 grid = 9 cards per page)
      const cards = '一 二 三 四 五 六 七 八 九 十 十一 十二 十三 十四 十五';
      await textInput.fill(cards);
      await this.page.waitForTimeout(3000);
    }

    console.log('✅ Multi-page content generated');
  }

  async navigateToPage(pageNumber: number): Promise<void> {
    console.log(`📄 Navigating to page ${pageNumber}...`);

    // Use page selector dropdown - Streamlit selectbox requires clicking and selecting
    try {
      const pageSelector = this.page.getByLabel('页码');
      await pageSelector.click();
      await this.page.waitForTimeout(500);

      // Look for the option in the dropdown
      const optionText = `第 ${pageNumber} 页`;
      const option = this.page.getByText(optionText, { exact: true });
      await option.click();

      // Wait for page change
      await this.page.waitForTimeout(1000);
      console.log(`✅ Navigated to page ${pageNumber}`);
    } catch (error) {
      console.log(`⚠️ Page navigation failed: ${error.message}`);
      // Fallback: try using navigation buttons
      if (pageNumber === 1) {
        await this.navigateFirstPage();
      } else {
        // Navigate step by step using next button
        const currentPageInfo = await this.getPageInfo();
        const steps = pageNumber - currentPageInfo.current;
        for (let i = 0; i < Math.abs(steps); i++) {
          if (steps > 0) {
            await this.navigateNextPage();
          } else {
            await this.navigatePreviousPage();
          }
        }
      }
    }
  }

  async getPageInfo(): Promise<{current: number, total: number}> {
    console.log('📊 Getting page information...');
    try {
      // Look for page info text
      const pageInfoElement = this.page.locator('text=/总计 \\d+ 张卡片，共 \\d+ 页/');
      await pageInfoElement.waitFor({ state: 'visible', timeout: 5000 });
      
      const pageInfoText = await pageInfoElement.textContent();
      const match = pageInfoText?.match(/总计 (\d+) 张卡片，共 (\d+) 页.*当前第 (\d+) 页/);
      
      if (match) {
        const totalCards = parseInt(match[1]);
        const totalPages = parseInt(match[2]);
        const currentPage = parseInt(match[3]);
        
        console.log(`📊 Page info: ${currentPage}/${totalPages} (${totalCards} total cards)`);
        return { current: currentPage, total: totalPages };
      }
      
      console.log('❌ Could not parse page info');
      return { current: 1, total: 1 };
    } catch (error) {
      console.log(`❌ Failed to get page info: ${error.message}`);
      return { current: 1, total: 1 };
    }
  }

  async navigateFirstPage(): Promise<void> {
    console.log('⏮️ Navigating to first page...');
    const firstPageButton = this.page.getByText('⏮️ 首页');
    await firstPageButton.click();
    await this.page.waitForTimeout(1000);
    console.log('✅ Navigated to first page');
  }

  async navigateLastPage(): Promise<void> {
    console.log('⏭️ Navigating to last page...');
    const lastPageButton = this.page.getByText('⏭️ 末页');
    await lastPageButton.click();
    await this.page.waitForTimeout(1000);
    console.log('✅ Navigated to last page');
  }

  async navigateNextPage(): Promise<void> {
    console.log('▶️ Navigating to next page...');
    const nextPageButton = this.page.getByText('▶️ 下页');
    await nextPageButton.click();
    await this.page.waitForTimeout(1000);
    console.log('✅ Navigated to next page');
  }

  async navigatePreviousPage(): Promise<void> {
    console.log('◀️ Navigating to previous page...');
    const prevPageButton = this.page.getByText('◀️ 上页');
    await prevPageButton.click();
    await this.page.waitForTimeout(1000);
    console.log('✅ Navigated to previous page');
  }

  async verifyCardsGenerated(allowedErrors: string[] = []): Promise<boolean> {
    console.log('🔍 Verifying cards are generated...');

    // First check for any Streamlit errors (allow specified errors)
    await this.checkForStreamlitErrors(allowedErrors);

    // Wait for cards to be generated
    await this.page.waitForTimeout(3000);

    // Check for cards in iframe or main page
    const frames = this.page.frames();
    let cardsFound = false;

    console.log(`🔍 Checking ${frames.length} frames for cards...`);

    for (let i = 0; i < frames.length; i++) {
      const frame = frames[i];
      try {
        // Look for various Chinese characters that might be in the cards
        const chinesePatterns = [
          'div:has-text("一")', 'div:has-text("二")', 'div:has-text("三")',
          'div:has-text("四")', 'div:has-text("五")', 'div:has-text("爱")',
          'div:has-text("家")', 'div:has-text("朋友")', 'div:has-text("水")',
          'div:has-text("火")', 'div:has-text("学习")', 'div:has-text("工作")'
        ];

        for (const pattern of chinesePatterns) {
          try {
            const hasCards = await frame.locator(pattern).first().isVisible({ timeout: 1000 });
            if (hasCards) {
              cardsFound = true;
              console.log(`✅ Cards found in iframe ${i} with pattern: ${pattern}`);
              break;
            }
          } catch {
            // Continue with next pattern
          }
        }

        if (cardsFound) break;

        // Also check for any div with Chinese characters using a more general approach
        try {
          const allDivs = await frame.locator('div').all();
          for (const div of allDivs) {
            const text = await div.textContent();
            if (text && /[\u4e00-\u9fff]/.test(text)) {
              cardsFound = true;
              console.log(`✅ Cards found in iframe ${i} with Chinese text: ${text.substring(0, 10)}...`);
              break;
            }
          }
        } catch {
          // Continue checking
        }

        if (cardsFound) break;
      } catch {
        // Continue checking other frames
      }
    }

    if (!cardsFound) {
      // Check if iframe exists at least
      try {
        await this.page.waitForSelector('iframe', { timeout: 5000 });
        console.log('⚠️ Preview iframe found but no card content detected');
        // This is now considered a failure - iframe exists but no content
        return false;
      } catch {
        console.log('❌ No preview iframe found');
        return false;
      }
    }

    return cardsFound;
  }

  async verifyPageNavigationButtons(currentPage: number, totalPages: number): Promise<boolean> {
    console.log(`🔍 Verifying navigation buttons for page ${currentPage}/${totalPages}...`);
    
    try {
      const firstPageButton = this.page.getByText('⏮️ 首页');
      const prevPageButton = this.page.getByText('◀️ 上页');
      const nextPageButton = this.page.getByText('▶️ 下页');
      const lastPageButton = this.page.getByText('⏭️ 末页');
      
      // Check if first/prev buttons are disabled on first page
      if (currentPage === 1) {
        const firstDisabled = await firstPageButton.isDisabled();
        const prevDisabled = await prevPageButton.isDisabled();
        if (!firstDisabled || !prevDisabled) {
          console.log('❌ First/Previous buttons should be disabled on first page');
          return false;
        }
      }
      
      // Check if next/last buttons are disabled on last page
      if (currentPage === totalPages) {
        const nextDisabled = await nextPageButton.isDisabled();
        const lastDisabled = await lastPageButton.isDisabled();
        if (!nextDisabled || !lastDisabled) {
          console.log('❌ Next/Last buttons should be disabled on last page');
          return false;
        }
      }
      
      console.log('✅ Navigation buttons state verified');
      return true;
    } catch (error) {
      console.log(`❌ Navigation button verification failed: ${error.message}`);
      return false;
    }
  }
}
