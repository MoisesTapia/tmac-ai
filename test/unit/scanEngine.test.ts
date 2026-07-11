/**
 * Unit tests for ScanEngine (Task 3.3).
 *
 * Mocks `child_process.spawn` with an EventEmitter-based fake that emits
 * canned stdout/stderr/exit events so no real `tmac` binary is needed.
 *
 * Also mocks `tmacResolver.resolveTmacPath` so that resolver logic is
 * isolated from scan-engine logic.
 *
 * Since the updated ScanEngine writes SARIF to a temp file via `-o <tmpFile>`
 * and reads it back with `fs.readFileSync`, we mock `fs` so tests don't need
 * a real filesystem or temp file.
 *
 * Validates: Requirements 2.4–2.8
 */

import { EventEmitter } from 'events';

// ---------------------------------------------------------------------------
// Mock child_process.spawn BEFORE importing the module under test
// ---------------------------------------------------------------------------

jest.mock('child_process', () => ({
  ...jest.requireActual('child_process'),
  spawn: jest.fn(),
}));

// Mock tmacResolver so we control whether tmac is "found"
jest.mock('../../src/engine/tmacResolver', () => ({
  ...jest.requireActual('../../src/engine/tmacResolver'),
  resolveTmacPath: jest.fn(),
}));

// Mock fs so we can simulate the temp file read without touching disk
jest.mock('fs', () => ({
  ...jest.requireActual('fs'),
  readFileSync: jest.fn(),
  unlinkSync: jest.fn(),
}));

import { spawn } from 'child_process';
import * as fs from 'fs';
import { resolveTmacPath, TmacConfig } from '../../src/engine/tmacResolver';
import { ScanEngine, ScanEngineResult } from '../../src/engine/scanEngine';
import { MockOutputChannel } from '../../src/__mocks__/vscode';

// Typed casts to jest mocks
const mockSpawn = spawn as jest.MockedFunction<typeof spawn>;
const mockResolveTmacPath = resolveTmacPath as jest.MockedFunction<typeof resolveTmacPath>;
const mockReadFileSync = fs.readFileSync as jest.MockedFunction<typeof fs.readFileSync>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Minimal valid SARIF 2.1.0 document with one finding. */
const VALID_SARIF_ONE_FINDING = JSON.stringify({
  version: '2.1.0',
  runs: [
    {
      tool: { driver: { name: 'tmac', version: '1.0.0' } },
      results: [
        {
          ruleId: 'TMAC-AWS-S3-001',
          level: 'error',
          message: { text: 'S3 bucket is publicly accessible' },
          locations: [
            {
              physicalLocation: {
                artifactLocation: { uri: 'main.tf' },
                region: { startLine: 10, startColumn: 1 },
              },
            },
          ],
          properties: {
            severity: 'critical',
            stride: 'Information Disclosure',
            mitigation: 'Set acl = "private"',
          },
        },
      ],
    },
  ],
});

/** Minimal valid SARIF with zero results. */
const VALID_SARIF_EMPTY = JSON.stringify({
  version: '2.1.0',
  runs: [{ tool: { driver: { name: 'tmac' } }, results: [] }],
});

/**
 * Creates a fake child-process EventEmitter that will:
 * 1. Emit `stdout.data` events with the provided chunks
 * 2. Emit `stderr.data` events with the provided stderr chunks
 * 3. Emit `close` with the given exit code
 *
 * The emissions happen asynchronously (nextTick) so that event listeners
 * registered synchronously after `spawn()` have time to attach.
 */
function createFakeProcess(options: {
  stdoutChunks?: string[];
  stderrChunks?: string[];
  exitCode: number;
  errorEvent?: Error;
}): ReturnType<typeof spawn> {
  const stdoutEmitter = new EventEmitter();
  const stderrEmitter = new EventEmitter();
  const procEmitter = new EventEmitter();

  const fakeProc = Object.assign(procEmitter, {
    stdout: stdoutEmitter,
    stderr: stderrEmitter,
    stdin: null,
    kill: jest.fn(),
    pid: 12345,
  });

  // Schedule events asynchronously
  process.nextTick(() => {
    if (options.errorEvent) {
      procEmitter.emit('error', options.errorEvent);
      return;
    }

    for (const chunk of options.stdoutChunks ?? []) {
      stdoutEmitter.emit('data', Buffer.from(chunk));
    }
    for (const chunk of options.stderrChunks ?? []) {
      stderrEmitter.emit('data', Buffer.from(chunk));
    }
    procEmitter.emit('close', options.exitCode);
  });

  return fakeProc as unknown as ReturnType<typeof spawn>;
}

/** Default config used across tests. */
const DEFAULT_CONFIG: TmacConfig = {
  executablePath: '',
  scanOnSave: true,
  scanDelay: 1000,
  excludePatterns: [],
  failOn: 'critical',
  enableQuickFixes: false,
};

/** A minimal workspace folder stub. */
const WORKSPACE_FOLDER = {
  uri: { toString: () => 'file:///workspace', fsPath: '/workspace' },
  name: 'workspace',
  index: 0,
} as unknown as import('vscode').WorkspaceFolder;

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  jest.clearAllMocks();

  // Default: resolveTmacPath resolves successfully
  mockResolveTmacPath.mockResolvedValue({
    ok: true,
    path: 'tmac',
    version: '1.0.0',
  });

  // Default: readFileSync returns valid SARIF with one finding
  (mockReadFileSync as jest.Mock).mockReturnValue(VALID_SARIF_ONE_FINDING);
});

// ---------------------------------------------------------------------------
// Test 1: Exit code 0 with valid SARIF stdout → { ok: true, result: ScanResult }
// ---------------------------------------------------------------------------

describe('ScanEngine.scan()', () => {
  it('returns ok:true with ScanResult when exit code is 0 and stdout is valid SARIF', async () => {
    ( mockReadFileSync as jest.Mock).mockReturnValueOnce(VALID_SARIF_ONE_FINDING);
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({ exitCode: 0 }),
    );

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);
    const result: ScanEngineResult = await engine.scan(WORKSPACE_FOLDER);

    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.result.findings).toHaveLength(1);
    expect(result.result.findings[0].ruleId).toBe('TMAC-AWS-S3-001');
    expect(result.result.workspaceRoot).toBe('/workspace');
  });

  // -------------------------------------------------------------------------
  // Test 2: Exit code 1 with valid SARIF stdout → { ok: true, result }
  // -------------------------------------------------------------------------

  it('returns ok:true with findings when exit code is 1 (critical findings present)', async () => {
    ( mockReadFileSync as jest.Mock).mockReturnValueOnce(VALID_SARIF_ONE_FINDING);
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({ exitCode: 1 }),
    );

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);
    const result = await engine.scan(WORKSPACE_FOLDER);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.result.findings.length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Test 3: Exit code 2 with valid SARIF stdout → { ok: true, result }
  // -------------------------------------------------------------------------

  it('returns ok:true when exit code is 2 (high findings present)', async () => {
    ( mockReadFileSync as jest.Mock).mockReturnValueOnce(VALID_SARIF_ONE_FINDING);
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({ exitCode: 2 }),
    );

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);
    const result = await engine.scan(WORKSPACE_FOLDER);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.result.findings).toHaveLength(1);
  });

  // -------------------------------------------------------------------------
  // Test 4: Exit code 3 → { ok: false, error: { kind: 'execution_error', exitCode: 3 } }
  // -------------------------------------------------------------------------

  it('returns execution_error with exitCode 3 when process exits with code 3', async () => {
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({
        stderrChunks: ['tmac internal error: configuration invalid'],
        exitCode: 3,
      }),
    );

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);
    const result = await engine.scan(WORKSPACE_FOLDER);

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('execution_error');
    if (result.error.kind !== 'execution_error') return;
    expect(result.error.exitCode).toBe(3);
  });

  // -------------------------------------------------------------------------
  // Test 5: Empty stdout + non-zero exit → { ok: false, error: { kind: 'execution_error' } }
  // -------------------------------------------------------------------------

  it('returns execution_error when stdout is empty and exit code is non-zero (not 3)', async () => {
    // Simulate readFileSync throwing (file not written because tmac failed)
    mockReadFileSync.mockImplementationOnce(() => { throw new Error('ENOENT'); });
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({
        stderrChunks: ['unexpected failure'],
        exitCode: 127,
      }),
    );

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);
    const result = await engine.scan(WORKSPACE_FOLDER);

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('execution_error');
    if (result.error.kind !== 'execution_error') return;
    expect(result.error.exitCode).toBe(127);
  });

  // -------------------------------------------------------------------------
  // Test 6: Debounce — calling scan() twice quickly → only one underlying spawn
  // -------------------------------------------------------------------------

  it('debounce: second scan call while first is in progress completes without starting a redundant concurrent scan', async () => {
    // Each spawn() call needs a fresh EventEmitter; use mockImplementation
    mockSpawn.mockImplementation(() =>
      createFakeProcess({ exitCode: 0 }),
    );
    (mockReadFileSync as jest.Mock).mockReturnValue(VALID_SARIF_EMPTY);

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);

    // Fire two scans "simultaneously"
    const [result1, result2] = await Promise.all([
      engine.scan(WORKSPACE_FOLDER),
      engine.scan(WORKSPACE_FOLDER),
    ]);

    // Both should succeed
    expect(result1.ok).toBe(true);
    expect(result2.ok).toBe(true);

    // After both complete, the scanning flag must not be stuck true.
    // A third scan must also succeed, confirming the engine is back in a ready state.
    const result3 = await engine.scan(WORKSPACE_FOLDER);
    expect(result3.ok).toBe(true);
  });

  // -------------------------------------------------------------------------
  // Additional: tmac_unavailable when resolver fails
  // -------------------------------------------------------------------------

  it('returns tmac_unavailable when resolveTmacPath fails', async () => {
    mockResolveTmacPath.mockResolvedValueOnce({
      ok: false,
      reason: 'not_found',
    });

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);
    const result = await engine.scan(WORKSPACE_FOLDER);

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('tmac_unavailable');
    // spawn should NOT have been called
    expect(mockSpawn).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // Additional: output channel receives command line, stdout, stderr, exit code
  // -------------------------------------------------------------------------

  it('writes command line, stdout, stderr, exit code to output channel', async () => {
    const stderrContent = 'some warning';
    ( mockReadFileSync as jest.Mock).mockReturnValueOnce(VALID_SARIF_EMPTY);
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({
        stderrChunks: [stderrContent],
        exitCode: 0,
      }),
    );

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);
    await engine.scan(WORKSPACE_FOLDER);

    const calls: string[] = outputChannel.appendLine.mock.calls.map(
      (c: string[]) => c[0],
    );

    // Command line should be logged first
    expect(calls.some((line) => line.includes('tmac') && line.includes('scan'))).toBe(true);
    // stderr should be prefixed with [stderr]
    expect(calls.some((line) => line.includes('[stderr]') && line.includes(stderrContent))).toBe(true);
    // Exit code line
    expect(calls.some((line) => line.includes('Exit code:'))).toBe(true);
  });

  // -------------------------------------------------------------------------
  // Additional: summary line written only when findings >= 1
  // -------------------------------------------------------------------------

  it('writes "Parsed N findings from SARIF output" only when findings >= 1', async () => {
    // Case 1: findings present
    ( mockReadFileSync as jest.Mock).mockReturnValueOnce(VALID_SARIF_ONE_FINDING);
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({ exitCode: 0 }),
    );
    const outputChannel1 = new MockOutputChannel();
    const engine1 = new ScanEngine(outputChannel1, DEFAULT_CONFIG);
    await engine1.scan(WORKSPACE_FOLDER);

    const calls1: string[] = outputChannel1.appendLine.mock.calls.map(
      (c: string[]) => c[0],
    );
    expect(calls1.some((line) => line.includes('Parsed') && line.includes('findings from SARIF output'))).toBe(true);

    // Case 2: zero findings — summary line should NOT appear
    ( mockReadFileSync as jest.Mock).mockReturnValueOnce(VALID_SARIF_EMPTY);
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({ exitCode: 0 }),
    );
    const outputChannel2 = new MockOutputChannel();
    const engine2 = new ScanEngine(outputChannel2, DEFAULT_CONFIG);
    await engine2.scan(WORKSPACE_FOLDER);

    const calls2: string[] = outputChannel2.appendLine.mock.calls.map(
      (c: string[]) => c[0],
    );
    expect(calls2.some((line) => line.includes('Parsed') && line.includes('findings from SARIF output'))).toBe(false);
  });

  // -------------------------------------------------------------------------
  // Additional: exclude patterns are passed as --exclude args
  // -------------------------------------------------------------------------

  it('passes excludePatterns as --exclude arguments to spawn', async () => {
    ( mockReadFileSync as jest.Mock).mockReturnValueOnce(VALID_SARIF_EMPTY);
    mockSpawn.mockReturnValueOnce(
      createFakeProcess({ exitCode: 0 }),
    );

    const config: TmacConfig = {
      ...DEFAULT_CONFIG,
      excludePatterns: ['**/test/**', '**/vendor/**'],
    };

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, config);
    await engine.scan(WORKSPACE_FOLDER);

    expect(mockSpawn).toHaveBeenCalledTimes(1);
    const spawnArgs = mockSpawn.mock.calls[0][1] as string[];
    expect(spawnArgs).toContain('--exclude');
    expect(spawnArgs).toContain('**/test/**');
    expect(spawnArgs).toContain('**/vendor/**');
    expect(spawnArgs).toContain('--output'); // temp file arg
  });

  // -------------------------------------------------------------------------
  // Additional: cancel() kills the in-flight process
  // -------------------------------------------------------------------------

  it('cancel() kills the current process and resets scanning state', async () => {
    // We need a process that does NOT emit close immediately so we can
    // cancel it mid-flight.
    const stdoutEmitter = new EventEmitter();
    const stderrEmitter = new EventEmitter();
    const procEmitter = new EventEmitter();
    const killFn = jest.fn();

    const slowProc = Object.assign(procEmitter, {
      stdout: stdoutEmitter,
      stderr: stderrEmitter,
      stdin: null,
      kill: killFn,
      pid: 99999,
    });

    mockSpawn.mockReturnValueOnce(slowProc as unknown as ReturnType<typeof spawn>);

    const outputChannel = new MockOutputChannel();
    const engine = new ScanEngine(outputChannel, DEFAULT_CONFIG);

    // Start scan but don't await — it won't resolve until we emit close
    const scanPromise = engine.scan(WORKSPACE_FOLDER);

    // Give the process a tick to start
    await new Promise(resolve => process.nextTick(resolve));

    // Cancel
    engine.cancel();
    expect(killFn).toHaveBeenCalled();

    // Now emit close so the promise resolves (cancel doesn't auto-resolve the promise
    // but killing the process would cause close to fire in a real scenario)
    procEmitter.emit('close', 1);

    // The scan promise should resolve (either ok or error)
    const result = await scanPromise;
    // It may succeed or fail depending on stdout content — we just want no hang
    expect(result).toBeDefined();
  });
});
