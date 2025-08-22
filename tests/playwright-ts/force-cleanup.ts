#!/usr/bin/env node

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function forceCleanup() {
  console.log('🚨 Force cleanup - closing test-related Chrome processes...');

  try {
    if (process.platform === 'win32') {
      // Windows: Only kill Chrome processes with test-related command line arguments
      try {
        // First, try to find Chrome processes with Playwright/test-related arguments
        const { stdout } = await execAsync('wmic process where "name=\'chrome.exe\'" get commandline,processid /format:csv');
        const lines = stdout.split('\n').filter(line => line.trim());

        let testProcessesFound = false;
        for (const line of lines) {
          const parts = line.split(',');
          if (parts.length >= 3) {
            const commandLine = parts[1] || '';
            const processId = parts[2] || '';

            // Check if this Chrome process has test-related arguments
            if (commandLine.includes('--test-type') ||
                commandLine.includes('--remote-debugging-port') ||
                commandLine.includes('--user-data-dir') && commandLine.includes('playwright') ||
                commandLine.includes('--disable-dev-shm-usage') ||
                commandLine.includes('--no-sandbox')) {

              if (processId.trim()) {
                await execAsync(`taskkill /F /PID ${processId.trim()}`);
                testProcessesFound = true;
                console.log(`✅ Terminated test Chrome process PID: ${processId.trim()}`);
              }
            }
          }
        }

        if (!testProcessesFound) {
          console.log('ℹ️ No test-related Chrome processes found');
        }
      } catch (wmicError) {
        console.log('⚠️ Could not identify test Chrome processes, skipping cleanup');
      }
    } else {
      // Unix-like systems: Only kill Chrome processes with test-related arguments
      try {
        const { stdout } = await execAsync('ps aux | grep chrome');
        const lines = stdout.split('\n');

        let testProcessesFound = false;
        for (const line of lines) {
          if (line.includes('--test-type') ||
              line.includes('--remote-debugging-port') ||
              (line.includes('--user-data-dir') && line.includes('playwright')) ||
              line.includes('--disable-dev-shm-usage') ||
              line.includes('--no-sandbox')) {

            const parts = line.trim().split(/\s+/);
            if (parts.length > 1) {
              const pid = parts[1];
              await execAsync(`kill -9 ${pid}`);
              testProcessesFound = true;
              console.log(`✅ Terminated test Chrome process PID: ${pid}`);
            }
          }
        }

        if (!testProcessesFound) {
          console.log('ℹ️ No test-related Chrome processes found');
        }
      } catch (psError) {
        console.log('⚠️ Could not identify test Chrome processes, skipping cleanup');
      }
    }
  } catch (error) {
    console.log(`⚠️ Error during Chrome cleanup: ${error instanceof Error ? error.message : String(error)}`);
  }

  // Wait for processes to fully close
  await new Promise(resolve => setTimeout(resolve, 1000));

  console.log('✅ Force cleanup completed');
}

// Run cleanup if called directly
if (require.main === module) {
  forceCleanup().catch(console.error);
}

export default forceCleanup;
