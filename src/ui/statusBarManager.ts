/**
 * StatusBarManager — manages the single vscode.StatusBarItem for the TMAC extension.
 *
 * Implements all six display states defined in the design document:
 *   idle (no prior result) | scanning | clean | findings > 0 | error | unavailable
 *
 * Requirements: 7.1 – 7.9
 */

import * as vscode from 'vscode';
import type { Finding, ScanState } from '../core/models';

// ---------------------------------------------------------------------------
// Interface (matches design.md)
// ---------------------------------------------------------------------------

export interface StatusBarManager {
  update(state: ScanState, findings?: Finding[]): void;
  setVersion(version: string): void;
  dispose(): void;
}

// ---------------------------------------------------------------------------
// Install instructions shown in the tooltip when TMAC is unavailable
// ---------------------------------------------------------------------------

const INSTALL_INSTRUCTIONS =
  'TMAC CLI not found. Install it with: pip install tmac';

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

export class StatusBarManagerImpl implements StatusBarManager {
  private readonly item: vscode.StatusBarItem;

  /** Stored version string, set once tmacResolver detects the CLI. */
  private version = '';

  /** Timestamp of the last completed scan (clean or findings). */
  private lastScanTime: Date | undefined;

  /**
   * Tracks whether any result has ever been produced in the current session.
   * Used to distinguish the true "idle" state (no prior result) from "idle
   * after a successful clean scan".
   */
  private hasPriorResult = false;

  constructor() {
    // Requirements 7.1: left alignment, priority 100
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100,
    );

    // Requirement 7.8: clicking the item triggers tmac.scanWorkspace
    this.item.command = 'tmac.scanWorkspace';

    // Show immediately so it is always visible while the extension is active
    this.item.show();

    // Render the default idle state right away
    this._applyIdleNoResult();
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /**
   * Store the TMAC CLI version string.  Called once during activation after
   * tmacResolver successfully detects the binary.
   *
   * Requirement 7.9: tooltip SHALL display the TMAC_CLI version string.
   */
  setVersion(version: string): void {
    this.version = version;
  }

  /**
   * Update the status bar to reflect the current ScanState.
   *
   * @param state   The new ScanState.
   * @param findings  The findings from the latest scan result (only relevant
   *                  when state is effectively 'idle' after a completed scan).
   *
   * Requirements 7.2 – 7.9
   */
  update(state: ScanState, findings?: Finding[]): void {
    switch (state) {
      case 'scanning':
        this._applyScanning();
        break;

      case 'error':
        this._applyError();
        break;

      case 'unavailable':
        this._applyUnavailable();
        break;

      case 'idle':
      default:
        // Distinguish "clean / findings" from "idle with no prior result"
        if (findings !== undefined) {
          // A scan just completed — record the timestamp
          this.lastScanTime = new Date();
          this.hasPriorResult = true;

          if (findings.length === 0) {
            this._applyClean();
          } else {
            this._applyFindings(findings.length);
          }
        } else if (this.hasPriorResult) {
          // Caller explicitly reset to idle without providing findings
          // (e.g. after clearDiagnostics).  Revert to no-result idle.
          this.hasPriorResult = false;
          this.lastScanTime = undefined;
          this._applyIdleNoResult();
        } else {
          this._applyIdleNoResult();
        }
        break;
    }
  }

  /**
   * Dispose the underlying StatusBarItem.
   *
   * Requirement: dispose() calls item.dispose()
   */
  dispose(): void {
    this.item.dispose();
  }

  // -------------------------------------------------------------------------
  // Private state appliers
  // -------------------------------------------------------------------------

  /** Requirement 7.2: idle with no prior result */
  private _applyIdleNoResult(): void {
    this.item.text = '$(shield) TMAC';
    this.item.tooltip = this._versionPrefix() + 'No scan yet';
    this.item.backgroundColor = undefined;
  }

  /** Requirement 7.3: scanning in progress */
  private _applyScanning(): void {
    this.item.text = '$(sync~spin) TMAC: Scanning\u2026';
    this.item.tooltip = this._versionPrefix(/*trailingNewline*/ false);
    this.item.backgroundColor = undefined;
  }

  /** Requirement 7.4: scan complete, zero findings */
  private _applyClean(): void {
    this.item.text = '$(shield-check) TMAC: Clean';
    this.item.tooltip =
      this._versionPrefix() + this._lastScanLine();
    this.item.backgroundColor = undefined;
  }

  /** Requirement 7.5: scan complete, one or more findings */
  private _applyFindings(count: number): void {
    this.item.text = `$(warning) TMAC: ${count} threat(s)`;
    this.item.tooltip =
      this._versionPrefix() + this._lastScanLine();
    this.item.backgroundColor = new vscode.ThemeColor(
      'statusBarItem.warningBackground',
    );
  }

  /** Requirement 7.6: error state */
  private _applyError(): void {
    this.item.text = '$(error) TMAC: Error';
    this.item.tooltip = 'See output channel';
    this.item.backgroundColor = new vscode.ThemeColor(
      'statusBarItem.errorBackground',
    );
  }

  /** Requirement 7.7: unavailable (TMAC CLI not installed) */
  private _applyUnavailable(): void {
    this.item.text = '$(circle-slash) TMAC: Not installed';
    this.item.tooltip = INSTALL_INSTRUCTIONS;
    this.item.backgroundColor = undefined;
  }

  // -------------------------------------------------------------------------
  // Tooltip helpers
  // -------------------------------------------------------------------------

  /**
   * Returns the version prefix for tooltips.
   * Produces "TMAC vX.Y.Z\n" when a version is known, or "" otherwise.
   */
  private _versionPrefix(trailingNewline = true): string {
    if (!this.version) {
      return '';
    }
    return `TMAC v${this.version}${trailingNewline ? '\n' : ''}`;
  }

  /**
   * Returns a formatted "Last scan: <timestamp>" string for tooltips.
   * Falls back to an empty string when no scan has completed yet.
   *
   * Requirement 7.9: tooltip SHALL display the timestamp of the last completed scan.
   */
  private _lastScanLine(): string {
    if (!this.lastScanTime) {
      return '';
    }
    return `Last scan: ${this.lastScanTime.toLocaleString()}`;
  }
}
