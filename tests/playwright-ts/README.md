# E2E Tests with Playwright

This directory contains End-to-End tests for the Chinese Learning Cards application using Playwright with TypeScript.

## 🚀 Quick Start

### Prerequisites
- Node.js (v16 or higher)
- The main application running on `http://localhost:8504`

### Setup
```bash
# Install dependencies
npm install

# Install Playwright browsers
npm run install
```

### Running Tests
```bash
# Run all tests
npm run test

# Run tests with browser visible
npm run test:headed

# Run tests in debug mode
npm run test:debug

# Run tests with UI mode
npm run test:ui

# Run tests safely (single worker, more stable)
npm run test:safe

# Run specific test file
npx playwright test auto-features.spec.ts

# Run specific test
npx playwright test --grep "should generate pinyin"
```

### Cleanup
```bash
# Manual cleanup (removes test artifacts)
npm run cleanup

# Force cleanup (terminates all Chrome processes)
npm run force-cleanup
```

## 📊 Test Overview

### Test Suites (36 tests total)
- **Application Health** (6 tests) - Error detection and stability checks
- **Auto Features** (4 tests) - Auto pinyin/translation generation
- **Basic Input Flow** (3 tests) - Core card generation functionality
- **Card Size Adjustment** (2 tests) - Card sizing in different modes
- **CSV Upload** (6 tests) - File upload and processing functionality
- **Export Functionality** (6 tests) - PPTX/PDF export and download
- **Pagination Navigation** (6 tests) - Multi-page content handling
- **Preview Modes** (3 tests) - Preview mode switching

### Current Status: ✅ 100% Passing (36/36 tests)
### Average Runtime: ~8.5 minutes (single worker)

## 📁 File Structure

```
tests/playwright-ts/
├── tests/                          # Test files
│   ├── app-health.spec.ts          # Application health checks
│   ├── auto-features.spec.ts       # Auto pinyin/translation
│   ├── basic-input-flow.spec.ts    # Core input functionality
│   ├── card-size-adjustment.spec.ts # UI customization
│   ├── csv-upload.spec.ts          # CSV file processing
│   ├── export-functionality.spec.ts # PPTX/PDF export
│   ├── pagination-navigation.spec.ts # Multi-page handling
│   └── preview-modes.spec.ts       # Display modes
├── page-objects/
│   └── ZikaAppPage.ts              # Main page object
├── test-data/
│   ├── csv-files/                  # Valid CSV test files
│   └── invalid-csv-files/          # Invalid CSV test files
├── cleanup.ts                      # Pre-test cleanup
├── force-cleanup.ts                # Post-test cleanup
├── global-teardown.ts              # Global cleanup
├── playwright.config.ts            # Playwright configuration
├── package.json                    # Dependencies and scripts
└── README.md                       # This file
```

## 🛠️ Configuration

### Key Settings
- **Base URL**: `http://localhost:8504`
- **Timeout**: 2 minutes per test
- **Workers**: 3 (reduced for stability)
- **Retries**: 2 on CI, 0 locally
- **Screenshots**: On failure only
- **Videos**: Retained on failure

### Browser Support
- **Primary**: Chromium (default)
- **Future**: Firefox, Safari support planned

## 🧪 Test Architecture

### Page Object Model
Tests use a `ZikaAppPage` class that provides:
- **Navigation and setup methods**: `goto()`, `setupCards()`, `checkForStreamlitErrors()`
- **CSV operations**: `uploadCSVFile()`, `validateCSVUploadError()`, `selectCSVUploadMethod()`
- **Export operations**: `exportToPPTX()`, `exportToPDF()`, `verifyDownloadedFile()`
- **Navigation methods**: `navigateToPage()`, `getPageInfo()`, `verifyPageNavigation()`
- **Element interaction**: Multiple fallback strategies for reliability
- **Verification helpers**: `verifyCardsGenerated()`, `verifyPreviewContent()`
- **Comprehensive logging**: Detailed debugging information

### Robust Element Interaction
Each interaction implements multiple strategies:
1. Standard Playwright selectors
2. Alternative selectors or force clicks
3. JavaScript manipulation when needed

### Comprehensive Cleanup
Three-layer cleanup system:
1. **Pre-test**: Removes old artifacts
2. **Per-test**: Closes pages and contexts
3. **Post-test**: Terminates browser processes

## 🐛 Debugging

### When Tests Fail
1. Check screenshots in `test-results/`
2. Review video recordings for failed tests
3. Use `--debug` flag for step-by-step debugging
4. Check browser console logs in test output

### Common Issues
- **Application not running**: Ensure app is running on `http://localhost:8504`
- **Browser processes**: Run `npm run force-cleanup` to clean up
- **Timeout errors**: Check if application is responsive

## 📚 Documentation

For detailed test documentation, see:
- **Complete E2E Documentation**: `../../docs/E2E_TESTS_DOCUMENTATION.md`
- **Architecture Overview**: `../../docs/TEST_SUMMARY.md`

## 🔧 Development

### Adding New Tests
1. Create new `.spec.ts` file in `tests/`
2. Import and use the `ZikaAppPage` class
3. Follow existing patterns for setup and cleanup
4. Add appropriate test descriptions and logging

### Best Practices
- Use descriptive test names
- Add comprehensive logging
- Implement multiple fallback strategies
- Clean up after each test
- Use Page Object Model pattern

---

**Need help?** Check the detailed documentation in `docs/E2E_TESTS_DOCUMENTATION.md`
