import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';
import * as path from 'path';

test.describe('CSV Upload Functionality', () => {
  let app: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    app = new ZikaAppPage(page);
    await app.goto();
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

  test('should successfully upload and process valid CSV file @critical', async () => {
    console.log('🧪 Testing successful CSV upload...');
    
    // Upload valid CSV file
    const csvPath = path.join(__dirname, '../test-data/valid-csv-files/basic-cards.csv');
    const uploadSuccess = await app.uploadCSVFile(csvPath);
    expect(uploadSuccess).toBe(true);
    
    // Verify success message
    const successValidated = await app.validateCSVUploadSuccess(10);
    expect(successValidated).toBe(true);
    
    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);
    
    console.log('✅ CSV upload test completed successfully');
  });

  test('should handle CSV with missing required columns gracefully', async () => {
    console.log('🧪 Testing CSV with missing hanzi column...');
    
    // Upload CSV without hanzi column
    const csvPath = path.join(__dirname, '../test-data/invalid-csv-files/missing-hanzi-column.csv');
    const uploadSuccess = await app.uploadCSVFile(csvPath);
    expect(uploadSuccess).toBe(true);
    
    // Verify error message appears
    const errorValidated = await app.validateCSVUploadError('CSV文件必须包含以下列: hanzi');
    expect(errorValidated).toBe(true);
    
    console.log('✅ Missing column error handling test completed');
  });

  test('should display appropriate errors for invalid CSV files', async () => {
    console.log('🧪 Testing malformed CSV file handling...');

    // Upload malformed CSV file
    const csvPath = path.join(__dirname, '../test-data/invalid-csv-files/malformed-data.csv');
    const uploadSuccess = await app.uploadCSVFile(csvPath);
    expect(uploadSuccess).toBe(true);

    // For malformed CSV files, we expect either:
    // 1. An error message to be displayed, OR
    // 2. Partial processing with some cards generated

    try {
      // First check if there's an error message (which is expected for malformed CSV)
      const hasError = await app.validateCSVUploadError('读取CSV文件时出错');
      if (hasError) {
        console.log('✅ Malformed CSV correctly shows error message');
        return;
      }
    } catch (error) {
      // If no error message, check if some cards were generated from valid rows
      console.log('⚠️ No error message found, checking for partial card generation...');
    }

    // If no error message, verify that at least some cards were generated from valid rows
    // Allow CSV parsing errors since they're expected for malformed files
    const cardsGenerated = await app.verifyCardsGenerated(['读取CSV文件时出错', 'Error tokenizing data']);
    expect(cardsGenerated).toBe(true);

    console.log('✅ Malformed CSV handling test completed');
  });

  test('should handle CSV with special characters and quoted fields', async () => {
    console.log('🧪 Testing CSV with special characters...');
    
    // Upload CSV with special characters and quotes
    const csvPath = path.join(__dirname, '../test-data/valid-csv-files/special-characters.csv');
    const uploadSuccess = await app.uploadCSVFile(csvPath);
    expect(uploadSuccess).toBe(true);
    
    // Verify success message
    const successValidated = await app.validateCSVUploadSuccess(10);
    expect(successValidated).toBe(true);
    
    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);
    
    console.log('✅ Special characters CSV test completed');
  });

  test('should handle large CSV files with progress feedback', async () => {
    console.log('🧪 Testing large CSV file upload...');
    
    // Upload large CSV file
    const csvPath = path.join(__dirname, '../test-data/valid-csv-files/large-dataset.csv');
    const uploadSuccess = await app.uploadCSVFile(csvPath);
    expect(uploadSuccess).toBe(true);
    
    // Verify success message with correct card count
    const successValidated = await app.validateCSVUploadSuccess(35);
    expect(successValidated).toBe(true);
    
    // Verify cards are generated
    const cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);
    
    console.log('✅ Large CSV file test completed');
  });

  test('should preserve CSV upload state when switching input methods', async () => {
    console.log('🧪 Testing CSV upload state persistence...');
    
    // Upload valid CSV file
    const csvPath = path.join(__dirname, '../test-data/valid-csv-files/basic-cards.csv');
    const uploadSuccess = await app.uploadCSVFile(csvPath);
    expect(uploadSuccess).toBe(true);
    
    // Verify cards are generated
    let cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);
    
    // Switch to manual input and back to CSV
    await app.page.getByText('手动输入').click();
    await app.page.waitForTimeout(1000);
    await app.page.getByText('上传CSV文件').click();
    await app.page.waitForTimeout(1000);
    
    // Verify cards are still there
    cardsGenerated = await app.verifyCardsGenerated();
    expect(cardsGenerated).toBe(true);
    
    console.log('✅ CSV state persistence test completed');
  });
});
