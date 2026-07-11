# TMAC VSCode Extension

The TMAC VSCode Plugin brings threat analysis directly into your editor. It shells out to your locally installed `tmac` CLI, parses its SARIF 2.1.0 output, and surfaces findings as inline diagnostics, hover tooltips, a sidebar panel, and a status bar badge — all without leaving VSCode.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Commands](#commands)
- [Settings](#settings)
- [Status Bar](#status-bar)
- [Sidebar Panel](#sidebar-panel)
- [Hover Tooltips](#hover-tooltips)
- [Output Channel](#output-channel)
- [Suppressing False Positives](#suppressing-false-positives)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **VSCode 1.80+** (or any compatible fork — Cursor, Windsurf, etc.)
- **TMAC CLI installed** in your environment:

```bash
pip install tmac
tmac --version   # should print: TMAC, version 1.6.0
```

The extension does **not** bundle the Python engine. You must have `tmac` accessible on your system `PATH` (or configure `tmac.executablePath`).

---

## Installation

### Option 1 — From VSIX (local build)

```bash
# 1. Install the CLI
pip install tmac

# 2. Clone the repo and build the extension
git clone https://github.com/MoisesTapia/tmac-ai.git
cd tmac-ai
npm install
npm run build
npx vsce package
# → generates tmac-vscode-plugin-0.1.0.vsix

# 3. Install in VSCode via CLI
code --install-extension tmac-vscode-plugin-0.1.0.vsix

# 4. Reload VSCode
# Cmd+Shift+P → Developer: Reload Window
```

### Option 2 — Install from VSIX in the UI

1. Open VSCode.
2. `Cmd+Shift+X` to open the Extensions panel.
3. Click the `···` menu → **Install from VSIX…**
4. Select `tmac-vscode-plugin-0.1.0.vsix`.
5. Reload the window when prompted.

### Option 3 — Visual Studio Marketplace *(coming soon)*

Search for **"TMAC — Threat Modeling as Code"** in the Extensions panel.

---

## Getting Started

1. Open a workspace folder that contains `.tf` files.
2. The extension activates automatically when it detects a `.tf` file.
3. Open or save any `.tf` file — a scan starts automatically.
4. Check the status bar at the bottom left for the scan result.
5. Findings appear as squiggly underlines directly in the editor.

If `tmac` is not installed or not on your PATH, the status bar shows `⊘ TMAC: Not installed` and a notification with installation instructions appears.

---

## Commands

Access all commands via `Cmd+Shift+P` → type `TMAC`.

| Command | ID | Description |
| :--- | :--- | :--- |
| **TMAC: Scan Workspace** | `tmac.scanWorkspace` | Run `tmac scan` against the open workspace folder. |
| **TMAC: Clear Diagnostics** | `tmac.clearDiagnostics` | Remove all TMAC findings from the Problems panel and editor. |
| **TMAC: Show Output Channel** | `tmac.showOutput` | Open the raw TMAC CLI output log for debugging. |
| **TMAC: Open Settings** | `tmac.openSettings` | Jump to the TMAC settings page in VSCode preferences. |

### Scan Workspace

Triggers an immediate scan regardless of `tmac.scanOnSave`. If a scan is already running, a toast message appears: `"Scan already in progress"`. If `tmac` is not installed, shows the installation notification instead.

### Clear Diagnostics

Clears all entries in the TMAC diagnostic collection and resets the status bar to idle. This operation is independent — a failure to reset the status bar does not roll back the diagnostic clear.

---

## Settings

Open via `Cmd+Shift+P` → `TMAC: Open Settings`, or navigate to **Preferences → Settings → Extensions → TMAC**.

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `tmac.executablePath` | `string` | `""` | Absolute path to the `tmac` binary. Leave empty to use the system PATH. Example: `/opt/anaconda3/bin/tmac`. |
| `tmac.scanOnSave` | `boolean` | `true` | Automatically scan the workspace when a `.tf` file is saved. Set to `false` to scan only on demand. |
| `tmac.scanDelay` | `number` | `1000` | Debounce delay in milliseconds between the last save event and scan start. Increase this on large workspaces. |
| `tmac.excludePatterns` | `string[]` | `[]` | Glob patterns of paths to exclude from scanning. Example: `[".terraform/**", "modules/vendor/**"]`. |
| `tmac.failOn` | `string` | `"critical"` | Minimum severity threshold passed to `tmac scan --fail-on`. Options: `critical`, `high`, `medium`, `low`, `info`. |
| `tmac.enableQuickFixes` | `boolean` | `false` | Register a CodeActionProvider to show inline quick-fix suggestions for findings with actionable mitigations. |

Settings changes apply to the **next scan**. An active scan always completes with the settings that were in effect when it started.

---

## Status Bar

The TMAC status bar item is always visible at the bottom left of the window (priority 100). Click it at any time to trigger a manual scan.

| State | Display | Meaning |
| :--- | :--- | :--- |
| Idle (no scan yet) | `🛡 TMAC` | Extension active, no scan run yet. |
| Scanning | `↻ TMAC: Scanning…` | Scan in progress. |
| Clean | `🛡✓ TMAC: Clean` | Last scan found zero threats. |
| Findings | `⚠ TMAC: N threat(s)` | Last scan found N threats. |
| Error | `⊗ TMAC: Error` | Scan failed — see Output Channel for details. |
| Not installed | `⊘ TMAC: Not installed` | `tmac` CLI not found. |

The tooltip shows the TMAC CLI version and the timestamp of the last completed scan.

---

## Sidebar Panel

The **TMAC Threats** panel appears in the Explorer activity bar. It groups all findings by file and updates automatically after each scan.

| State | Display |
| :--- | :--- |
| Scanning | Loading indicator + stale file nodes from the last scan. |
| Error | Error message at the top of the tree. |
| Not installed | "TMAC not found" message with installation instructions. |
| Clean | "No threats found." |
| Findings | One node per file, each expandable to show individual findings. |

Each finding node shows:
- **Severity icon**: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low · 🔵 Info
- **Rule ID** and truncated message (≤ 60 chars)

Click any finding node to open the file and jump directly to the line.

---

## Hover Tooltips

Hover over any squiggly-underlined region in a `.tf` file to see full threat details:

```
$(shield) TMAC — TMAC-AWS-S3-001

🔴 Critical · STRIDE: Tampering

Resource `aws_s3_bucket.example` has public ACL enabled.

Mitigation: Set `acl = "private"` and enable bucket policy.
```

If multiple findings cover the same position, all are shown in a single hover separated by horizontal rules.

---

## Output Channel

The `TMAC` output channel logs every scan in detail. Open it via `Cmd+Shift+P` → **TMAC: Show Output Channel**, or click the status bar when the state is `Error`.

Each scan entry includes:
1. The full command line executed (with all arguments).
2. Any stderr output from the CLI, prefixed with `[stderr]`.
3. The process exit code and elapsed time in milliseconds.
4. `Parsed N findings from SARIF output` (only when findings ≥ 1).

---

## Suppressing False Positives

Use the same `# tmac:ignore` comments in your `.tf` files that work with the CLI:

```hcl
# Ignore all TMAC rules for this resource
# tmac:ignore
resource "aws_s3_bucket" "public_assets" {
  bucket = "public-assets"
}

# Ignore a specific rule
# tmac:ignore[TMAC-AWS-S3-001]
resource "aws_s3_bucket" "another" {
  bucket = "another"
}
```

After adding an ignore comment, save the file to trigger a re-scan. The suppressed finding disappears from the editor.

---

## Troubleshooting

### Status bar shows "⊘ TMAC: Not installed"

The extension cannot find the `tmac` binary. Fix options:

1. **Install the CLI**: `pip install tmac`
2. **Set the executable path** if tmac is installed in a virtual environment or non-standard location:
   - `Cmd+Shift+P` → **TMAC: Open Settings**
   - Set `tmac.executablePath` to the full path, e.g. `/opt/anaconda3/bin/tmac`

Verify tmac is reachable: `which tmac && tmac --version`

### Status bar shows "⊗ TMAC: Error"

The scan ran but failed. Open the output channel (`Cmd+Shift+P` → **TMAC: Show Output Channel**) to see the full error.

Common causes:
- The workspace has no `.tf` files — this is expected (extension skips the scan silently).
- `tmac scan` exited with code 3 (configuration or directory error) — check the stderr output in the channel.
- The SARIF output could not be parsed — verify `tmac` produces valid JSON with `tmac scan --dir . --report json`.

### No diagnostics appear after scan

1. Check the output channel — if it shows `Parsed 0 findings`, the scan ran clean.
2. Confirm you opened a workspace folder (not just a single file).
3. Check `tmac.excludePatterns` — make sure your `.tf` files are not accidentally excluded.

### Scan never starts on save

Check `tmac.scanOnSave` — if set to `false`, scans only run manually via `tmac.scanWorkspace`.

### Custom tmac binary path not recognized

Ensure the path in `tmac.executablePath` is absolute and points to the executable directly (not a wrapper script), e.g. `/Users/you/.venv/bin/tmac`, not `~/.venv/bin/tmac`.
