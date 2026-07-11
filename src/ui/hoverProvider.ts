/**
 * HoverProvider - surfaces TMAC Finding details when the user hovers over a
 * Diagnostic region in a Terraform file.
 *
 * Responsibilities:
 *  - Maintain an internal per-file index (Map<fileUri, Finding[]>) rebuilt on
 *    each updateFindings() call.
 *  - On provideHover(), perform an O(n) scan over the findings for the
 *    current file to find those whose start line covers the hovered position.
 *  - Build a vscode.MarkdownString per matching Finding (severity badge,
 *    rule ID, STRIDE, message, mitigation) and combine multiple findings with
 *    a `---` horizontal rule separator.
 *  - Register for language ID 'terraform' and glob '**&#47;*.tf'.
 *
 * The vscode import is satisfied by the Jest manual mock at
 * src/__mocks__/vscode.ts when running under Jest.
 */

import * as vscode from 'vscode';
import { Finding, FindingSeverity } from '../core/models';

// ---------------------------------------------------------------------------
// Severity badge map (Requirement 5.5)
// ---------------------------------------------------------------------------

const SEVERITY_BADGE: Record<FindingSeverity, string> = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🟢',
  info: '🔵',
};

// ---------------------------------------------------------------------------
// Interface
// ---------------------------------------------------------------------------

export interface HoverProvider extends vscode.HoverProvider {
  /**
   * Rebuild the internal per-file Finding index from the latest scan result.
   * Called by the extension after each completed scan.
   */
  updateFindings(findings: Finding[]): void;
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

export class HoverProviderImpl implements HoverProvider {
  /**
   * Internal index: absolute fileUri → array of Findings for that file.
   * Rebuilt wholesale on every `updateFindings()` call.
   */
  private _index = new Map<string, Finding[]>();

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /**
   * Rebuild the per-file Finding index.  Completely replaces any previous
   * state so that stale findings from an earlier scan are never shown.
   */
  updateFindings(findings: Finding[]): void {
    this._index.clear();

    for (const finding of findings) {
      const key = finding.location.fileUri;
      const bucket = this._index.get(key);
      if (bucket) {
        bucket.push(finding);
      } else {
        this._index.set(key, [finding]);
      }
    }
  }

  /**
   * VSCode calls this when the user hovers over a position in a document.
   *
   * Position coverage check: a Finding covers a position when
   *   `position.line` (0-based) === `finding.location.startLine - 1`
   * (i.e. the hover is on the same line as the finding's start line, which
   * is the line underlined by the corresponding Diagnostic).
   *
   * Returns `undefined` when no finding covers the position (Requirement 5.3).
   * Returns a combined `vscode.Hover` for one or more matching findings
   * (Requirements 5.2, 5.4).
   */
  provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
    _token: vscode.CancellationToken,
  ): vscode.Hover | undefined {
    const fileUri = document.uri.fsPath;
    const filefindings = this._index.get(fileUri);

    if (!filefindings || filefindings.length === 0) {
      return undefined;
    }

    // O(n) scan: collect all findings whose start line covers this position.
    const matching: Finding[] = [];
    for (const finding of filefindings) {
      const findingLine = finding.location.startLine - 1; // convert to 0-based
      if (findingLine === position.line) {
        matching.push(finding);
      }
    }

    if (matching.length === 0) {
      return undefined;
    }

    // Build a combined MarkdownString, separating multiple findings with ---
    const combined = new vscode.MarkdownString('');
    combined.isTrusted = true;
    combined.supportThemeIcons = true;

    matching.forEach((finding, index) => {
      if (index > 0) {
        combined.appendMarkdown('\n\n---\n\n');
      }
      combined.appendMarkdown(buildFindingMarkdown(finding));
    });

    return new vscode.Hover(combined);
  }
}

// ---------------------------------------------------------------------------
// Markdown builder
// ---------------------------------------------------------------------------

/**
 * Build the Markdown block for a single Finding.
 *
 * Format (Requirement 5.2, 5.5):
 *
 * **$(shield) TMAC — TMAC-AWS-S3-001**
 *
 * 🔴 **Critical** · STRIDE: Tampering
 *
 * Resource `aws_s3_bucket.example` has public ACL enabled.
 *
 * **Mitigation:** Set `acl = "private"` and enable bucket policy.
 */
export function buildFindingMarkdown(finding: Finding): string {
  const badge = SEVERITY_BADGE[finding.severity] ?? '🔵';
  const severityLabel =
    finding.severity.charAt(0).toUpperCase() + finding.severity.slice(1);
  const mitigationLine =
    finding.mitigation.trim().length > 0
      ? `\n\n**Mitigation:** ${finding.mitigation}`
      : '';

  return [
    `**$(shield) TMAC — ${finding.ruleId}**`,
    '',
    `${badge} **${severityLabel}** · STRIDE: ${finding.strideCategory}`,
    '',
    finding.message,
    mitigationLine,
  ].join('\n');
}

// ---------------------------------------------------------------------------
// Factory helper + registration
// ---------------------------------------------------------------------------

/**
 * Create a HoverProviderImpl instance, register it for `terraform` language
 * and the `**\/*.tf` glob, and return both the provider and the disposable
 * so the extension entry-point can push the disposable to `context.subscriptions`.
 */
export function createHoverProvider(): {
  provider: HoverProviderImpl;
  disposable: vscode.Disposable;
} {
  const provider = new HoverProviderImpl();

  // Register for documents with language ID 'terraform' (Requirement 5.1)
  const disposable = vscode.languages.registerHoverProvider(
    [
      { language: 'terraform' },
      { pattern: '**/*.tf' },
    ],
    provider,
  );

  return { provider, disposable };
}
