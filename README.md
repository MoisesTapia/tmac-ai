<div align="center">

# 🛡️ TMAC — Threat Modeling as Code

**Static security analysis for Infrastructure as Code, powered by the STRIDE framework.**

![Version](https://img.shields.io/badge/version-1.6.0%20%22Ixtla%22-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Rules](https://img.shields.io/badge/rules-1075%2B-orange)
![Services](https://img.shields.io/badge/AWS%20services-178-yellow)

</div>

TMAC automates threat modeling by identifying vulnerabilities in Terraform code **before deployment**. It scans the full infrastructure state, analyzes the risk delta of a plan, renders architecture diagrams, and now lives directly in your repository as a native CI/CD security agent — all offline, with no data sent to external APIs.

It also ships as a **VSCode extension** that surfaces findings inline as squiggly underlines, hover tooltips, and a sidebar threat panel without leaving your editor.

## Table of Contents

- [Key Features](#key-features)
- [Installation](#installation)
- [VSCode Extension](#vscode-extension)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Examples](#examples)
- [Rule Catalog](#rule-catalog)
- [Contributing](#contributing)
- [License](#license)

## Key Features

- **Terraform analysis (`tmac scan`)** — static scan of `.tf` files against **1,075+ STRIDE rules** covering **269 AWS resource types** across **178 services**.
- **Risk delta analysis (`tmac plan`)** — detects threats only in the resources a Terraform plan will create, modify, or destroy. Answers: *"what new risk does this PR introduce?"*
- **Native CI/CD agent (`tmac ci`)** — analyzes only the `.tf` files changed in a push/PR, posts a narrative comment on the PR/MR, and uploads the report as an artifact.
- **Architecture diagrams (`tmac diagram`)** — builds the dependency graph between resources and exports it to Mermaid, Graphviz (DOT), draw.io (XML), or image (PNG/SVG/PDF).
- **VSCode extension** — inline diagnostics, hover tooltips, sidebar threat panel, and status bar badge — no context switching required.
- **YAML rule engine** — declarative, strongly-typed threat rules validated with Pydantic.
- **STRIDE categorization** — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege.
- **Multiple report formats** — HTML, Markdown, and JSON/SARIF 2.1.0.
- **Structured exit codes** — breaks the pipeline on critical threats.
- **Offline by design** — no telemetry, no external API calls.

## Installation

```bash
# From PyPI (recommended)
pip install tmac

# From source
git clone https://github.com/MoisesTapia/tmac-ai.git && cd tmac-ai
pip install -e .

# Docker
docker run --rm -v $(pwd)/infra:/scan tmac-security/tmac:latest scan --dir /scan
```

> Full installation options (Poetry, Docker, pre-commit) in [DOCS/INSTALLATION.md](DOCS/INSTALLATION.md).

## VSCode Extension

The TMAC VSCode Plugin brings threat analysis directly into your editor. It shells out to your locally installed `tmac` CLI and surfaces SARIF findings without leaving VSCode.

### Install

**Option 1 — From VSIX (local build):**

```bash
# 1. Clone the repo and install the CLI first
pip install tmac

# 2. Package the extension
cd tmac-ai
npm install
npm run build
npx vsce package

# 3. Install in VSCode
code --install-extension tmac-vscode-plugin-0.1.0.vsix
```

**Option 2 — Visual Studio Marketplace** *(coming soon)*:

Search for **"TMAC — Threat Modeling as Code"** in the Extensions panel (`Cmd+Shift+X`).

### Extension Commands

| Command | ID | Description |
| :--- | :--- | :--- |
| TMAC: Scan Workspace | `tmac.scanWorkspace` | Run `tmac scan` against the open workspace folder. |
| TMAC: Clear Diagnostics | `tmac.clearDiagnostics` | Remove all TMAC findings from the Problems panel. |
| TMAC: Show Output Channel | `tmac.showOutput` | Open the raw TMAC CLI output log. |
| TMAC: Open Settings | `tmac.openSettings` | Jump directly to the TMAC settings in VSCode preferences. |

Access all commands via `Cmd+Shift+P` → type `TMAC`.

### Extension Settings

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `tmac.executablePath` | string | `""` | Absolute path to the `tmac` binary. Leave empty to use system PATH. |
| `tmac.scanOnSave` | boolean | `true` | Auto-scan on `.tf` file save. |
| `tmac.scanDelay` | number | `1000` | Debounce delay (ms) between save and scan. |
| `tmac.excludePatterns` | string[] | `[]` | Glob patterns to exclude from scanning. |
| `tmac.failOn` | string | `"critical"` | Minimum severity passed to `--fail-on`. |
| `tmac.enableQuickFixes` | boolean | `false` | Enable inline quick-fix suggestions. |

### What you get

- **Inline diagnostics** — squiggly underlines on every threatened resource.
- **Hover tooltips** — severity badge, STRIDE category, rule ID, message, and mitigation on hover.
- **Sidebar panel** — "TMAC Threats" tree view grouped by file with finding counts.
- **Status bar badge** — live threat count at the bottom of the screen, always visible.
- **Output channel** — full CLI output for debugging scan failures.

> See [DOCS/VSCODE.md](DOCS/VSCODE.md) for full extension documentation.

## Quick Start

```bash
# Scan a Terraform directory
tmac scan --dir ./infra

# Analyze the risk delta of a plan
terraform plan -out=plan.bin && terraform show -json plan.bin > plan.json
tmac plan --plan-file plan.json --fail-on critical

# Native CI/CD scan (changed files only)
tmac ci --dir ./infra --base-ref main --head-ref HEAD --fail-on high

# Render an architecture diagram
tmac diagram --dir ./infra --simplify --group --format png --output arch.png
```

> See [DOCS/EXAMPLES.md](DOCS/EXAMPLES.md) for basic, intermediate, and advanced usage.

## Documentation

Full documentation lives in the [`DOCS/`](DOCS/README.md) directory.

| Document | Description |
| :--- | :--- |
| [Installation](DOCS/INSTALLATION.md) | Requirements, pip, Poetry, Docker, and pre-commit. |
| [VSCode Extension](DOCS/VSCODE.md) | Installing, configuring, and using the TMAC VSCode plugin. |
| [Command reference](DOCS/COMMANDS.md) | Complete guide to `scan`, `plan`, `ci`, and `diagram`. |
| [Examples](DOCS/EXAMPLES.md) | Basic, intermediate, and advanced usage — console and CI/CD. |
| [CI/CD integration](DOCS/CICD.md) | GitHub Actions, GitLab CI, Docker, and pre-commit pipelines. |
| [Rule catalog](DOCS/RULES.md) | The 1,075+ rules by service and severity. |
| [Writing rules](DOCS/WRITING_RULES.md) | Rule format, condition operators, and custom rules. |
| [Architecture](DOCS/ARCHITECTURE.md) | Project layout and the full-state vs. risk-delta model. |
| [AWS STRIDE mapping](DOCS/aws_stride_mapping.md) | How AWS services map to STRIDE categories. |
| [Roadmap](ROADMAP.md) | Vision and future versions. |

## Examples

The [`examples/`](examples/) directory contains ready-to-use Terraform architectures:

| Example | Description |
| :--- | :--- |
| `examples/ecommerce/` | Serverless microservices: API Gateway → Lambda → DynamoDB, EventBridge, SQS. |
| `examples/enterprise/` | Multi-AZ, multi-region enterprise architecture: VPC, ALB+WAF, Aurora, Cognito, Route53 failover. |

```bash
tmac scan --dir examples/enterprise --report html --output report.html --diagram
```

## Rule Catalog

TMAC v1.6.0 includes **1,075 rules** covering **269 AWS resource types** across **178 services**.

| Severity | Rules |
| :--- | :--- |
| 🔴 Critical | 81 |
| 🟠 High | 268 |
| 🟡 Medium | 278 |
| 🟢 Low | 145 |
| 🔵 Info | 303 |
| **Total** | **1,075** |

See the [complete rule catalog](DOCS/RULES.md) for the full breakdown by service.

## Contributing

Contributions are welcome. See the [contribution guide](CONTRIBUTING.md) for how to add rules and run the tests, and [Writing rules](DOCS/WRITING_RULES.md) for the rule format.

## License

MIT — see [LICENSE](LICENSE) for details.
