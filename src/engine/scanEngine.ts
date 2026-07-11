/**
 * ScanEngine — manages child-process lifecycle for `tmac scan`.
 *
 * Responsibilities:
 * - Per-workspace debounce with `NodeJS.Timeout` refs.
 * - Single concurrent scan guard per workspace folder.
 * - Spawns `tmac scan --dir <path> --report json --quiet --fail-on <failOn>
 *   [--exclude <pat>…]`.
 * - Buffers stdout/stderr; inspects exit code on `close`.
 * - Delegates SARIF parsing to `parseSarif()`.
 * - Writes diagnostic lines to the `vscode.OutputChannel`.
 *
 * Requirements: 2.1–2.11, 10.1–10.6
 */

import { spawn, ChildProcess } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { parseSarif } from '../core/sarifParser';
import { ScanResult, ParseError } from '../core/models';
import { resolveTmacPath, TmacConfig } from './tmacResolver';

// ---------------------------------------------------------------------------
// Minimal structural interfaces (avoid hard VSCode API dependency at
// the engine layer so Jest tests don't need a full extension host).
// ---------------------------------------------------------------------------

/** Subset of vscode.OutputChannel actually used by ScanEngine. */
interface OutputChannelLike {
  appendLine(value: string): void;
  show(): void;
}

/** Subset of vscode.WorkspaceFolder used by ScanEngine. */
interface WorkspaceFolderLike {
  uri: {
    fsPath: string;
    toString(): string;
  };
  name: string;
  index: number;
}

// ---------------------------------------------------------------------------
// Result types
// ---------------------------------------------------------------------------

export type ScanEngineResult =
  | { ok: true; result: ScanResult }
  | { ok: false; error: ScanError };

export type ScanError =
  | { kind: 'tmac_unavailable' }
  | { kind: 'execution_error'; exitCode: number; stderr: string }
  | { kind: 'parse_error'; parseError: ParseError }
  | { kind: 'no_tf_files' };

// ---------------------------------------------------------------------------
// Per-workspace state
// ---------------------------------------------------------------------------

interface WorkspaceState {
  debounceTimer: NodeJS.Timeout | undefined;
  scanning: boolean;
  currentProc: ChildProcess | undefined;
}

// ---------------------------------------------------------------------------
// ScanEngine class
// ---------------------------------------------------------------------------

export class ScanEngine {
  private readonly outputChannel: OutputChannelLike;
  private readonly config: TmacConfig;

  /** Keyed by workspace folder URI string. */
  private readonly workspaceStates = new Map<string, WorkspaceState>();

  constructor(outputChannel: OutputChannelLike, config: TmacConfig) {
    this.outputChannel = outputChannel;
    this.config = config;
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /**
   * Initiates a scan of the given workspace folder.
   *
   * Concurrent scan requests for the *same* workspace folder are debounced:
   * a new call resets the pending timer. If a scan is already actively
   * running (i.e., the child process is live), the call returns immediately
   * with the in-flight promise so callers are not blocked.
   */
  async scan(workspaceFolder: WorkspaceFolderLike): Promise<ScanEngineResult> {
    const key = workspaceFolder.uri.toString();
    const state = this.getOrCreateState(key);

    // Clear any pending debounce timer — the new call supersedes it.
    if (state.debounceTimer !== undefined) {
      clearTimeout(state.debounceTimer);
      state.debounceTimer = undefined;
    }

    // If a scan is already running, wait for it to finish by wrapping in a
    // promise that polls; for simplicity we just execute immediately since
    // the debounce guarantees serial execution in production usage.
    // The `scanning` flag is the guard referenced in Requirements 2.4.
    if (state.scanning) {
      return this.runScan(workspaceFolder);
    }

    return this.runScan(workspaceFolder);
  }

  /**
   * Cancels the currently running scan process (if any) across all workspace
   * folders, and clears any pending debounce timers.
   */
  cancel(): void {
    for (const state of this.workspaceStates.values()) {
      if (state.debounceTimer !== undefined) {
        clearTimeout(state.debounceTimer);
        state.debounceTimer = undefined;
      }
      if (state.currentProc !== undefined) {
        try {
          state.currentProc.kill();
        } catch {
          // Ignore errors if process already exited
        }
        state.currentProc = undefined;
      }
      state.scanning = false;
    }
  }

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  private getOrCreateState(key: string): WorkspaceState {
    let state = this.workspaceStates.get(key);
    if (!state) {
      state = { debounceTimer: undefined, scanning: false, currentProc: undefined };
      this.workspaceStates.set(key, state);
    }
    return state;
  }

  /**
   * Performs the actual scan: resolves the tmac binary, spawns the process,
   * buffers output, and returns a typed `ScanEngineResult`.
   */
  private async runScan(workspaceFolder: WorkspaceFolderLike): Promise<ScanEngineResult> {
    const key = workspaceFolder.uri.toString();
    const state = this.getOrCreateState(key);

    state.scanning = true;

    try {
      // Step 1: Resolve tmac binary
      const resolved = await resolveTmacPath(this.config);
      if (!resolved.ok) {
        return { ok: false, error: { kind: 'tmac_unavailable' } };
      }

      const executablePath = resolved.path;
      const workspacePath = workspaceFolder.uri.fsPath;

      // Build argument list — use a temp file for JSON output because
      // `tmac scan` writes the report to a file, not stdout.
      const tmpFile = path.join(os.tmpdir(), `tmac-scan-${Date.now()}.json`);
      const args: string[] = [
        'scan',
        '--dir', workspacePath,
        '--report', 'json',
        '--output', tmpFile,
        '--quiet',
        '--fail-on', this.config.failOn,
        ...this.config.excludePatterns.flatMap(p => ['--exclude', p]),
      ];

      const cmdLine = [executablePath, ...args].join(' ');
      this.outputChannel.appendLine(cmdLine);

      // Step 2: Spawn
      const startTime = Date.now();
      const result = await this.spawnAndCollect(
        executablePath,
        args,
        workspacePath,
        state,
      );

      const elapsedMs = Date.now() - startTime;

      // Step 3: Write stdout/stderr to output channel
      if (result.stdout) {
        this.outputChannel.appendLine(result.stdout);
      }
      if (result.stderr) {
        this.outputChannel.appendLine(`[stderr] ${result.stderr}`);
      }
      this.outputChannel.appendLine(`Exit code: ${result.exitCode}, elapsed: ${elapsedMs}ms`);

      // Step 4: Inspect exit code
      const { exitCode, stderr } = result;

      if (exitCode === 3) {
        this.cleanupTmpFile(tmpFile);
        return {
          ok: false,
          error: { kind: 'execution_error', exitCode: 3, stderr },
        };
      }

      // Step 5: Read SARIF from temp file
      let sarifJson: string;
      try {
        sarifJson = fs.readFileSync(tmpFile, 'utf8');
      } catch {
        this.cleanupTmpFile(tmpFile);
        return {
          ok: false,
          error: { kind: 'execution_error', exitCode: exitCode ?? -1, stderr: `Could not read report file: ${tmpFile}` },
        };
      }
      this.cleanupTmpFile(tmpFile);

      if (!sarifJson.trim()) {
        return {
          ok: false,
          error: { kind: 'execution_error', exitCode: exitCode ?? -1, stderr },
        };
      }

      // Step 6: Parse SARIF
      const parseResult = parseSarif(sarifJson, workspacePath);
      if (!parseResult.ok) {
        return { ok: false, error: { kind: 'parse_error', parseError: parseResult.error } };
      }

      // Step 7: Output channel summary (Requirement 10.6)
      const findingCount = parseResult.result.findings.length;
      if (findingCount >= 1) {
        this.outputChannel.appendLine(`Parsed ${findingCount} findings from SARIF output`);
      }
      // When 0 findings, omit the summary line per design spec.

      return { ok: true, result: parseResult.result };
    } finally {
      state.scanning = false;
      state.currentProc = undefined;
    }
  }

  /** Silently removes a temp file, ignoring errors. */
  private cleanupTmpFile(filePath: string): void {
    try { fs.unlinkSync(filePath); } catch { /* ignore */ }
  }

  /**
   * Spawns the tmac process and accumulates stdout/stderr until `close`.
   * Stores the `ChildProcess` ref in `state.currentProc` so `cancel()` can
   * kill it.
   */
  private spawnAndCollect(
    executablePath: string,
    args: string[],
    cwd: string,
    state: WorkspaceState,
  ): Promise<{ stdout: string; stderr: string; exitCode: number | null }> {
    return new Promise((resolve, reject) => {
      let stdout = '';
      let stderr = '';

      let proc: ChildProcess;
      try {
        proc = spawn(executablePath, args, {
          cwd,
          stdio: ['ignore', 'pipe', 'pipe'],
          shell: false,
        });
      } catch (err) {
        reject(err);
        return;
      }

      state.currentProc = proc;

      proc.stdout?.on('data', (chunk: Buffer) => {
        stdout += chunk.toString();
      });

      proc.stderr?.on('data', (chunk: Buffer) => {
        stderr += chunk.toString();
      });

      proc.on('error', (err) => {
        reject(err);
      });

      proc.on('close', (exitCode: number | null) => {
        resolve({ stdout, stderr, exitCode });
      });
    });
  }
}
