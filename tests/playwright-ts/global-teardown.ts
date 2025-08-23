import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';

const execAsync = promisify(exec);

async function globalTeardown() {
  console.log('🧹 Starting global cleanup...');

  // Note: Playwright automatically handles browser cleanup when tests complete normally.
  // We only need to clean up artifacts and handle edge cases where processes might be stuck.

  try {
    // 1. Let Playwright handle browser cleanup naturally
    console.log('🔄 Allowing Playwright to complete browser cleanup...');
    // Playwright automatically closes browsers when tests complete
    // We only clean up artifacts and temporary files

    // 2. Clean up test artifacts
    console.log('🗑️ Cleaning up test artifacts...');
    const artifactDirs = [
      'test-results',
      'playwright-report',
      'playwright/.cache'
    ];

    for (const dir of artifactDirs) {
      const dirPath = path.join(__dirname, dir);
      if (fs.existsSync(dirPath)) {
        try {
          fs.rmSync(dirPath, { recursive: true, force: true });
          console.log(`✅ Removed ${dir}`);
        } catch (error) {
          console.log(`⚠️ Could not remove ${dir}: ${error instanceof Error ? error.message : String(error)}`);
        }
      }
    }

    // 3. Clean up temporary files (none at present)
    console.log('🧽 Cleaning up temporary files...');

    console.log('✅ Global cleanup completed');
  } catch (error) {
    console.log(`⚠️ Cleanup error: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export default globalTeardown;
