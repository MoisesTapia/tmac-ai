# Usage Examples — TMAC v1.6.0

This guide covers TMAC usage from simple one-liners to fully automated CI/CD pipelines. For the complete option reference, see [COMMANDS.md](COMMANDS.md). For CI/CD pipeline templates, see [CICD.md](CICD.md).

## Table of Contents

- [Basic usage](#basic-usage)
  - [1. Scan a directory](#1-scan-a-directory)
  - [2. Analyze a Terraform plan](#2-analyze-a-terraform-plan)
  - [3. Generate an architecture diagram](#3-generate-an-architecture-diagram)
- [Intermediate usage](#intermediate-usage)
  - [4. Exclude directories and modules](#4-exclude-directories-and-modules)
  - [5. Thresholds and report formats](#5-thresholds-and-report-formats)
  - [6. Suppress false positives](#6-suppress-false-positives)
  - [7. Custom rules](#7-custom-rules)
  - [8. Basic CI/CD scan (changed files only)](#8-basic-cicd-scan-changed-files-only)
- [Advanced usage](#advanced-usage)
  - [9. Full pipeline in one line](#9-full-pipeline-in-one-line)
  - [10. CI agent with PR comment](#10-ci-agent-with-pr-comment)
  - [11. Diagram with embedded metadata](#11-diagram-with-embedded-metadata)
  - [12. GitHub Action (official)](#12-github-action-official)
  - [13. GitLab CI template (official)](#13-gitlab-ci-template-official)
  - [14. Docker — scan in a container](#14-docker--scan-in-a-container)
  - [15. Pre-commit hook](#15-pre-commit-hook)
  - [16. SARIF upload to GitHub Code Scanning](#16-sarif-upload-to-github-code-scanning)
- [Included example architectures](#included-example-architectures)

---

## Basic usage

### 1. Scan a directory

The simplest scenario: scan a local Terraform directory and view findings in the terminal.

```bash
# HTML report (default)
tmac scan --dir ./infra

# Markdown report
tmac scan --dir ./infra --report md --output infra-threats.md

# JSON/SARIF report
tmac scan --dir ./infra --report json --output results.sarif
```

The HTML report opens in any browser and shows each finding with its severity, resource, STRIDE category, and mitigation.

### 2. Analyze a Terraform plan

Detect threats only in the resources that are going to change — no noise from pre-existing technical debt.

```bash
# Step 1: generate the plan
terraform plan -out=plan.bin

# Step 2: export to JSON
terraform show -json plan.bin > plan.json

# Step 3: analyze the delta
tmac plan --plan-file plan.json
```

The report shows the **RiskDelta** = threats introduced − threats resolved, with `NEW`, `MODIFIED`, and `REMOVED` labels per resource.

### 3. Generate an architecture diagram

Build the dependency graph between Terraform resources and export it.

```bash
# Mermaid diagram (paste into GitHub / GitLab)
tmac diagram --dir ./infra

# View the output file
cat tmac-diagram.mmd
```

---

## Intermediate usage

### 4. Exclude directories and modules

```bash
# Exclude .terraform and third-party modules
tmac scan --dir ./infra \
  --exclude .terraform \
  --exclude "**/modules/vendor/**" \
  --exclude "**/.terraform/**"
```

You can also declare exclusions permanently in `.tmac.yaml` at the repository root:

```yaml
scan:
  exclude:
    - ".terraform"
    - "**/.terraform/**"
    - "modules/third-party/**"
```

Then just run `tmac scan --dir ./infra` — TMAC picks up the config file automatically.

### 5. Thresholds and report formats

```bash
# Fail only on Critical findings (tolerant of High and below)
tmac scan --dir ./infra --fail-on critical

# Fail on High or above (stricter)
tmac scan --dir ./infra --fail-on high

# Show only High and Critical in the report
tmac scan --dir ./infra --severity high --report md --output report.md

# No ANSI colors (ideal for CI logs)
tmac scan --dir ./infra --no-color --quiet
```

### 6. Suppress false positives

Add `tmac:ignore` comments directly in `.tf` files. See [COMMANDS.md — tmac:ignore](COMMANDS.md#suppressing-false-positives-tmacignore) for the full syntax.

```hcl
# Ignore all rules for this resource (audited exception)
# tmac:ignore
resource "aws_s3_bucket" "public_static" {
  bucket = "my-public-static-assets"
  acl    = "public-read"
}

# Ignore one specific rule
# tmac:ignore[TMAC-AWS-S3-001]
resource "aws_s3_bucket" "cdn_assets" {
  bucket = "cdn-assets"
  acl    = "public-read"
}
```

### 7. Custom rules

Write your own rules in YAML and point TMAC at that directory. See [WRITING_RULES.md](WRITING_RULES.md) for the full rule format.

```yaml
# my-rules/custom.yaml
version: "1.0"
rules:
  - id: CUSTOM-AWS-S3-001
    name: "S3 bucket missing environment tag"
    resource_type: "aws_s3_bucket"
    check:
      attribute: "tags.Environment"
      condition: "not_exists"
      values: []
    severity: "Medium"
    stride: "Repudiation"
    description: "All buckets must carry an environment tag."
    mitigation: "Add tags { Environment = \"prod\" }"
```

```bash
tmac scan --dir ./infra --rules-dir ./my-rules
```

### 8. Basic CI/CD scan (changed files only)

`tmac ci` analyzes only the `.tf` files that changed between two git refs — ideal for pre-push hooks or lightweight pipelines.

```bash
# Analyze files changed between main and HEAD
tmac ci --dir ./infra --base-ref main --head-ref HEAD

# Generate report only, no PR comment
tmac ci --dir ./infra --base-ref origin/main --head-ref HEAD --no-comment --fail-on high

# Full scan (no delta restriction)
tmac ci --dir ./infra --no-delta-only --fail-on critical
```

---

## Advanced usage

### 9. Full pipeline in one line

```bash
terraform plan -out=plan.bin && \
  terraform show -json plan.bin > plan.json && \
  tmac plan --plan-file plan.json --fail-on critical --report md --output delta-report.md
```

### 10. CI agent with PR comment

When running inside a real pipeline with CI environment variables available, `tmac ci` auto-detects the platform, reads the token from the environment, and publishes the comment.

```bash
# GitHub Actions — GITHUB_TOKEN is injected automatically
tmac ci \
  --dir ./infra \
  --base-ref "$GITHUB_BASE_REF" \
  --head-ref "$GITHUB_HEAD_REF" \
  --fail-on high \
  --comment \
  --platform github

# GitLab CI — CI_JOB_TOKEN is injected automatically
tmac ci \
  --dir "${TMAC_DIR:-.}" \
  --base-ref "${CI_MERGE_REQUEST_DIFF_BASE_SHA:-HEAD~1}" \
  --head-ref "${CI_COMMIT_SHA}" \
  --fail-on high \
  --comment \
  --platform gitlab
```

### 11. Diagram with embedded metadata

Generate a clean architecture diagram plus a security metadata document for manual threat modeling:

```bash
# Diagram as PNG + JSON metadata
tmac diagram --dir ./infra \
  --simplify \
  --group \
  --format png \
  --output arch.png \
  --metadata \
  --metadata-format json

# Embed the diagram directly in the scan HTML report
tmac scan --dir ./infra --report html --output report.html --diagram
```

### 12. GitHub Action (official)

For the complete workflow YAML and all available inputs, see [CICD.md — GitHub Actions](CICD.md#github-actions--official-action-tmac-ci).

```yaml
# .github/workflows/tmac.yml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0

- name: Install TMAC
  run: pip install "https://github.com/MoisesTapia/tmac-ai/archive/main.tar.gz"  # pin a tag or SHA

- uses: ./   # or: tmac-security/tmac-action@v1.6.0
  with:
    dir: ./infra
    fail-on: high
    delta-only: "true"
    comment: "true"
    report-format: Markdown
```

### 13. GitLab CI template (official)

For the complete template and variable reference, see [CICD.md — GitLab CI](CICD.md#gitlab-ci--official-template).

```yaml
# .gitlab-ci.yml
include:
  - project: tmac-security/tmac-ci
    file: /ci/gitlab/tmac.gitlab-ci.yml

variables:
  TMAC_FAIL_ON: "high"
  TMAC_DIR: "./infra"
```

### 14. Docker — scan in a container

No Python installation needed on the host.

```bash
# Basic scan
docker run --rm \
  -v $(pwd)/infra:/scan:ro \
  -v $(pwd)/reports:/out \
  tmac-security/tmac:latest scan \
    --dir /scan \
    --report html \
    --output /out/report.html \
    --fail-on high

# Plan delta analysis
docker run --rm \
  -v $(pwd)/plan.json:/plan.json:ro \
  -v $(pwd)/reports:/out \
  tmac-security/tmac:latest plan \
    --plan-file /plan.json \
    --report md \
    --output /out/delta.md
```

For Docker usage inside a GitHub Actions or GitLab CI pipeline, see [CICD.md — Docker](CICD.md#docker--scan-in-any-cicd).

### 15. Pre-commit hook

Block commits that introduce security threats before they are pushed. See [CICD.md — pre-commit](CICD.md#pre-commit-hook) for details.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/MoisesTapia/tmac-ai
    rev: v1.6.0
    hooks:
      - id: tmac
        args: ["--fail-on", "high"]
```

```bash
pip install pre-commit
pre-commit install
```

### 16. SARIF upload to GitHub Code Scanning

For the full workflow YAML, see [CICD.md — GitHub Actions tmac scan + SARIF](CICD.md#github-actions--tmac-scan-full-scan--sarif).

```bash
tmac scan \
  --dir ./infra \
  --report json \
  --output tmac-results.sarif \
  --no-color
```

Then upload with `github/codeql-action/upload-sarif@v3`.

---

## Included example architectures

### `examples/ecommerce/`

Serverless microservices: API Gateway → Lambda → DynamoDB, EventBridge, SQS.

```bash
tmac scan --dir examples/ecommerce --report md --output ecommerce-threats.md
tmac diagram --dir examples/ecommerce --simplify --format png --output ecommerce-arch.png
```

### `examples/enterprise/`

Multi-AZ, multi-region enterprise architecture: VPC, ALB+WAF, Auto Scaling, Aurora Serverless, RDS Proxy, Cognito, DevOps pipeline, VPC endpoints, Kinesis/S3/Glacier, Pinpoint, Route53 failover, CloudTrail, warm standby.

```bash
# Full HTML report with embedded diagram
tmac scan --dir examples/enterprise --report html --output report.html --diagram

# Critical and High findings only
tmac scan --dir examples/enterprise --severity high --report md --output high-threats.md

# Grouped architecture diagram as PNG
tmac diagram --dir examples/enterprise --simplify --group --format png --output arch.png
```

### `examples/demo/`

Minimal architecture used to generate the sample reports and diagrams included in the repository.

```bash
tmac scan --dir examples/demo
tmac diagram --dir examples/demo --format mermaid
```
