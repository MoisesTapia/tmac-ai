/**
 * Tests for DiagnosticsManagerImpl — property-based (Task 4.2, Properties 7–9)
 * and example-based (Task 4.3, Requirements 4.4 and 4.5).
 *
 * Import strategy:
 *   - DiagnosticsManagerImpl is imported from src so it can be compiled under
 *     ts-jest with the vscode mock in place.
 *   - Uri, MockDiagnosticCollection, and vscode types are imported directly
 *     from the mock source file so that the Uri type used in collection.get()
 *     matches exactly (no @types/vscode vs mock mismatch).
 *
 * Validates: Requirements 4.1, 4.3, 4.4, 4.5, 4.6, 4.7
 */

import * as fc from 'fast-check';
// Import directly from the mock so that Uri type is the mock's own class —
// this avoids the "@types/vscode Uri vs mock Uri" TypeScript mismatch.
import {
  Uri,
  MockDiagnosticCollection,
  DiagnosticSeverity,
} from '../../src/__mocks__/vscode';
import { DiagnosticsManagerImpl } from '../../src/ui/diagnosticsManager';
import { Finding, FindingSeverity } from '../../src/core/models';

// Re-export type alias for readability
type MockCollection = InstanceType<typeof MockDiagnosticCollection>;

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function makeFinding(
  fileUri: string,
  overrides: Partial<Finding> = {},
): Finding {
  return {
    ruleId: 'TMAC-TEST-001',
    message: 'Test finding',
    severity: 'medium' as FindingSeverity,
    strideCategory: 'Tampering',
    mitigation: 'Fix it.',
    location: {
      fileUri,
      startLine: 1,
      startColumn: 1,
      locationUnknown: false,
    },
    ...overrides,
  };
}

/** Create a fresh manager backed by a new MockDiagnosticCollection. */
function makeManager(): {
  manager: DiagnosticsManagerImpl;
  collection: MockCollection;
} {
  const collection = new MockDiagnosticCollection();
  // DiagnosticsManagerImpl accepts vscode.DiagnosticCollection; the mock is
  // structurally compatible at runtime so we cast via unknown.
  const manager = new DiagnosticsManagerImpl(
    collection as unknown as import('vscode').DiagnosticCollection,
  );
  return { manager, collection };
}

// ---------------------------------------------------------------------------
// Arbitrary Finding generator (for property-based tests)
// ---------------------------------------------------------------------------

function arbitraryFinding(): fc.Arbitrary<Finding> {
  return fc.record({
    ruleId: fc.string({ minLength: 1, maxLength: 30 }),
    message: fc.string({ minLength: 1, maxLength: 100 }),
    severity: fc.constantFrom(
      'critical',
      'high',
      'medium',
      'low',
      'info',
    ) as fc.Arbitrary<Finding['severity']>,
    strideCategory: fc.string({ minLength: 1 }),
    mitigation: fc.string(),
    location: fc.record({
      fileUri: fc.string({ minLength: 1 }).map(s => '/workspace/' + s),
      startLine: fc.integer({ min: 1, max: 10000 }),
      startColumn: fc.integer({ min: 1, max: 200 }),
      locationUnknown: fc.boolean(),
    }),
  });
}

// ===========================================================================
// Task 4.2 — Property-based tests (Properties 7–9)
// ===========================================================================

// ---------------------------------------------------------------------------
// Property 7: Diagnostic location mapping
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 7: Diagnostic location mapping
describe('Property 7: Diagnostic location mapping', () => {
  it('converts 1-based Finding locations to 0-based Diagnostic ranges', () => {
    fc.assert(
      fc.property(
        fc.array(arbitraryFinding(), { minLength: 1, maxLength: 10 }),
        (findings) => {
          const { manager, collection } = makeManager();
          manager.update(findings);

          for (const finding of findings) {
            const uri = Uri.file(finding.location.fileUri);
            const diagnostics = collection.get(uri);

            // There must be at least one diagnostic for this file.
            expect(diagnostics).toBeDefined();
            expect(diagnostics!.length).toBeGreaterThan(0);

            // Locate the diagnostic matching this finding by its expected
            // 0-based start position.
            const expectedLine = finding.location.startLine - 1;
            const expectedCharacter = finding.location.startColumn - 1;

            const matched = diagnostics!.find(
              d =>
                d.range.start.line === expectedLine &&
                d.range.start.character === expectedCharacter,
            );

            expect(matched).toBeDefined();
            expect(matched!.range.start.line).toBe(expectedLine);
            expect(matched!.range.start.character).toBe(expectedCharacter);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 8: Diagnostic update atomicity / last-write-wins
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 8: Diagnostic update atomicity / last-write-wins
describe('Property 8: Diagnostic update atomicity / last-write-wins', () => {
  it('only retains diagnostics from the second update call for the same URI', () => {
    const uri = '/workspace/main.tf';

    // Give each batch a distinguishable ruleId prefix so we can detect leakage.
    const arbitraryFindingForUri = (ruleIdPrefix: string) =>
      arbitraryFinding().map(f => ({
        ...f,
        ruleId: ruleIdPrefix + f.ruleId,
        location: { ...f.location, fileUri: uri },
      }));

    fc.assert(
      fc.property(
        fc.array(arbitraryFindingForUri('FIRST-'), { minLength: 1, maxLength: 5 }),
        fc.array(arbitraryFindingForUri('SECOND-'), { minLength: 1, maxLength: 5 }),
        (firstFindings, secondFindings) => {
          const { manager, collection } = makeManager();

          // First update — will be replaced by the second.
          manager.update(firstFindings);
          // Second update — must atomically replace everything for this URI.
          manager.update(secondFindings);

          const vsUri = Uri.file(uri);
          const diagnostics = collection.get(vsUri) ?? [];

          // Count must match the second batch exactly.
          expect(diagnostics).toHaveLength(secondFindings.length);

          // Every remaining diagnostic must come from the second call.
          for (const diag of diagnostics) {
            expect(String(diag.code)).toMatch(/^SECOND-/);
          }

          // No diagnostic from the first call should remain.
          const hasFirstCallDiag = diagnostics.some(d =>
            String(d.code).startsWith('FIRST-'),
          );
          expect(hasFirstCallDiag).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 9: Diagnostic metadata invariants
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 9: Diagnostic metadata invariants
describe('Property 9: Diagnostic metadata invariants', () => {
  it('sets source="tmac" and code=finding.ruleId on every Diagnostic', () => {
    fc.assert(
      fc.property(
        fc.array(arbitraryFinding(), { minLength: 1, maxLength: 10 }),
        (findings) => {
          const { manager, collection } = makeManager();
          manager.update(findings);

          for (const finding of findings) {
            const uri = Uri.file(finding.location.fileUri);
            const diagnostics = collection.get(uri);

            expect(diagnostics).toBeDefined();

            // Locate the diagnostic by ruleId (stored as `code`).
            const matched = diagnostics!.find(d => d.code === finding.ruleId);
            expect(matched).toBeDefined();

            expect(matched!.source).toBe('tmac');
            expect(matched!.code).toBe(finding.ruleId);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ===========================================================================
// Task 4.3 — Example-based unit tests (Requirements 4.4 and 4.5)
// ===========================================================================

describe('DiagnosticsManagerImpl — example-based (Task 4.3)', () => {
  // -------------------------------------------------------------------------
  // Requirement 4.4 — clearFile() removes only the targeted URI's diagnostics
  // -------------------------------------------------------------------------
  describe('clearFile() selectively removes only the targeted URI', () => {
    it('removes diagnostics for the specified file but leaves other files intact', () => {
      const { manager, collection } = makeManager();

      const mainUri = '/workspace/main.tf';
      const otherUri = '/workspace/other.tf';

      manager.update([
        makeFinding(mainUri),
        makeFinding(otherUri, { ruleId: 'TMAC-TEST-002', message: 'Other finding' }),
      ]);

      expect(collection.get(Uri.file(mainUri))).toHaveLength(1);
      expect(collection.get(Uri.file(otherUri))).toHaveLength(1);

      manager.clearFile(Uri.file(mainUri) as unknown as import('vscode').Uri);

      expect(collection.has(Uri.file(mainUri))).toBe(false);
      expect(collection.get(Uri.file(otherUri))).toHaveLength(1);
      expect(collection.get(Uri.file(otherUri))![0].message).toBe('Other finding');
    });

    it('does nothing when clearing a file that has no diagnostics', () => {
      const { manager, collection } = makeManager();

      const knownUri = '/workspace/known.tf';
      const unknownUri = '/workspace/unknown.tf';

      manager.update([makeFinding(knownUri)]);
      expect(collection.get(Uri.file(knownUri))).toHaveLength(1);

      expect(() =>
        manager.clearFile(Uri.file(unknownUri) as unknown as import('vscode').Uri),
      ).not.toThrow();
      expect(collection.get(Uri.file(knownUri))).toHaveLength(1);
    });

    it('removes all diagnostics for a file that had multiple findings', () => {
      const { manager, collection } = makeManager();

      const targetUri = '/workspace/target.tf';
      const keepUri = '/workspace/keep.tf';

      manager.update([
        makeFinding(targetUri, { ruleId: 'TMAC-A', message: 'Finding A' }),
        makeFinding(targetUri, {
          ruleId: 'TMAC-B',
          message: 'Finding B',
          location: {
            fileUri: targetUri,
            startLine: 5,
            startColumn: 3,
            locationUnknown: false,
          },
        }),
        makeFinding(keepUri, { ruleId: 'TMAC-C', message: 'Finding C' }),
      ]);

      expect(collection.get(Uri.file(targetUri))).toHaveLength(2);
      expect(collection.get(Uri.file(keepUri))).toHaveLength(1);

      manager.clearFile(Uri.file(targetUri) as unknown as import('vscode').Uri);

      expect(collection.has(Uri.file(targetUri))).toBe(false);
      expect(collection.get(Uri.file(keepUri))).toHaveLength(1);
    });
  });

  // -------------------------------------------------------------------------
  // Requirement 4.5 — clearAll() is independent of StatusBar failures
  // -------------------------------------------------------------------------
  describe('clearAll() succeeds independently of subsequent StatusBar failure (Req 4.5)', () => {
    it('clears all diagnostics even when a subsequent statusBar update throws', () => {
      const { manager, collection } = makeManager();

      const fileA = '/workspace/a.tf';
      const fileB = '/workspace/b.tf';

      manager.update([makeFinding(fileA), makeFinding(fileB)]);
      expect(collection.size).toBe(2);

      const faultyStatusBar = {
        update: jest.fn(() => {
          throw new Error('StatusBar update failed');
        }),
      };

      manager.clearAll();
      expect(collection.size).toBe(0);
      expect(collection.has(Uri.file(fileA))).toBe(false);
      expect(collection.has(Uri.file(fileB))).toBe(false);

      // Simulated StatusBar failure must not undo the already-completed clear.
      expect(() => faultyStatusBar.update()).toThrow('StatusBar update failed');
      expect(collection.size).toBe(0);
    });

    it('clears all diagnostics across multiple files', () => {
      const { manager, collection } = makeManager();

      manager.update([
        makeFinding('/workspace/alpha.tf'),
        makeFinding('/workspace/beta.tf'),
        makeFinding('/workspace/gamma.tf'),
      ]);
      expect(collection.size).toBe(3);

      manager.clearAll();
      expect(collection.size).toBe(0);
    });

    it('clearAll() on an already-empty collection does not throw', () => {
      const { manager, collection } = makeManager();
      expect(() => manager.clearAll()).not.toThrow();
      expect(collection.size).toBe(0);
    });
  });
});
