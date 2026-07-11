# Command Reference — TMAC v1.6.0

TMAC exposes four subcommands through the `tmac` CLI:

```bash
tmac [--version] [--help] <command> [options]
```

| Command | Purpose |
| :--- | :--- |
| [`tmac scan`](#tmac-scan) | Static analysis of the full infrastructure state in `.tf` files. |
| [`tmac plan`](#tmac-plan) | Risk delta analysis over a `tfplan.json`. |
| [`tmac ci`](#tmac-ci) | Native CI/CD agent: delta scan of changed files and PR/MR comment. |
| [`tmac diagram`](#tmac-diagram) | Architecture diagram from the dependency graph. |

See [DOCS/EXAMPLES.md](EXAMPLES.md) for step-by-step usage examples at each level of complexity.

---

## tmac scan

Scans a directory of `.tf` files and evaluates every resource against the STRIDE rule catalog.

```bash
tmac scan [options]
```

### Options

| Option | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--dir` | `-d` | Directory to scan. | `.` |
| `--report` | `-r` | Report format: `html`, `json`, `md`. | `html` |
| `--output` | `-o` | Report file path. | `tmac-report.[fmt]` |
| `--rules-dir` | | Directory of additional YAML rules. | (built-in rules) |
| `--config` | | Path to the configuration file. | `.tmac.yaml` |
| `--fail-on` | | Minimum severity for a non-zero exit: `critical`, `high`, `medium`, `low`, `info`. | `critical` |
| `--severity` | | Minimum severity to include in the report. | `all` |
| `--exclude` | `-e` | Glob pattern to exclude (repeatable). | — |
| `--diagram` | | Embed the simplified Mermaid diagram in the HTML/MD report. | `False` |
| `--no-color` | | Disable ANSI colors in terminal output. | `False` |
| `--verbose` | `-v` | Enable debug logging. | `False` |
| `--quiet` | `-q` | Suppress terminal output. | `False` |

### Exit codes

| Code | Condition |
| :--- | :--- |
| `0` | No findings above the `--fail-on` threshold. |
| `1` | **Critical** findings detected. |
| `2` | **High** findings detected, none Critical. |
| `3` | Execution error (inaccessible directory, invalid config, parse error). |

---

## tmac plan

Analyzes a `tfplan.json` (`terraform show -json`) and detects threats **only in the plan diff**: created, modified, or destroyed resources. Answers: *"what new risk does this change introduce?"*

```bash
tmac plan --plan-file plan.json [options]
```

### Generating the `tfplan.json`

```bash
terraform plan -out=plan.bin
terraform show -json plan.bin > plan.json
```

### Options

| Option | Short | Description | Required |
| :--- | :--- | :--- | :--- |
| `--plan-file` | `-p` | Path to the `tfplan.json`. | **Yes** |
| `--report` | `-r` | Report format: `html`, `json`, `md`. | No |
| `--output` | `-o` | Report file path. | No |
| `--rules-dir` | | Directory of additional YAML rules. | No |
| `--fail-on` | | Minimum severity for a non-zero exit. | No |
| `--no-color` | | Disable ANSI colors. | No |
| `--verbose` | `-v` | Debug logging. | No |
| `--quiet` | `-q` | Suppress output. | No |

### Delta semantics

| Action | Behavior |
| :--- | :--- |
| **create** | Threats in the final state → labeled `NEW`. |
| **update / replace** | Threats introduced by the change (not pre-existing ones) → labeled `MODIFIED`. |
| **delete** | Threats resolved by removing the resource → labeled `REMOVED`. |

The report shows the net **RiskDelta** = `threats introduced − threats resolved`.

### Exit codes

| Code | Condition |
| :--- | :--- |
| `0` | No Critical/High `DeltaFinding` (safe plan). |
| `1` | At least one **Critical** `DeltaFinding`. |
| `2` | **High** `DeltaFinding`, none Critical. |
| `3` | Execution error (file not found, invalid JSON, missing `resource_changes`). |

---

## tmac ci

Native CI/CD agent. Orchestrates automatically: detects changed `.tf` files between two git refs, scans them, writes the report artifact, formats a narrative comment, and publishes it on the PR/MR.

```bash
tmac ci [options]
```

> **Token note:** The authentication token is read exclusively from environment variables (`GITHUB_TOKEN`, `CI_JOB_TOKEN`, or `TMAC_TOKEN`). It is never passed as a CLI argument.

### Options

| Option | Description | Default |
| :--- | :--- | :--- |
| `--dir` | Terraform directory to analyze. | `.` |
| `--plan-file` | Path to `tfplan.json` (uses `DeltaScanner` instead of `Scanner`). | — |
| `--base-ref` | Base git ref for the delta comparison. | — |
| `--head-ref` | Head git ref for the delta comparison. | — |
| `--delta-only / --no-delta-only` | Restrict analysis to changed files only. | `--delta-only` |
| `--comment / --no-comment` | Publish comment on the PR/MR. | `--comment` |
| `--fail-on` | Severity threshold for a non-zero exit: `critical`, `high`, `medium`, `low`, `info`. | `high` |
| `--report` | Report format: `html`, `json`, `md`. | `md` |
| `--output` | Report output path. | `tmac-report.md` |
| `--platform` | CI platform: `github` or `gitlab` (auto-detected from env). | auto |
| `--exclude` | Glob patterns to exclude (repeatable). | — |
| `--quiet` | Suppress terminal output. | `False` |
| `--no-color` | Disable ANSI colors. | `False` |
| `--verbose` | Debug logging. | `False` |

### Token environment variables

| Variable | Platform |
| :--- | :--- |
| `GITHUB_TOKEN` | GitHub Actions (injected automatically by the runner) |
| `CI_JOB_TOKEN` | GitLab CI (injected automatically by the runner) |
| `TMAC_TOKEN` | Any platform (custom token) |

### PR/MR comment format

The comment is grouped by severity with collapsible sections:

```
<!-- tmac:pr-comment:v1 -->
## 🛡️ TMAC Threat Model Analysis

**Status:** 🚫 BLOCKED
**Summary:** 2 threats introduced, 0 resolved

### Severity Breakdown
| Severity | Count |
|----------|-------|
| 🔴 Critical | 1 |
| 🟠 High | 1 |
| 🟡 Medium | 0 |
| 🟢 Low | 0 |
| 🔵 Info | 0 |

### Findings

<details>
<summary>🔴 Critical — 1 finding</summary>

| Resource | Rule | File | STRIDE | Mitigation |
|----------|------|------|--------|------------|
| `aws_s3_bucket.uploads` | `TMAC-AWS-S3-001` | [`main.tf:12`](https://github.com/org/repo/blob/HEAD/main.tf#L12) | Information Disclosure | Change the 'acl' attribute to 'private'... |

</details>

<details>
<summary>🟠 High — 1 finding</summary>

| Resource | Rule | File | STRIDE | Mitigation |
|----------|------|------|--------|------------|
| `aws_security_group.web` | `TMAC-AWS-SG-001` | [`sg.tf:5`](https://github.com/org/repo/blob/HEAD/sg.tf#L5) | Tampering | Restrict SSH access to known CIDR ranges... |

</details>

📎 Full report: tmac-report.md
```

Each severity section is collapsed by default — click to expand. File links go directly to the line in the PR diff.

### Idempotent publishing behavior

| State | Action |
| :--- | :--- |
| No comment with the TMAC marker exists | Creates exactly one new comment. |
| Exactly one marked comment exists | Updates that comment's body in place. |
| Multiple marked comments exist | Updates the most-recently-created one; leaves the others unchanged. |

A publish failure (permission error, missing token, no PR context) **never changes** the findings-based exit code.

### Exit codes

| Code | Condition |
| :--- | :--- |
| `0` | No findings above the threshold (clean). |
| `1` | **Critical** findings detected. |
| `2` | **High** findings detected, none Critical. |
| `3` | Execution error (invalid/missing refs, inaccessible directory, parse error). |

---

## tmac diagram

Reads all Terraform code in a directory, builds the dependency graph between resources (from `${type.name.attribute}` references), and generates an architecture diagram.

```bash
tmac diagram [options]
```

### Options

| Option | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--dir` | `-d` | Terraform directory to analyze. | `.` |
| `--format` | `-f` | `mermaid`, `dot`, `drawio`, `png`, `svg`, `pdf`. | `mermaid` |
| `--output` | `-o` | Output file path. | `tmac-diagram.[ext]` |
| `--simplify` | `-s` | Hide plumbing resources (IAM, permissions, policies). | `False` |
| `--group` | `-g` | Group resources by microservice (subgraphs/clusters). | `False` |
| `--exclude-type` | | Resource type to hide (repeatable). | — |
| `--metadata` | | Also generate a document with the configuration of each resource. | `False` |
| `--metadata-format` | | Metadata document format: `md`, `json`. | `md` |
| `--exclude` | `-e` | Glob patterns to exclude (repeatable). | — |
| `--verbose` | `-v` | Debug logging. | `False` |
| `--quiet` | `-q` | Suppress output. | `False` |

### Output formats

| Format | Description | Requirements |
| :--- | :--- | :--- |
| `mermaid` | Mermaid text; native rendering in GitHub/GitLab/Markdown. | — |
| `dot` | Graphviz DOT text. | — |
| `drawio` | XML editable in draw.io / diagrams.net. | — |
| `png` / `svg` / `pdf` | Rendered image. | [Graphviz](https://graphviz.org/) installed. |

### Exit codes

| Code | Condition |
| :--- | :--- |
| `0` | Diagram generated successfully. |
| `3` | Execution error (inaccessible directory, Graphviz not installed for image formats). |

---

## Suppressing false positives (`tmac:ignore`)

Applies to `tmac scan`, `tmac plan`, and `tmac ci`. Suppress findings with inline comments in `.tf` files:

```hcl
# Ignore all rules for this resource
# tmac:ignore
resource "aws_s3_bucket" "public_assets" { bucket = "public-assets" }

# Ignore a specific rule
# tmac:ignore[TMAC-AWS-S3-001]
resource "aws_s3_bucket" "another" { bucket = "another" }

# Ignore multiple rules
# tmac:ignore[TMAC-AWS-S3-001]
# tmac:ignore[TMAC-AWS-S3-002]
resource "aws_s3_bucket" "yet_another" { bucket = "yet-another" }
```

## Configuration file (`.tmac.yaml`)

Place `.tmac.yaml` at the repository root to avoid repeating flags on every invocation:

```yaml
scan:
  exclude:
    - ".terraform"
    - "**/.terraform/**"
    - "modules/third-party/**"

report:
  format: html
```

Pass a different file with `--config ./config/tmac-prod.yaml`.
