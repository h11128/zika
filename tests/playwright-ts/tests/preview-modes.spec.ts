import { test, expect } from '@playwright/test';

class ZikaAppPage {
  constructor(private page: any) {}

  async goto() {
    console.log('🌐 Navigating to app...');
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForSelector('text=Chinese Learning Cards Generator', { timeout: 10000 });
    console.log('✅ App loaded successfully');
  }

  async setupCards() {
    console.log('🔧 Setting up cards...');

    // Input test text
    const textInput = this.page.getByLabel('输入汉字（空格分隔）');
    await textInput.waitFor({ state: 'visible', timeout: 5000 });
    await textInput.clear();
    await textInput.fill('你好世界测试');

    // Wait for processing
    await this.page.waitForTimeout(2000);
    console.log('✅ Cards setup completed');
  }

  async switchToSimpleGridMode() {
    console.log('🔄 Switching to simple grid mode...');
    
    try {
      // Wait for preview mode section
      await this.page.waitForTimeout(1000);
      
      // Try multiple methods to find and click simple grid radio button
      let success = false;
      
      // Method 1: Direct text search (most reliable)
      try {
        await this.page.getByText('🔲 简单网格').click({ timeout: 5000 });
        console.log('✅ Switched to simple grid mode via text click');
        success = true;
      } catch (error) {
        console.log('⚠️ Method 1 failed:', error.message);
      }

      // Method 2: Find radio input and click
      if (!success) {
        try {
          // Find all radio inputs and click the one associated with simple grid
          const radios = await this.page.locator('input[type="radio"]').all();
          for (const radio of radios) {
            const parent = radio.locator('..');
            const text = await parent.textContent();
            if (text && text.includes('简单网格')) {
              await radio.click({ force: true });
              console.log('✅ Switched to simple grid mode via radio input');
              success = true;
              break;
            }
          }
        } catch (error) {
          console.log('⚠️ Method 2 failed:', error.message);
        }
      }
      
      if (success) {
        await this.page.waitForTimeout(2000); // Wait for mode switch
      } else {
        console.log('⚠️ Could not switch to simple grid mode');
      }
      
      return success;
    } catch (error) {
      console.log('⚠️ Switch to simple grid error:', error.message);
      return false;
    }
  }

  async switchToFullPageMode() {
    console.log('🔄 Switching to full page mode...');
    
    try {
      // Wait for preview mode section
      await this.page.waitForTimeout(1000);
      
      // Try multiple methods to find and click full page radio button
      let success = false;
      
      // Method 1: Direct text search (most reliable)
      try {
        await this.page.getByText('📄 完整页面').click({ timeout: 5000 });
        console.log('✅ Switched to full page mode via text click');
        success = true;
      } catch (error) {
        console.log('⚠️ Method 1 failed:', error.message);
      }

      // Method 2: Find radio input and click
      if (!success) {
        try {
          // Find all radio inputs and click the one associated with full page
          const radios = await this.page.locator('input[type="radio"]').all();
          for (const radio of radios) {
            const parent = radio.locator('..');
            const text = await parent.textContent();
            if (text && text.includes('完整页面')) {
              await radio.click({ force: true });
              console.log('✅ Switched to full page mode via radio input');
              success = true;
              break;
            }
          }
        } catch (error) {
          console.log('⚠️ Method 2 failed:', error.message);
        }
      }
      
      if (success) {
        await this.page.waitForTimeout(2000); // Wait for mode switch
      } else {
        console.log('⚠️ Could not switch to full page mode');
      }
      
      return success;
    } catch (error) {
      console.log('⚠️ Switch to full page error:', error.message);
      return false;
    }
  }

  async getCurrentPreviewMode(): Promise<'simple' | 'fullpage' | 'unknown'> {
    console.log('🔍 Detecting current preview mode...');

    try {
      // Try multiple strategies to detect the current mode

      // Strategy 1: Check radio buttons by text content
      try {
        const simpleGridRadio = this.page.getByText('🔲 简单网格');
        const fullPageRadio = this.page.getByText('📄 完整页面');

        // Check if the radio buttons are visible
        const simpleVisible = await simpleGridRadio.isVisible({ timeout: 2000 });
        const fullPageVisible = await fullPageRadio.isVisible({ timeout: 2000 });

        if (simpleVisible && fullPageVisible) {
          // Try to determine which one is selected by checking the input elements
          const allRadios = await this.page.locator('input[type="radio"]').all();
          for (const radio of allRadios) {
            const isChecked = await radio.isChecked();
            if (isChecked) {
              // Get the label text associated with this radio
              const parent = radio.locator('..');
              const text = await parent.textContent();
              if (text && text.includes('简单网格')) {
                console.log('📊 Current mode: Simple Grid (detected via text)');
                return 'simple';
              } else if (text && text.includes('完整页面')) {
                console.log('📄 Current mode: Full Page (detected via text)');
                return 'fullpage';
              }
            }
          }
        }
      } catch (error) {
        console.log('⚠️ Strategy 1 failed:', error.message);
      }

      // Strategy 2: Check by iframe content
      try {
        const frames = this.page.frames();
        for (const frame of frames) {
          try {
            const hasSimpleGrid = await frame.locator('.simple-grid').isVisible({ timeout: 1000 });
            if (hasSimpleGrid) {
              console.log('📊 Current mode: Simple Grid (detected via iframe content)');
              return 'simple';
            }

            const hasPageGrid = await frame.locator('.page-grid').isVisible({ timeout: 1000 });
            if (hasPageGrid) {
              console.log('📄 Current mode: Full Page (detected via iframe content)');
              return 'fullpage';
            }
          } catch {
            // Continue checking other frames
          }
        }
      } catch (error) {
        console.log('⚠️ Strategy 2 failed:', error.message);
      }

      console.log('❓ Current mode: Unknown');
      return 'unknown';
    } catch (error) {
      console.log('⚠️ Could not detect preview mode:', error.message);
      return 'unknown';
    }
  }

  async verifyPreviewContent(expectedMode: 'simple' | 'fullpage') {
    console.log(`🔍 Verifying preview content for ${expectedMode} mode...`);
    
    // Wait for preview to update
    await this.page.waitForTimeout(2000);
    
    // Check for iframe and content
    const frames = this.page.frames();
    let contentFound = false;
    let modeSpecificContentFound = false;
    
    for (const frame of frames) {
      try {
        // Check for general content
        const hasContent = await frame.locator('div:has-text("你"), div:has-text("好"), div:has-text("世")').first().isVisible({ timeout: 3000 });
        if (hasContent) {
          contentFound = true;
          
          // Check for mode-specific indicators
          if (expectedMode === 'simple') {
            const hasSimpleGrid = await frame.locator('.simple-grid, [class*="simple"]').first().isVisible({ timeout: 2000 });
            if (hasSimpleGrid) {
              modeSpecificContentFound = true;
              console.log('✅ Simple grid content detected');
            }
          } else if (expectedMode === 'fullpage') {
            const hasPageGrid = await frame.locator('.page-grid, [class*="page"]').first().isVisible({ timeout: 2000 });
            if (hasPageGrid) {
              modeSpecificContentFound = true;
              console.log('✅ Full page content detected');
            }
          }
          
          break;
        }
      } catch {
        // Continue checking other frames
      }
    }
    
    console.log(`📊 Content found: ${contentFound}, Mode-specific: ${modeSpecificContentFound}`);
    return { contentFound, modeSpecificContentFound };
  }

  async verifyDataPersistence() {
    console.log('🔍 Verifying data persistence...');

    // Check that the input text is still there
    const textInput = this.page.getByLabel('输入汉字（空格分隔）');
    const inputValue = await textInput.inputValue();

    const hasData = inputValue.length > 0;
    console.log(`📊 Input data preserved: ${hasData} (length: ${inputValue.length})`);

    return hasData;
  }
}

test.describe('Preview Modes', () => {
  // Clean up after each test
  test.afterEach(async ({ page, context }) => {
    console.log('🧹 Cleaning up test page and context...');
    try {
      // Close all pages in the context
      const pages = context.pages();
      for (const p of pages) {
        if (!p.isClosed()) {
          await p.close();
        }
      }
      // Close the context
      await context.close();
      console.log('✅ Test page and context closed');
    } catch (error) {
      console.log('ℹ️ Page/context already closed');
    }
  });

  test('should switch from full page to simple grid mode @critical', async ({ page }) => {
    const app = new ZikaAppPage(page);
    
    // Setup
    await app.goto();
    await app.setupCards();
    
    // Verify initial mode (should be full page by default)
    const initialMode = await app.getCurrentPreviewMode();
    console.log(`📊 Initial mode: ${initialMode}`);
    
    // Switch to simple grid mode
    const switchSuccess = await app.switchToSimpleGridMode();
    expect(switchSuccess).toBe(true);
    
    // Verify mode changed
    const newMode = await app.getCurrentPreviewMode();
    expect(newMode).toBe('simple');
    
    // Verify preview content
    const { contentFound } = await app.verifyPreviewContent('simple');
    expect(contentFound).toBe(true);
    
    // Verify data persistence
    const dataPersisted = await app.verifyDataPersistence();
    expect(dataPersisted).toBe(true);
    
    console.log('✅ Full page to simple grid switch test completed');
  });

  test('should switch from simple grid to full page mode @critical', async ({ page }) => {
    const app = new ZikaAppPage(page);
    
    // Setup
    await app.goto();
    await app.setupCards();
    
    // First switch to simple grid
    await app.switchToSimpleGridMode();
    
    // Then switch to full page mode
    const switchSuccess = await app.switchToFullPageMode();
    expect(switchSuccess).toBe(true);
    
    // Verify mode changed
    const newMode = await app.getCurrentPreviewMode();
    expect(newMode).toBe('fullpage');
    
    // Verify preview content
    const { contentFound } = await app.verifyPreviewContent('fullpage');
    expect(contentFound).toBe(true);
    
    // Verify data persistence
    const dataPersisted = await app.verifyDataPersistence();
    expect(dataPersisted).toBe(true);
    
    console.log('✅ Simple grid to full page switch test completed');
  });

  test('should maintain preview content when switching modes multiple times', async ({ page }) => {
    const app = new ZikaAppPage(page);
    
    // Setup
    await app.goto();
    await app.setupCards();
    
    // Switch modes multiple times
    await app.switchToSimpleGridMode();
    await app.switchToFullPageMode();
    await app.switchToSimpleGridMode();
    
    // Verify final state
    const finalMode = await app.getCurrentPreviewMode();
    expect(finalMode).toBe('simple');
    
    // Verify content is still there
    const { contentFound } = await app.verifyPreviewContent('simple');
    expect(contentFound).toBe(true);
    
    // Verify data persistence
    const dataPersisted = await app.verifyDataPersistence();
    expect(dataPersisted).toBe(true);
    
    console.log('✅ Multiple mode switches test completed');
  });
});
