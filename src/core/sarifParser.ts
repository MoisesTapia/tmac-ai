/**
 * SARIF 2.1.0 parser for the TMAC VSCode Plugin.
 *
 * Pure module — no VSCode API imports. Converts raw SARIF JSON text produced
 * by `tmac scan --report json` into a {@link ParseResult}.
 */

import * as path from 'path';
import { fileURLToPath } from 'url';
import {
  Finding,
  FindingSeverity,
  ParseResult,
  SarifResult,
} from './models';
import { sarifLevelToFindingSeverity } from './severityMapper';

// ---------------------------------------------------------------------------
// URI resolution helper
// ---------------------------------------------------------------------------

/**
 * Resolves a SARIF artifact URI to an absolute file-system path.
 *
 * - Absolute paths are returned as-is.
 * - `file://` URIs are converted via `fileURLToPath` then returned.
 * - Relative URIs are resolved against `workspaceRoot`.
 */
function resolveUri(uri: string, workspaceRoot: string): string {
  if (path.isAbsolute(uri)) {
    return uri;
  }
  if (uri.startsWith('file://')) {
    return fileURLToPath(uri);
  }
  return path.resolve(workspaceRoot, uri);
}

// ---------------------------------------------------------------------------
// Main parse function
// ---------------------------------------------------------------------------

/**
 * Parses a SARIF 2.1.0 JSON string into a {@link ParseResult}.
 *
 * @param json          - Raw JSON string from `tmac scan --report json` stdout.
 * @param workspaceRoot - Absolute path to the scanned workspace folder; used
 *                        to resolve relative artifact URIs and as the fallback
 *                        `fileUri` when physical location is absent.
 */
export function parseSarif(json: string, workspaceRoot: string): ParseResult {
  // Step 1: Parse JSON — catch SyntaxError.
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return { ok: false, error: { kind: 'invalid_json', message } };
  }

  // Step 2: Validate presence of `runs` array.
  if (
    typeof parsed !== 'object' ||
    parsed === null ||
    !('runs' in parsed) ||
    !Array.isArray((parsed as Record<string, unknown>)['runs'])
  ) {
    return {
      ok: false,
      error: {
        kind: 'schema_error',
        message: "SARIF document is missing required 'runs' array",
      },
    };
  }

  // Step 3: Extract findings from runs[0].results.
  const log = parsed as { runs: Array<{ results?: SarifResult[] }> };
  const firstRun = log.runs[0];
  const results: SarifResult[] = firstRun?.results ?? [];

  const findings: Finding[] = results.map((result): Finding => {
    // --- Severity ---
    let severity: FindingSeverity;
    const propSeverity = result.properties?.severity;
    if (
      propSeverity === 'critical' ||
      propSeverity === 'high' ||
      propSeverity === 'medium' ||
      propSeverity === 'low' ||
      propSeverity === 'info'
    ) {
      severity = propSeverity;
    } else {
      severity = sarifLevelToFindingSeverity(result.level);
    }

    // --- STRIDE category ---
    const strideCategory = result.properties?.stride ?? 'Unknown';

    // --- Mitigation ---
    const mitigation = result.properties?.mitigation ?? '';

    // --- Physical location ---
    const physLoc =
      result.locations?.[0]?.physicalLocation;

    let fileUri: string;
    let startLine: number;
    let startColumn: number;
    let locationUnknown: boolean;

    if (physLoc) {
      const rawUri = physLoc.artifactLocation.uri;
      fileUri = resolveUri(rawUri, workspaceRoot);
      startLine = physLoc.region?.startLine ?? 1;
      startColumn = physLoc.region?.startColumn ?? 1;
      locationUnknown = false;
    } else {
      fileUri = workspaceRoot;
      startLine = 1;
      startColumn = 1;
      locationUnknown = true;
    }

    return {
      ruleId: result.ruleId,
      message: result.message.text,
      severity,
      strideCategory,
      mitigation,
      location: {
        fileUri,
        startLine,
        startColumn,
        locationUnknown,
      },
    };
  });

  return {
    ok: true,
    result: {
      findings,
      scannedAt: new Date(),
      workspaceRoot,
    },
  };
}
