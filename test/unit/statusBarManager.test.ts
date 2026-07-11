/**
 * Unit tests for StatusBarManagerImpl — example-based tests for all six
 * ScanState display strings.
 *
 * Requirements: 7.2–7.7
 */

import * as vscode from 'vscode';
import { StatusBarManagerImpl } from '../../src/ui/statusBarManager';
import type { Finding } from '../../src/core/models';

// The mock file exports MockStatusBarItem as a class but TypeScript's named
// exports don't expose it through the `vscode` namespace type.  We access it
// at runtime via `(vscode as any).MockStatusBarItem` and type the variable
// with a structural inline type that mirrors the properties we need.
type MockStatusBarItemType = {
  text: string;
  tooltip: string | undefined;
  backgroundColor: unknown;
  command: string | undefined;
  show: jest.Mock;
  hide: jest.Mock;
  dispose: jest.Mock;
};

// ---------------------------------------------------------------------------
// Helper — build a minimal Finding for tests that need findings > 0
// ---------------------------------------------------------------------------

function makeFinding(ruleId = 'TMAC-001'): Finding {
  return {
    ruleId,
    message: 'Test finding',
    severity: 'high',
    strideCategory: 'Tampering',
    mitigation: 'Fix it',
    location: {
      fileUri: '/workspace/main.tf',
      startLine: 1,
      startColumn: 1,
      locationUnknown: false,
    },
  };
}

// ---------------------------------------------------------------------------
// Test setup — capture the MockStatusBarItem before constructing the manager
// ---------------------------------------------------------------------------

describe('StatusBarManagerImpl', () => {
  let mockItem: MockStatusBarItemType;
  let manager: StatusBarManagerImpl;

  beforeEach(() => {
    // Reset mock call history between tests
    (vscode.window.createStatusBarItem as jest.Mock).mockClear();

    // Create the item that will be returned by the constructor's call to
    // vscode.window.createStatusBarItem, then capture it.
    mockItem = new (vscode as any).MockStatusBarItem();
    (vscode.window.createStatusBarItem as jest.Mock).mockReturnValue(mockItem);

    manager = new StatusBarManagerImpl();
  });

  afterEach(() => {
    manager.dispose();
  });

  // -------------------------------------------------------------------------
  // Requirement 7.2 — idle with no prior result
  // -------------------------------------------------------------------------

  it('shows $(shield) TMAC on construction (idle, no prior result)', () => {
    // The constructor calls _applyIdleNoResult() immediately
    expect(mockItem.text).toBe('$(shield) TMAC');
  });

  // -------------------------------------------------------------------------
  // Requirement 7.3 — scanning in progress
  // -------------------------------------------------------------------------

  it('shows $(sync~spin) TMAC: Scanning… when state is scanning', () => {
    manager.update('scanning');
    expect(mockItem.text).toBe('$(sync~spin) TMAC: Scanning\u2026');
  });

  // -------------------------------------------------------------------------
  // Requirement 7.4 — clean scan (0 findings)
  // -------------------------------------------------------------------------

  it('shows $(shield-check) TMAC: Clean when update called with idle and empty findings', () => {
    manager.update('idle', []);
    expect(mockItem.text).toBe('$(shield-check) TMAC: Clean');
  });

  // -------------------------------------------------------------------------
  // Requirement 7.5 — findings > 0
  // -------------------------------------------------------------------------

  it('shows $(warning) TMAC: 3 threat(s) when update called with 3 findings', () => {
    const findings = [makeFinding('R-001'), makeFinding('R-002'), makeFinding('R-003')];
    manager.update('idle', findings);
    expect(mockItem.text).toBe('$(warning) TMAC: 3 threat(s)');
  });

  it('shows $(warning) TMAC: 1 threat(s) when update called with 1 finding', () => {
    manager.update('idle', [makeFinding()]);
    expect(mockItem.text).toBe('$(warning) TMAC: 1 threat(s)');
  });

  // -------------------------------------------------------------------------
  // Requirement 7.6 — error state
  // -------------------------------------------------------------------------

  it('shows $(error) TMAC: Error when state is error', () => {
    manager.update('error');
    expect(mockItem.text).toBe('$(error) TMAC: Error');
  });

  // -------------------------------------------------------------------------
  // Requirement 7.7 — unavailable (TMAC CLI not installed)
  // -------------------------------------------------------------------------

  it('shows $(circle-slash) TMAC: Not installed when state is unavailable', () => {
    manager.update('unavailable');
    expect(mockItem.text).toBe('$(circle-slash) TMAC: Not installed');
  });

  // -------------------------------------------------------------------------
  // Requirement 7.8 — clicking the item triggers tmac.scanWorkspace
  // -------------------------------------------------------------------------

  it('sets item.command to tmac.scanWorkspace on construction', () => {
    expect(mockItem.command).toBe('tmac.scanWorkspace');
  });
});
