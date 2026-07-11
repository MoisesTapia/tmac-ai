/**
 * Unit tests for CommandRegistryImpl.
 *
 * Tests cover:
 *  - All 5 commands are registered with context.subscriptions (Req 8.1–8.4)
 *  - tmac.scanWorkspace: scanning guard → "Scan already in progress" (Req 8.6)
 *  - tmac.scanWorkspace: unavailable guard → install notification (Req 8.5)
 *  - tmac.scanWorkspace: no workspace folders → warning message
 *  - tmac.scanWorkspace: successful scan path calls onScanComplete
 *  - tmac.clearDiagnostics: always calls clearAll() (Req 8.2)
 *  - tmac.clearDiagnostics: status bar failure does NOT roll back clear (Req 4.5)
 *  - tmac.showOutput: calls outputChannel.show() (Req 8.3)
 *  - tmac.openSettings: calls workbench.action.openSettings with 'tmac' (Req 8.4)
 *  - tmac.revealFinding: opens document + calls showTextDocument (Req 6.3)
 */

import * as vscode from 'vscode';
import { CommandRegistryImpl, CommandRegistryDeps } from '../../src/ui/commandRegistry';
import type { Finding, ScanState } from '../../src/core/models';
import type { ScanEngineResult } from '../../src/engine/scanEngine';

// ---------------------------------------------------------------------------
// Helper factories
// ---------------------------------------------------------------------------

function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    ruleId: 'TMAC-AWS-S3-001',
    message: 'Public ACL enabled',
    severity: 'high',
    strideCategory: 'Tampering',
    mitigation: 'Set acl = "private"',
    location: {
      fileUri: '/workspace/main.tf',
      startLine: 10,
      startColumn: 3,
      locationUnknown: false,
    },
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Test utilities — capture registered command handlers
// ---------------------------------------------------------------------------

type HandlerMap = Map<string, (...args: unknown[]) => Promise<void> | void>;

/**
 * Builds a fake ExtensionContext that captures subscriptions and exposes
 * registered command handlers for direct invocation in tests.
 */
function makeContext(): {
  context: vscode.ExtensionContext;
  getHandler(commandId: string): ((...args: unknown[]) => Promise<void> | void) | undefined;
} {
  const subscriptions: Array<{ dispose(): void }> = [];
  const handlerMap: HandlerMap = new Map();

  (vscode.commands.registerCommand as jest.Mock).mockImplementation(
    (id: string, handler: (...args: unknown[]) => unknown) => {
      handlerMap.set(id, handler as (...args: unknown[]) => Promise<void> | void);
      return { dispose: jest.fn() };
    },
  );

  const context = {
    subscriptions,
    extensionPath: '/mock/extension',
  } as unknown as vscode.ExtensionContext;

  return {
    context,
    getHandler: (id) => handlerMap.get(id),
  };
}

// ---------------------------------------------------------------------------
// Deps factory
// ---------------------------------------------------------------------------

function makeDeps(overrides: Partial<CommandRegistryDeps> = {}): CommandRegistryDeps {
  const scanEngine = {
    scan: jest.fn().mockResolvedValue({ ok: true, result: { findings: [], scannedAt: new Date(), workspaceRoot: '/workspace' } } as ScanEngineResult),
    cancel: jest.fn(),
  } as unknown as import('../../src/engine/scanEngine').ScanEngine;

  const diagnosticsManager = {
    update: jest.fn(),
    clearFile: jest.fn(),
    clearAll: jest.fn(),
    dispose: jest.fn(),
  };

  const statusBarManager = {
    update: jest.fn(),
    setVersion: jest.fn(),
    dispose: jest.fn(),
  };

  const sidebarProvider = {
    refresh: jest.fn(),
    getTreeItem: jest.fn(),
    getChildren: jest.fn(),
  };

  const outputChannel = {
    show: jest.fn(),
    appendLine: jest.fn(),
  };

  return {
    scanEngine,
    diagnosticsManager,
    statusBarManager,
    sidebarProvider,
    outputChannel,
    getScanState: jest.fn().mockReturnValue('idle' as ScanState),
    setScanState: jest.fn(),
    onScanComplete: jest.fn(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CommandRegistryImpl', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // -------------------------------------------------------------------------
  // Registration
  // -------------------------------------------------------------------------

  describe('registerAll', () => {
    it('registers all 5 commands with context.subscriptions', () => {
      const { context } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);

      registry.registerAll(context);

      const registeredIds = (vscode.commands.registerCommand as jest.Mock).mock.calls.map(
        (call) => call[0],
      );

      expect(registeredIds).toContain('tmac.scanWorkspace');
      expect(registeredIds).toContain('tmac.clearDiagnostics');
      expect(registeredIds).toContain('tmac.showOutput');
      expect(registeredIds).toContain('tmac.openSettings');
      expect(registeredIds).toContain('tmac.revealFinding');
    });

    it('pushes disposables to context.subscriptions', () => {
      const { context } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);

      registry.registerAll(context);

      // 5 commands should push 5 disposables
      expect(context.subscriptions).toHaveLength(5);
    });
  });

  // -------------------------------------------------------------------------
  // tmac.scanWorkspace — Requirement 8.6: scanning guard takes precedence
  // -------------------------------------------------------------------------

  describe('tmac.scanWorkspace', () => {
    it('shows "Scan already in progress" and does NOT call scan when state is scanning (Req 8.6)', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps({
        getScanState: jest.fn().mockReturnValue('scanning' as ScanState),
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      await getHandler('tmac.scanWorkspace')?.();

      expect(vscode.window.showInformationMessage).toHaveBeenCalledWith(
        'Scan already in progress',
      );
      expect(deps.scanEngine.scan).not.toHaveBeenCalled();
    });

    // -----------------------------------------------------------------------
    // tmac.scanWorkspace — Requirement 8.5: unavailable guard
    // -----------------------------------------------------------------------

    it('shows install notification when state is unavailable (Req 8.5)', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps({
        getScanState: jest.fn().mockReturnValue('unavailable' as ScanState),
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      (vscode.window.showWarningMessage as jest.Mock).mockResolvedValue(undefined);

      await getHandler('tmac.scanWorkspace')?.();

      expect(vscode.window.showWarningMessage).toHaveBeenCalledWith(
        expect.stringContaining('pip install tmac'),
        'Open Installation Docs',
      );
      expect(deps.scanEngine.scan).not.toHaveBeenCalled();
    });

    it('does not open docs when user dismisses unavailable notification', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps({
        getScanState: jest.fn().mockReturnValue('unavailable' as ScanState),
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      (vscode.window.showWarningMessage as jest.Mock).mockResolvedValue(undefined);

      await getHandler('tmac.scanWorkspace')?.();

      // executeCommand should NOT be called to open docs since user dismissed
      expect(vscode.commands.executeCommand).not.toHaveBeenCalledWith('vscode.open', expect.anything());
    });

    it('opens docs when user clicks "Open Installation Docs" in unavailable notification', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps({
        getScanState: jest.fn().mockReturnValue('unavailable' as ScanState),
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      (vscode.window.showWarningMessage as jest.Mock).mockResolvedValue('Open Installation Docs');

      await getHandler('tmac.scanWorkspace')?.();

      expect(vscode.commands.executeCommand).toHaveBeenCalledWith(
        'vscode.open',
        expect.anything(),
      );
    });

    it('shows warning if no workspace folders are open', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps({
        getScanState: jest.fn().mockReturnValue('idle' as ScanState),
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      // Ensure no workspace folders
      (vscode.workspace as { workspaceFolders: undefined }).workspaceFolders = undefined;

      await getHandler('tmac.scanWorkspace')?.();

      expect(vscode.window.showWarningMessage).toHaveBeenCalledWith(
        expect.stringContaining('No workspace folder'),
      );
      expect(deps.scanEngine.scan).not.toHaveBeenCalled();
    });

    it('calls scan with the active workspace folder and onScanComplete when idle', async () => {
      const { context, getHandler } = makeContext();
      const mockFolder = {
        uri: { fsPath: '/workspace', toString: () => 'file:///workspace' },
        name: 'workspace',
        index: 0,
      };
      const scanResult: ScanEngineResult = {
        ok: true,
        result: { findings: [], scannedAt: new Date(), workspaceRoot: '/workspace' },
      };

      const deps = makeDeps({
        getScanState: jest.fn().mockReturnValue('idle' as ScanState),
        scanEngine: {
          scan: jest.fn().mockResolvedValue(scanResult),
          cancel: jest.fn(),
        } as unknown as import('../../src/engine/scanEngine').ScanEngine,
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      (vscode.workspace as unknown as { workspaceFolders: unknown[] }).workspaceFolders = [mockFolder];

      await getHandler('tmac.scanWorkspace')?.();

      expect(deps.scanEngine.scan).toHaveBeenCalledWith(mockFolder);
      expect(deps.setScanState).toHaveBeenCalledWith('scanning');
      expect(deps.onScanComplete).toHaveBeenCalledWith(scanResult);
    });
  });

  // -------------------------------------------------------------------------
  // tmac.clearDiagnostics — Requirements 8.2, 4.5
  // -------------------------------------------------------------------------

  describe('tmac.clearDiagnostics', () => {
    it('calls diagnosticsManager.clearAll() (Req 8.2)', () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      getHandler('tmac.clearDiagnostics')?.();

      expect(deps.diagnosticsManager.clearAll).toHaveBeenCalledTimes(1);
    });

    it('calls statusBarManager.update("idle") after clearAll() (Req 4.5)', () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      getHandler('tmac.clearDiagnostics')?.();

      expect(deps.statusBarManager.update).toHaveBeenCalledWith('idle');
    });

    it('does NOT roll back clearAll() when statusBarManager.update throws (Req 4.5)', () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps({
        statusBarManager: {
          update: jest.fn().mockImplementation(() => {
            throw new Error('StatusBar reset failure');
          }),
          setVersion: jest.fn(),
          dispose: jest.fn(),
        },
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      // Must not throw
      expect(() => getHandler('tmac.clearDiagnostics')?.()).not.toThrow();

      // clearAll() must still have been called
      expect(deps.diagnosticsManager.clearAll).toHaveBeenCalledTimes(1);

      // Error is logged to the output channel
      expect(deps.outputChannel.appendLine).toHaveBeenCalledWith(
        expect.stringContaining('StatusBar reset failure'),
      );
    });

    it('logs status bar failure to output channel (Req 4.5)', () => {
      const { context, getHandler } = makeContext();
      const errMsg = 'boom';
      const deps = makeDeps({
        statusBarManager: {
          update: jest.fn().mockImplementation(() => {
            throw new Error(errMsg);
          }),
          setVersion: jest.fn(),
          dispose: jest.fn(),
        },
      });
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      getHandler('tmac.clearDiagnostics')?.();

      expect(deps.outputChannel.appendLine).toHaveBeenCalledWith(
        expect.stringContaining(errMsg),
      );
    });
  });

  // -------------------------------------------------------------------------
  // tmac.showOutput — Requirement 8.3
  // -------------------------------------------------------------------------

  describe('tmac.showOutput', () => {
    it('calls outputChannel.show() (Req 8.3)', () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      getHandler('tmac.showOutput')?.();

      expect(deps.outputChannel.show).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // tmac.openSettings — Requirement 8.4
  // -------------------------------------------------------------------------

  describe('tmac.openSettings', () => {
    it('executes workbench.action.openSettings with "tmac" (Req 8.4)', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      await getHandler('tmac.openSettings')?.();

      expect(vscode.commands.executeCommand).toHaveBeenCalledWith(
        'workbench.action.openSettings',
        'tmac',
      );
    });
  });

  // -------------------------------------------------------------------------
  // tmac.revealFinding — Requirement 6.3
  // -------------------------------------------------------------------------

  describe('tmac.revealFinding', () => {
    it('opens the document and calls showTextDocument for the finding location (Req 6.3)', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      const mockEditor = {
        revealRange: jest.fn(),
        selection: undefined,
      };

      (vscode.workspace.openTextDocument as jest.Mock).mockResolvedValue({});
      (vscode.window.showTextDocument as jest.Mock).mockResolvedValue(mockEditor);

      const finding = makeFinding();
      await getHandler('tmac.revealFinding')?.(finding);

      // Should open the document by file URI
      expect(vscode.workspace.openTextDocument).toHaveBeenCalledTimes(1);
      expect(vscode.window.showTextDocument).toHaveBeenCalledTimes(1);
    });

    it('converts 1-based location to 0-based range when revealing (Req 6.3)', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      const mockEditor = {
        revealRange: jest.fn(),
        selection: undefined,
      };

      (vscode.workspace.openTextDocument as jest.Mock).mockResolvedValue({});
      (vscode.window.showTextDocument as jest.Mock).mockResolvedValue(mockEditor);

      // Finding with startLine=10, startColumn=3 (1-based)
      const finding = makeFinding({ location: { fileUri: '/workspace/main.tf', startLine: 10, startColumn: 3, locationUnknown: false } });
      await getHandler('tmac.revealFinding')?.(finding);

      // revealRange should be called with range starting at line=9, char=2 (0-based)
      expect(mockEditor.revealRange).toHaveBeenCalledTimes(1);
      const [calledRange] = mockEditor.revealRange.mock.calls[0];
      expect(calledRange.start.line).toBe(9);       // 10 - 1
      expect(calledRange.start.character).toBe(2);  // 3 - 1
    });

    it('does nothing when called with no finding argument', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      // Should not throw
      await expect(getHandler('tmac.revealFinding')?.(undefined as unknown as Finding)).resolves.toBeUndefined();

      expect(vscode.workspace.openTextDocument).not.toHaveBeenCalled();
    });

    it('shows error message and logs when openTextDocument throws', async () => {
      const { context, getHandler } = makeContext();
      const deps = makeDeps();
      const registry = new CommandRegistryImpl(deps);
      registry.registerAll(context);

      (vscode.workspace.openTextDocument as jest.Mock).mockRejectedValue(
        new Error('File not found'),
      );

      const finding = makeFinding();

      // Should not throw — error is caught and surfaced via showErrorMessage
      await getHandler('tmac.revealFinding')?.(finding);

      expect(vscode.window.showErrorMessage).toHaveBeenCalledWith(
        expect.stringContaining(finding.location.fileUri),
      );
      expect(deps.outputChannel.appendLine).toHaveBeenCalledWith(
        expect.stringContaining('File not found'),
      );
    });
  });
});
