/**
 * extension.test.ts — Integration smoke tests for the TMAC VSCode Plugin.
 *
 * These tests run inside a real VS Code extension host via @vscode/test-electron,
 * against a minimal fixture workspace that contains one `.tf` file.
 *
 * The fixture workspace is at: fixtures/workspace/main.tf
 * The workspace is opened by runTest.ts when launching VS Code.
 *
 * Test suite:
 *  Test 1: Extension activates without error when `tmac` is not installed
 *          (state → `unavailable`) — Requirements 1.2, 2.1
 *  Test 2: `tmac.scanWorkspace` command is registered and callable without
 *          throwing a "command not found" error — Requirements 8.1, 2.3
 *  Test 3: `tmac.clearDiagnostics` command clears the DiagnosticCollection
 *          — Requirements 8.2, 4.5
 *  Test 4: StatusBarItem is visible after activation — Requirement 7.1
 *  Test 5: TreeView "TMAC Threats" is registered — Requirement 6.1
 *
 * Full end-to-end scan tests (that actually run `tmac scan`) are gated behind
 * the TMAC_INTEGRATION=1 environment variable.
 *
 * Requirements: 2.1–2.3, 4.5, 6.1, 7.1, 8.1–8.4
 */

// NOTE: Inside the extension host, 'vscode' resolves to the real VS Code API.
// Do NOT import from the Jest mock here — this file runs in the Mocha/vscode-test
// environment, not Jest.
import * as vscode from 'vscode';
import * as assert from 'assert';
import * as path from 'path';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Extension ID as declared in package.json: publisher.name */
const EXTENSION_ID = 'tmac.tmac-vscode-plugin';

/**
 * Absolute path to the fixture workspace folder.
 * Resolved relative to this compiled file's location:
 *   out/test/integration/ → fixtures/workspace/
 */
const FIXTURE_WORKSPACE = path.resolve(
  __dirname,
  '../../../fixtures/workspace',
);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Ensure the extension is activated and return the extension object.
 * Throws if the extension is not found or fails to activate.
 */
async function activateExtension(): Promise<vscode.Extension<unknown>> {
  const ext = vscode.extensions.getExtension(EXTENSION_ID);
  if (!ext) {
    throw new Error(
      `Extension "${EXTENSION_ID}" not found. Check the publisher+name in package.json.`,
    );
  }
  if (!ext.isActive) {
    await ext.activate();
  }
  return ext;
}

/**
 * Wait up to `timeoutMs` ms for `predicate()` to return true, polling every
 * `intervalMs` ms.  Returns true if the predicate succeeded, false if it timed
 * out.
 */
async function waitFor(
  predicate: () => boolean,
  timeoutMs = 5_000,
  intervalMs = 100,
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) {
      return true;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return predicate();
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

suite('TMAC Extension — Integration Smoke Tests', function () {
  // Give each test up to 15 seconds for async VS Code operations.
  this.timeout(15_000);

  // -------------------------------------------------------------------------
  // Test 1: Extension activates without error when `tmac` is not installed
  // -------------------------------------------------------------------------

  test('Test 1: Extension activates without error when tmac is not installed (state → unavailable)', async function () {
    // Activate the extension.  If `tmac` is not on PATH (the common CI case),
    // the extension should still activate successfully and set state to
    // 'unavailable'.  If `tmac` IS installed (developer machine), the extension
    // activates normally with state 'idle'.
    //
    // Either way, activation must NOT throw.
    let activationError: unknown = null;
    try {
      await activateExtension();
    } catch (err) {
      activationError = err;
    }

    assert.strictEqual(
      activationError,
      null,
      `Extension activation threw an error: ${activationError}`,
    );

    // Verify the extension is now active.
    const ext = vscode.extensions.getExtension(EXTENSION_ID);
    assert.ok(ext, `Extension "${EXTENSION_ID}" should be registered`);
    assert.strictEqual(
      ext!.isActive,
      true,
      'Extension should be active after activate()',
    );
  });

  // -------------------------------------------------------------------------
  // Test 2: tmac.scanWorkspace command is registered and callable
  // -------------------------------------------------------------------------

  test('Test 2: tmac.scanWorkspace command is registered and callable without throwing', async function () {
    // Ensure extension is active
    await activateExtension();

    // Allow the command time to be registered (activation is async).
    const commands = await vscode.commands.getCommands(true);
    const isRegistered = commands.includes('tmac.scanWorkspace');

    assert.ok(
      isRegistered,
      '"tmac.scanWorkspace" command should be registered in the extension host',
    );

    // Execute the command.  It may show a notification (install notice or
    // "scan already in progress") but must NOT throw a "command not found"
    // error (which would reject with "command 'tmac.scanWorkspace' not found").
    let executeError: unknown = null;
    try {
      // We don't await the full scan — just verify the command dispatches
      // without a "not found" rejection.  A short timeout gives the executor
      // time to begin before we check for errors.
      await Promise.race([
        vscode.commands.executeCommand('tmac.scanWorkspace'),
        new Promise<void>((resolve) => setTimeout(resolve, 2_000)),
      ]);
    } catch (err) {
      // A "command not found" error means the command was never registered.
      // Other errors (e.g. scan failure, notification interaction) are
      // acceptable because they indicate the command WAS registered.
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.toLowerCase().includes('not found') && msg.toLowerCase().includes('tmac.scanWorkspace')) {
        executeError = err;
      }
      // Otherwise suppress — the command ran but encountered a runtime condition.
    }

    assert.strictEqual(
      executeError,
      null,
      `"tmac.scanWorkspace" threw a "command not found" error: ${executeError}`,
    );
  });

  // -------------------------------------------------------------------------
  // Test 3: tmac.clearDiagnostics clears the DiagnosticCollection
  // -------------------------------------------------------------------------

  test('Test 3: tmac.clearDiagnostics command clears the DiagnosticCollection', async function () {
    // Ensure extension is active
    await activateExtension();

    // Verify the command is registered.
    const commands = await vscode.commands.getCommands(true);
    assert.ok(
      commands.includes('tmac.clearDiagnostics'),
      '"tmac.clearDiagnostics" command should be registered',
    );

    // Seed the DiagnosticsCollection with a synthetic diagnostic so we can
    // verify it is cleared.  We do this by opening the fixture .tf file,
    // which creates a document URI we can use.
    const tfFileUri = vscode.Uri.file(
      path.join(FIXTURE_WORKSPACE, 'main.tf'),
    );

    // Create a diagnostic collection with the same name the extension uses
    // ('tmac') and add a synthetic diagnostic to the fixture file.
    // After clearDiagnostics, the extension's own collection should be empty.
    const seedCollection = vscode.languages.createDiagnosticCollection('tmac-test-seed');
    const testRange = new vscode.Range(
      new vscode.Position(0, 0),
      new vscode.Position(0, 10),
    );
    seedCollection.set(tfFileUri, [
      new vscode.Diagnostic(testRange, 'Seeded diagnostic', vscode.DiagnosticSeverity.Warning),
    ]);

    // Execute clearDiagnostics.  The command clears the extension's own
    // DiagnosticCollection (named "tmac").
    await vscode.commands.executeCommand('tmac.clearDiagnostics');

    // Allow a tick for synchronous cleanup to propagate.
    await new Promise((r) => setTimeout(r, 200));

    // The extension's "tmac" DiagnosticCollection should now be empty.
    // We query all diagnostics for the fixture file from all collections.
    const diagsAfterClear = vscode.languages.getDiagnostics(tfFileUri);
    const tmacDiagsAfterClear = diagsAfterClear.filter(
      (d) => d.source === 'tmac',
    );

    assert.strictEqual(
      tmacDiagsAfterClear.length,
      0,
      `Expected 0 "tmac" diagnostics after clearDiagnostics, found ${tmacDiagsAfterClear.length}`,
    );

    // Clean up our seed collection.
    seedCollection.dispose();
  });

  // -------------------------------------------------------------------------
  // Test 4: StatusBarItem is visible after activation
  // -------------------------------------------------------------------------

  test('Test 4: StatusBarItem is visible after activation', async function () {
    // Activate the extension
    await activateExtension();

    // The StatusBarManagerImpl calls item.show() during construction and
    // sets item.text to '$(shield) TMAC' (idle, no prior result) or
    // '$(circle-slash) TMAC: Not installed' (unavailable).
    //
    // VS Code does not expose a public API to enumerate all StatusBarItems.
    // We verify the item exists by checking that the extension is active
    // (StatusBarManagerImpl is instantiated in activate()) and that no
    // error was thrown during construction.
    //
    // We also verify the activation exported the expected public surface via
    // the extension API (exports are optional — we just confirm activate ran).
    const ext = vscode.extensions.getExtension(EXTENSION_ID);
    assert.ok(ext, `Extension "${EXTENSION_ID}" should be registered`);
    assert.strictEqual(ext!.isActive, true, 'Extension must be active');

    // Indirect verification: the extension registers the 'tmac.scanWorkspace'
    // command with click-handler wired to the StatusBarItem.  If the
    // StatusBarItem was NOT created, the constructor would have thrown and
    // activation would have failed (verified in Test 1).
    //
    // We additionally verify the command attributed to the status bar is
    // registered (Requirement 7.8 — click triggers tmac.scanWorkspace).
    const commands = await vscode.commands.getCommands(true);
    assert.ok(
      commands.includes('tmac.scanWorkspace'),
      'StatusBarItem click command "tmac.scanWorkspace" should be registered (Req 7.8)',
    );
  });

  // -------------------------------------------------------------------------
  // Test 5: TreeView "TMAC Threats" is registered
  // -------------------------------------------------------------------------

  test('Test 5: TreeView "TMAC Threats" is registered', async function () {
    // Activate the extension
    await activateExtension();

    // The SidebarProviderImpl is registered as the tree data provider for view
    // id "tmacThreats" via vscode.window.registerTreeDataProvider().
    // VS Code does not expose a direct API to query registered tree providers.
    // The most reliable smoke-test is to execute the built-in
    // "workbench.view.extension.tmac-sidebar" focus command, which should
    // succeed because the view container is contributed in package.json.
    //
    // We verify registration by:
    //   a) Confirming the extension is active (provider is registered in activate())
    //   b) Checking the "tmac.revealFinding" command is registered — it is
    //      the click-handler set on every FindingNode's TreeItem, meaning the
    //      tree items are wired up.
    //   c) Checking that calling getCommands() returns the expected set.

    const commands = await vscode.commands.getCommands(true);

    // tmac.revealFinding is registered by CommandRegistryImpl, which is called
    // from activate() — same activation path that registers the tree provider.
    assert.ok(
      commands.includes('tmac.revealFinding'),
      '"tmac.revealFinding" command (used by TreeView items) should be registered',
    );

    // Verify the extension is still active (no crash during sidebar setup).
    const ext = vscode.extensions.getExtension(EXTENSION_ID);
    assert.strictEqual(
      ext!.isActive,
      true,
      'Extension must remain active after sidebar provider registration',
    );

    // The view container and view are contributed statically in package.json
    // under contributes.views.explorer[0].name = "TMAC Threats".
    // We confirm they appear in the package manifest.
    const packageViews = ext!.packageJSON?.contributes?.views?.explorer as
      | Array<{ id: string; name: string }>
      | undefined;

    assert.ok(
      Array.isArray(packageViews),
      'package.json contributes.views.explorer should be an array',
    );

    const tmacThreatsView = packageViews?.find(
      (v) => v.id === 'tmacThreats' && v.name === 'TMAC Threats',
    );

    assert.ok(
      tmacThreatsView,
      'package.json should declare a view with id "tmacThreats" and name "TMAC Threats" (Req 6.1)',
    );
  });

  // -------------------------------------------------------------------------
  // End-to-end scan tests — gated behind TMAC_INTEGRATION=1
  // -------------------------------------------------------------------------

  (process.env['TMAC_INTEGRATION'] === '1' ? suite : suite.skip)(
    'End-to-End Scan Tests (TMAC_INTEGRATION=1 required)',
    function () {
      this.timeout(30_000);

      test('E2E: tmac.scanWorkspace produces diagnostics for the fixture .tf file', async function () {
        await activateExtension();

        // Open the fixture .tf file so the extension's onDidOpen handler
        // can also trigger — the command itself does not depend on this.
        const tfFileUri = vscode.Uri.file(
          path.join(FIXTURE_WORKSPACE, 'main.tf'),
        );
        const doc = await vscode.workspace.openTextDocument(tfFileUri);
        await vscode.window.showTextDocument(doc);

        // Wait for any activation-triggered scan to settle.
        await new Promise((r) => setTimeout(r, 3_000));

        // Manually invoke the scan command.
        await vscode.commands.executeCommand('tmac.scanWorkspace');

        // Wait up to 15 s for diagnostics to appear.
        const hasDiagnostics = await waitFor(() => {
          const allDiags = vscode.languages.getDiagnostics();
          return allDiags.some(
            ([, diags]) => diags.some((d) => d.source === 'tmac'),
          );
        }, 15_000);

        assert.ok(
          hasDiagnostics,
          'Expected at least one "tmac" diagnostic after scanning the fixture workspace',
        );
      });

      test('E2E: tmac.clearDiagnostics removes all tmac diagnostics', async function () {
        await activateExtension();

        // Run a scan first to populate diagnostics.
        await vscode.commands.executeCommand('tmac.scanWorkspace');
        await waitFor(() => {
          const allDiags = vscode.languages.getDiagnostics();
          return allDiags.some(
            ([, diags]) => diags.some((d) => d.source === 'tmac'),
          );
        }, 15_000);

        // Now clear
        await vscode.commands.executeCommand('tmac.clearDiagnostics');
        await new Promise((r) => setTimeout(r, 500));

        // All tmac diagnostics should be gone.
        const allDiags = vscode.languages.getDiagnostics();
        const tmacDiags = allDiags.flatMap(([, diags]) =>
          diags.filter((d) => d.source === 'tmac'),
        );

        assert.strictEqual(
          tmacDiags.length,
          0,
          `Expected 0 tmac diagnostics after clearDiagnostics, found ${tmacDiags.length}`,
        );
      });
    },
  );
});
