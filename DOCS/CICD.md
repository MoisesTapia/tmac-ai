# CI/CD Integration

TMAC returns structured [exit codes](COMMANDS.md#exit-codes) based on finding
severity, which makes it straightforward to break a pipeline when a change
degrades the security posture.

- Use **`tmac scan`** to audit the full infrastructure state.
- Use **`tmac plan`** to block only the new risk introduced by a pull request.

## GitHub Actions — `tmac scan`

```yaml
name: TMAC Security Scan

on:
  pull_request:
    paths:
      - "**.tf"

jobs:
  tmac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install TMAC
        run: pip install -e .

      - name: Run TMAC scan
        run: |
          tmac scan \
            --dir ./infra \
            --exclude .terraform \
            --report json \
            --output tmac-results.json \
            --fail-on high \
            --no-color

      - name: Upload SARIF to GitHub Security
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: tmac-results.json
```

## GitHub Actions — `tmac plan` (delta analysis on PRs)

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
          python-version: "3.10"

      - name: Install TMAC
        run: pip install -e .

      - name: Terraform Init
        run: terraform init
        working-directory: ./infra

      - name: Generate Terraform Plan
        run: |
          terraform plan -out=plan.bin
          terraform show -json plan.bin > plan.json
        working-directory: ./infra

      - name: Run TMAC Delta Analysis
        # Exit code 1 = Critical findings → blocks the PR
        # Exit code 2 = High findings → blocks the PR (adjust --fail-on per policy)
        # Exit code 0 = safe plan → allows the merge
        run: |
          tmac plan \
            --plan-file ./infra/plan.json \
            --report json \
            --output tmac-delta.json \
            --fail-on critical \
            --no-color

      - name: Upload Delta Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: tmac-delta-report
          path: tmac-delta.json

      - name: Upload SARIF to GitHub Security
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: tmac-delta.json
```

## GitLab CI

```yaml
tmac-security-scan:
  stage: test
  image: python:3.10-slim
  before_script:
    - pip install -e .
  script:
    - tmac scan
        --dir ./infra
        --exclude .terraform
        --report json
        --output tmac-results.json
        --fail-on high
        --no-color
  artifacts:
    when: always
    paths:
      - tmac-results.json
    reports:
      sast: tmac-results.json
  rules:
    - changes:
        - "**/*.tf"
```
