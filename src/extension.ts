/**
 * extension.ts — TMAC VSCode Plugin entry point.
 *
 * Wires all components together and registers all event listeners and commands
 * with VSCode's extension API. Every disposable is pushed to
 * `context.subscriptions` so VSCode cleans up on deactivation.
 *
 * Activation flow:
 *  1. Create OutputChannel
 *  2. Instantiate DiagnosticsManager, StatusBarManager, SidebarProvider,
 *     HoverProvider, ScanEngine
 *  3. Resolve tmac binary — set ScanState and update StatusBarManager
 *  4. Register event listeners (onDidSaveTextDocument, onDidOpenTextDocument,
 *     onDidDeleteFiles)
 *  5. Register all commands via CommandRegistryImpl
 *  6. Push all disposables to context.subscriptions
 *
 * Requirements: 1.1–1.5, 2.1–2.3, 2.9–2.10, 4.4
 */

import * as vscode from 'vscode';
import { ScanState, Finding } from './core/models';
import { resolveTmacPath, TmacConfig } from './engine/tmacResolver';
import { ScanEngine, ScanEngineResult } from './engine/scanEngine';
import { createDiagnosticsManager } from './ui/diagnosticsManager';
import { StatusBarManagerImpl } from './ui/statusBarManager';
import { createSidebarProvider } from './ui/sidebarProvider';
import { createHoverProvider } from './ui/hoverProvider';
import { CommandRegistryImpl } from './ui/commandRegistry';

// ---------------------------------------------------------------------------
// Module-level state (lifecycle: activate → deactivate)
// ---------------------------------------------------------------------------

/** The current scan state, shared between event listeners and commands. */
let _scanState: ScanState = 'idle';

/** Per-workspace debounce timers keyed by workspace folder URI string. */
const _saveDebounceTimers = new Map<string, NodeJS.Timeout>();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Read the current TMAC configuration from VSCode workspace settings.
 * Always reads fresh values so changes take effect on the next scan.
 */
function getConfig(): TmacConfig {
  const cfg = vscode.workspace.getConfiguration('tmac');
  return {
    executablePath: cfg.get<string>('executablePath', ''),
    scanOnSave: cfg.get<boolean>('scanOnSave', true),
    scanDelay: cfg.get<number>('scanDelay', 1000),
    excludePatterns: cfg.get<string[]>('excludePatterns', []),
    failOn: cfg.get<string>('failOn', 'critical'),
    enableQuickFixes: cfg.get<boolean>('enableQuickFixes', false),
  };
}

// ---------------------------------------------------------------------------
// Exported extension lifecycle functions
// ---------------------------------------------------------------------------

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  // -------------------------------------------------------------------------
  // 1. Output channel
  // -------------------------------------------------------------------------
  const outputChannel = vscode.window.createOutputChannel('TMAC');
  context.subscriptions.push(outputChannel);

  outputChannel.appendLine('[TMAC] Extension activating…');

  // -------------------------------------------------------------------------
  // 2. UI managers
  // -------------------------------------------------------------------------
  const diagnosticsManager = createDiagnosticsManager();
  context.subscriptions.push({ dispose: () => diagnosticsManager.dispose() });

  const statusBarManager = new StatusBarManagerImpl();
  context.subscriptions.push({ dispose: () => statusBarManager.dispose() });

  const { provider: sidebarProvider, disposable: sidebarDisposable } =
    createSidebarProvider();
  context.subscriptions.push(sidebarDisposable);

  const { provider: hoverProvider, disposable: hoverDisposable } =
    createHoverProvider();
  context.subscriptions.push(hoverDisposable);

  // -------------------------------------------------------------------------
  // 3. Scan engine
  // -------------------------------------------------------------------------
  const scanEngine = new ScanEngine(outputChannel, getConfig());

  // -------------------------------------------------------------------------
  // 4. Resolve tmac binary — Requirements 1.1–1.5
  // -------------------------------------------------------------------------
  const resolveResult = await resolveTmacPath(getConfig());

  if (resolveResult.ok) {
    // Requirements 1.1, 1.3: found — store version, set state idle
    statusBarManager.setVersion(resolveResult.version);
    _scanState = 'idle';
    statusBarManager.update('idle');
    outputChannel.appendLine(
      `[TMAC] Found tmac at "${resolveResult.path}" (version ${resolveResult.version})`,
    );
  } else {
    // Requirements 1.2, 1.5: not found or bad configured path
    _scanState = 'unavailable';
    statusBarManager.update('unavailable');
    sidebarProvider.refresh([], 'unavailable');

    if (resolveResult.reason === 'bad_path') {
      // Requirement 1.5: configured path doesn't exist
      const configuredPath = resolveResult.configuredPath ?? '<unknown>';
      outputChannel.appendLine(
        `[TMAC] Configured executable not found: "${configuredPath}"`,
      );
      const action = await vscode.window.showErrorMessage(
        `TMAC: Configured executable not found at "${configuredPath}". ` +
          'Check the tmac.executablePath setting.',
        'Open Settings',
      );
      if (action === 'Open Settings') {
        await vscode.commands.executeCommand(
          'workbench.action.openSettings',
          'tmac.executablePath',
        );
      }
    } else {
      // Requirement 1.2: tmac not on PATH
      outputChannel.appendLine('[TMAC] tmac CLI not found on PATH.');
      const action = await vscode.window.showWarningMessage(
        'TMAC: CLI not found. Install it with: pip install tmac',
        'View Installation Docs',
      );
      if (action === 'View Installation Docs') {
        await vscode.commands.executeCommand(
          'vscode.open',
          vscode.Uri.parse('https://pypi.org/project/tmac/'),
        );
      }
    }
  }

  // -------------------------------------------------------------------------
  // 5. onScanComplete callback (used by CommandRegistry and event listeners)
  // -------------------------------------------------------------------------

  /** Last successful findings, kept for stale display during 'scanning' state. */
  let _lastFindings: Finding[] = [];

  function onScanComplete(result: ScanEngineResult): void {
    if (result.ok) {
      _lastFindings = result.result.findings;
      diagnosticsManager.update(result.result.findings);
      hoverProvider.updateFindings(result.result.findings);
      sidebarProvider.refresh(result.result.findings, 'idle');
      statusBarManager.update('idle', result.result.findings);
      _scanState = 'idle';
      outputChannel.appendLine(
        `[TMAC] Scan complete. ${result.result.findings.length} finding(s).`,
      );
    } else {
      _scanState = 'error';
      statusBarManager.update('error');
      sidebarProvider.refresh(_lastFindings, 'error');

      const errMsg =
        result.error.kind === 'execution_error'
          ? `tmac exited with code ${result.error.exitCode}: ${result.error.stderr}`
          : result.error.kind === 'parse_error'
            ? `SARIF parse error: ${result.error.parseError.message}`
            : result.error.kind === 'tmac_unavailable'
              ? 'TMAC CLI is not available. Install it with: pip install tmac'
              : 'No .tf files found in workspace.';

      outputChannel.appendLine(`[TMAC] Scan error: ${errMsg}`);
      vscode.window.showErrorMessage(`TMAC: Scan failed — ${errMsg}`);
    }
  }

  // -------------------------------------------------------------------------
  // 6. Helper: trigger a scan for the workspace folder that owns a file URI
  // -------------------------------------------------------------------------

  async function triggerScanForFile(fileUri: vscode.Uri): Promise<void> {
    const folder = vscode.workspace.getWorkspaceFolder(fileUri);
    if (!folder) {
      return;
    }

    if (_scanState === 'scanning') {
      outputChannel.appendLine('[TMAC] Scan already in progress — skipping.');
      return;
    }
    if (_scanState === 'unavailable') {
      return;
    }

    _scanState = 'scanning';
    statusBarManager.update('scanning');
    sidebarProvider.refresh(_lastFindings, 'scanning');

    try {
      const result = await scanEngine.scan(folder);
      onScanComplete(result);
    } catch (err) {
      _scanState = 'error';
      const message = err instanceof Error ? err.message : String(err);
      outputChannel.appendLine(`[TMAC] scan() threw: ${message}`);
      statusBarManager.update('error');
      sidebarProvider.refresh(_lastFindings, 'error');
      vscode.window.showErrorMessage(`TMAC: Scan failed — ${message}`);
    }
  }

  // -------------------------------------------------------------------------
  // 7. onDidSaveTextDocument — Requirements 2.2, 2.9, 2.10
  // -------------------------------------------------------------------------

  const onSaveDisposable = vscode.workspace.onDidSaveTextDocument(
    (document: vscode.TextDocument) => {
      if (!document.fileName.endsWith('.tf')) {
        return;
      }

      // Requirement 2.9: respect tmac.scanOnSave
      const config = getConfig();
      if (!config.scanOnSave) {
        return;
      }

      const folder = vscode.workspace.getWorkspaceFolder(document.uri);
      if (!folder) {
        return;
      }

      const key = folder.uri.toString();

      // Requirement 2.10: debounce using tmac.scanDelay
      const existing = _saveDebounceTimers.get(key);
      if (existing !== undefined) {
        clearTimeout(existing);
      }

      const timer = setTimeout(() => {
        _saveDebounceTimers.delete(key);
        void triggerScanForFile(document.uri);
      }, config.scanDelay);

      _saveDebounceTimers.set(key, timer);
    },
  );
  context.subscriptions.push(onSaveDisposable);

  // -------------------------------------------------------------------------
  // 8. onDidOpenTextDocument — Requirement 2.1
  // -------------------------------------------------------------------------

  const onOpenDisposable = vscode.workspace.onDidOpenTextDocument(
    (document: vscode.TextDocument) => {
      if (!document.fileName.endsWith('.tf')) {
        return;
      }
      void triggerScanForFile(document.uri);
    },
  );
  context.subscriptions.push(onOpenDisposable);

  // -------------------------------------------------------------------------
  // 9. onDidDeleteFiles — Requirement 4.4
  // -------------------------------------------------------------------------

  const onDeleteDisposable = vscode.workspace.onDidDeleteFiles(
    (event: vscode.FileDeleteEvent) => {
      for (const fileUri of event.files) {
        if (fileUri.fsPath.endsWith('.tf')) {
          diagnosticsManager.clearFile(fileUri);
        }
      }
    },
  );
  context.subscriptions.push(onDeleteDisposable);

  // -------------------------------------------------------------------------
  // 10. Command registry — Requirements 8.1–8.6
  // -------------------------------------------------------------------------

  const commandRegistry = new CommandRegistryImpl({
    scanEngine,
    diagnosticsManager,
    statusBarManager,
    sidebarProvider,
    outputChannel,
    getScanState: () => _scanState,
    setScanState: (state: ScanState) => {
      _scanState = state;
      statusBarManager.update(state);
      sidebarProvider.refresh(_lastFindings, state);
    },
    onScanComplete,
  });

  commandRegistry.registerAll(context);

  // -------------------------------------------------------------------------
  // 11. Clear debounce timers on deactivation
  // -------------------------------------------------------------------------

  context.subscriptions.push({
    dispose() {
      for (const timer of _saveDebounceTimers.values()) {
        clearTimeout(timer);
      }
      _saveDebounceTimers.clear();
    },
  });

  outputChannel.appendLine('[TMAC] Extension activated.');
}

export function deactivate(): void {
  // VSCode automatically disposes everything in context.subscriptions.
  // Additional cleanup (if needed) can go here.
  for (const timer of _saveDebounceTimers.values()) {
    clearTimeout(timer);
  }
  _saveDebounceTimers.clear();
}
