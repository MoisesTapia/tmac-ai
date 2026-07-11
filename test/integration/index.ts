/**
 * index.ts — Mocha test runner index for @vscode/test-electron.
 *
 * @vscode/test-electron requires this module to export a `run()` function that
 * sets up Mocha and returns a Promise which resolves on success and rejects on
 * failure.  The extension host calls `run()` after it has activated.
 */

import * as path from 'path';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Mocha = require('mocha') as typeof import('mocha');
// glob v7 ships a synchronous API; we use it to avoid the promise-based v10 API.
import { sync as globSync } from 'glob';

export function run(): Promise<void> {
  // Create the Mocha runner with a 10 second per-test timeout to allow for
  // async VS Code operations (command execution, activation, etc.)
  const mocha = new Mocha({
    ui: 'tdd',
    color: true,
    timeout: 10_000,
  });

  const testsRoot = path.resolve(__dirname, '.');

  return new Promise((resolve, reject) => {
    try {
      const files = globSync('**/*.test.js', { cwd: testsRoot });

      // Add all test files to the Mocha runner
      files.forEach((f: string) => mocha.addFile(path.resolve(testsRoot, f)));

      mocha.run((failures: number) => {
        if (failures > 0) {
          reject(new Error(`${failures} test(s) failed.`));
        } else {
          resolve();
        }
      });
    } catch (err) {
      reject(err);
    }
  });
}
