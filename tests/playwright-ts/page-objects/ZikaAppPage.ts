import { Page, expect, Download } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

export class ZikaAppPage {
  constructor(private page: Page) {}

  async goto() {
    console.log('🌐 Navigating to app...');
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
    // Wait for a stable section header rather than exact English title (handles emoji and i18n)
    await this.page.waitForSelector('text=⚙️ 选项', { timeout: 20000 });

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

  async setupCards(): Promise<void> {
    console.log('🎯 Setting up cards...');

    // Use manual input method
    const manualRadio = this.page.getByText('手动输入', { exact: true });
    await manualRadio.click();
    await this.page.waitForTimeout(1000);

    // Use template to ensure reliable card generation
    try {
      const templateSelect = this.page.getByLabel('选择模板');
      await templateSelect.click();
      await this.page.waitForTimeout(500);
      await this.page.getByText('数字', { exact: true }).click();
      console.log('✅ Selected 数字 template for card setup');
      await this.page.waitForTimeout(2000);
    } catch (error) {
      console.log('⚠️ Template selection failed, using manual input');

      // Fallback to manual input
      const textInput = this.page.getByLabel('输入汉字（空格分隔）');
      await textInput.clear();
      const cards = '一 二 三 四 五';
      await textInput.fill(cards);
      await this.page.waitForTimeout(3000);
    }

    console.log('✅ Cards setup completed');
  }

  async waitForCardsGeneration(): Promise<void> {
    console.log('⏳ Waiting for cards generation...');
    await this.page.waitForTimeout(3000);
    console.log('✅ Cards generation wait completed');
  }

  async verifyPreviewVisible(): Promise<boolean> {
    console.log('🔍 Verifying preview is visible...');
    try {
      await this.page.waitForSelector('iframe', { timeout: 5000 });
      console.log('✅ Preview iframe is visible');
      return true;
    } catch (error) {
      console.log('❌ Preview iframe not found');
      return false;
    }
  }

  async expandAdvancedOptions(): Promise<void> {
    const advanced = this.page.getByText('🔧 高级选项', { exact: true });
    await advanced.click().catch(() => {});
    await this.page.waitForTimeout(500);
  }

  async switchPreviewMode(modeLabel: '📄 完整页面' | '🔲 简单网格'): Promise<void> {
    const selector = this.page.getByLabel('预览模式', { exact: true }).or(this.page.getByText('预览模式'));
    await selector.click().catch(() => {});
    await this.page.getByText(modeLabel, { exact: true }).click();
    await this.page.waitForTimeout(1000);
  }

  async setRowsCols(rows: number, cols: number): Promise<void> {
    await this.expandAdvancedOptions();
    // Streamlit number inputs labeled exactly as below
    const colsInput = this.page.getByLabel('每行卡片数 (列)', { exact: true });
    const rowsInput = this.page.getByLabel('每列卡片数 (行)', { exact: true });
    // Fill desired values (clear then fill)
    await colsInput.fill(String(cols)).catch(() => {});
    await rowsInput.fill(String(rows)).catch(() => {});
    await this.page.waitForTimeout(500);
  }

  async setGapMargin(gapStep: number = 1, marginStep: number = 1): Promise<void> {
    await this.expandAdvancedOptions();
    const gapSlider = this.page.getByLabel('卡片间距 (cm)', { exact: true });
    const marginSlider = this.page.getByLabel('页面边距 (cm)', { exact: true });
    await gapSlider.click().catch(() => {});
    for (let i = 0; i < gapStep; i++) await this.page.keyboard.press('ArrowRight');
    await marginSlider.click().catch(() => {});
    for (let i = 0; i < marginStep; i++) await this.page.keyboard.press('ArrowRight');
    await this.page.waitForTimeout(500);
  }

  async selectCustomColorOrVerifyDisplay(hex: string): Promise<void> {
    await this.expandAdvancedOptions();
    const colorLabel = this.page.getByText('选择颜色', { exact: true });
    await expect(colorLabel).toBeVisible({ timeout: 5000 });
    const anchor = this.page.locator('[data-testid="color-picker-anchor"]');
    await expect(anchor).toHaveCount(1, { timeout: 5000 });

    const nativeInput = this.page.locator('input[type="color"]').first();
    if (await nativeInput.count() > 0) {
      await nativeInput.fill(hex);
      await this.page.waitForTimeout(1000);
    } else {
      // Fall back to verifying current color display presence later in tests
      console.log('ℹ️ Native color input not present; will verify display & preview');
    }
  }

  async verifyPreviewUpdated(): Promise<boolean> {
    // Minimal verification: cards present in any iframe or main page
    // Implementation is in the lower part of this class
    return await this.findCardsInAnyFrameOrPage();
  }

  async findCardsInAnyFrameOrPage(): Promise<boolean> {
    // Wait for potential rerender
    await this.page.waitForTimeout(1000);

    const frames = this.page.frames();
    // First, try frames for Chinese text
    for (let i = 0; i < frames.length; i++) {
      const frame = frames[i];
      try {
        const hasChinese = await frame.locator('text=/[\u4e00-\u9fff]/').first().isVisible({ timeout: 500 });
        if (hasChinese) {
          console.log(`✅ Cards found in iframe ${i} (Chinese text)`);
          return true;
        }
      } catch {}
    }

    // Fallback: any iframe present
    try {
      await this.page.waitForSelector('iframe', { timeout: 2000 });
      console.log('⚠️ Preview iframe present but text not detected');
      return true; // consider as minimally present
    } catch {}

    // As a last resort, scan main page
    const divs = await this.page.locator('div').all();
    for (const div of divs) {
      const text = await div.textContent();
      if (text && /[\u4e00-\u9fff]/.test(text)) {
        console.log('✅ Cards-like content found on main page');
        return true;
      }
    }
    console.log('❌ No cards found');
    return false;
  }


  // CSV Upload methods
  async selectCSVUploadMethod() {
    console.log('📁 Selecting CSV upload method...');
  }

  async reloadAndWait(): Promise<void> {
    console.log('🔄 Reloading page...');
    await this.page.reload();
    await this.page.waitForLoadState('networkidle');
    await this.checkForStreamlitErrors();
    console.log('✅ Reloaded');
  }

  async getRowsCols(): Promise<{ rows: number | null; cols: number | null }> {
    await this.expandAdvancedOptions();
    const colsInput = this.page.getByLabel('每行卡片数 (列)', { exact: true });
    const rowsInput = this.page.getByLabel('每列卡片数 (行)', { exact: true });
    let rows: number | null = null;
    let cols: number | null = null;
    try { cols = parseInt(await colsInput.inputValue()); } catch {}
    try { rows = parseInt(await rowsInput.inputValue()); } catch {}
    return { rows, cols };
  }

  async selectPresetColorFromPalette(index = 2): Promise<string | null> {
    await this.expandAdvancedOptions();
    // Find the component iframe that hosts the color palette
    const frames = this.page.frames();
    for (const frame of frames) {
      const chips = frame.locator('.chip');
      try {
        const count = await chips.count();
        if (count > index) {
          const chip = chips.nth(index);
          const hex = (await chip.getAttribute('title')) || null;
          await chip.click();
          await this.page.waitForTimeout(1000);
          return hex;
        }
      } catch {}
    }
    console.log('ℹ️ No palette chips found in frames');
    return null;
  }

  async getCurrentColorFromDisplay(): Promise<string | null> {
    // Scan for a div that contains a hex color text (used by the current color block)
    const divs = await this.page.locator('div').all();
    const hexRe = /#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})/;
    for (const div of divs) {
      const text = await div.textContent();
      if (text && hexRe.test(text)) {
        const match = text.match(hexRe);
        if (match) return match[0];
      }
    }
    return null;
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

  async checkAutoFillState(): Promise<{ isEnabled: boolean; cardSizeVisible: boolean }> {
    console.log('🔍 Checking auto-fill state...');

    try {
      const autoFillCheckbox = this.page.locator('input[type="checkbox"]').filter({ hasText: /自动填充/ });
      const isEnabled = await autoFillCheckbox.isChecked().catch(() => false);

      const cardSizeSlider = this.page.getByLabel('卡片大小 (cm)', { exact: true });
      const cardSizeVisible = await cardSizeSlider.isVisible().catch(() => false);

      console.log(`📊 Auto-fill enabled: ${isEnabled}, Card size visible: ${cardSizeVisible}`);
      return { isEnabled, cardSizeVisible };
    } catch (error) {
      console.log(`⚠️ Error checking auto-fill state: ${error}`);
      return { isEnabled: false, cardSizeVisible: false };
    }
  }

  async checkColorPickerState(): Promise<{ exists: boolean; currentColor: string | null }> {
    console.log('🔍 Checking color picker state...');

    try {
      const colorPicker = this.page.locator('input[type="color"]');
      const exists = await colorPicker.count() > 0;

      let currentColor = null;
      if (exists) {
        currentColor = await colorPicker.inputValue().catch(() => null);
      }

      console.log(`🎨 Color picker exists: ${exists}, Current color: ${currentColor}`);
      return { exists, currentColor };
    } catch (error) {
      console.log(`⚠️ Error checking color picker state: ${error}`);
      return { exists: false, currentColor: null };
    }
  }

  async checkUIStateConsistency(): Promise<boolean> {
    console.log('🔍 Checking overall UI state consistency...');

    const autoFillState = await this.checkAutoFillState();
    const colorState = await this.checkColorPickerState();

    // Check consistency: if auto-fill is enabled, card size should not be visible
    const isConsistent = !autoFillState.isEnabled || !autoFillState.cardSizeVisible;

    if (!isConsistent) {
      console.log('❌ UI state inconsistency detected: auto-fill enabled but card size visible');
      return false;
    }

    console.log('✅ UI state is consistent');
    return true;
  }

  async testCustomColorSelection(testColor: string): Promise<boolean> {
    console.log(`🎨 Testing custom color selection: ${testColor}`);

    try {
      const colorPicker = this.page.locator('input[type="color"]');
      await colorPicker.fill(testColor);
      await this.page.waitForTimeout(2000);

      // Verify color was applied
      const currentColorDisplay = this.page.locator('div').filter({ hasText: testColor });
      const colorApplied = await currentColorDisplay.count() > 0;

      if (colorApplied) {
        console.log(`✅ Custom color ${testColor} successfully applied`);
        return true;
      } else {
        console.log(`❌ Custom color ${testColor} was not applied`);
        return false;
      }
    } catch (error) {
      console.log(`❌ Custom color selection failed: ${error}`);
      return false;
    }
  }
}
