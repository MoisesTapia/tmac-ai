# CI/CD Integration — TMAC v1.6.0

TMAC returns [structured exit codes](COMMANDS.md#exit-codes) based on finding severity, making it straightforward to break a pipeline when a change degrades the security posture.

| Command | When to use |
| :--- | :--- |
| `tmac scan` | Audit the full infrastructure state on pushes to `main`. |
| `tmac plan` | Block the new risk introduced by a PR (requires a `tfplan.json`). |
| `tmac ci` | **Recommended for PRs** — native agent that detects changed files, scans them, and publishes a comment on the PR/MR automatically. |

For step-by-step examples and short snippets, see [EXAMPLES.md](EXAMPLES.md#advanced-usage).

---

## GitHub Actions — Official Action (`tmac ci`)

The simplest integration. The token is injected automatically and the PR comment is published only on `pull_request` events.

```yaml
# .github/workflows/tmac.yml
name: TMAC Security Review

on:
  pull_request:
    paths:
      - "**.tf"
  push:
    branches:
      - main

permissions:
  pull-requests: write
  contents: read

jobs:
  threat-model:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # required for delta mode

      - name: Install TMAC
        run: pip install "https://github.com/MoisesTapia/tmac-ai/archive/main.tar.gz"  # pin a tag or SHA

      - uses: ./                # or: tmac-security/tmac-action@v1.6.0
        with:
          dir: ./infra
          fail-on: high
          delta-only: "true"
          comment: "true"
          report-format: Markdown
```

### Action inputs

| Input | Default | Description |
| :--- | :--- | :--- |
| `dir` | `.` | Terraform directory to analyze. |
| `fail-on` | `high` | Severity threshold: `critical`, `high`, `medium`, `low`. |
| `delta-only` | `true` | Analyze only `.tf` files changed in the PR. |
| `comment` | `true` | Publish a PR comment. |
| `report-format` | `Markdown` | Report format: `Markdown`, `html`, `json`. |
| `output` | workspace default | Report output path. |

The report is always uploaded as a workflow artifact regardless of the exit code.

---

## GitHub Actions — `tmac scan` (full scan + SARIF)

Audits the full infrastructure and uploads results to GitHub Code Scanning:

```yaml
name: TMAC Full Scan

on:
  push:
    branches: [main]
  pull_request:
    paths:
      - "**.tf"

permissions:
  security-events: write
  contents: read

jobs:
  tmac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install TMAC
        run: pip install "https://github.com/MoisesTapia/tmac-ai/archive/main.tar.gz"  # pin a tag or SHA

      - name: Run TMAC scan
        run: |
          tmac scan \
            --dir ./infra \
            --exclude .terraform \
            --report json \
            --output tmac-results.sarif \
            --fail-on high \
            --no-color
        continue-on-error: true

      - name: Upload SARIF to GitHub Security
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: tmac-results.sarif
          category: tmac-threat-model

      - name: Upload report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: tmac-report
          path: tmac-results.sarif
```

---

## GitHub Actions — `tmac plan` (delta over tfplan)

Blocks the merge when the Terraform plan introduces Critical threats:

```yaml
name: TMAC Delta Risk Analysis

on:
  pull_request:
    paths:
      - "**.tf"

jobs:
  tmac-plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.0"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install TMAC
        run: pip install "https://github.com/MoisesTapia/tmac-ai/archive/main.tar.gz"  # pin a tag or SHA

      - name: Terraform Init & Plan
        run: |
          terraform init
          terraform plan -out=plan.bin
          terraform show -json plan.bin > plan.json
        working-directory: ./infra

      - name: Run TMAC Delta Analysis
        run: |
          tmac plan \
            --plan-file ./infra/plan.json \
            --report md \
            --output tmac-delta.md \
            --fail-on critical \
            --no-color

      - name: Upload Delta Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: tmac-delta-report
          path: tmac-delta.md
```

---

## GitLab CI — Official Template

Include the official template in your `.gitlab-ci.yml`. `CI_JOB_TOKEN` is injected automatically.

```yaml
# .gitlab-ci.yml
include:
  - project: tmac-security/tmac-ci
    file: /ci/gitlab/tmac.gitlab-ci.yml

# Override variables (optional — defaults match the GitHub Action)
variables:
  TMAC_DIR: "./infra"
  TMAC_FAIL_ON: "high"
  TMAC_DELTA_ONLY: "true"
  TMAC_COMMENT: "true"
```

The `tmac` job defined in the template:
- Publishes a comment on the MR only when `CI_PIPELINE_SOURCE == "merge_request_event"`.
- Stores the report artifact with `when: always`.
- A comment publish failure **does not fail the job** — the exit code is always findings-based.

### Available CI/CD variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `TMAC_DIR` | `.` | Directory to analyze. |
| `TMAC_FAIL_ON` | `high` | Severity threshold. |
| `TMAC_DELTA_ONLY` | `true` | Restrict to changed files. |
| `TMAC_COMMENT` | `true` | Publish comment on the MR. |

### GitLab CI — Manual job (without template)

```yaml
tmac-security-scan:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install "https://github.com/MoisesTapia/tmac-ai/archive/main.tar.gz"  # pin a tag or SHA
  script:
    - |
      tmac ci \
        --dir "${TMAC_DIR:-.}" \
        --fail-on "${TMAC_FAIL_ON:-high}" \
        --base-ref "${CI_MERGE_REQUEST_DIFF_BASE_SHA:-HEAD~1}" \
        --head-ref "${CI_COMMIT_SHA}" \
        --comment \
        --platform gitlab \
        --output tmac-report.md
  artifacts:
    paths:
      - tmac-report.md
    when: always
    expire_in: 30 days
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH'
```

---

## Docker — Scan in any CI/CD

Use the official Docker image without needing Python on the runner:

```bash
docker run --rm \
  -v $(pwd)/infra:/scan:ro \
  -v $(pwd)/output:/out \
  tmac-security/tmac:latest scan \
    --dir /scan \
    --report html \
    --output /out/report.html \
    --fail-on high
```

```yaml
# GitHub Actions — using the Docker image directly
- name: TMAC scan via Docker
  run: |
    docker run --rm \
      -v ${{ github.workspace }}/infra:/scan:ro \
      -v ${{ github.workspace }}:/out \
      tmac-security/tmac:latest scan \
        --dir /scan \
        --report json \
        --output /out/tmac-results.sarif \
        --fail-on high \
        --no-color
```

```yaml
# GitLab CI — using the Docker image as the job image
tmac-docker:
  image: tmac-security/tmac:latest
  script:
    - tmac scan --dir ./infra --report json --output tmac-results.sarif --fail-on high --no-color
  artifacts:
    paths:
      - tmac-results.sarif
    when: always
```

---

## Pre-commit hook

Block commits that introduce security threats before pushing:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/MoisesTapia/tmac-ai
    rev: v1.6.0
    hooks:
      - id: tmac
        args: ["--fail-on", "high"]   # optional
```

```bash
pip install pre-commit
pre-commit install
```

**Hook behavior:**
- ✅ Commit allowed → no findings above the threshold.
- ❌ Commit blocked → findings ≥ threshold or execution error (exit 3).
- ⏭️ Hook skipped automatically → no staged `.tf` files.

---

## Quick Reference Table

| Platform | Method | PR Comment | Artifact | Token |
| :--- | :--- | :--- | :--- | :--- |
| GitHub Actions (official Action) | `uses: tmac-security/tmac-action@v1.6.0` | ✅ automatic | ✅ `upload-artifact` | `GITHUB_TOKEN` (automatic) |
| GitHub Actions (`tmac ci` manual) | `run: tmac ci ...` | ✅ manual | ✅ manual | `GITHUB_TOKEN` (automatic) |
| GitHub Actions (`tmac scan` + SARIF) | `run: tmac scan ...` | ❌ | ✅ SARIF + Code Scanning | — |
| GitLab CI (official template) | `include: /ci/gitlab/tmac.gitlab-ci.yml` | ✅ automatic on MR | ✅ `when: always` | `CI_JOB_TOKEN` (automatic) |
| GitLab CI (manual job) | `tmac ci ...` script | ✅ manual | ✅ manual | `CI_JOB_TOKEN` (automatic) |
| Docker | `docker run tmac-security/tmac:latest` | ❌ | ✅ mounted volume | — |
| Pre-commit | Local hook | ❌ | ❌ | — |

---

## Token and Security Notes

- The token is **never** passed as a CLI argument — always read from an environment variable.
- GitHub Actions: `GITHUB_TOKEN` is injected automatically by the runner.
- GitLab CI: `CI_JOB_TOKEN` is injected automatically by the runner.
- Custom token: export `TMAC_TOKEN=<value>` before running `tmac ci`.
- Fork PRs: the token may lack comment-write permission → TMAC detects this, skips the comment, and uploads the artifact regardless.
- All output that might contain the token is passed through automatic redaction (`***REDACTED***`).
