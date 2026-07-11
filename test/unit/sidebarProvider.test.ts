/**
 * Property-based tests for SidebarProvider (Properties 12–13).
 *
 * Feature: tmac-vscode-plugin
 * Uses fast-check with numRuns: 100 per property.
 */

import * as fc from 'fast-check';
import { SidebarProviderImpl } from '../../src/ui/sidebarProvider';
import type { FileNode, FindingNode } from '../../src/ui/sidebarProvider';
import type { Finding, FindingSeverity } from '../../src/core/models';

// ---------------------------------------------------------------------------
// Arbitrary helpers
// ---------------------------------------------------------------------------

/**
 * Build an arbitrary Finding pinned to a specific fileUri.
 */
function arbitraryFindingWithUri(uri: string): fc.Arbitrary<Finding> {
  return fc.record({
    ruleId: fc.string({ minLength: 1 }),
    message: fc.string({ minLength: 1 }),
    severity: fc.constantFrom(
      'critical',
      'high',
      'medium',
      'low',
      'info',
    ) as fc.Arbitrary<FindingSeverity>,
    strideCategory: fc.string(),
    mitigation: fc.string(),
    location: fc.record({
      fileUri: fc.constant(uri),
      startLine: fc.integer({ min: 1, max: 1000 }),
      startColumn: fc.integer({ min: 1, max: 200 }),
      locationUnknown: fc.constant(false),
    }),
  });
}

// ---------------------------------------------------------------------------
// Property 12: Sidebar grouping correctness
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 12: Sidebar grouping correctness
describe('Property 12: Sidebar grouping correctness', () => {
  it(
    'produces exactly one FileNode per unique fileUri and findingCount matches',
    () => {
      fc.assert(
        fc.property(
          // Generate 1-3 unique URIs then build a list of findings spread across them.
          // We pick from a fixed pool of 3 URIs so we get meaningful grouping.
          fc
            .array(
              fc.constantFrom(
                '/workspace/a.tf',
                '/workspace/b.tf',
                '/workspace/c.tf',
              ),
              { minLength: 1, maxLength: 3 },
            )
            .chain((uriPool) => {
              const uniqueUris = Array.from(new Set(uriPool));

              // For each unique URI, generate 1–5 findings
              const findingArbitraries = uniqueUris.map((uri) =>
                fc.array(arbitraryFindingWithUri(uri), {
                  minLength: 1,
                  maxLength: 5,
                }),
              );

              return (
                fc.tuple(
                  ...(findingArbitraries as [
                    fc.Arbitrary<Finding[]>,
                    ...fc.Arbitrary<Finding[]>[],
                  ]),
                ) as fc.Arbitrary<Finding[][]>
              ).map((groups) => ({
                findings: groups.flat(),
                uniqueUris,
              }));
            }),
          ({ findings, uniqueUris }) => {
            const provider = new SidebarProviderImpl();
            provider.refresh(findings, 'idle');

            const rootItems = provider.getChildren();

            // All root items should be FileNodes when state === 'idle' and findings.length > 0
            const fileNodes = rootItems.filter(
              (item): item is FileNode => item.kind === 'file',
            );

            // Assert: exactly one FileNode per unique fileUri
            expect(fileNodes).toHaveLength(uniqueUris.length);

            // Assert: each FileNode's findingCount matches the number of findings for that URI
            for (const fileNode of fileNodes) {
              const uri = fileNode.uri.fsPath;
              const expectedCount = findings.filter(
                (f) => f.location.fileUri === uri,
              ).length;
              expect(fileNode.findingCount).toBe(expectedCount);
            }

            // Assert: no StatusNodes in root when findings exist
            expect(rootItems.length).toBe(fileNodes.length);
          },
        ),
        { numRuns: 100 },
      );
    },
  );
});

// ---------------------------------------------------------------------------
// Property 13: Sidebar message truncation
// ---------------------------------------------------------------------------

// Feature: tmac-vscode-plugin, Property 13: Sidebar message truncation
describe('Property 13: Sidebar message truncation', () => {
  it(
    'FindingNode label contains no more than 60 characters from the message',
    () => {
      fc.assert(
        fc.property(
          // Generate messages of any length, including > 60 chars
          fc.string({ minLength: 0, maxLength: 200 }),
          (message) => {
            const finding: Finding = {
              ruleId: 'RULE-001',
              message,
              severity: 'high',
              strideCategory: 'Tampering',
              mitigation: 'Fix it.',
              location: {
                fileUri: '/workspace/main.tf',
                startLine: 1,
                startColumn: 1,
                locationUnknown: false,
              },
            };

            const provider = new SidebarProviderImpl();
            provider.refresh([finding], 'idle');

            // Get root FileNode
            const rootItems = provider.getChildren();
            const fileNode = rootItems.find(
              (item): item is FileNode => item.kind === 'file',
            );
            expect(fileNode).toBeDefined();

            // Get FindingNode children
            const findingChildren = provider.getChildren(fileNode!);
            expect(findingChildren).toHaveLength(1);

            const findingNode = findingChildren[0] as FindingNode;
            expect(findingNode.kind).toBe('finding');

            // Get the TreeItem label
            const treeItem = provider.getTreeItem(findingNode);
            const label = treeItem.label as string;

            // Label format: `${ruleId} — ${message.slice(0, 60)}`
            // Extract the message portion after the em-dash separator
            const separator = ' \u2014 '; // ' — '
            const separatorIndex = label.indexOf(separator);
            expect(separatorIndex).toBeGreaterThan(-1);

            const messagePortion = label.slice(separatorIndex + separator.length);

            // Assert: the message portion is at most 60 characters
            expect(messagePortion.length).toBeLessThanOrEqual(60);

            // Assert: message portion matches the first 60 chars of the original message
            expect(messagePortion).toBe(message.slice(0, 60));
          },
        ),
        { numRuns: 100 },
      );
    },
  );
});
