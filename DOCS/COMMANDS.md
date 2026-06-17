# Command Reference — TMAC v1.1.0

TMAC exposes three subcommands. All of them are run through the `tmac` CLI:

```bash
tmac [--version] [--help] <command> [options]
```

| Command | Purpose |
| :--- | :--- |
| [`tmac scan`](#tmac-scan) | Static analysis of the full infrastructure state in `.tf` files. |
| [`tmac plan`](#tmac-plan) | Risk delta analysis over a `tfplan.json`. |
| [`tmac diagram`](#tmac-diagram) | Architecture diagram from the dependency graph. |

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
| `--fail-on` | | Minimum severity for exit code 1: `critical`, `high`, `medium`, `low`, `info`. | `critical` |
| `--severity` | | Minimum severity to include in the report. | `all` |
| `--exclude` | `-e` | Glob pattern to exclude (repeatable). | — |
| `--diagram` | | Embeds the (simplified) Mermaid diagram in the HTML/MD report. | `False` |
| `--no-color` | | Disables ANSI colors in the output. | `False` |
| `--verbose` | `-v` | Enables debug logging. | `False` |
| `--quiet` | `-q` | Suppresses terminal output. | `False` |

### Examples

```bash
# Basic scan (HTML report)
tmac scan --dir ./infra

# Markdown report, fail on High or higher
tmac scan --dir ./infra --report md --output report.md --fail-on high

# Exclude third-party modules and .terraform
tmac scan --dir ./infra --exclude .terraform --exclude "**/modules/third-party/**"

# HTML report with the embedded architecture diagram
tmac scan --dir ./infra --report html --output report.html --diagram

# JSON/SARIF output without colors (CI)
tmac scan --dir ./infra --report json --output results.sarif --no-color
```

### Exit codes

| Code | Condition |
| :--- | :--- |
| `0` | No findings above the `--fail-on` threshold. |
| `1` | **Critical** findings. |
| `2` | **High** findings but none Critical. |
| `3` | Execution error (inaccessible directory, invalid config, parse error). |

---

## tmac plan

Analyzes a `tfplan.json` (`terraform show -json`) and detects threats **only in the plan diff**: created, modified, or destroyed resources. It answers *"what new risk does this change introduce?"*.

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
| `--fail-on` | | Minimum severity for exit code 1. | No |
| `--no-color` | | Disables ANSI colors. | No |
| `--verbose` | `-v` | Debug logging. | No |
| `--quiet` | `-q` | Suppresses output. | No |

### Delta semantics

- **Created resources**: threats in the final state.
- **Modified resources**: threats introduced by the change (not pre-existing ones).
- **Deleted resources**: threats resolved by removing the resource.

The report shows the net **RiskDelta** = `introduced threats − resolved threats`.

### Examples

```bash
# Basic analysis (HTML report)
tmac plan --plan-file plan.json

# Markdown report to comment on a PR
tmac plan --plan-file plan.json --report md --output delta.md

# Full pipeline in one line
terraform plan -out=plan.bin && terraform show -json plan.bin > plan.json && tmac plan --plan-file plan.json --fail-on critical
```

### Exit codes

| Code | Condition |
| :--- | :--- |
| `0` | No Critical/High `DeltaFinding` (safe plan). |
| `1` | At least one **Critical** `DeltaFinding`. |
| `2` | **High** `DeltaFinding` but none Critical. |
| `3` | Execution error (file does not exist, invalid JSON, no `resource_changes`). |

---

## tmac diagram

Reads all the Terraform code in a directory, builds the dependency graph between resources (from `${type.name.attribute}` references), and generates an architecture diagram.

```bash
tmac diagram [options]
```

### Options

| Option | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--dir` | `-d` | Terraform directory to analyze. | `.` |
| `--format` | `-f` | `mermaid`, `dot`, `drawio`, `png`, `svg`, `pdf`. | `mermaid` |
| `--output` | `-o` | Output file path. | `tmac-diagram.[ext]` |
| `--simplify` | `-s` | Hides plumbing resources (IAM, permissions, policies, stages) while preserving connectivity. | `False` |
| `--group` | `-g` | Groups resources by microservice (subgraphs/clusters). | `False` |
| `--exclude-type` | | Resource type to hide (repeatable). | — |
| `--metadata` | | Also generates a document with the configuration of each resource. | `False` |
| `--metadata-format` | | Metadata document format: `md`, `json`. | `md` |
| `--exclude` | `-e` | Glob pattern to exclude (repeatable). | — |
| `--verbose` | `-v` | Debug logging. | `False` |
| `--quiet` | `-q` | Suppresses output. | `False` |

### Output formats

| Format | Description | Requirements |
| :--- | :--- | :--- |
| `mermaid` | Mermaid text; native rendering in GitHub/GitLab/Markdown. | — |
| `dot` | Graphviz DOT (text). | — |
| `drawio` | XML editable in draw.io / diagrams.net. | — |
| `png` / `svg` / `pdf` | Rendered image. | [Graphviz](https://graphviz.org/) (`brew install graphviz` / `apt-get install graphviz`). |

### Metadata document (`--metadata`)

Generates `tmac-metadata.md` (or `.json`) with the configuration of each resource, classified into:

- **Security-relevant attributes** (defined in `security_attrs.yaml`); if missing, they are marked as `<not defined>`.
- **Configuration** (scalar attributes).
- **Connections** (references to other resources).
- **Nested blocks** (`ingress`, `egress`, etc.).
- **Related configuration** (satellite resources, e.g. `aws_flow_log` → "VPC Flow Logs").

### Examples

```bash
# Full Mermaid diagram
tmac diagram --dir ./infra

# Clean diagram, grouped by microservice, as PNG
tmac diagram --dir ./infra --simplify --group --format png --output arch.png

# Diagram + JSON metadata for threat modeling
tmac diagram --dir ./infra --metadata --metadata-format json

# Hide specific types
tmac diagram --dir ./infra --exclude-type aws_iam_role --exclude-type aws_cloudwatch_log_group

# Export to draw.io for manual editing
tmac diagram --dir ./infra --simplify --format drawio --output arch.drawio
```

### Exit codes

| Code | Condition |
| :--- | :--- |
| `0` | Diagram generated successfully. |
| `3` | Execution error (inaccessible directory, Graphviz not installed for image formats). |

---

## Ignoring false positives (`tmac:ignore`)

Applies to `tmac scan` and `tmac plan`. Suppresses findings with comments in the `.tf` files:

```hcl
# Ignore all rules for the resource
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

## Configuration (`.tmac.yaml`)

```yaml
scan:
  exclude:
    - ".terraform"
    - "**/.terraform/**"
    - "modules/third-party/**"

report:
  format: html
```
