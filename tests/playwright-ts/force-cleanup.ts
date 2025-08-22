#!/usr/bin/env node

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function forceCleanup() {
  console.log('🚨 Force cleanup - closing all Chrome processes...');

  try {
    if (process.platform === 'win32') {
      // Windows: Kill all Chrome processes
      await execAsync('taskkill /F /IM chrome.exe /T');
      console.log('✅ All Chrome processes terminated on Windows');
    } else {
      // Unix-like systems: Kill all Chrome processes
      await execAsync('pkill -f chrome');
      console.log('✅ All Chrome processes terminated on Unix');
    }
  } catch (error) {
    console.log('ℹ️ No Chrome processes found to terminate');
  }

  // Wait for processes to fully close
  await new Promise(resolve => setTimeout(resolve, 2000));

  console.log('✅ Force cleanup completed');
}

// Run cleanup if called directly
if (require.main === module) {
  forceCleanup().catch(console.error);
}

export default forceCleanup;
