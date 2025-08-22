import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

test.describe('Complex State Transition Tests', () => {
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

  test('should handle complete auto-fill state cycle correctly @critical', async () => {
    console.log('🧪 Testing complete auto-fill state cycle...');
    
    await app.goto();
    await app.setupCards();
    
    // Expand advanced options
    const advancedOptions = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions.click();
    await app.page.waitForTimeout(1000);
    
    // Step 1: Verify initial state (auto-fill enabled)
    console.log('📋 Step 1: Verify initial auto-fill enabled state...');
    
    const disableAutoFillButton = app.page.getByText('关闭自动填充以手动调整大小');
    const initialHasButton = await disableAutoFillButton.isVisible().catch(() => false);
    
    const cardSizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    const initialSliderVisible = await cardSizeSlider.isVisible().catch(() => false);
    
    console.log(`🔍 Initial state: button=${initialHasButton}, slider=${initialSliderVisible}`);
    expect(initialHasButton).toBe(true);
    expect(initialSliderVisible).toBe(false);
    
    // Step 2: Disable auto-fill using the button
    console.log('📋 Step 2: Disable auto-fill using button...');
    
    await disableAutoFillButton.click();
    await app.page.waitForTimeout(2000);
    
    // Verify auto-fill is disabled
    const afterDisableButton = await disableAutoFillButton.isVisible().catch(() => false);
    const afterDisableSlider = await cardSizeSlider.isVisible().catch(() => false);
    
    console.log(`🔍 After disable: button=${afterDisableButton}, slider=${afterDisableSlider}`);
    expect(afterDisableButton).toBe(false);
    expect(afterDisableSlider).toBe(true);
    
    // Step 3: Adjust card size (this is the critical step that might cause issues)
    console.log('📋 Step 3: Adjust card size...');
    
    // Interact with the slider (click and drag)
    await cardSizeSlider.click();
    await app.page.waitForTimeout(1000);

    // Use keyboard to change the value
    await cardSizeSlider.press('ArrowRight');
    await cardSizeSlider.press('ArrowRight');
    await app.page.waitForTimeout(2000);
    
    // Verify the slider was interacted with
    console.log(`✅ Card size slider was adjusted`);
    
    // Step 4: Re-enable auto-fill using the checkbox in advanced options
    console.log('📋 Step 4: Re-enable auto-fill using advanced options checkbox...');

    // The disable button triggers a rerun which may collapse the expander; open it again
    const advancedOptions2 = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions2.click();

    const autoFillCheckbox = app.page.getByLabel('自动填充（按边距与间距自动计算卡片大小）');
    const checkboxExists = await autoFillCheckbox.count() > 0;

    if (checkboxExists) {
      const isChecked = await autoFillCheckbox.isChecked().catch(() => false);
      console.log(`🔍 Checkbox checked before click: ${isChecked}`);

      if (!isChecked) {
        await autoFillCheckbox.scrollIntoViewIfNeeded().catch(() => {});
        // Fallback: click the visible label text if the control is not visible/clickable
        const labelText = app.page.getByText('自动填充（按边距与间距自动计算卡片大小）', { exact: true });
        const labelVisible = await labelText.isVisible().catch(() => false);
        if (labelVisible) {
          await labelText.click();
        } else {
          await autoFillCheckbox.click({ timeout: 5000 });
        }
        await app.page.waitForTimeout(3000); // Wait longer for state to update
      }
    }
    
    // Step 5: Verify final state (THIS IS WHERE THE BUG SHOULD BE DETECTED)
    console.log('📋 Step 5: Verify final state after re-enabling auto-fill...');
    
    await app.page.waitForTimeout(2000);
    
    const finalButton = await disableAutoFillButton.isVisible().catch(() => false);
    const finalSlider = await cardSizeSlider.isVisible().catch(() => false);
    
    console.log(`🔍 Final state: button=${finalButton}, slider=${finalSlider}`);
    
    // This should pass if the bug is fixed, fail if the bug exists
    expect(finalButton).toBe(true);
    expect(finalSlider).toBe(false);
    
    if (finalButton && !finalSlider) {
      console.log('✅ Auto-fill state cycle completed correctly');
    } else {
      console.log('❌ BUG DETECTED: Auto-fill state cycle failed');
      console.log('   Expected: button=true, slider=false');
      console.log(`   Actual: button=${finalButton}, slider=${finalSlider}`);
    }
  });

  test('should handle complete color selection cycle correctly', async () => {
    console.log('🧪 Testing complete color selection cycle...');
    
    await app.goto();
    await app.setupCards();
    
    // Expand advanced options
    const advancedOptions = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions.click();
    await app.page.waitForTimeout(1000);
    
    // Step 1: Record initial color
    console.log('📋 Step 1: Record initial color...');
    
    const initialColorDisplay = app.page.locator('div').filter({ hasText: /#[0-9a-fA-F]{6}/ });
    const initialColorText = await initialColorDisplay.textContent().catch(() => '');
    console.log(`🔍 Initial color: ${initialColorText}`);
    
    // Step 2: Select custom color (if picker exists)
    console.log('📋 Step 2: Select custom color...');
    
    const colorPicker = app.page.locator('input[type="color"]').first();
    const pickerExists = await colorPicker.count() > 0;
    
    let customColorWorked = false;
    if (pickerExists) {
      const testColor1 = '#ff5722'; // Orange
      await colorPicker.fill(testColor1);
      await app.page.waitForTimeout(3000);
      
      // Verify custom color was applied
      const afterCustomColor = app.page.locator('div').filter({ hasText: testColor1 });
      const customColorApplied = await afterCustomColor.count() > 0;
      customColorWorked = customColorApplied;
      console.log(`🔍 Custom color ${testColor1} applied: ${customColorApplied}`);
    } else {
      console.log('⚠️ Color picker not found, skipping custom color test');
    }
    
    // Step 3: Select a preset color
    console.log('📋 Step 3: Select preset color...');
    
    // Look for preset color buttons in iframe
    const iframe = app.page.frameLocator('iframe').first();
    const presetColorButton = iframe.locator('.color-button').first();
    const presetButtonExists = await presetColorButton.count() > 0;
    
    if (presetButtonExists) {
      await presetColorButton.click();
      await app.page.waitForTimeout(3000);
      console.log('✅ Preset color selected');
    } else {
      console.log('⚠️ Preset color buttons not found');
    }
    
    // Step 4: Try to select custom color again (THIS IS WHERE THE BUG SHOULD BE DETECTED)
    console.log('📋 Step 4: Try custom color again after preset selection...');
    
    if (pickerExists && customColorWorked) {
      const testColor2 = '#4caf50'; // Green
      await colorPicker.fill(testColor2);
      await app.page.waitForTimeout(3000);
      
      // Verify custom color works again
      const afterSecondCustom = app.page.locator('div').filter({ hasText: testColor2 });
      const secondCustomColorApplied = await afterSecondCustom.count() > 0;
      
      console.log(`🔍 Second custom color ${testColor2} applied: ${secondCustomColorApplied}`);
      
      if (secondCustomColorApplied) {
        console.log('✅ Color selection cycle completed correctly');
      } else {
        console.log('❌ BUG DETECTED: Custom color selection failed after preset selection');
        console.log('   Custom color picker became non-functional after selecting preset color');
      }
      
      // This assertion will catch the bug
      expect(secondCustomColorApplied).toBe(true);
    } else {
      console.log('⚠️ Skipping second custom color test - picker not available');
    }
  });

  test('should maintain state consistency during rapid complex transitions', async () => {
    console.log('🧪 Testing rapid complex state transitions...');
    
    await app.goto();
    await app.setupCards();
    
    // Expand advanced options
    const advancedOptions = app.page.getByText('🔧 高级选项', { exact: true });
    await advancedOptions.click();
    await app.page.waitForTimeout(1000);
    
    // Perform rapid state changes
    console.log('📋 Performing rapid state transitions...');
    
    const disableButton = app.page.getByText('关闭自动填充以手动调整大小');
    const cardSizeSlider = app.page.getByLabel('卡片大小 (cm)', { exact: true });
    const autoFillCheckbox = app.page.locator('input[type="checkbox"]').first();
    
    // Rapid sequence: disable → adjust → enable → disable → enable
    for (let i = 0; i < 2; i++) {
      console.log(`🔄 Rapid transition cycle ${i + 1}...`);
      
      // Disable auto-fill
      const hasButton = await disableButton.isVisible().catch(() => false);
      if (hasButton) {
        await disableButton.click();
        await app.page.waitForTimeout(1000);
      }
      
      // Adjust slider if visible
      const sliderVisible = await cardSizeSlider.isVisible().catch(() => false);
      if (sliderVisible) {
        await cardSizeSlider.click();
        await cardSizeSlider.press('ArrowRight');
        await app.page.waitForTimeout(500);
      }
      
      // Re-enable auto-fill
      const checkboxExists = await autoFillCheckbox.count() > 0;
      if (checkboxExists) {
        const isChecked = await autoFillCheckbox.isChecked();
        if (!isChecked) {
          await autoFillCheckbox.click();
          await app.page.waitForTimeout(1000);
        }
      }
    }
    
    // Verify final state is consistent
    await app.page.waitForTimeout(2000);
    
    const finalButton = await disableButton.isVisible().catch(() => false);
    const finalSlider = await cardSizeSlider.isVisible().catch(() => false);
    
    // State should be consistent
    const isConsistent = (finalButton && !finalSlider) || (!finalButton && finalSlider);
    expect(isConsistent).toBe(true);
    
    console.log(`✅ Rapid transitions completed: button=${finalButton}, slider=${finalSlider}`);
  });
});
