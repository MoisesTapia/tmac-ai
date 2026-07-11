/**
 * Severity mapping utilities for the TMAC VSCode Plugin.
 *
 * Two pure functions that convert between SARIF levels, TMAC FindingSeverity
 * values, and VSCode DiagnosticSeverity values.
 *
 * The `vscode` import is satisfied by the Jest manual mock at
 * src/__mocks__/vscode.ts when running under Jest.
 */

import * as vscode from 'vscode';
import { FindingSeverity } from './models';

/**
 * Maps a SARIF 2.1.0 result `level` string to a {@link FindingSeverity}.
 *
 * | SARIF level | FindingSeverity |
 * |-------------|----------------|
 * | "error"     | "critical"      |
 * | "warning"   | "medium"        |
 * | "note"      | "info"          |
 * | "none"      | "info"          |
 * | (other)     | "info"          |
 */
export function sarifLevelToFindingSeverity(level: string): FindingSeverity {
  switch (level) {
    case 'error':
      return 'critical';
    case 'warning':
      return 'medium';
    case 'note':
      return 'info';
    case 'none':
      return 'info';
    default:
      return 'info';
  }
}

/**
 * Maps a {@link FindingSeverity} to a `vscode.DiagnosticSeverity`.
 *
 * | FindingSeverity | DiagnosticSeverity |
 * |-----------------|--------------------|
 * | "critical"      | Error (0)           |
 * | "high"          | Error (0)           |
 * | "medium"        | Warning (1)         |
 * | "low"           | Information (2)     |
 * | "info"          | Hint (3)            |
 */
export function findingSeverityToVscodeSeverity(
  s: FindingSeverity,
): vscode.DiagnosticSeverity {
  switch (s) {
    case 'critical':
      return vscode.DiagnosticSeverity.Error;
    case 'high':
      return vscode.DiagnosticSeverity.Error;
    case 'medium':
      return vscode.DiagnosticSeverity.Warning;
    case 'low':
      return vscode.DiagnosticSeverity.Information;
    case 'info':
      return vscode.DiagnosticSeverity.Hint;
  }
}
