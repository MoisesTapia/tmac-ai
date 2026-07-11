/**
 * Property-based tests for the SARIF parser (Properties 1–6).
 *
 * Uses fast-check with numRuns: 100.
 *
 * Validates: Requirements 3.1–3.9
 */

import * as path from 'path';
import * as fc from 'fast-check';
import { parseSarif } from '../../src/core/sarifParser';
import { FindingSeverity, SarifResult } from '../../src/core/models';

// ---------------------------------------------------------------------------
// Helper arbitraries
// ---------------------------------------------------------------------------

const SEVERITY_VALUES: FindingSeverity[] = ['critical', 'high', 'medium', 'low', 'info'];
const SARIF_LEVEL_VALUES = ['error', 'warning', 'note', 'none'] as const;

/** Arbitrary that generates a non-empty alphanumeric identifier string. */
const arbIdentifier = fc.stringMatching(/^[A-Za-z][A-Za-z0-9_-]{0,30}$/);

/** Arbitrary for a valid FindingSeverity string. */
const arbFindingSeverity = fc.constantFrom(...SEVERITY_VALUES);

/** Arbitrary for a valid SARIF level. */
const arbSarifLevel = fc.constantFrom(...SARIF_LEVEL_VALUES);

/**
 * Arbitrary for a fully-populated SarifResult with a physicalLocation,
 * explicit properties.severity, stride, and mitigation.
 */
function arbFullSarifResult(): fc.Arbitrary<SarifResult> {
  return fc.record({
    ruleId: arbIdentifier,
    level: arbSarifLevel,
    message: fc.record({ text: fc.string({ minLength: 1, maxLength: 200 }) }),
    locations: fc.tuple(
      fc.record({
        physicalLocation: fc.record({
          artifactLocation: fc.record({
            uri: fc.string({ minLength: 1, maxLength: 50 }).filter(s =>
              /^[A-Za-z0-9_/.-]+$/.test(s) && !s.startsWith('/')
            ),
          }),
          region: fc.record({
            startLine: fc.integer({ min: 1, max: 10_000 }),
            startColumn: fc.integer({ min: 1, max: 500 }),
          }),
        }),
      }),
    ).map(t => [t[0]]),
    properties: fc.record({
      severity: arbFindingSeverity,
      stride: arbIdentifier,
      mitigation: fc.string({ maxLength: 200 }),
    }),
  });
}

/**
 * Arbitrary for a SarifResult with no physicalLocation (locations missing
 * entirely or empty array).
 */
function arbSarifResultNoLocation(): fc.Arbitrary<SarifResult> {
  return fc.record({
    ruleId: arbIdentifier,
    level: arbSarifLevel,
    message: fc.record({ text: fc.string({ minLength: 1 }) }),
    locations: fc.constantFrom(undefined, [] as []),
    properties: fc.option(
      fc.record({
        severity: fc.option(arbFindingSeverity, { nil: undefined }),
        stride: fc.option(arbIdentifier, { nil: undefined }),
        mitigation: fc.option(fc.string(), { nil: undefined }),
      }),
      { nil: undefined },
    ),
  }) as fc.Arbitrary<SarifResult>;
}

/**
 * Wraps an array of SarifResults into a minimal SARIF 2.1.0 log object.
 */
function wrapInSarifLog(results: SarifResult[]): object {
  return {
    version: '2.1.0',
    runs: [
      {
        tool: { driver: { name: 'tmac', version: '1.0.0' } },
        results,
      },
    ],
  };
}

/** Fisher-Yates shuffle (returns a new array). */
function shuffle<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// ---------------------------------------------------------------------------
// Property 1: SARIF field extraction round-trip
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 1: SARIF field extraction round-trip
describe('Property 1: SARIF field extraction round-trip', () => {
  it('extracts all fields from a fully-populated SARIF result', () => {
    fc.assert(
      fc.property(fc.array(arbFullSarifResult(), { minLength: 1, maxLength: 5 }), (sarifResults) => {
        const sarif = wrapInSarifLog(sarifResults);
        const parsed = parseSarif(JSON.stringify(sarif), '/workspace');

        expect(parsed.ok).toBe(true);
        if (!parsed.ok) return;

        const findings = parsed.result.findings;
        expect(findings).toHaveLength(sarifResults.length);

        for (let i = 0; i < sarifResults.length; i++) {
          const sr = sarifResults[i];
          const f = findings[i];

          expect(f.ruleId).toBe(sr.ruleId);
          expect(f.message).toBe(sr.message.text);
          // severity comes from properties.severity when present
          expect(f.severity).toBe(sr.properties?.severity);
          expect(f.strideCategory).toBe(sr.properties?.stride);
          expect(f.mitigation).toBe(sr.properties?.mitigation);

          const region = sr.locations![0].physicalLocation!.region!;
          expect(f.location.startLine).toBe(region.startLine);
          expect(f.location.startColumn).toBe(region.startColumn);
        }
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 2: Relative URI resolution
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 2: Relative URI resolution
describe('Property 2: Relative URI resolution', () => {
  it('resolves relative URIs against workspaceRoot', () => {
    /** Arbitrary for a relative URI using safe alphanumeric path segments. */
    const arbRelativeUri = fc
      .array(
        fc.stringMatching(/^[A-Za-z0-9_-]+$/),
        { minLength: 1, maxLength: 4 },
      )
      .map(segments => segments.join('/') + '.tf');

    /** Arbitrary for an absolute workspace root path. */
    const arbWorkspaceRoot = fc
      .array(
        fc.stringMatching(/^[A-Za-z0-9_-]+$/),
        { minLength: 1, maxLength: 4 },
      )
      .map(segments => '/' + segments.join('/'));

    fc.assert(
      fc.property(arbRelativeUri, arbWorkspaceRoot, (relativeUri, workspaceRoot) => {
        const result: SarifResult = {
          ruleId: 'RULE-001',
          level: 'error',
          message: { text: 'test message' },
          locations: [
            {
              physicalLocation: {
                artifactLocation: { uri: relativeUri },
                region: { startLine: 1, startColumn: 1 },
              },
            },
          ],
        };

        const sarif = wrapInSarifLog([result]);
        const parsed = parseSarif(JSON.stringify(sarif), workspaceRoot);

        expect(parsed.ok).toBe(true);
        if (!parsed.ok) return;

        const expectedUri = path.resolve(workspaceRoot, relativeUri);
        expect(parsed.result.findings[0].location.fileUri).toBe(expectedUri);
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 3: Missing location fallback
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 3: Missing location fallback
describe('Property 3: Missing location fallback', () => {
  it('uses workspaceRoot and line/col 1 when physicalLocation is absent', () => {
    fc.assert(
      fc.property(arbSarifResultNoLocation(), (sarifResult) => {
        const workspaceRoot = '/test/workspace';
        const sarif = wrapInSarifLog([sarifResult]);
        const parsed = parseSarif(JSON.stringify(sarif), workspaceRoot);

        expect(parsed.ok).toBe(true);
        if (!parsed.ok) return;

        const loc = parsed.result.findings[0].location;
        expect(loc.startLine).toBe(1);
        expect(loc.startColumn).toBe(1);
        expect(loc.locationUnknown).toBe(true);
        expect(loc.fileUri).toBe(workspaceRoot);
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 4: Result order independence
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 4: Result order independence
describe('Property 4: Result order independence', () => {
  it('produces identical Finding sets regardless of result ordering', () => {
    fc.assert(
      fc.property(
        fc.array(arbFullSarifResult(), { minLength: 2, maxLength: 6 }),
        (sarifResults) => {
          const workspaceRoot = '/workspace';
          const shuffled = shuffle(sarifResults);

          const parsedOriginal = parseSarif(
            JSON.stringify(wrapInSarifLog(sarifResults)),
            workspaceRoot,
          );
          const parsedShuffled = parseSarif(
            JSON.stringify(wrapInSarifLog(shuffled)),
            workspaceRoot,
          );

          expect(parsedOriginal.ok).toBe(true);
          expect(parsedShuffled.ok).toBe(true);
          if (!parsedOriginal.ok || !parsedShuffled.ok) return;

          const sortedOriginal = [...parsedOriginal.result.findings]
            .map(f => f.ruleId)
            .sort();
          const sortedShuffled = [...parsedShuffled.result.findings]
            .map(f => f.ruleId)
            .sort();

          expect(sortedShuffled).toEqual(sortedOriginal);
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 5: Invalid JSON always produces invalid_json error
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 5: Invalid JSON always produces invalid_json error
describe('Property 5: Invalid JSON always produces invalid_json error', () => {
  it('returns { ok: false, error: { kind: "invalid_json" } } for non-JSON input', () => {
    // Generate strings that are NOT valid JSON
    const arbNonJson = fc.string().filter(s => {
      try {
        JSON.parse(s);
        return false; // valid JSON — skip
      } catch {
        return true; // invalid JSON — keep
      }
    });

    fc.assert(
      fc.property(arbNonJson, (s) => {
        let result: ReturnType<typeof parseSarif>;
        expect(() => {
          result = parseSarif(s, '/workspace');
        }).not.toThrow();

        expect(result!.ok).toBe(false);
        if (result!.ok) return;
        expect(result!.error.kind).toBe('invalid_json');
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 6: Valid JSON without runs always produces schema_error
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 6: Valid JSON without runs always produces schema_error
describe('Property 6: Valid JSON without runs always produces schema_error', () => {
  it('returns { ok: false, error: { kind: "schema_error" } } for JSON without a runs array', () => {
    /**
     * Generate arbitrary JSON values that are NOT objects with a `runs` array:
     * - Primitives: null, booleans, numbers, strings
     * - Arrays (top-level)
     * - Objects without a `runs` key
     * - Objects where `runs` is not an array (object, number, string, null)
     */
    const arbNoRunsValue: fc.Arbitrary<unknown> = fc.oneof(
      fc.constant(null),
      fc.boolean(),
      fc.integer(),
      fc.double({ noNaN: true, noDefaultInfinity: true }),
      fc.string(),
      fc.array(fc.anything()),
      // Objects without `runs`
      fc.dictionary(
        fc.string().filter(k => k !== 'runs'),
        fc.anything(),
      ),
      // Objects where `runs` is not an array
      fc.record({ runs: fc.oneof(fc.constant(null), fc.integer(), fc.string(), fc.record({})) }),
    );

    fc.assert(
      fc.property(arbNoRunsValue, (v) => {
        const json = JSON.stringify(v);
        let result: ReturnType<typeof parseSarif>;
        expect(() => {
          result = parseSarif(json, '/workspace');
        }).not.toThrow();

        expect(result!.ok).toBe(false);
        if (result!.ok) return;
        expect(result!.error.kind).toBe('schema_error');
      }),
      { numRuns: 100 },
    );
  });
});
