# Architecture — TMAC

## Project layout

```
src/tmac/
├── cli.py              # CLI (Click) — scan, cfn, plan, ci, diagram subcommands
├── scanner.py          # Format-agnostic scan pipeline: Scanner(parser=...) + discover_files()
│                       # → include_paths param (v1.6.0) for CI delta mode
├── config.py           # .tmac.yaml loading and validation
├── models/             # Pydantic models: Finding, ScanResult, ScanIssue, ResourceModel, ThreatRule
├── parsers/            # TerraformParser (.tf/.tofu), CloudFormationParser, TfplanParser
├── delta/              # DeltaScanner, DeltaFinding, DeltaScanResult, PlannedChange
├── engine/             # RuleLoader, Matcher, Evaluator, severity helpers
├── graph/              # GraphBuilder, filters, grouping, metadata, diagram renderers
├── reporters/          # HTMLReporter, MarkdownReporter, JSONReporter (SARIF 2.1.0)
├── rules/              # aws/threats*.yaml (Terraform), cfn/threats.yaml (CloudFormation),
│                       # aws/security_attrs.yaml (diagram metadata)
├── templates/          # Jinja2 templates for HTML and Markdown (scan + delta)
└── ci/                 # CI layer — NEW in v1.6.0
    ├── __init__.py
    ├── git_diff.py     # changed_tf_files() (.tf/.tofu) + GitRefError
    ├── secrets.py      # read_token(), redact()
    ├── comment.py      # CommentFormatter — collapsible Markdown PR comment
    ├── publisher.py    # GitHubCommentPublisher, GitLabCommentPublisher
    └── runner.py       # CIRunner — orchestrates the full CI flow

ci/                     # Distribution entrypoints
├── github/
│   └── entrypoint.sh  # GitHub Action entrypoint — validates inputs, runs tmac ci
└── gitlab/
    └── tmac.gitlab-ci.yml  # Includable GitLab CI template

scripts/
└── generate_rules_doc.py  # Generates DOCS/RULES.md from the rule YAML (checked by a test)

action.yml              # Official GitHub Action definition
Dockerfile              # Official Docker image (python:3.11-slim, ENTRYPOINT tmac)
.pre-commit-hooks.yaml  # pre-commit hook: tmac scan on staged *.tf files
```

---

## Architecture overview

```
Entry points (repo root)
  action.yml + entrypoint.sh  ─┐
  tmac.gitlab-ci.yml          ─┤─→  tmac ci (CLI)  ─→  CIRunner
  Dockerfile                  ─┤                             │
  .pre-commit-hooks.yaml      ─┘                             │
                                                             ├─→ git_diff.py → changed .tf/.tofu paths
                 tmac scan (CLI) ─→ Scanner(TerraformParser) ├─→ Scanner (include_paths)
                 tmac cfn  (CLI) ─→ Scanner(CloudFormationParser)
                 tmac plan (CLI) ─→ DeltaScanner
                                                             ├─→ CommentFormatter → Markdown body
                                                             ├─→ GitHubCommentPublisher / GitLabCommentPublisher
                                                             └─→ Reporters → Report Artifact
```

### Adding an IaC format

`Scanner` does not know about formats: it walks the directory (`discover_files`, which never
enters `.git`, `.terraform`, `node_modules`, virtualenvs, …) and delegates to a `BaseParser`
subclass. The parser declares `file_patterns`, can reject files with `can_parse()`, and implements
`parse_strict()` — raising `ParseError`, so the scan is reported as incomplete instead of silently
treating the file as empty. Inline suppressions travel on `ResourceModel.ignored_rules`. A new format
is a parser plus a rules file; the rule engine and reporters are reused unchanged.

---

## CI layer design (`src/tmac/ci/`)

The CI layer is a **thin orchestration package** that sits *above* the existing engine and
*beside* the CLI commands. It calls the same public APIs that `scan` and `plan` already use —
it never reaches into engine internals.

### Key architectural decisions

**AD-1 — Dedicated `tmac ci` subcommand.**
CI orchestration bundles several steps (diff → scan → artifact → comment → publish → exit code).
Mixing this into `scan`/`plan` would bloat their option surface. A dedicated command keeps the
concern isolated and `scan`/`plan` untouched.

**AD-2 — Thin git helper decoupled from the engine.**
`git_diff.py` is the only module that knows about git. It shells out to
`git diff --name-status --diff-filter=AMR <base>...<head>` and returns a sorted list of
changed `.tf`/`.tofu` paths. The engine never imports git.

**AD-3 — Restrict `Scanner` via an injected path list, not a fork.**
`Scanner.run_scan` has one optional parameter `include_paths: list[str] | None = None`.
When provided, discovery is intersected with that list *before* the exclude patterns.
Default `None` = full-scan behavior (fully backward-compatible).

**AD-4 — stdlib `urllib` for HTTP, no new runtime dependency.**
GitHub and GitLab comment APIs are simple authenticated JSON REST calls. `urllib.request`
avoids adding `requests`/`httpx` to the dependency closure. HTTP is hidden behind an
injectable `HttpTransport` protocol so tests use a fake transport.

**AD-5 — Provider-agnostic `CommentPublisher` interface.**
`find_existing`, `create`, `update` are defined on an ABC. GitHub and GitLab implementations
differ only in URL construction and JSON shape. The orchestrator depends on the interface.

**AD-6 — Centralized secret hygiene.**
`secrets.py` owns (a) reading the token from env only (never argv), and (b) a `redact(text)`
function applied to every user-facing string before it is emitted.

**AD-7 — The comment treats scanned code as untrusted.**
Resource names and file paths come from the PR under review; `CommentFormatter` escapes them
before putting them in the Markdown table, and file links point at the PR head ref.

---

## Full-state analysis vs. risk delta vs. CI delta

| Command | Scope | Question answered |
| :--- | :--- | :--- |
| `tmac scan` | All `.tf`/`.tofu` files in a directory | *"What risk exists in the full infrastructure?"* |
| `tmac cfn` | All CloudFormation templates in a directory | *"What risk exists in these templates?"* |
| `tmac plan` | Resources in a `tfplan.json` diff | *"What new risk does this plan introduce?"* |
| `tmac ci` | Only `.tf`/`.tofu` files changed between two git refs | *"What risk does this PR introduce?"* |

### How `tmac plan` works

Parses `terraform show -json` (or `tofu show -json`) output and evaluates **only the resources in
the diff**:

- **Created** resources → threats in final state → labeled `NEW`
- **Modified** resources → threats introduced by the change → labeled `MODIFIED`
- **Deleted** resources → threats resolved → labeled `REMOVED`

### How `tmac ci` works

```
1. git diff --name-status --diff-filter=AMR <base>...<head>
           → changed .tf/.tofu paths (Changed_File_Set)
2. Scanner.run_scan(directory, include_paths=changed_paths)
           → ScanResult restricted to changed files
3. Reporter.generate(result) → write Report Artifact (always, even without a token)
4. CommentFormatter.format(result, ctx) → collapsible Markdown body
5. CommentPublisher.publish(ctx, body) → create or update PR comment
6. exit 3 if the scan is incomplete (unless --lenient), else findings-based exit code
```

---

## STRIDE framework

Findings are automatically categorized using the STRIDE model:
Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege.

See [aws_stride_mapping.md](aws_stride_mapping.md) for the full AWS → STRIDE mapping.

---

## Exit codes

| Code | Meaning |
| :--- | :--- |
| `0` | No findings at or above the configured threshold |
| `1` | Critical findings detected |
| `2` | High findings detected, none Critical |
| `3` | Execution error (bad ref, missing file) or **incomplete scan** (unparseable file, invalid rule) |

These codes are consistent across `scan`, `cfn`, `plan`, `ci`, and the Docker container. An
incomplete scan fails closed: the report is still written, flagged as incomplete; `--lenient`
only warns.
