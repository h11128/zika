#!/usr/bin/env node

import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';

const execAsync = promisify(exec);

async function cleanup() {
  console.log('🧹 Pre-test cleanup...');

  try {
    // 1. Clean up any leftover test pages (gentle approach)
    console.log('🔗 Preparing for test run...');
    // We don't kill browsers here, just clean up artifacts

    // 2. Clean up test artifacts
    const keep = process.env.KEEP_ARTIFACTS === '1';
    console.log('🗑️ Cleaning up test artifacts...');
    if (keep) {
      console.log('🔒 KEEP_ARTIFACTS=1 set; skipping artifact cleanup');
    } else {
      const artifactDirs = [
        'test-results',
        'playwright-report'
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
    }

    console.log('✅ Pre-test cleanup completed');
  } catch (error) {
    console.log(`⚠️ Cleanup error: ${error instanceof Error ? error.message : String(error)}`);
  }
}

// Run cleanup if called directly
if (require.main === module) {
  cleanup();
}

export default cleanup;
