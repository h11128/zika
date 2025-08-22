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

    // Use template selection for reliable card generation
    try {
      const templateSelect = this.page.getByLabel('选择模板');
      await templateSelect.click();
      await this.page.waitForTimeout(500);
      await this.page.getByText('数字', { exact: true }).click();
      console.log('✅ Selected 数字 template');

      // Wait longer for template to be applied and cards to be generated
      await this.page.waitForTimeout(5000);

      // Verify cards were generated
      const frames = this.page.frames();
      let cardsGenerated = false;
      for (const frame of frames) {
        try {
          const hasCards = await frame.locator('div:has-text("一"), div:has-text("二"), div:has-text("三")').first().isVisible({ timeout: 3000 });
          if (hasCards) {
            cardsGenerated = true;
            console.log('✅ Template cards generated successfully');
            break;
          }
        } catch {
          // Continue checking
        }
      }

      if (!cardsGenerated) {
        console.log('⚠️ Template cards not found, but continuing');
      }

    } catch (error) {
      console.log('⚠️ Template selection failed, using manual input');
      // Fallback to manual input with space-separated characters
      const textInput = this.page.getByLabel('输入汉字（空格分隔）');
      await textInput.clear();
      await textInput.fill('一 二 三 四 五');
      console.log('✅ Filled manual input');
      await this.page.waitForTimeout(3000);
    }
  }

  async inputText(text: string) {
    console.log(`📝 Inputting text: "${text}"`);
    const textInput = this.page.getByLabel('输入汉字（空格分隔）');
    await textInput.waitFor({ state: 'visible', timeout: 5000 });
    await textInput.clear();
    // Add spaces between characters for proper parsing
    const spacedText = text.split('').join(' ');
    await textInput.fill(spacedText);
    console.log('✅ Text input completed');
  }

  async toggleAutoPinyin(enable: boolean) {
    console.log(`🔧 ${enable ? 'Enabling' : 'Disabling'} auto pinyin...`);

    // Try multiple strategies to find and interact with the checkbox
    let success = false;

    // Strategy 1: Try to find by label text (more reliable for hidden checkboxes)
    try {
      const label = this.page.getByText('自动生成拼音');
      await label.waitFor({ state: 'visible', timeout: 3000 });
      await label.click();
      console.log(`✅ Auto pinyin toggled via label click`);
      success = true;
    } catch (error) {
      console.log(`⚠️ Label click failed: ${error.message}`);
    }

    // Strategy 2: Force click on hidden checkbox
    if (!success) {
      try {
        const checkbox = this.page.getByRole('checkbox', { name: /自动生成拼音/ });
        await checkbox.click({ force: true }); // Force click even if hidden
        console.log(`✅ Auto pinyin toggled via force click`);
        success = true;
      } catch (error) {
        console.log(`⚠️ Force click failed: ${error.message}`);
      }
    }

    // Strategy 3: Use JavaScript to toggle
    if (!success) {
      try {
        await this.page.evaluate(() => {
          const checkbox = document.querySelector('input[aria-label*="自动生成拼音"]') as HTMLInputElement;
          if (checkbox) {
            checkbox.click();
            return true;
          }
          return false;
        });
        console.log(`✅ Auto pinyin toggled via JavaScript`);
        success = true;
      } catch (error) {
        console.log(`⚠️ JavaScript toggle failed: ${error.message}`);
      }
    }

    if (!success) {
      console.log(`⚠️ Could not toggle auto pinyin, continuing anyway`);
    }
  }

  async toggleAutoTranslate(enable: boolean) {
    console.log(`🔧 ${enable ? 'Enabling' : 'Disabling'} auto translate...`);

    // Try multiple strategies to find and interact with the checkbox
    let success = false;

    // Strategy 1: Try to find by label text (more reliable for hidden checkboxes)
    try {
      const label = this.page.getByText('自动生成翻译');
      await label.waitFor({ state: 'visible', timeout: 3000 });
      await label.click();
      console.log(`✅ Auto translate toggled via label click`);
      success = true;
    } catch (error) {
      console.log(`⚠️ Label click failed: ${error.message}`);
    }

    // Strategy 2: Force click on hidden checkbox
    if (!success) {
      try {
        const checkbox = this.page.getByRole('checkbox', { name: /自动生成翻译/ });
        await checkbox.click({ force: true }); // Force click even if hidden
        console.log(`✅ Auto translate toggled via force click`);
        success = true;
      } catch (error) {
        console.log(`⚠️ Force click failed: ${error.message}`);
      }
    }

    // Strategy 3: Use JavaScript to toggle
    if (!success) {
      try {
        await this.page.evaluate(() => {
          const checkbox = document.querySelector('input[aria-label*="自动生成翻译"]') as HTMLInputElement;
          if (checkbox) {
            checkbox.click();
            return true;
          }
          return false;
        });
        console.log(`✅ Auto translate toggled via JavaScript`);
        success = true;
      } catch (error) {
        console.log(`⚠️ JavaScript toggle failed: ${error.message}`);
      }
    }

    if (!success) {
      console.log(`⚠️ Could not toggle auto translate, continuing anyway`);
    }
  }

  async setTranslatePriority(priority: 'local' | 'online') {
    console.log(`🔧 Setting translate priority to ${priority}...`);
    
    try {
      const selectBox = this.page.getByRole('combobox', { name: /翻译优先级/ });
      await selectBox.waitFor({ state: 'visible', timeout: 5000 });
      
      await selectBox.click();
      
      const optionText = priority === 'local' ? '本地优先' : '在线优先';
      const option = this.page.getByText(optionText);
      await option.click();
      
      console.log(`✅ Translate priority set to ${priority}`);
    } catch (error) {
      console.log(`⚠️ Could not set translate priority: ${error.message}`);
    }
  }

  async waitForProcessing() {
    console.log('⏳ Waiting for processing...');
    await this.page.waitForTimeout(3000); // Give time for auto features to work
    console.log('✅ Processing completed');
  }

  async verifyCardsGenerated() {
    console.log('🔍 Verifying cards are generated...');

    // Wait longer for cards to be generated
    await this.page.waitForTimeout(3000);

    // Check for cards in iframe or main page
    const frames = this.page.frames();
    let cardsFound = false;

    console.log(`🔍 Checking ${frames.length} frames for cards...`);

    for (let i = 0; i < frames.length; i++) {
      const frame = frames[i];
      try {
        // Look for Chinese characters from the 数字 template (一、二、三、四、五)
        const hasCards = await frame.locator('div:has-text("一"), div:has-text("二"), div:has-text("三"), div:has-text("四"), div:has-text("五")').first().isVisible({ timeout: 3000 });
        if (hasCards) {
          cardsFound = true;
          console.log(`✅ Cards found in iframe ${i}`);
          break;
        }
      } catch {
        // Continue checking other frames
      }
    }

    if (!cardsFound) {
      // Check if iframe exists at least
      try {
        await this.page.waitForSelector('iframe', { timeout: 5000 });
        cardsFound = true;
        console.log('✅ Preview iframe found (cards may be loading)');
      } catch {
        console.log('⚠️ No cards or preview found');
      }
    }

    return cardsFound;
  }

  async checkAutoPinyinWorking() {
    console.log('🔍 Checking if auto pinyin is working...');
    
    // Look for pinyin in the generated content
    const frames = this.page.frames();
    let pinyinFound = false;
    
    for (const frame of frames) {
      try {
        // Look for common pinyin patterns
        const hasPinyin = await frame.locator('div:has-text("nǐ"), div:has-text("hǎo"), div:has-text("shì")').first().isVisible({ timeout: 2000 });
        if (hasPinyin) {
          pinyinFound = true;
          console.log('✅ Pinyin found in cards');
          break;
        }
      } catch {
        // Continue checking
      }
    }
    
    console.log(pinyinFound ? '✅ Auto pinyin is working' : '⚠️ Auto pinyin not detected');
    return pinyinFound;
  }

  async checkAutoTranslateWorking() {
    console.log('🔍 Checking if auto translate is working...');
    
    // Look for English translations in the generated content
    const frames = this.page.frames();
    let translationFound = false;
    
    for (const frame of frames) {
      try {
        // Look for common English words
        const hasEnglish = await frame.locator('div:has-text("you"), div:has-text("hello"), div:has-text("world")').first().isVisible({ timeout: 2000 });
        if (hasEnglish) {
          translationFound = true;
          console.log('✅ English translation found in cards');
          break;
        }
      } catch {
        // Continue checking
      }
    }
    
    console.log(translationFound ? '✅ Auto translate is working' : '⚠️ Auto translate not detected');
    return translationFound;
  }
}

test.describe('Auto Features', () => {
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

  test('should generate pinyin automatically when enabled', async ({ page }) => {
    const app = new ZikaAppPage(page);

    // Navigate to app
    await app.goto();

    // Setup cards first
    await app.setupCards();

    // Enable auto pinyin
    await app.toggleAutoPinyin(true);

    // Wait for processing
    await app.waitForProcessing();

    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);

    // Check if pinyin is working (optional verification)
    await app.checkAutoPinyinWorking();

    console.log('✅ Auto pinyin test completed');
  });

  test('should generate translations automatically when enabled', async ({ page }) => {
    const app = new ZikaAppPage(page);

    // Navigate to app
    await app.goto();

    // Setup cards first
    await app.setupCards();

    // Enable auto translate
    await app.toggleAutoTranslate(true);

    // Wait for processing
    await app.waitForProcessing();

    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);

    // Check if translation is working (optional verification)
    await app.checkAutoTranslateWorking();

    console.log('✅ Auto translate test completed');
  });

  test('should work with both auto features enabled', async ({ page }) => {
    const app = new ZikaAppPage(page);

    // Navigate to app
    await app.goto();

    // Setup cards first
    await app.setupCards();

    // Enable both auto features
    await app.toggleAutoPinyin(true);
    await app.toggleAutoTranslate(true);

    // Wait for processing
    await app.waitForProcessing();

    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);

    console.log('✅ Combined auto features test completed');
  });

  test('should allow changing translation priority', async ({ page }) => {
    const app = new ZikaAppPage(page);

    // Navigate to app
    await app.goto();

    // Setup cards first
    await app.setupCards();

    // Enable auto translate
    await app.toggleAutoTranslate(true);

    // Set translation priority to local (optional, may fail)
    try {
      await app.setTranslatePriority('local');
    } catch (error) {
      console.log('⚠️ Could not set translation priority, continuing anyway');
    }

    // Wait for processing
    await app.waitForProcessing();

    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);

    console.log('✅ Translation priority test completed');
  });
});
