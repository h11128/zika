import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Reduce parallel workers to prevent too many browser instances */
  workers: process.env.CI ? 1 : 3, // Reduced from default to 3 workers
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['list'],
    ['junit', { outputFile: 'test-results/results.xml' }]
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  /* Global test timeout */
  timeout: 120000, // 2 minutes per test

  /* Clean up test artifacts */
  globalTeardown: require.resolve('./global-teardown.ts'),

  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.BASE_URL || 'http://localhost:8504',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Global timeout for each action */
    actionTimeout: 30000, // Increased from 15s

    /* Global timeout for navigation */
    navigationTimeout: 60000, // Increased from 30s

    /* Automatically close pages after tests */
    contextOptions: {
      // Close context after each test to clean up pages
    },

    /* Close browser after each test */
    launchOptions: {
      // Ensure browser closes properly
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    },
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment to test on other browsers
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'python -m streamlit run web_ui.py --server.port 8504',
    url: 'http://localhost:8504',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000, // 2 minutes
    cwd: '../..',
  },
});
