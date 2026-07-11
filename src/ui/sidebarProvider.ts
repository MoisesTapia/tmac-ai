/**
 * SidebarProvider — TreeDataProvider implementation for the "TMAC Threats" panel.
 *
 * Responsibilities:
 *  - Group Findings by file URI into FileNodes, each containing FindingNodes
 *  - Display status messages (scanning, error, unavailable, empty) as StatusNodes
 *  - Fire onDidChangeTreeData whenever refresh() is called
 *  - Produce vscode.TreeItem instances for each node type
 *
 * Tree structure:
 *  - state === 'scanning'    : StatusNode (loading) + stale FileNodes (if any)
 *  - state === 'error'       : single StatusNode with error message
 *  - state === 'unavailable' : single StatusNode with install instructions
 *  - findings empty          : single StatusNode "No threats found."
 *  - otherwise               : one FileNode per unique fileUri, sorted by file name
 *
 * The vscode import is satisfied by the Jest manual mock at
 * src/__mocks__/vscode.ts when running under Jest.
 */

import * as vscode from 'vscode';
import { Finding, ScanState } from '../core/models';

// ---------------------------------------------------------------------------
// Node types
// ---------------------------------------------------------------------------

export interface FileNode {
  kind: 'file';
  uri: vscode.Uri;
  findingCount: number;
  children: FindingNode[];
}

export interface FindingNode {
  kind: 'finding';
  finding: Finding;
}

export interface StatusNode {
  kind: 'status';
  message: string;
}

export type TmacTreeItem = FileNode | FindingNode | StatusNode;

// ---------------------------------------------------------------------------
// Severity icon mapping
// ---------------------------------------------------------------------------

/**
 * Maps a FindingSeverity to a vscode.ThemeIcon id.
 *
 * ThemeIcon names correspond to VS Code Codicons; we use the closest semantic
 * match for each severity level.
 */
function severityThemeIconId(severity: Finding['severity']): string {
  switch (severity) {
    case 'critical':
      return 'error';
    case 'high':
      return 'warning';
    case 'medium':
      return 'warning';
    case 'low':
      return 'info';
    case 'info':
      return 'info';
  }
}

// ---------------------------------------------------------------------------
// Interface
// ---------------------------------------------------------------------------

export interface SidebarProvider extends vscode.TreeDataProvider<TmacTreeItem> {
  /** Update displayed findings and scan state, then fire a tree refresh. */
  refresh(findings: Finding[], state: ScanState): void;
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

export class SidebarProviderImpl implements SidebarProvider {
  // Emitter used to signal tree data changes to VS Code.
  private readonly _onDidChangeTreeData =
    new vscode.EventEmitter<TmacTreeItem | undefined | null | void>();

  /**
   * VS Code subscribes to this event to know when to re-query the tree.
   * The cast is required because the EventEmitter mock exposes `event` as
   * `jest.fn()`, which is compatible at runtime but slightly diverges from the
   * real API's typed signature.
   */
  readonly onDidChangeTreeData =
    this._onDidChangeTreeData
      .event as vscode.TreeDataProvider<TmacTreeItem>['onDidChangeTreeData'];

  private _state: ScanState = 'idle';
  private _findings: Finding[] = [];

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Update internal state and trigger a full tree refresh.
   *
   * Called by ScanEngine (or command handlers) after every scan transition.
   */
  refresh(findings: Finding[], state: ScanState): void {
    this._findings = findings;
    this._state = state;
    this._onDidChangeTreeData.fire(undefined);
  }

  // ---------------------------------------------------------------------------
  // TreeDataProvider
  // ---------------------------------------------------------------------------

  /**
   * Return the root children, or children of a FileNode.
   *
   * VS Code calls getChildren(undefined) for root items, and
   * getChildren(fileNode) for the children of an expanded FileNode.
   */
  getChildren(element?: TmacTreeItem): TmacTreeItem[] {
    // Children of a FileNode → its FindingNodes.
    if (element !== undefined) {
      if (element.kind === 'file') {
        return element.children;
      }
      // FindingNodes and StatusNodes are leaves.
      return [];
    }

    // Root-level children depend on ScanState.
    switch (this._state) {
      case 'scanning': {
        const loadingNode: StatusNode = {
          kind: 'status',
          message: '$(sync~spin) Scanning…',
        };
        return [loadingNode, ...this._buildFileNodes(this._findings)];
      }

      case 'error': {
        const errorNode: StatusNode = {
          kind: 'status',
          message: '$(error) Scan failed. See the TMAC output channel for details.',
        };
        return [errorNode];
      }

      case 'unavailable': {
        const unavailableNode: StatusNode = {
          kind: 'status',
          message: '$(circle-slash) TMAC not found. Run: pip install tmac',
        };
        return [unavailableNode];
      }

      case 'idle':
      default: {
        if (this._findings.length === 0) {
          const emptyNode: StatusNode = {
            kind: 'status',
            message: 'No threats found.',
          };
          return [emptyNode];
        }
        return this._buildFileNodes(this._findings);
      }
    }
  }

  /**
   * Convert a TmacTreeItem into a vscode.TreeItem for rendering.
   *
   * FileNode    → collapsed tree item with child count badge
   * FindingNode → leaf with severity icon, truncated label, revealFinding command
   * StatusNode  → leaf with plain message label
   */
  getTreeItem(element: TmacTreeItem): vscode.TreeItem {
    switch (element.kind) {
      case 'file': {
        const fileName = element.uri.fsPath.split('/').pop() ?? element.uri.fsPath;
        const item = new vscode.TreeItem(
          `${fileName} (${element.findingCount})`,
          vscode.TreeItemCollapsibleState.Collapsed,
        );
        item.tooltip = element.uri.fsPath;
        item.iconPath = new vscode.ThemeIcon('file');
        return item;
      }

      case 'finding': {
        const { finding } = element;
        // Truncate message to 60 characters as per Requirement 6.4
        const truncatedMessage = finding.message.slice(0, 60);
        const label = `${finding.ruleId} — ${truncatedMessage}`;
        const item = new vscode.TreeItem(
          label,
          vscode.TreeItemCollapsibleState.None,
        );
        item.iconPath = new vscode.ThemeIcon(severityThemeIconId(finding.severity));
        item.command = {
          title: 'Reveal Finding',
          command: 'tmac.revealFinding',
          arguments: [finding],
        };
        item.tooltip = finding.message;
        return item;
      }

      case 'status': {
        const item = new vscode.TreeItem(
          element.message,
          vscode.TreeItemCollapsibleState.None,
        );
        return item;
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /**
   * Group findings by fileUri into FileNodes, sorted by file name.
   */
  private _buildFileNodes(findings: Finding[]): FileNode[] {
    const byUri = new Map<string, FindingNode[]>();

    for (const finding of findings) {
      const uri = finding.location.fileUri;
      const bucket = byUri.get(uri);
      const node: FindingNode = { kind: 'finding', finding };
      if (bucket) {
        bucket.push(node);
      } else {
        byUri.set(uri, [node]);
      }
    }

    const fileNodes: FileNode[] = Array.from(byUri.entries()).map(
      ([uriStr, findingNodes]) => ({
        kind: 'file' as const,
        uri: vscode.Uri.file(uriStr),
        findingCount: findingNodes.length,
        children: findingNodes,
      }),
    );

    // Sort by base file name (case-insensitive) for a stable, predictable order.
    fileNodes.sort((a, b) => {
      const nameA = (a.uri.fsPath.split('/').pop() ?? '').toLowerCase();
      const nameB = (b.uri.fsPath.split('/').pop() ?? '').toLowerCase();
      return nameA < nameB ? -1 : nameA > nameB ? 1 : 0;
    });

    return fileNodes;
  }
}

// ---------------------------------------------------------------------------
// Factory helper
// ---------------------------------------------------------------------------

/**
 * Create a SidebarProvider and register it as the tree data provider for
 * the "tmacThreats" view.  Returns both the provider and the disposable so
 * the caller can push both to context.subscriptions.
 */
export function createSidebarProvider(): {
  provider: SidebarProvider;
  disposable: { dispose(): void };
} {
  const provider = new SidebarProviderImpl();
  const disposable = vscode.window.registerTreeDataProvider('tmacThreats', provider);
  return { provider, disposable };
}
