/**
 * DiagnosticsManager — adapter between TMAC Finding[] and vscode.DiagnosticCollection.
 *
 * Responsibilities:
 *  - Translate Finding objects into vscode.Diagnostic instances (1-based → 0-based indexing)
 *  - Group updates by file URI and apply them atomically via collection.set()
 *  - Provide clearFile(), clearAll(), and dispose() lifecycle helpers
 *
 * The vscode import is satisfied by the Jest manual mock at
 * src/__mocks__/vscode.ts when running under Jest.
 */

import * as vscode from 'vscode';
import { Finding } from '../core/models';
import { findingSeverityToVscodeSeverity } from '../core/severityMapper';

// ---------------------------------------------------------------------------
// Interface
// ---------------------------------------------------------------------------

export interface DiagnosticsManager {
  /** Replace all diagnostics derived from the given Findings (grouped per file). */
  update(findings: Finding[]): void;
  /** Remove all diagnostics associated with the given file URI. */
  clearFile(uri: vscode.Uri): void;
  /** Remove all diagnostics from the collection. */
  clearAll(): void;
  /** Dispose the underlying DiagnosticCollection. */
  dispose(): void;
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

export class DiagnosticsManagerImpl implements DiagnosticsManager {
  private readonly collection: vscode.DiagnosticCollection;

  constructor(collection: vscode.DiagnosticCollection) {
    this.collection = collection;
  }

  /**
   * Translate an array of Findings into vscode.Diagnostics and push them to
   * the collection.  Updates are applied **per file, atomically**: a single
   * `collection.set(uri, diagnosticsArray)` call is made for each unique
   * fileUri so that VSCode replaces the previous set for that file in one
   * operation rather than appending.
   *
   * Coordinate conversion: SARIF / TMAC locations are 1-based; VSCode ranges
   * are 0-based.  The end of the range is set to the same line, column 0 of
   * the *next* character (i.e. end.character = Number.MAX_SAFE_INTEGER), which
   * effectively underlines the remainder of the line — a common pattern for
   * linter extensions that don't know the exact symbol length.
   */
  update(findings: Finding[]): void {
    // Group findings by their file URI string so we can set each file atomically.
    const byFile = new Map<string, Finding[]>();
    for (const finding of findings) {
      const key = finding.location.fileUri;
      const bucket = byFile.get(key);
      if (bucket) {
        bucket.push(finding);
      } else {
        byFile.set(key, [finding]);
      }
    }

    // For each unique file, build the Diagnostic array and apply it atomically.
    for (const [fileUriStr, filefindings] of byFile) {
      const uri = vscode.Uri.file(fileUriStr);
      const diagnostics = filefindings.map((finding) =>
        this._toDiagnostic(finding),
      );
      this.collection.set(uri, diagnostics);
    }
  }

  /** Remove all diagnostics for a single file. */
  clearFile(uri: vscode.Uri): void {
    this.collection.delete(uri);
  }

  /** Remove all diagnostics across every file. */
  clearAll(): void {
    this.collection.clear();
  }

  /** Dispose the underlying DiagnosticCollection, releasing VSCode resources. */
  dispose(): void {
    this.collection.dispose();
  }

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  /**
   * Convert a single Finding to a vscode.Diagnostic.
   *
   * Zero-index conversion:
   *   range.start.line      = finding.location.startLine - 1
   *   range.start.character = finding.location.startColumn - 1
   *   range.end             = same line, end of line (MAX_SAFE_INTEGER)
   *
   * Metadata:
   *   source = "tmac"
   *   code   = finding.ruleId  (e.g. "TMAC-AWS-S3-001")
   */
  private _toDiagnostic(finding: Finding): vscode.Diagnostic {
    const startLine = finding.location.startLine - 1;
    const startCharacter = finding.location.startColumn - 1;
    // Extend to end-of-line so the squiggle covers the rest of the line.
    const range = new vscode.Range(
      new vscode.Position(startLine, startCharacter),
      new vscode.Position(startLine, Number.MAX_SAFE_INTEGER),
    );

    const severity = findingSeverityToVscodeSeverity(finding.severity);
    const diagnostic = new vscode.Diagnostic(range, finding.message, severity);
    diagnostic.source = 'tmac';
    diagnostic.code = finding.ruleId;

    return diagnostic;
  }
}

// ---------------------------------------------------------------------------
// Factory helper
// ---------------------------------------------------------------------------

/**
 * Create a DiagnosticsManager backed by a freshly-created DiagnosticCollection
 * named "tmac".  Pass the returned manager's `dispose()` to
 * `context.subscriptions` so VSCode cleans it up on deactivation.
 */
export function createDiagnosticsManager(): DiagnosticsManager {
  const collection = vscode.languages.createDiagnosticCollection('tmac');
  return new DiagnosticsManagerImpl(collection);
}
