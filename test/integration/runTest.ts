/**
 * runTest.ts — Entry point for the @vscode/test-electron integration test runner.
 *
 * This file is compiled and run as a Node.js script (outside the extension host).
 * It downloads/resolves VS Code, launches it with the extension installed, opens
 * the fixture workspace, and runs the extension.test.ts suite inside the host.
 *
 * Run via:  npm run test:integration
 * (package.json script: "node ./out/test/integration/runTest.js")
 *
 * Requirements: 2.1–2.3, 4.5, 6.1, 7.1, 8.1–8.4
 */

import * as path from 'path';
import { runTests } from '@vscode/test-electron';

async function main(): Promise<void> {
  try {
    // The folder containing the extension's package.json (workspace root)
    const extensionDevelopmentPath = path.resolve(__dirname, '../..');

    // The path to the compiled test suite index (the entry point for the
    // extension host test runner — Mocha is used by @vscode/test-electron by
    // default).
    const extensionTestsPath = path.resolve(__dirname, './index');

    // The fixture workspace opened inside VS Code during the integration tests.
    // Must contain at least one .tf file so the extension's activationEvents
    // trigger ("workspaceContains:**/*.tf").
    const workspacePath = path.resolve(
      __dirname,
      '../../fixtures/workspace',
    );

    // Launch VS Code, install the extension, open the workspace, and run tests.
    await runTests({
      extensionDevelopmentPath,
      extensionTestsPath,
      launchArgs: [
        workspacePath,
        // Disable all other extensions to isolate our extension
        '--disable-extensions',
        '--disable-gpu',
      ],
    });
  } catch (err) {
    console.error('Integration test run failed:', err);
    process.exit(1);
  }
}

main();
