/**
 * Unit tests for the severity mapper functions.
 *
 * Table-driven tests covering all 4 SARIF level → FindingSeverity mappings
 * and all 5 FindingSeverity → vscode.DiagnosticSeverity mappings.
 *
 * Validates: Requirements 3.5, 4.2
 */

import {
  sarifLevelToFindingSeverity,
  findingSeverityToVscodeSeverity,
} from '../../src/core/severityMapper';
import { DiagnosticSeverity } from '../../src/__mocks__/vscode';
import { FindingSeverity } from '../../src/core/models';

// ---------------------------------------------------------------------------
// sarifLevelToFindingSeverity — table-driven tests
// ---------------------------------------------------------------------------

describe('sarifLevelToFindingSeverity', () => {
  const table: Array<[string, FindingSeverity]> = [
    ['error', 'critical'],
    ['warning', 'medium'],
    ['note', 'info'],
    ['none', 'info'],
  ];

  test.each(table)('maps "%s" → "%s"', (level, expected) => {
    expect(sarifLevelToFindingSeverity(level)).toBe(expected);
  });

  it('defaults unrecognized levels to "info"', () => {
    expect(sarifLevelToFindingSeverity('unknown')).toBe('info');
    expect(sarifLevelToFindingSeverity('')).toBe('info');
    expect(sarifLevelToFindingSeverity('CRITICAL')).toBe('info');
  });
});

// ---------------------------------------------------------------------------
// findingSeverityToVscodeSeverity — table-driven tests
// ---------------------------------------------------------------------------

describe('findingSeverityToVscodeSeverity', () => {
  const table: Array<[FindingSeverity, DiagnosticSeverity]> = [
    ['critical', DiagnosticSeverity.Error],
    ['high', DiagnosticSeverity.Error],
    ['medium', DiagnosticSeverity.Warning],
    ['low', DiagnosticSeverity.Information],
    ['info', DiagnosticSeverity.Hint],
  ];

  test.each(table)('maps "%s" → DiagnosticSeverity.%s (%i)', (severity, expected) => {
    expect(findingSeverityToVscodeSeverity(severity)).toBe(expected);
  });

  it('"critical" maps to numeric value 0 (Error)', () => {
    expect(findingSeverityToVscodeSeverity('critical')).toBe(0);
  });

  it('"high" maps to numeric value 0 (Error)', () => {
    expect(findingSeverityToVscodeSeverity('high')).toBe(0);
  });

  it('"medium" maps to numeric value 1 (Warning)', () => {
    expect(findingSeverityToVscodeSeverity('medium')).toBe(1);
  });

  it('"low" maps to numeric value 2 (Information)', () => {
    expect(findingSeverityToVscodeSeverity('low')).toBe(2);
  });

  it('"info" maps to numeric value 3 (Hint)', () => {
    expect(findingSeverityToVscodeSeverity('info')).toBe(3);
  });
});
