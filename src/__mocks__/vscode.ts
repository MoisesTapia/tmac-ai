/**
 * Jest manual mock for the 'vscode' module.
 *
 * Provides typed stubs for all VSCode API surface used by the TMAC extension so
 * that Jest unit tests can run without a running VSCode extension host.
 *
 * Place this file at src/__mocks__/vscode.ts and add the following to jest.config.js:
 *   moduleNameMapper: { '^vscode$': '<rootDir>/src/__mocks__/vscode.ts' }
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export enum DiagnosticSeverity {
  Error = 0,
  Warning = 1,
  Information = 2,
  Hint = 3,
}

export enum StatusBarAlignment {
  Left = 1,
  Right = 2,
}

export enum TreeItemCollapsibleState {
  None = 0,
  Collapsed = 1,
  Expanded = 2,
}

// ---------------------------------------------------------------------------
// Value types
// ---------------------------------------------------------------------------

export class Position {
  constructor(
    public readonly line: number,
    public readonly character: number,
  ) {}
}

export class Range {
  public readonly start: Position;
  public readonly end: Position;

  constructor(start: Position, end: Position);
  constructor(
    startLine: number,
    startCharacter: number,
    endLine: number,
    endCharacter: number,
  );
  constructor(
    startOrLine: Position | number,
    endOrCharacter: Position | number,
    endLine?: number,
    endCharacter?: number,
  ) {
    if (startOrLine instanceof Position && endOrCharacter instanceof Position) {
      this.start = startOrLine;
      this.end = endOrCharacter;
    } else {
      this.start = new Position(
        startOrLine as number,
        endOrCharacter as number,
      );
      this.end = new Position(endLine ?? 0, endCharacter ?? 0);
    }
  }
}

export class Diagnostic {
  public source?: string;
  public code?: string | number | { value: string | number; target: Uri };

  constructor(
    public readonly range: Range,
    public readonly message: string,
    public readonly severity: DiagnosticSeverity = DiagnosticSeverity.Error,
  ) {}
}

export class Uri {
  public readonly scheme: string;
  public readonly fsPath: string;
  private readonly _raw: string;

  private constructor(scheme: string, fsPath: string, raw: string) {
    this.scheme = scheme;
    this.fsPath = fsPath;
    this._raw = raw;
  }

  toString(): string {
    return this._raw;
  }

  static file(path: string): Uri {
    return new Uri('file', path, `file://${path}`);
  }

  static parse(str: string): Uri {
    // Minimal parse: strip file:// scheme when present
    if (str.startsWith('file://')) {
      const fsPath = str.slice('file://'.length);
      return new Uri('file', fsPath, str);
    }
    return new Uri('', str, str);
  }
}

export class MarkdownString {
  public value: string;

  constructor(value = '') {
    this.value = value;
  }

  appendMarkdown(str: string): this {
    this.value += str;
    return this;
  }
}

export class Hover {
  public contents: MarkdownString[];

  constructor(contents: MarkdownString | MarkdownString[]) {
    this.contents = Array.isArray(contents) ? contents : [contents];
  }
}

export class ThemeIcon {
  constructor(public readonly id: string) {}
}

export class ThemeColor {
  constructor(public readonly id: string) {}
}

export class TreeItem {
  public iconPath?: ThemeIcon | Uri | string;
  public command?: Command;
  public tooltip?: string | MarkdownString;

  constructor(
    public label: string,
    public collapsibleState: TreeItemCollapsibleState = TreeItemCollapsibleState.None,
  ) {}
}

/** Minimal EventEmitter generic stub. */
export class EventEmitter<T> {
  // Underlying jest.fn() so tests can assert fire() calls
  fire = jest.fn((_data: T): void => {});

  /** The event property — a jest.fn() that accepts a listener callback. */
  event = jest.fn();
}

// ---------------------------------------------------------------------------
// Command interface (used by TreeItem and CommandRegistry)
// ---------------------------------------------------------------------------

export interface Command {
  title: string;
  command: string;
  arguments?: unknown[];
}

// ---------------------------------------------------------------------------
// DiagnosticCollection stub
// ---------------------------------------------------------------------------

/**
 * Internally backed by a Map so test code can assert on its contents:
 *   const col = vscode.languages.createDiagnosticCollection('test');
 *   col.set(uri, diags);
 *   expect(col.get(uri)).toHaveLength(1);
 */
export class MockDiagnosticCollection {
  private _map = new Map<string, Diagnostic[]>();

  set = jest.fn((uri: Uri, diagnostics: Diagnostic[] | undefined): void => {
    if (diagnostics == null || diagnostics.length === 0) {
      this._map.delete(uri.toString());
    } else {
      this._map.set(uri.toString(), diagnostics);
    }
  });

  delete = jest.fn((uri: Uri): void => {
    this._map.delete(uri.toString());
  });

  clear = jest.fn((): void => {
    this._map.clear();
  });

  dispose = jest.fn((): void => {
    this._map.clear();
  });

  get(uri: Uri): Diagnostic[] | undefined {
    return this._map.get(uri.toString());
  }

  has(uri: Uri): boolean {
    return this._map.has(uri.toString());
  }

  get size(): number {
    return this._map.size;
  }

  forEach(
    callback: (
      uri: Uri,
      diagnostics: Diagnostic[],
      collection: MockDiagnosticCollection,
    ) => void,
  ): void {
    this._map.forEach((diags, uriStr) => {
      callback(Uri.parse(uriStr), diags, this);
    });
  }
}

// ---------------------------------------------------------------------------
// StatusBarItem stub
// ---------------------------------------------------------------------------

export class MockStatusBarItem {
  text = '';
  tooltip: string | MarkdownString | undefined = '';
  backgroundColor: ThemeColor | undefined = undefined;
  command: string | Command | undefined = undefined;

  show = jest.fn((): void => {});
  hide = jest.fn((): void => {});
  dispose = jest.fn((): void => {});
}

// ---------------------------------------------------------------------------
// OutputChannel stub
// ---------------------------------------------------------------------------

export class MockOutputChannel {
  appendLine = jest.fn((_value: string): void => {});
  append = jest.fn((_value: string): void => {});
  show = jest.fn((): void => {});
  hide = jest.fn((): void => {});
  dispose = jest.fn((): void => {});
}

// ---------------------------------------------------------------------------
// TreeDataProvider interface stub
// ---------------------------------------------------------------------------

export interface TreeDataProvider<T> {
  onDidChangeTreeData?: EventEmitter<T | undefined | null | void>['event'];
  getTreeItem(element: T): TreeItem | Thenable<TreeItem>;
  getChildren(element?: T): ProviderResult<T[]>;
  getParent?(element: T): ProviderResult<T>;
}

export type ProviderResult<T> =
  | T
  | undefined
  | null
  | Thenable<T | undefined | null>;

// ---------------------------------------------------------------------------
// Top-level namespace mocks
// ---------------------------------------------------------------------------

export const commands = {
  registerCommand: jest.fn(
    (_id: string, _handler: (...args: unknown[]) => unknown) => ({
      dispose: jest.fn(),
    }),
  ),
  executeCommand: jest.fn(
    (_id: string, ..._args: unknown[]): Thenable<unknown> =>
      Promise.resolve(undefined),
  ),
};

export const window = {
  createDiagnosticCollection: jest.fn(
    (_name?: string): MockDiagnosticCollection => new MockDiagnosticCollection(),
  ),
  createStatusBarItem: jest.fn(
    (
      _alignment?: StatusBarAlignment,
      _priority?: number,
    ): MockStatusBarItem => new MockStatusBarItem(),
  ),
  createOutputChannel: jest.fn(
    (_name: string): MockOutputChannel => new MockOutputChannel(),
  ),
  showInformationMessage: jest.fn(
    (_message: string, ..._items: string[]): Thenable<string | undefined> =>
      Promise.resolve(undefined),
  ),
  showWarningMessage: jest.fn(
    (_message: string, ..._items: string[]): Thenable<string | undefined> =>
      Promise.resolve(undefined),
  ),
  showErrorMessage: jest.fn(
    (_message: string, ..._items: string[]): Thenable<string | undefined> =>
      Promise.resolve(undefined),
  ),
  showTextDocument: jest.fn((): Thenable<unknown> => Promise.resolve({})),
  registerTreeDataProvider: jest.fn(
    (_viewId: string, _provider: TreeDataProvider<unknown>) => ({
      dispose: jest.fn(),
    }),
  ),
  createTreeView: jest.fn(
    (_viewId: string, _options: { treeDataProvider: TreeDataProvider<unknown> }) => ({
      dispose: jest.fn(),
      reveal: jest.fn(),
    }),
  ),
};

export const workspace = {
  workspaceFolders: undefined as
    | Array<{ uri: Uri; name: string; index: number }>
    | undefined,
  getConfiguration: jest.fn((_section?: string) => ({
    get: jest.fn((_key: string, defaultValue?: unknown) => defaultValue),
    has: jest.fn((_key: string) => false),
    update: jest.fn(),
    inspect: jest.fn(),
  })),
  onDidSaveTextDocument: jest.fn(
    (_listener: (doc: unknown) => void) => ({ dispose: jest.fn() }),
  ),
  onDidOpenTextDocument: jest.fn(
    (_listener: (doc: unknown) => void) => ({ dispose: jest.fn() }),
  ),
  onDidDeleteFiles: jest.fn(
    (_listener: (event: unknown) => void) => ({ dispose: jest.fn() }),
  ),
  openTextDocument: jest.fn(
    (_uri: Uri | string): Thenable<unknown> => Promise.resolve({}),
  ),
  findFiles: jest.fn((): Thenable<Uri[]> => Promise.resolve([])),
};

export const languages = {
  createDiagnosticCollection: jest.fn(
    (_name?: string): MockDiagnosticCollection => new MockDiagnosticCollection(),
  ),
  registerHoverProvider: jest.fn(
    (_selector: unknown, _provider: unknown) => ({ dispose: jest.fn() }),
  ),
  registerCodeActionsProvider: jest.fn(
    (_selector: unknown, _provider: unknown) => ({ dispose: jest.fn() }),
  ),
};

// ---------------------------------------------------------------------------
// ExtensionContext stub (handy for tests that activate the extension)
// ---------------------------------------------------------------------------

export class MockExtensionContext {
  subscriptions: Array<{ dispose(): void }> = [];
  extensionPath = '/mock/extension';
  globalStoragePath = '/mock/globalStorage';
  workspaceState = {
    get: jest.fn(),
    update: jest.fn(),
  };
  globalState = {
    get: jest.fn(),
    update: jest.fn(),
    setKeysForSync: jest.fn(),
  };
  asAbsolutePath = jest.fn((relativePath: string) => `/mock/extension/${relativePath}`);
}

// ---------------------------------------------------------------------------
// Default export (mirrors how the real vscode module is imported)
// ---------------------------------------------------------------------------

const vscode = {
  DiagnosticSeverity,
  StatusBarAlignment,
  TreeItemCollapsibleState,
  Position,
  Range,
  Diagnostic,
  Uri,
  MarkdownString,
  Hover,
  ThemeIcon,
  ThemeColor,
  TreeItem,
  EventEmitter,
  MockDiagnosticCollection,
  MockStatusBarItem,
  MockOutputChannel,
  MockExtensionContext,
  commands,
  window,
  workspace,
  languages,
};

export default vscode;
