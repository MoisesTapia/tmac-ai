/**
 * tmacResolver — TMAC CLI path resolution and version detection.
 *
 * Spawns `tmac --version` to verify the binary exists and parse its version
 * string. Supports a custom executable path via `TmacConfig.executablePath`.
 *
 * Requirements: 1.1–1.5
 */

import { spawn } from 'child_process';

// ---------------------------------------------------------------------------
// Config interface (subset used by the resolver)
// ---------------------------------------------------------------------------

export interface TmacConfig {
  /** Absolute path to the tmac binary. Empty string → use system PATH. */
  executablePath: string;
  scanOnSave: boolean;
  scanDelay: number;
  excludePatterns: string[];
  failOn: string;
  enableQuickFixes: boolean;
}

// ---------------------------------------------------------------------------
// Result types
// ---------------------------------------------------------------------------

export type ResolveResult =
  | { ok: true; path: string; version: string }
  | { ok: false; reason: 'not_found' | 'bad_path'; configuredPath?: string };

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

/**
 * Resolves the path to the `tmac` binary and returns its version string.
 *
 * - If `config.executablePath` is non-empty, uses that path.
 * - Otherwise, uses the string `"tmac"` (relies on the system PATH).
 *
 * On success returns `{ ok: true, path, version }`.
 * On failure returns:
 * - `{ ok: false, reason: 'bad_path', configuredPath }` when a custom path
 *   was set but the binary was not found at that location.
 * - `{ ok: false, reason: 'not_found' }` when no custom path was set and
 *   `tmac` is not on the system PATH.
 */
export function resolveTmacPath(config: TmacConfig): Promise<ResolveResult> {
  const customPath = config.executablePath.trim();
  const executablePath = customPath.length > 0 ? customPath : 'tmac';
  const usingCustomPath = customPath.length > 0;

  return new Promise<ResolveResult>((resolve) => {
    let stdout = '';
    let stderr = '';

    let proc: ReturnType<typeof spawn>;
    try {
      proc = spawn(executablePath, ['--version'], {
        stdio: ['ignore', 'pipe', 'pipe'],
        // Do not inherit shell — we want a clean PATH lookup
        shell: false,
      });
    } catch {
      // spawn() itself threw (e.g. ENOENT on some platforms)
      if (usingCustomPath) {
        resolve({ ok: false, reason: 'bad_path', configuredPath: customPath });
      } else {
        resolve({ ok: false, reason: 'not_found' });
      }
      return;
    }

    proc.stdout?.on('data', (chunk: Buffer) => {
      stdout += chunk.toString();
    });

    proc.stderr?.on('data', (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    proc.on('error', () => {
      // Binary not found or not executable
      if (usingCustomPath) {
        resolve({ ok: false, reason: 'bad_path', configuredPath: customPath });
      } else {
        resolve({ ok: false, reason: 'not_found' });
      }
    });

    proc.on('close', (code: number | null) => {
      if (code !== 0 && code !== null) {
        // Exited with a non-zero code — treat as unavailable
        if (usingCustomPath) {
          resolve({ ok: false, reason: 'bad_path', configuredPath: customPath });
        } else {
          resolve({ ok: false, reason: 'not_found' });
        }
        return;
      }

      // Parse version string from stdout (first non-empty token on the first line).
      // Example stdout: "tmac 1.2.3\n" or just "1.2.3\n"
      const combined = (stdout + '\n' + stderr).trim();
      const version = parseVersion(combined) ?? 'unknown';

      resolve({ ok: true, path: executablePath, version });
    });
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extracts a semver-like version string from a `--version` output string.
 * Returns the first token matching `\d+\.\d+(\.\d+)*` or `null` if not found.
 */
function parseVersion(output: string): string | null {
  const match = output.match(/\d+\.\d+(?:\.\d+)*/);
  return match ? match[0] : null;
}
