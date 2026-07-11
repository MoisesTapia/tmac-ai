/**
 * CommandRegistry — registers all vscode.commands for the TMAC extension.
 *
 * Responsibilities:
 *  - Register tmac.scanWorkspace, tmac.clearDiagnostics, tmac.showOutput,
 *    tmac.openSettings, and tmac.revealFinding commands.
 *  - Guard tmac.scanWorkspace against 'scanning' state (takes precedence) and
 *    'unavailable' state (show install notification).
 *  - Ensure tmac.clearDiagnostics calls DiagnosticsManager.clearAll()
 *    independently from StatusBarManager.update('idle') so a status-bar
 *    failure does NOT roll back the diagnostic clear (Requirement 4.5).
 *
 * Requirements: 8.1–8.6, 4.5
 */

import * as vscode from 'vscode';
import type { Finding, ScanState } from '../core/models';
import type { DiagnosticsManager } from './diagnosticsManager';
import type { StatusBarManager } from './statusBarManager';
import type { SidebarProvider } from './sidebarProvider';
import { ScanEngine } from '../engine/scanEngine';

// ---------------------------------------------------------------------------
// Minimal OutputChannel subset (avoids hard dependency on vscode.OutputChannel)
// ---------------------------------------------------------------------------

interface OutputChannelLike {
  show(): void;
  appendLine(value: string): void;
}

// ---------------------------------------------------------------------------
// Interface (matches design.md)
// ---------------------------------------------------------------------------

export interface CommandRegistry {
  registerAll(context: vscode.ExtensionContext): void;
}

// ---------------------------------------------------------------------------
// Dependencies injected at construction time
// ---------------------------------------------------------------------------

export interface CommandRegistryDeps {
  scanEngine: ScanEngine;
  diagnosticsManager: DiagnosticsManager;
  statusBarManager: StatusBarManager;
  sidebarProvider: SidebarProvider;
  outputChannel: OutputChannelLike;
  /** Returns the current ScanState; consulted on every tmac.scanWorkspace invocation. */
  getScanState(): ScanState;
  /** Called by the registry after a successful scan to update global state. */
  setScanState(state: ScanState): void;
  /** Called after scan completes so results propagate to UI managers. */
  onScanComplete(result: import('../engine/scanEngine').ScanEngineResult): void;
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

export class CommandRegistryImpl implements CommandRegistry {
  private readonly deps: CommandRegistryDeps;

  constructor(deps: CommandRegistryDeps) {
    this.deps = deps;
  }

  /**
   * Register all commands and push their disposables to context.subscriptions
   * so VSCode disposes them on extension deactivation.
   */
  registerAll(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
      vscode.commands.registerCommand(
        'tmac.scanWorkspace',
        this._handleScanWorkspace.bind(this),
      ),
      vscode.commands.registerCommand(
        'tmac.clearDiagnostics',
        this._handleClearDiagnostics.bind(this),
      ),
      vscode.commands.registerCommand(
        'tmac.showOutput',
        this._handleShowOutput.bind(this),
      ),
      vscode.commands.registerCommand(
        'tmac.openSettings',
        this._handleOpenSettings.bind(this),
      ),
      vscode.commands.registerCommand(
        'tmac.revealFinding',
        this._handleRevealFinding.bind(this),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Command handlers
  // -------------------------------------------------------------------------

  /**
   * tmac.scanWorkspace — Requirement 8.1, 8.5, 8.6
   *
   * Guard order (Requirement 8.6 takes precedence over 8.5):
   *   1. ScanState === 'scanning'    → show "Scan already in progress" toast, STOP
   *   2. ScanState === 'unavailable' → show install notification, STOP
   *   3. Otherwise                   → run ScanEngine.scan() for active folder
   */
  private async _handleScanWorkspace(): Promise<void> {
    const state = this.deps.getScanState();

    // Requirement 8.6: scanning guard takes precedence
    if (state === 'scanning') {
      await vscode.window.showInformationMessage('Scan already in progress');
      return;
    }

    // Requirement 8.5: unavailable guard
    if (state === 'unavailable') {
      const action = await vscode.window.showWarningMessage(
        'TMAC CLI is not installed. Install it with: pip install tmac',
        'Open Installation Docs',
      );
      if (action === 'Open Installation Docs') {
        await vscode.commands.executeCommand(
          'vscode.open',
          vscode.Uri.parse('https://pypi.org/project/tmac/'),
        );
      }
      return;
    }

    // Resolve the active workspace folder
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
      await vscode.window.showWarningMessage(
        'TMAC: No workspace folder is open. Please open a folder to scan.',
      );
      return;
    }

    // Use the first (active) workspace folder
    const workspaceFolder = folders[0];

    try {
      this.deps.setScanState('scanning');
      const result = await this.deps.scanEngine.scan(workspaceFolder);
      this.deps.onScanComplete(result);
    } catch (err) {
      this.deps.setScanState('error');
      const message = err instanceof Error ? err.message : String(err);
      this.deps.outputChannel.appendLine(`[error] tmac.scanWorkspace threw: ${message}`);
      await vscode.window.showErrorMessage(`TMAC scan failed: ${message}`);
    }
  }

  /**
   * tmac.clearDiagnostics — Requirements 8.2, 4.5
   *
   * DiagnosticsManager.clearAll() MUST complete regardless of whether the
   * subsequent StatusBarManager.update('idle') succeeds.  The two operations
   * are independent: failure in the status bar reset SHALL NOT roll back the
   * diagnostic clear.
   */
  private _handleClearDiagnostics(): void {
    // Step 1: Clear diagnostics (always executed)
    this.deps.diagnosticsManager.clearAll();

    // Step 2: Reset status bar to idle — errors here must not roll back step 1
    try {
      this.deps.statusBarManager.update('idle');
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.deps.outputChannel.appendLine(
        `[error] StatusBarManager.update('idle') failed after clearDiagnostics: ${message}`,
      );
    }
  }

  /**
   * tmac.showOutput — Requirement 8.3
   */
  private _handleShowOutput(): void {
    this.deps.outputChannel.show();
  }

  /**
   * tmac.openSettings — Requirement 8.4
   */
  private async _handleOpenSettings(): Promise<void> {
    await vscode.commands.executeCommand('workbench.action.openSettings', 'tmac');
  }

  /**
   * tmac.revealFinding — Requirement 6.3
   *
   * Opens the file containing the given Finding and reveals the exact line/column.
   *
   * @param finding  The Finding to navigate to (passed as a command argument
   *                 from the SidebarProvider's TreeItem command).
   */
  private async _handleRevealFinding(finding: Finding): Promise<void> {
    if (!finding) {
      return;
    }

    try {
      const uri = vscode.Uri.file(finding.location.fileUri);
      const document = await vscode.workspace.openTextDocument(uri);
      const editor = await vscode.window.showTextDocument(document);

      // Convert 1-based SARIF location to 0-based VSCode Position
      const line = Math.max(0, finding.location.startLine - 1);
      const character = Math.max(0, finding.location.startColumn - 1);
      const position = new vscode.Position(line, character);
      const range = new vscode.Range(position, position);

      // Reveal the range — TextEditorRevealType.Default = 0; use numeric
      // constant so tests running against the mock (which lacks the enum)
      // still compile and work.
      editor.revealRange(range);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.deps.outputChannel.appendLine(
        `[error] tmac.revealFinding failed: ${message}`,
      );
      await vscode.window.showErrorMessage(
        `TMAC: Could not open file: ${finding.location.fileUri}`,
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Factory helper
// ---------------------------------------------------------------------------

/**
 * Create a CommandRegistry with the provided dependencies and immediately
 * call registerAll() to push all commands into context.subscriptions.
 */
export function createAndRegisterCommands(
  context: vscode.ExtensionContext,
  deps: CommandRegistryDeps,
): CommandRegistry {
  const registry = new CommandRegistryImpl(deps);
  registry.registerAll(context);
  return registry;
}
