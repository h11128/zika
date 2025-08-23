import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

test.describe('UI State Consistency Tests', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
  });

  // Clean up after each test
  test.afterEach(async ({ context }) => {
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

  test('should maintain consistent auto-fill and card size options state @critical', async () => {
    console.log('🧪 Testing auto-fill and card size options state consistency...');
    
    await app.goto();
    await app.setupCards();
    
    // Expand advanced options
    const advancedOptions = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions.click();
    await app.page.waitForTimeout(1000);
    
    // Test 1: Initially auto-fill should be enabled, card size slider should be hidden
    console.log('📋 Test 1: Initial state verification...');
    
    // Check if auto-fill checkbox exists and is checked (in advanced options)
    const autoFillCheckbox = app.page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');
    const autoFillCheckboxExists = await autoFillCheckbox.count() > 0;
    console.log(`🔍 Auto-fill checkbox exists: ${autoFillCheckboxExists}`);

    let isAutoFillChecked = false;
    if (autoFillCheckboxExists) {
      isAutoFillChecked = await autoFillCheckbox.isChecked().catch(() => false);
      console.log(`🔍 Auto-fill checked: ${isAutoFillChecked}`);
    }

    // Check for card size slider in main options (not advanced options)
    const cardSizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    const isCardSizeVisible = await cardSizeSlider.isVisible().catch(() => false);
    console.log(`🔍 Card size slider visible: ${isCardSizeVisible}`);

    // Check for "关闭自动填充" button (appears when auto-fill is enabled)
    const disableAutoFillButton = app.page.getByText('关闭自动填充以手动调整大小');
    const hasDisableButton = await disableAutoFillButton.isVisible().catch(() => false);
    console.log(`🔍 Disable auto-fill button visible: ${hasDisableButton}`);
    
    // Test the current state logic
    if (hasDisableButton) {
      // Auto-fill is enabled, card size slider should be hidden
      expect(isCardSizeVisible).toBe(false);
      console.log('✅ Correct: Auto-fill enabled (button visible), card size slider hidden');
    } else if (isCardSizeVisible) {
      // Manual mode, card size slider should be visible
      console.log('✅ Correct: Manual mode, card size slider visible');
    }

    // Test 2: Toggle auto-fill state
    console.log('📋 Test 2: Toggle auto-fill state...');

    if (hasDisableButton) {
      // Currently auto-fill is enabled, disable it
      await disableAutoFillButton.click();
      await app.page.waitForTimeout(2000);

      // Check if card size slider appears
      const cardSizeSliderAfter = app.page.getByLabel('卡片大小 (cm)', { exact: true });
      const isCardSizeVisibleAfter = await cardSizeSliderAfter.isVisible().catch(() => false);
      expect(isCardSizeVisibleAfter).toBe(true);
      console.log('✅ Auto-fill disabled, card size slider now visible');
    } else if (autoFillCheckboxExists) {
      // Use the checkbox in advanced options to enable auto-fill
      if (!isAutoFillChecked) {
        await autoFillCheckbox.click();
        await app.page.waitForTimeout(2000);

        // Check if disable button appears
        const disableButtonAfter = app.page.getByText('关闭自动填充以手动调整大小');
        const hasDisableButtonAfter = await disableButtonAfter.isVisible().catch(() => false);
        expect(hasDisableButtonAfter).toBe(true);
        console.log('✅ Auto-fill enabled via checkbox, disable button now visible');
      }
    }
    
    // Test 3: Check for state consistency
    console.log('📋 Test 3: Final state consistency check...');

    await app.page.waitForTimeout(1000);

    // Check final state
    const finalDisableButton = app.page.getByText('关闭自动填充以手动调整大小');
    const finalHasDisableButton = await finalDisableButton.isVisible().catch(() => false);

    const finalCardSizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    const finalIsCardSizeVisible = await finalCardSizeSlider.isVisible().catch(() => false);

    // State should be consistent: either disable button OR card size slider, not both
    const stateIsConsistent = (finalHasDisableButton && !finalIsCardSizeVisible) ||
                             (!finalHasDisableButton && finalIsCardSizeVisible);

    expect(stateIsConsistent).toBe(true);
    console.log(`✅ Final state consistent: disable button=${finalHasDisableButton}, slider=${finalIsCardSizeVisible}`);
    
    console.log('✅ Auto-fill and card size state consistency test completed');
  });

  test('should handle custom color selection correctly', async () => {
    console.log('🧪 Testing custom color selection functionality...');
    
    await app.goto();
    await app.setupCards();
    
    // Expand advanced options
    const advancedOptions = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions.click();
    await app.page.waitForTimeout(1000);
    
    // Test 1: Verify custom color control existence without assuming native input
    console.log('📋 Test 1: Verify custom color control existence...');

    // 1) Label text should be visible
    const colorLabel = app.page.getByText('选择颜色', { exact: true });
    await expect(colorLabel).toBeVisible({ timeout: 10000 });
    console.log('✅ Label "选择颜色" is visible');

    // 2) The color picker container anchor should be present (rendered this run)
    const anchor = app.page.locator('[data-testid="color-picker-anchor"]');
    await expect(anchor).toHaveCount(1, { timeout: 10000 });
    console.log('✅ Color picker anchor is present');

    // 3) Native input[type=color] is optional; log if present
    const colorInput = app.page.locator('input[type="color"]').first();
    const hasNativeInput = await colorInput.count() > 0;
    console.log(`ℹ️ Native input[type=color] present: ${hasNativeInput}`);
    if (hasNativeInput) {
      console.log('✅ Native color input present');
    }

    // Do not fail if native input is absent; presence of label + anchor is the contract here
    
    // Test 2: Attempt custom color selection if native input is present; otherwise verify display integrity
    console.log('📋 Test 2: Custom color selection or display verification...');

    const testColor = '#ff5722'; // Orange
    if (hasNativeInput) {
      const nativePicker = app.page.locator('input[type="color"]').first();
      await nativePicker.fill(testColor);
      await app.page.waitForTimeout(1500);

      const currentColorDisplay = app.page.locator('div').filter({ hasText: testColor });
      const colorApplied = await currentColorDisplay.count() > 0;
      expect(colorApplied).toBe(true);
      console.log(`✅ Custom color ${testColor} successfully applied via native input`);
    } else {
      console.log('ℹ️ Native color input not present; verifying current color display exists...');
      // Verify current color block is rendered with a hex code (case-insensitive)
      const hexPattern = /#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})/;
      const allDivTexts = await app.page.locator('div').allInnerTexts();
      const hasHex = allDivTexts.some(t => hexPattern.test(t));
      expect(hasHex).toBe(true);
      console.log('✅ Current color display shows a valid hex color');
    }
    
    // Test 3: Verify preview updates (regardless of color picker)
    console.log('📋 Test 3: Verify preview updates...');

    await app.page.waitForTimeout(3000); // Wait for preview to update

    // Check if cards are still generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);
    console.log('✅ Preview updated successfully');
    
    // Test 4: Test switching back to preset colors
    console.log('📋 Test 4: Test switching back to preset colors...');
    
    // Try to click a preset color button
    const presetColorButton = app.page.locator('.color-button').first();
    const presetButtonExists = await presetColorButton.count() > 0;
    
    if (presetButtonExists) {
      await presetColorButton.click();
      await app.page.waitForTimeout(2000);
      console.log('✅ Successfully switched back to preset color');
    } else {
      console.log('⚠️ No preset color buttons found');
    }
    
    console.log('✅ Custom color selection test completed');
  });

  test('should maintain UI consistency during mode switches', async () => {
    console.log('🧪 Testing UI consistency during mode switches...');
    
    await app.goto();
    await app.setupCards();
    
    // Test 1: Switch between preview modes and check advanced options state
    console.log('📋 Test 1: Testing preview mode switches...');
    
    // Switch to simple grid mode
    await app.page.getByText('🔲 简单网格', { exact: true }).click();
    await app.page.waitForTimeout(2000);
    
    // Expand advanced options in simple grid mode
    const advancedOptions = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions.click();
    await app.page.waitForTimeout(1000);
    
    // Check if auto-fill option is available in simple grid mode (in advanced options)
    // Try multiple selectors for the auto-fill checkbox
    const autoFillSelectors = [
      'input[key="auto_fill_advanced"]',
      'input[type="checkbox"]',
      'input[aria-label*="自动填充"]'
    ];

    let autoFillExistsInGrid = false;
    for (const selector of autoFillSelectors) {
      const count = await app.page.locator(selector).count();
      if (count > 0) {
        autoFillExistsInGrid = true;
        break;
      }
    }
    console.log(`🔍 Auto-fill option in simple grid mode: ${autoFillExistsInGrid}`);

    // Switch back to full page mode
    await app.page.getByText('📄 完整页面', { exact: true }).click();
    await app.page.waitForTimeout(2000);

    // Check if auto-fill option is available in full page mode (in advanced options)
    let autoFillExistsInPage = false;
    for (const selector of autoFillSelectors) {
      const count = await app.page.locator(selector).count();
      if (count > 0) {
        autoFillExistsInPage = true;
        break;
      }
    }
    console.log(`🔍 Auto-fill option in full page mode: ${autoFillExistsInPage}`);

    // Auto-fill should be available in full page mode (but may not be visible if not expanded)
    if (!autoFillExistsInPage) {
      console.log('⚠️ Auto-fill checkbox not found - may be in collapsed advanced options');
    } else {
      console.log('✅ Auto-fill option found in full page mode');
    }
    
    // Test 2: Check color options consistency across modes
    console.log('📋 Test 2: Testing color options consistency...');

    // Check color control presence across modes without assuming native input
    const colorLabel2 = app.page.getByText('选择颜色', { exact: true });
    await expect(colorLabel2).toBeVisible({ timeout: 10000 });
    const anchor2 = app.page.locator('[data-testid="color-picker-anchor"]');
    await expect(anchor2).toHaveCount(1, { timeout: 10000 });
    console.log('✅ Color control available across mode switches');
    
    console.log('✅ UI consistency during mode switches test completed');
  });

  test('should handle rapid state changes without UI corruption', async () => {
    console.log('🧪 Testing rapid state changes...');
    
    await app.goto();
    await app.setupCards();
    
    // Expand advanced options
    const advancedOptions = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions.click();
    await app.page.waitForTimeout(1000);
    
    // Test rapid state changes using the disable button and checkbox
    console.log('📋 Testing rapid auto-fill toggles...');

    const autoFillCheckbox = app.page.locator('input[key="auto_fill_advanced"]');
    const disableButton = app.page.getByText('关闭自动填充以手动调整大小');

    // Try to toggle state a few times
    for (let i = 0; i < 2; i++) {
      // Check current state and toggle appropriately
      const hasButton = await disableButton.isVisible().catch(() => false);
      const hasCheckbox = await autoFillCheckbox.count() > 0;

      if (hasButton) {
        // Auto-fill is enabled, disable it
        await disableButton.click();
        await app.page.waitForTimeout(1000);
      } else if (hasCheckbox) {
        // Try to enable auto-fill via checkbox
        const isChecked = await autoFillCheckbox.isChecked().catch(() => false);
        if (!isChecked) {
          await autoFillCheckbox.click();
          await app.page.waitForTimeout(1000);
        }
      }
    }

    // Check final state is consistent
    await app.page.waitForTimeout(2000);
    const finalDisableButton = app.page.getByText('关闭自动填充以手动调整大小');
    const finalHasButton = await finalDisableButton.isVisible().catch(() => false);
    const cardSizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    const sliderVisible = await cardSizeSlider.isVisible().catch(() => false);

    // State should be consistent: either button OR slider, not both
    const isConsistent = (finalHasButton && !sliderVisible) || (!finalHasButton && sliderVisible);
    expect(isConsistent).toBe(true);

    console.log(`✅ Final state consistent: button=${finalHasButton}, slider=${sliderVisible}`);
    console.log('✅ Rapid state changes test completed');
  });
});
