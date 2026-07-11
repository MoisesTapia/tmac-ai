/**
 * Shared data model interfaces and types for the TMAC VSCode Plugin.
 *
 * This module is pure TypeScript — no VSCode API dependencies — so it can be
 * imported by both the extension host and Jest unit tests.
 */

// ---------------------------------------------------------------------------
// Finding and location types
// ---------------------------------------------------------------------------

export interface Finding {
  ruleId: string;
  message: string;
  severity: FindingSeverity;
  strideCategory: string;
  mitigation: string;
  location: FindingLocation;
}

export interface FindingLocation {
  fileUri: string;
  startLine: number;
  startColumn: number;
  locationUnknown: boolean;
}

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

// ---------------------------------------------------------------------------
// Scan types
// ---------------------------------------------------------------------------

export interface ScanResult {
  findings: Finding[];
  scannedAt: Date;
  workspaceRoot: string;
  rawSarif?: string;
}

export type ScanState = 'idle' | 'scanning' | 'error' | 'unavailable';

// ---------------------------------------------------------------------------
// Parse result types
// ---------------------------------------------------------------------------

export type ParseResult =
  | { ok: true; result: ScanResult }
  | { ok: false; error: ParseError };

export type ParseError =
  | { kind: 'invalid_json'; message: string }
  | { kind: 'schema_error'; message: string };

// ---------------------------------------------------------------------------
// SARIF 2.1.0 internal shape (used only by sarifParser)
// ---------------------------------------------------------------------------

export interface SarifLog {
  version: string;
  runs: SarifRun[];
}

export interface SarifRun {
  tool: { driver: { name: string; version?: string } };
  results: SarifResult[];
}

export interface SarifResult {
  ruleId: string;
  level: 'error' | 'warning' | 'note' | 'none';
  message: { text: string };
  locations?: SarifLocation[];
  properties?: {
    severity?: string;
    stride?: string;
    mitigation?: string;
  };
}

export interface SarifLocation {
  physicalLocation?: {
    artifactLocation: { uri: string; uriBaseId?: string };
    region?: { startLine: number; startColumn: number };
  };
}
