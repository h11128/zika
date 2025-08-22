import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';

const execAsync = promisify(exec);

async function globalTeardown() {
  console.log('🧹 Starting global cleanup...');

  try {
    // 1. Force close all Chrome processes (aggressive cleanup)
    console.log('🔪 Force closing all Chrome processes...');
    try {
      if (process.platform === 'win32') {
        await execAsync('taskkill /F /IM chrome.exe /T');
        console.log('✅ All Chrome processes terminated');
      } else {
        await execAsync('pkill -f chrome');
        console.log('✅ All Chrome processes terminated');
      }
    } catch (error) {
      console.log('ℹ️ No Chrome processes to terminate');
    }

    // Wait a moment for processes to fully close
    await new Promise(resolve => setTimeout(resolve, 2000));

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

    // 3. Clean up temporary files
    console.log('🧽 Cleaning up temporary files...');
    const tempFiles = [
      '../../test_card_size_fix.py',
      '../../debug_card_size.py',
      '../../debug_auto_fill.py'
    ];

    for (const file of tempFiles) {
      const filePath = path.join(__dirname, file);
      if (fs.existsSync(filePath)) {
        try {
          fs.unlinkSync(filePath);
          console.log(`✅ Removed ${file}`);
        } catch (error) {
          console.log(`⚠️ Could not remove ${file}: ${error instanceof Error ? error.message : String(error)}`);
        }
      }
    }

    console.log('✅ Global cleanup completed');
  } catch (error) {
    console.log(`⚠️ Cleanup error: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export default globalTeardown;
