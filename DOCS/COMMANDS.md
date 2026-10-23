# Command Reference — TMAC

TMAC exposes five subcommands through the `tmac` CLI:

```bash
tmac [--version] [--help] <command> [options]
```

| Command | Purpose |
| :--- | :--- |
| [`tmac scan`](#tmac-scan) | Static analysis of the full infrastructure state in `.tf` / `.tofu` files. |
| [`tmac cfn`](#tmac-cfn) | Static analysis of AWS CloudFormation templates (YAML/JSON). |
| [`tmac plan`](#tmac-plan) | Risk delta analysis over a `tfplan.json`. |
| [`tmac ci`](#tmac-ci) | Native CI/CD agent: delta scan of changed files and PR/MR comment. |
| [`tmac diagram`](#tmac-diagram) | Architecture diagram from the dependency graph. |

See [DOCS/EXAMPLES.md](EXAMPLES.md) for step-by-step usage examples at each level of complexity.

---

## tmac scan

Scans a directory of Terraform / OpenTofu files (`.tf`, `.tofu`) and evaluates every resource
against the STRIDE rule catalog. When both `x.tf` and `x.tofu` exist, only `x.tofu` is read (as
OpenTofu does). `.git`, `.terraform`, `.terragrunt-cache`, `node_modules`, `.aws-sam`, virtualenvs
and tool caches are never walked; pass one of them as `--dir` to scan it explicitly.

```bash
tmac scan [options]
```

### Options

| Option | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--dir` | `-d` | Directory to scan. | `scan.dir` from config, else `.` |
| `--report` | `-r` | Report format: `html`, `json`, `md`. | `html` |
| `--output` | `-o` | Report file path. | `tmac-report.[fmt]` |
| `--rules-dir` | | Directory of additional YAML rules. | (built-in rules) |
| `--config` | | Path to the configuration file. | `.tmac.yaml` |
| `--fail-on` | | Minimum severity for a non-zero exit: `critical`, `high`, `medium`, `low`, `info`. | `critical` |
| `--severity` | | Minimum severity to include in the report. | `all` |
| `--exclude` | `-e` | Glob pattern to exclude (repeatable). | — |
| `--lenient` | | Only warn (don't exit `3`) when files can't be parsed or rules are invalid. | `False` |
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
| `3` | Execution error (inaccessible directory, invalid config, missing explicit `--config`) or **incomplete scan**. |

**Fail closed.** If a file cannot be parsed or a rule is invalid, the results may be missing
findings, so the command exits `3` — the report is still written, with an *Incomplete scan*
banner (SARIF: `invocations[0].executionSuccessful = false`). `--lenient` only warns.

---

## tmac cfn

Scans AWS CloudFormation templates (YAML and JSON) with the same options, reports and exit
codes as `tmac scan` (except `--diagram`, which is Terraform-only). Default report:
`tmac-cfn-report.[fmt]`.

```bash
tmac cfn --dir ./templates
tmac cfn --dir ./templates --report md --fail-on high --severity medium
```

### Files analyzed

`.yaml`, `.yml`, `.json` and `.template` files that look like CloudFormation (they contain
`AWSTemplateFormatVersion` or a `Type: AWS::…`). Other YAML/JSON — Kubernetes manifests, Helm
templates, `package.json` — is skipped without errors. The format is detected from the content.
To scan AWS CDK output: `tmac cfn --dir cdk.out`. A template that looks like CloudFormation but
cannot be read (invalid YAML/JSON, resource without `Type`, larger than 5 MB) makes the scan
incomplete → exit `3` unless `--lenient`.

### Intrinsic functions

`!Ref`, `!Sub`, `!GetAtt`, `!If`, `!Join`, … (short or long `Fn::` form) are kept as values that
are only known at deploy time: they count as **present** for `exists` / `not_exists`, but **no
comparison raises a finding** on them (e.g. `Encrypted: !Ref EncryptVolumes` is not reported as
an unencrypted volume). Parameters, mappings and conditions are not resolved.

### Suppressions in CloudFormation

```yaml
Resources:
  # tmac:ignore                       ← all rules for this resource
  PublicAssets:
    Type: AWS::S3::Bucket

  # tmac:ignore[TMAC-CFN-S3-003]      ← one rule (stack several lines for more)
  Logs:
    Type: AWS::S3::Bucket

  Website:  # tmac:ignore[TMAC-CFN-S3-004]   ← also on the LogicalId line
    Type: AWS::S3::Bucket

  JsonFriendly:                       # Metadata also works in JSON templates
    Type: AWS::S3::Bucket
    Metadata:
      tmac:
        ignore: ["TMAC-CFN-S3-002"]   # or "*"
```

### Known limitations

- Values from `Parameters`, `Mappings` and `Conditions` are not resolved (see above).
- Each resource is evaluated on its own: `TMAC-CFN-VPC-001` relies on a `FlowLogs=enabled` tag
  (same workaround as `TMAC-AWS-VPC-001`), and Security Group port/CIDR checks are not
  correlated per ingress rule.
- Not covered yet: `AWS::IAM::AccessKey`, inline policies of `AWS::IAM::User`,
  `AWS::RDS::DBCluster`, SAM (`AWS::Serverless::*`).

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
| `--plan-file` | `-p` | Path to the plan JSON (`terraform show -json` or `tofu show -json`). | **Yes** |
| `--report` | `-r` | Report format: `html`, `json`, `md`. | No |
| `--output` | `-o` | Report file path. | No |
| `--rules-dir` | | Directory of additional YAML rules. | No |
| `--config` | | Configuration file (`report.format`, `report.fail_on`, `scan.rules_dir`). | No |
| `--source-dir` | | Directory with the plan's `.tf`/`.tofu` sources, to apply their `tmac:ignore` comments. | No |
| `--fail-on` | | Minimum severity for a non-zero exit. | No |
| `--lenient` | | Only warn (don't exit `3`) when rules are invalid. | No |
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
| `3` | Execution error (file not found, invalid JSON, missing `resource_changes`) or invalid rules (unless `--lenient`). |

---

## tmac ci

Native CI/CD agent. Orchestrates automatically: detects changed `.tf`/`.tofu` files between two git refs, scans them, writes the report artifact, formats a narrative comment, and publishes it on the PR/MR.

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
| `--lenient` | Only warn (don't exit `3`) on an incomplete scan. | `False` |
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

```
<!-- tmac:pr-comment:v1 -->
## 🔴 TMAC Security Review — 2 threats detected

This PR modifies 3 `.tf` files and introduces the following threats:

| Severity | Resource | Rule | STRIDE | Action | Mitigation |
|---|---|---|---|---|---|
| 🔴 Critical | `aws_s3_bucket.uploads` | TMAC-AWS-S3-001 | Information Disclosure | NEW | Set ACL to `private` |
| 🟠 High | `aws_security_group.web` | TMAC-AWS-SG-001 | Tampering | MODIFIED | Restrict port 22 |

**Status:** ❌ BLOCKED — Critical findings were detected.
[View full report](artifacts/tmac-report.md)
```

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
| `3` | Execution error (invalid/missing refs, inaccessible directory) or incomplete scan — the report and PR/MR comment (with an *Incomplete scan* note) are still produced. |

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

Applies to `tmac scan` and `tmac ci`, and to `tmac plan` with `--source-dir` (plan JSON keeps no
comments, so suppressions are matched to planned changes by resource type and name). Each
suppression applies only to that exact resource (file + type + name). For CloudFormation syntax
see [`tmac cfn`](#suppressions-in-cloudformation). In `.tf` files:

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
  dir: ./infra                 # default --dir
  rules_dir: ./custom-rules    # additional YAML rules
  exclude:
    - "modules/third-party/**"

report:
  format: html                 # html | json | md
  fail_on: high                # critical | high | medium | low | info
  severity: all                # all | critical | high | medium | low | info
```

Precedence: **CLI flag > `.tmac.yaml` > built-in default**. `./.tmac.yaml` is read by default;
pass another file with `--config ./config/tmac-prod.yaml` (a missing explicit `--config` exits `3`).
Unknown keys and invalid values are ignored with a warning.
