/**
 * Property-based tests for the HoverProvider (Properties 10–11).
 *
 * Uses fast-check with numRuns: 100.
 *
 * Validates: Requirements 5.2, 5.4
 */

import * as fc from 'fast-check';
import * as vscode from 'vscode';
import { HoverProviderImpl, buildFindingMarkdown } from '../../src/ui/hoverProvider';
import { Finding, FindingSeverity } from '../../src/core/models';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FILE_URI = '/workspace/main.tf';

/** Arbitrary for a non-empty FindingSeverity. */
const arbitrarySeverity = fc.constantFrom(
  'critical',
  'high',
  'medium',
  'low',
  'info',
) as fc.Arbitrary<FindingSeverity>;

/**
 * Arbitrary that produces a fully-populated Finding with non-empty required fields.
 * mitigation is non-empty so we can assert it appears in the markdown.
 */
function arbitraryFinding(): fc.Arbitrary<Finding> {
  return fc.record({
    ruleId: fc.string({ minLength: 1, maxLength: 30 }),
    message: fc.string({ minLength: 1, maxLength: 100 }),
    severity: arbitrarySeverity,
    strideCategory: fc.string({ minLength: 1, maxLength: 50 }),
    mitigation: fc.string({ minLength: 1, maxLength: 100 }),
    location: fc.record({
      fileUri: fc.constant(FILE_URI),
      startLine: fc.integer({ min: 1, max: 1000 }),
      startColumn: fc.integer({ min: 1, max: 200 }),
      locationUnknown: fc.constant(false),
    }),
  });
}

/**
 * Arbitrary that produces an array of ≥2 Findings all sharing the same
 * startLine so they all map to the same hovered position.
 */
function arbitraryMultiFindings(): fc.Arbitrary<Finding[]> {
  return fc.integer({ min: 1, max: 1000 }).chain((sharedLine) =>
    fc.array(
      arbitraryFinding().map((f) => ({
        ...f,
        location: { ...f.location, startLine: sharedLine },
      })),
      { minLength: 2, maxLength: 5 },
    ),
  );
}

/** Build a mock TextDocument for the given file path. */
function makeMockDocument(fsPath: string): vscode.TextDocument {
  return {
    uri: vscode.Uri.file(fsPath),
  } as unknown as vscode.TextDocument;
}

/** Build a mock Position at the given 0-based line. */
function makeMockPosition(line: number): vscode.Position {
  return new vscode.Position(line, 0);
}

/** Build a minimal CancellationToken stub. */
const mockToken: vscode.CancellationToken = {
  isCancellationRequested: false,
  onCancellationRequested: jest.fn(),
};

// ---------------------------------------------------------------------------
// Property 10: Hover markdown contains all required fields
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 10: Hover markdown contains all required fields
describe('Property 10: Hover markdown contains all required fields', () => {
  /**
   * Validates: Requirements 5.2
   *
   * For any arbitrary Finding with non-empty ruleId, severity, strideCategory,
   * message, and mitigation, buildFindingMarkdown() must produce a string that
   * contains each of those values as a substring.
   */
  it('markdown contains ruleId, severity, strideCategory, message, and mitigation', () => {
    fc.assert(
      fc.property(arbitraryFinding(), (finding) => {
        const markdown = buildFindingMarkdown(finding);

        // ruleId must appear verbatim
        expect(markdown).toContain(finding.ruleId);

        // severity must appear (case-insensitive — badge uses capitalised form)
        expect(markdown.toLowerCase()).toContain(finding.severity.toLowerCase());

        // strideCategory must appear verbatim
        expect(markdown).toContain(finding.strideCategory);

        // message must appear verbatim
        expect(markdown).toContain(finding.message);

        // mitigation must appear (non-empty by generator constraint)
        expect(markdown).toContain(finding.mitigation);
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 11: Multi-finding hover combines all findings
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 11: Multi-finding hover combines all findings
describe('Property 11: Multi-finding hover combines all findings', () => {
  /**
   * Validates: Requirements 5.4
   *
   * For any array of ≥2 Findings that all cover the same document position,
   * the combined hover response must:
   *   - not be undefined
   *   - contain every finding's ruleId
   *   - contain at least one '---' separator between findings
   */
  it('hover contains every ruleId and --- separators when multiple findings match', () => {
    fc.assert(
      fc.property(arbitraryMultiFindings(), (findings) => {
        const provider = new HoverProviderImpl();
        provider.updateFindings(findings);

        const sharedLine = findings[0].location.startLine; // 1-based
        const mockDoc = makeMockDocument(FILE_URI);
        const mockPos = makeMockPosition(sharedLine - 1); // convert to 0-based

        const hover = provider.provideHover(mockDoc, mockPos, mockToken);

        // hover must be defined
        expect(hover).toBeDefined();
        if (!hover) return;

        // Retrieve the combined markdown value.
        // hover.contents is typed as (MarkdownString | MarkedString)[] by @types/vscode,
        // but at runtime it holds a single vscode.MarkdownString (our mock class).
        const contents = hover.contents as unknown as vscode.MarkdownString[];
        const text = contents[0].value;

        // Every ruleId must appear in the combined output
        for (const finding of findings) {
          expect(text).toContain(finding.ruleId);
        }

        // There must be at least one --- separator (one per adjacent pair)
        expect(text).toContain('---');
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Example-based tests: Hover returns undefined for non-covered positions
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Task 4.10: HoverProvider example-based tests
describe('HoverProvider — example-based (Requirement 5.3)', () => {
  const mockToken: vscode.CancellationToken = {
    isCancellationRequested: false,
    onCancellationRequested: jest.fn(),
  };

  function makeMockDocument(fsPath: string): vscode.TextDocument {
    return { uri: vscode.Uri.file(fsPath) } as unknown as vscode.TextDocument;
  }

  /** Build a minimal Finding at a given file path and 1-based line. */
  function makeFinding(fsPath: string, startLine: number): Finding {
    return {
      ruleId: 'TMAC-TEST-001',
      message: 'Test finding message',
      severity: 'high' as Finding['severity'],
      strideCategory: 'Tampering',
      mitigation: 'Fix it.',
      location: {
        fileUri: fsPath,
        startLine,
        startColumn: 1,
        locationUnknown: false,
      },
    };
  }

  it('returns undefined when hovering over a position with no covering Finding', () => {
    // Provider has a finding at line 5 (1-based), hover at line 10 (0-based) → no match
    const provider = new HoverProviderImpl();
    provider.updateFindings([makeFinding('/workspace/main.tf', 5)]);

    const doc = makeMockDocument('/workspace/main.tf');
    const pos = new vscode.Position(9, 0); // line 10 (0-based = 9), not line 4

    const result = provider.provideHover(doc, pos, mockToken);

    expect(result).toBeUndefined();
  });

  it('returns undefined when the provider has no findings at all', () => {
    // Empty provider — hover anywhere should return undefined
    const provider = new HoverProviderImpl();
    provider.updateFindings([]);

    const doc = makeMockDocument('/workspace/main.tf');
    const pos = new vscode.Position(0, 0);

    const result = provider.provideHover(doc, pos, mockToken);

    expect(result).toBeUndefined();
  });

  it('returns undefined when hovering over a different file than the one with findings', () => {
    // Findings are for main.tf, but we hover in other.tf at the same line
    const provider = new HoverProviderImpl();
    provider.updateFindings([makeFinding('/workspace/main.tf', 3)]);

    const doc = makeMockDocument('/workspace/other.tf');
    const pos = new vscode.Position(2, 0); // line 3 (0-based = 2) — same line but different file

    const result = provider.provideHover(doc, pos, mockToken);

    expect(result).toBeUndefined();
  });
});
