# Architecture — TMAC v1.6.0

## Project layout

```
src/tmac/
├── cli.py              # CLI (Click) — scan, plan, ci, diagram subcommands
├── scanner.py          # Scan pipeline orchestrator (tmac scan)
│                       # → include_paths param added in v1.6.0 for CI delta mode
├── config.py           # .tmac.yaml loading and validation
├── models/             # Pydantic models: Finding, ScanResult, ScanMetadata
├── parsers/            # TerraformParser (.tf) and TfplanParser (tfplan.json)
├── delta/              # DeltaScanner, DeltaFinding, DeltaScanResult, PlannedChange
├── engine/             # RuleLoader, Matcher, Evaluator
├── graph/              # GraphBuilder, filters, grouping, metadata, diagram renderers
├── reporters/          # HTMLReporter, MarkdownReporter, JSONReporter (SARIF 2.1.0)
├── templates/          # Jinja2 templates for HTML and Markdown (scan + delta)
└── ci/                 # CI layer — NEW in v1.6.0
    ├── __init__.py
    ├── git_diff.py     # changed_tf_files() + GitRefError
    ├── secrets.py      # read_token(), redact()
    ├── comment.py      # CommentFormatter — collapsible Markdown PR comment
    ├── publisher.py    # GitHubCommentPublisher, GitLabCommentPublisher
    └── runner.py       # CIRunner — orchestrates the full CI flow

ci/                     # Distribution entrypoints
├── github/
│   └── entrypoint.sh  # GitHub Action entrypoint — validates inputs, runs tmac ci
└── gitlab/
    └── tmac.gitlab-ci.yml  # Includable GitLab CI template

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
                                                             ├─→ git_diff.py → changed .tf paths
                                tmac scan (CLI) ─→ Scanner  ├─→ Scanner (include_paths)
                                tmac plan (CLI) ─→ DeltaScanner
                                                             ├─→ CommentFormatter → Markdown body
                                                             ├─→ GitHubCommentPublisher / GitLabCommentPublisher
                                                             └─→ Reporters → Report Artifact
```

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
changed `.tf` paths. The engine never imports git.

**AD-3 — Restrict `Scanner` via an injected path list, not a fork.**
`Scanner.run_scan` has one new optional parameter `include_paths: Optional[List[str]] = None`.
When provided, discovery is intersected with that list *before* existing `_is_excluded` logic.
Default `None` = today's full-scan behavior (fully backward-compatible).

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

---

## Full-state analysis vs. risk delta vs. CI delta

| Command | Scope | Question answered |
| :--- | :--- | :--- |
| `tmac scan` | All `.tf` files in a directory | *"What risk exists in the full infrastructure?"* |
| `tmac plan` | Resources in a `tfplan.json` diff | *"What new risk does this plan introduce?"* |
| `tmac ci` | Only `.tf` files changed between two git refs | *"What risk does this PR introduce?"* |

### How `tmac plan` works

Parses `terraform show -json` output and evaluates **only the resources in the diff**:

- **Created** resources → threats in final state → labeled `NEW`
- **Modified** resources → threats introduced by the change → labeled `MODIFIED`
- **Deleted** resources → threats resolved → labeled `REMOVED`

### How `tmac ci` works

```
1. git diff --name-status --diff-filter=AMR <base>...<head>
           → changed .tf paths (Changed_File_Set)
2. Scanner.run_scan(directory, include_paths=changed_paths)
           → ScanResult restricted to changed files
3. Reporter.generate(result) → write Report Artifact
4. CommentFormatter.format(result, ctx) → collapsible Markdown body
5. CommentPublisher.publish(ctx, body) → create or update PR comment
6. _exit_with_code(findings, fail_on) → findings-based exit code
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
| `3` | Execution error (bad ref, missing file, parse error) |

These codes are consistent across `scan`, `plan`, `ci`, and the Docker container.
