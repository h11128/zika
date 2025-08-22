import { test, expect, Page, Locator } from '@playwright/test';

interface CardSize {
  width: number;
  height: number;
}

interface SliderInfo {
  value: string;
  min: string;
  max: string;
}

class ZikaAppPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto() {
    await this.page.goto('/');
    await expect(this.page.getByText('Chinese Learning Cards Generator', { exact: true })).toBeVisible({ timeout: 30000 });
    console.log('✅ App loaded successfully');
  }

  async setupCards() {
    console.log('🔧 Setting up cards...');
    
    // Try template selection first
    try {
      const templateSelect = this.page.getByLabel('选择模板');
      await templateSelect.click();
      await this.page.waitForTimeout(500);
      await this.page.getByText('数字', { exact: true }).click();
      console.log('✅ Selected 数字 template');
      await this.page.waitForTimeout(2000);
    } catch (error) {
      console.log('⚠️ Template selection failed, using manual input');
      // Fallback to manual input
      const textInput = this.page.getByLabel('输入汉字（空格分隔）');
      await textInput.fill('一 二 三 四 五 六 七 八 九 十');
      console.log('✅ Filled manual input');
      await this.page.waitForTimeout(2000);
    }
  }

  async switchToSimpleGridMode() {
    console.log('🔄 Switching to simple grid mode...');

    try {
      // Wait for preview mode section to be visible
      await this.page.waitForTimeout(2000);

      // Try multiple methods to find the simple grid radio button
      let success = false;

      // Method 1: By role and text
      try {
        const radioGroup = this.page.getByRole('radiogroup', { name: '预览模式' });
        await radioGroup.waitFor({ state: 'visible', timeout: 10000 });

        const simpleGridRadio = radioGroup.getByRole('radio').filter({ hasText: '简单网格' });
        await simpleGridRadio.check({ timeout: 5000 });
        console.log('✅ Switched to simple grid mode via radiogroup');
        success = true;
      } catch (error: any) {
        console.log('⚠️ Method 1 failed:', error?.message || 'Unknown error');
      }

      // Method 2: Direct text search
      if (!success) {
        try {
          await this.page.getByText('🔲 简单网格', { exact: true }).click({ timeout: 5000 });
          console.log('✅ Switched to simple grid mode via text click');
          success = true;
        } catch (error: any) {
          console.log('⚠️ Method 2 failed:', error?.message || 'Unknown error');
        }
      }

      if (success) {
        await this.page.waitForTimeout(2000); // Wait for mode switch
      } else {
        console.log('⚠️ Could not switch to simple grid mode, using default');
      }
    } catch (error: any) {
      console.log('⚠️ Switch mode error:', error?.message || 'Unknown error');
    }
  }

  async waitForPreviewReady(): Promise<Locator> {
    console.log('⏳ Waiting for preview to be ready...');
    
    // Wait for either iframe or main frame content
    let frame: Page | any = this.page;
    
    // Check if content is in an iframe
    const frames = this.page.frames();
    console.log(`🔍 Checking ${frames.length} frames for preview content...`);

    for (let i = 0; i < frames.length; i++) {
      const f = frames[i];
      try {
        // Check for simple grid (simple grid mode)
        const simpleGrid = f.locator('.simple-grid');
        if (await simpleGrid.isVisible({ timeout: 1000 })) {
          console.log(`✅ Found simple-grid in iframe ${i}`);
          frame = f;
          break;
        }

        // Check for page grid (full page mode)
        const pageGrid = f.locator('.page-grid');
        if (await pageGrid.isVisible({ timeout: 1000 })) {
          console.log(`✅ Found page-grid in iframe ${i}`);
          frame = f;
          break;
        }

        // Check for any content with Chinese characters (fallback for full page mode)
        const chineseContent = f.locator('div:has-text("一"), div:has-text("二"), div:has-text("三")');
        if (await chineseContent.first().isVisible({ timeout: 1000 })) {
          console.log(`✅ Found Chinese content in iframe ${i}`);
          frame = f;
          break;
        }

      } catch (error) {
        console.log(`⚠️ Frame ${i} check failed: ${error.message}`);
      }
    }

    // If not found in iframe, check main frame
    if (frame === this.page) {
      try {
        // Check for various preview indicators
        const indicators = ['.simple-grid', '.page-grid', 'div:has-text("一")'];
        for (const indicator of indicators) {
          try {
            await this.page.locator(indicator).waitFor({ state: 'visible', timeout: 2000 });
            console.log(`✅ Found preview in main frame (${indicator})`);
            return frame;
          } catch {
            // Continue to next indicator
          }
        }
        console.log('⚠️ Preview not found, continuing anyway');
      } catch {
        console.log('⚠️ Preview not found, continuing anyway');
      }
    }
    
    return frame;
  }

  async disableAutoFill() {
    console.log('🔧 Disabling auto fill...');

    let success = false;

    // Method 1: Try button first (more reliable)
    try {
      const disableButton = this.page.getByRole('button', { name: /关闭自动填充/ });
      await disableButton.waitFor({ state: 'visible', timeout: 10000 });
      await disableButton.click({ timeout: 5000 });
      console.log('✅ Clicked disable auto fill button');
      success = true;
    } catch (error) {
      console.log('⚠️ Button method failed:', error.message);
    }

    // Method 2: Try checkbox in advanced options
    if (!success) {
      try {
        // First expand advanced options
        const advancedToggle = this.page.getByText('🔧 高级选项', { exact: true });
        await advancedToggle.click({ timeout: 5000 });
        await this.page.waitForTimeout(1000);

        // Then find and uncheck the checkbox
        const autoFillCheckbox = this.page.getByRole('checkbox').filter({ hasText: '自动填充' });
        if (await autoFillCheckbox.isChecked({ timeout: 5000 })) {
          await autoFillCheckbox.uncheck();
          console.log('✅ Unchecked auto fill checkbox in advanced options');
          success = true;
        }
      } catch (error) {
        console.log('⚠️ Advanced checkbox method failed:', error.message);
      }
    }

    if (!success) {
      console.log('⚠️ Could not disable auto fill, continuing anyway');
    }

    await this.page.waitForTimeout(2000); // Wait for UI update
  }

  async getSliderInfo(): Promise<SliderInfo> {
    // Try multiple ways to find the slider
    let slider: any;

    try {
      // Method 1: By role and text
      slider = this.page.getByRole('slider', { name: /卡片大小/ });
      await slider.waitFor({ state: 'visible', timeout: 2000 });
    } catch {
      try {
        // Method 2: By input type and nearby text
        slider = this.page.locator('input[type="range"]').filter({ hasText: '卡片大小' });
        await slider.waitFor({ state: 'visible', timeout: 2000 });
      } catch {
        // Method 3: Any range input
        slider = this.page.locator('input[type="range"]').first();
        await slider.waitFor({ state: 'visible', timeout: 2000 });
      }
    }

    const value = await slider.getAttribute('aria-valuenow') || await slider.getAttribute('value') || '0';
    const min = await slider.getAttribute('aria-valuemin') || await slider.getAttribute('min') || '0';
    const max = await slider.getAttribute('aria-valuemax') || await slider.getAttribute('max') || '10';

    return { value, min, max };
  }

  async adjustCardSizeSlider(): Promise<{ before: SliderInfo; after: SliderInfo }> {
    console.log('🎚️ Adjusting card size slider...');

    // Find slider using multiple strategies
    let slider: any;
    try {
      // Strategy 1: By role and name
      try {
        slider = this.page.getByRole('slider', { name: /卡片大小/ });
        await slider.waitFor({ state: 'visible', timeout: 3000 });
        console.log('✅ Found slider by role and name');
      } catch {
        // Strategy 2: By input type near text
        try {
          await this.page.getByText('卡片大小 (cm)', { exact: true }).waitFor({ state: 'visible', timeout: 3000 });
          slider = this.page.locator('input[type="range"]').first();
          await slider.waitFor({ state: 'visible', timeout: 3000 });
          console.log('✅ Found slider by input type');
        } catch {
          // Strategy 3: Any visible range input
          slider = this.page.locator('input[type="range"]').first();
          await slider.waitFor({ state: 'visible', timeout: 5000 });
          console.log('✅ Found slider as first range input');
        }
      }
    } catch (error) {
      console.log('❌ Could not find card size slider:', error.message);
      throw error;
    }

    const before = await this.getSliderInfo();
    console.log(`📊 Initial slider: ${before.value} (range: ${before.min}-${before.max})`);

    // Try multiple methods to adjust slider
    let success = false;

    // Method 1: Direct value setting (skip for Streamlit sliders which are divs)
    // Streamlit sliders are <div> elements, not <input>, so fill() won't work
    console.log('ℹ️ Skipping fill() method for Streamlit slider (div element)');

    // Method 1: Mouse drag (primary method for Streamlit sliders)
    try {
      const box = await slider.boundingBox();
      if (box) {
        const startX = box.x + box.width * 0.2;  // Start from left
        const endX = box.x + box.width * 0.95;   // Drag almost to the end
        const y = box.y + box.height / 2;

        await this.page.mouse.move(startX, y);
        await this.page.mouse.down();
        await this.page.mouse.move(endX, y, { steps: 20 }); // More steps for smoother drag
        await this.page.mouse.up();
        console.log('✅ Adjusted slider via mouse drag');
        success = true;
      }
    } catch (error) {
      console.log('⚠️ Mouse drag failed:', error.message);
    }

    // Method 2: Keyboard (fallback)
    if (!success) {
      try {
        await slider.focus();
        console.log('🎹 Using keyboard to adjust slider...');
        for (let i = 0; i < 20; i++) {
          await this.page.keyboard.press('ArrowRight');
          if (i % 5 === 0) {
            await this.page.waitForTimeout(50);
          }
        }
        console.log('✅ Adjusted slider via keyboard');
        success = true;
      } catch (error) {
        console.log('⚠️ Keyboard method failed:', error.message);
      }
    }

    if (!success) {
      console.log('❌ All slider adjustment methods failed');
      throw new Error('Could not adjust slider');
    }

    // Wait for Streamlit to process the change
    await this.page.waitForTimeout(5000);

    const after = await this.getSliderInfo();
    console.log(`📊 Final slider: ${after.value} (range: ${after.min}-${after.max})`);

    return { before, after };
  }

  async getCardSize(frame: Locator | Page): Promise<CardSize> {
    console.log('📏 Measuring card size...');

    // First, let's discover what elements actually exist
    try {
      const allDivs = await frame.locator('div').count();
      console.log(`🔍 Found ${allDivs} div elements in frame`);

      // Check for common class patterns
      const classPatterns = ['card', 'grid', 'simple', 'page'];
      for (const pattern of classPatterns) {
        const count = await frame.locator(`[class*="${pattern}"]`).count();
        if (count > 0) {
          console.log(`🔍 Found ${count} elements with class containing "${pattern}"`);
        }
      }
    } catch (error) {
      console.log(`⚠️ Element discovery failed: ${error.message}`);
    }

    // Try selectors in order of preference, with shorter timeouts
    const selectors = [
      '.simple-card',        // Simple grid cards
      '.page-card',          // Full page cards
      '.card',               // Generic cards
      '.simple-grid > div',  // Children of simple grid
      '.page-grid > div',    // Children of page grid
      // For full page mode: look for divs that contain Chinese characters
      'div:has-text("一")',  // Div containing Chinese character "一"
      'div:has-text("二")',  // Div containing Chinese character "二"
      'div:has-text("三")',  // Div containing Chinese character "三"
      // Generic patterns for card-like content
      'div:has-text("yī")',  // Div containing pinyin
      'div:has-text("one")', // Div containing English
      '[class*="card"]:not([class*="slider"]):not([class*="container"])', // Cards but not sliders/containers
      'div[style*="width"]:not([class*="slider"])', // Divs with width but not sliders
      'div[style*="grid"]'   // Any div with grid style
    ];

    for (const selector of selectors) {
      try {
        const card = frame.locator(selector).first();
        await card.waitFor({ state: 'visible', timeout: 1000 }); // Shorter timeout

        const box = await card.boundingBox();
        if (box && box.width > 0 && box.height > 0) {
          // Additional validation: check if this looks like a real card
          const styles = await card.evaluate((el) => {
            const computed = getComputedStyle(el);
            const parent = el.parentElement;
            const text = el.textContent && el.textContent.trim();
            return {
              className: el.className,
              width: computed.width,
              height: computed.height,
              gridTemplateColumns: parent ? getComputedStyle(parent).gridTemplateColumns : 'none',
              hasCardContent: text && text.length > 0,
              textContent: text,
              isSliderContainer: el.className.includes('slider') || el.className.includes('container'),
              isReasonableSize: parseFloat(computed.width) > 50 && parseFloat(computed.height) > 50
            };
          });

          // Skip if this looks like a slider container or other UI element
          if (styles.isSliderContainer && !styles.hasCardContent) {
            console.log(`⚠️ Skipping ${selector}: looks like UI container, not card content`);
            continue;
          }

          // Skip if the element is too small to be a card (likely a border or line)
          if (!styles.isReasonableSize) {
            console.log(`⚠️ Skipping ${selector}: too small (${styles.width} x ${styles.height})`);
            continue;
          }

          console.log(`✅ Found card with ${selector}: ${box.width.toFixed(1)}x${box.height.toFixed(1)}`);
          console.log(`🎨 Card styles:`, styles);

          return { width: box.width, height: box.height };
        }
      } catch (error) {
        // Don't log every timeout, only unexpected errors
        if (!error.message.includes('Timeout')) {
          console.log(`⚠️ Selector ${selector} failed:`, error.message);
        }
      }
    }

    throw new Error('No card found with any selector');
  }
}

test.describe('Card Size Adjustment', () => {
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

  test('should update preview when card size is manually adjusted in simple grid mode', async ({ page }) => {
    const app = new ZikaAppPage(page);

    // Setup
    await app.goto();
    await app.setupCards();
    await app.switchToSimpleGridMode();

    // Wait for initial preview
    let frame = await app.waitForPreviewReady();

    // Disable auto fill
    await app.disableAutoFill();

    // Re-get frame after auto fill disable (frame may have been recreated)
    console.log('🔄 Re-acquiring frame after auto fill disable...');
    frame = await app.waitForPreviewReady();

    // Measure initial card size
    const initialSize = await app.getCardSize(frame);
    console.log(`📐 Initial card size: ${initialSize.width.toFixed(1)}x${initialSize.height.toFixed(1)}`);

    // Adjust slider
    const sliderChange = await app.adjustCardSizeSlider();

    // Verify slider actually changed
    expect(sliderChange.after.value).not.toBe(sliderChange.before.value);
    console.log(`✅ Slider changed from ${sliderChange.before.value} to ${sliderChange.after.value}`);

    // Wait for preview to update and re-get frame again
    await page.waitForTimeout(3000);
    console.log('🔄 Re-acquiring frame after slider adjustment...');
    frame = await app.waitForPreviewReady();

    // Measure final card size
    const finalSize = await app.getCardSize(frame);
    console.log(`📐 Final card size: ${finalSize.width.toFixed(1)}x${finalSize.height.toFixed(1)}`);

    // Verify card size changed
    const sizeChanged = Math.abs(finalSize.width - initialSize.width) > 5 ||
                       Math.abs(finalSize.height - initialSize.height) > 5;

    expect(sizeChanged).toBe(true);
    console.log(`✅ Card size changed successfully in simple grid mode!`);
  });

  test('should update preview when card size is manually adjusted in full page mode', async ({ page }) => {
    const app = new ZikaAppPage(page);

    // Setup
    await app.goto();
    await app.setupCards();

    // Use full page mode (default)
    console.log('📄 Using full page mode...');

    // Wait for initial preview
    let frame = await app.waitForPreviewReady();

    // Disable auto fill
    await app.disableAutoFill();

    // Re-get frame after auto fill disable
    console.log('🔄 Re-acquiring frame after auto fill disable...');
    frame = await app.waitForPreviewReady();

    // Measure initial card size
    const initialSize = await app.getCardSize(frame);
    console.log(`📐 Initial card size: ${initialSize.width.toFixed(1)}x${initialSize.height.toFixed(1)}`);

    // Adjust slider
    const sliderChange = await app.adjustCardSizeSlider();

    // Verify slider actually changed
    expect(sliderChange.after.value).not.toBe(sliderChange.before.value);
    console.log(`✅ Slider changed from ${sliderChange.before.value} to ${sliderChange.after.value}`);

    // Wait for preview to update and re-get frame again
    await page.waitForTimeout(3000);
    console.log('🔄 Re-acquiring frame after slider adjustment...');
    frame = await app.waitForPreviewReady();

    // Measure final card size
    const finalSize = await app.getCardSize(frame);
    console.log(`📐 Final card size: ${finalSize.width.toFixed(1)}x${finalSize.height.toFixed(1)}`);

    // Verify card size changed (use smaller threshold for full page mode)
    const widthChange = Math.abs(finalSize.width - initialSize.width);
    const heightChange = Math.abs(finalSize.height - initialSize.height);
    const sizeChanged = widthChange > 2 || heightChange > 2;

    console.log(`📊 Size changes: width ${widthChange.toFixed(1)}px, height ${heightChange.toFixed(1)}px`);

    expect(sizeChanged).toBe(true);
    console.log(`✅ Card size changed successfully in full page mode!`);
  });
});
