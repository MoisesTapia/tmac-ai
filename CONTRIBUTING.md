# Contribution Guide — TMAC

Thanks for your interest in contributing to TMAC! This guide covers how to set up the environment,
run the tests, and the process for adding new threat rules.

## Table of contents

1. [Set up the development environment](#1-set-up-the-development-environment)
2. [Run the tests](#2-run-the-tests)
3. [Contribute new rules](#3-contribute-new-rules)
4. [Pull Request process](#4-pull-request-process)

---

## 1. Set up the development environment

### Prerequisites

- Python **3.10+**
- [Poetry](https://python-poetry.org/docs/#installation) (dependency manager)
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/tmac-security/tmac.git
cd tmac

# 2. Install dependencies (including dev)
poetry install

# 3. Activate the Poetry virtual environment
poetry shell

# 4. Verify the installation
tmac --version
```

### Alternative with pip

```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install --require-hashes -r requirements-dev.txt   # pinned, audited, hash-verified
pip install -e . --no-deps
```

### Dependencies and lockfiles

- `requirements.in` / `requirements-dev.in`: direct dependencies with version ranges (edited by hand).
- `requirements.txt` / `requirements-dev.txt`: **generated** lockfiles with the exact version and SHA-256 hash of every package. Never edit them by hand.

To add or upgrade a dependency, edit the `.in` file, regenerate the lockfiles with [uv](https://docs.astral.sh/uv/) and audit them:

```bash
uv pip compile requirements.in --universal --generate-hashes --python-version 3.10 -o requirements.txt
uv pip compile requirements-dev.in --universal --generate-hashes --python-version 3.11 -o requirements-dev.txt
pip-audit --require-hashes --disable-pip -r requirements.txt
pip-audit --require-hashes --disable-pip -r requirements-dev.txt
```

To move to newer versions within the ranges, add `--upgrade` (or `--upgrade-package <name>`) to `uv pip compile`. CI re-audits the lockfiles every week.

### Included development tools

| Tool | Use |
| :--- | :--- |
| `pytest` | Running tests |
| `pytest-cov` | Code coverage |
| `hypothesis` | Property-based testing |
| `ruff` | Linting and formatting |
| `black` | Code formatting |
| `mypy` | Type checking |

---

## 2. Run the tests

### Full suite

```bash
pytest
```

### With code coverage

```bash
# Coverage of production code (target: ≥90%)
pytest --cov=tmac --cov-report=term-missing

# Integration tests only (target: ≥80%)
pytest tests/integration/ --cov=tmac
```

### Specific tests

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# A specific module
pytest tests/unit/test_evaluator.py

# A specific test
pytest tests/unit/test_evaluator.py::test_evaluator_list_any_match -v
```

### Property tests (Hypothesis)

The property tests use Hypothesis with `@settings(max_examples=100)`.
To run them with more examples during development:

```bash
# Run with more examples for greater confidence
pytest tests/ -k "property" --hypothesis-seed=0
```

### Linting and types

```bash
# Linting with ruff
ruff check src/ tests/

# Formatting with black
black src/ tests/

# Type checking with mypy
mypy src/tmac/
```

---

## 3. Contribute new rules

Threat rules are defined in `threats*.yaml` files inside `src/tmac/rules/aws/`.
The `RuleLoader` automatically loads all files that match `threats*.yaml`
(`threats.yaml`, `threats_extended.yaml`, ...), so you can add rules to the
existing file or create a new one following that naming pattern.

### Schema of a rule

```yaml
- id: TMAC-AWS-{SERVICE}-{NNN}       # Mandatory format, e.g.: TMAC-AWS-S3-007
  name: "Descriptive name of the threat"
  resource_type: "aws_resource_type"  # Exact Terraform resource type
  check:
    attribute: "path.to.attribute"     # Path to the resource attribute
    condition: "equals"               # See available operators
    values: ["expected_value"]
    and_check:                        # Optional: additional condition (logical AND)
      attribute: "other.attribute"
      condition: "contains"
      values: ["other_value"]
  severity: "Critical"                # Critical | High | Medium | Low | Info
  stride: "Information Disclosure"    # STRIDE category (see list below)
  description: >
    Detailed description of the threat and its impact.
  mitigation: >
    Concrete steps to mitigate the threat with a Terraform code example.
  references:
    - "https://docs.aws.amazon.com/..."
    - "CIS AWS Benchmark vX.X - X.X"
  tags: ["service", "category", "tag"]
```

### Naming conventions

- **ID**: `TMAC-{CLOUD}-{SERVICE}-{NNN}` where:
  - `CLOUD`: cloud provider in uppercase (`AWS`, `GCP`, `AZURE`)
  - `SERVICE`: service in uppercase (`S3`, `IAM`, `SG`, `RDS`, `EC2`, `VPC`, `CW`)
  - `NNN`: 3-digit sequential number (`001`, `002`, ...)
- **`resource_type`**: must match exactly the Terraform resource type (e.g., `aws_s3_bucket`)
- **`severity`**: use `Critical`, `High`, `Medium`, `Low`, or `Info` (capitalized)
- **`stride`**: one of the 6 categories: `Spoofing`, `Tampering`, `Repudiation`, `Information Disclosure`, `Denial of Service`, `Elevation of Privilege`

### Available condition operators

| Operator | Description |
| :--- | :--- |
| `equals` | The attribute equals the value. |
| `not_equals` | The attribute does not equal the value. |
| `in` | The attribute is in the list of values. |
| `not_in` | The attribute is not in the list of values. |
| `contains` | The attribute contains the value (string or list). |
| `not_contains` | The attribute does not contain the value. |
| `regex` | The attribute matches the regular expression. |
| `exists` | The attribute exists in the resource. |
| `not_exists` | The attribute does not exist in the resource. |

### Complete example: new S3 rule

```yaml
- id: TMAC-AWS-S3-007
  name: "S3 Bucket without Versioning Enabled"
  resource_type: "aws_s3_bucket"
  check:
    attribute: "versioning.enabled"
    condition: "not_exists"
    values: []
  severity: "Medium"
  stride: "Tampering"
  description: >
    The S3 bucket does not have object versioning enabled. Without versioning,
    accidental or malicious overwriting or deletion of objects is
    irreversible, facilitating Tampering attacks.
  mitigation: >
    Enable versioning on the bucket:
      resource "aws_s3_bucket_versioning" "example" {
        bucket = aws_s3_bucket.example.id
        versioning_configuration {
          status = "Enabled"
        }
      }
  references:
    - "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html"
  tags: ["s3", "versioning", "data-integrity"]
```

### Add test fixtures for the new rule

Every new rule must include at least one positive fixture (that triggers the rule) and one negative fixture (that does not trigger it) in `tests/fixtures/`:

**`tests/fixtures/s3_no_versioning.tf`** (positive — triggers the rule):
```hcl
resource "aws_s3_bucket" "no_versioning" {
  bucket = "my-bucket-no-versioning"
}
```

**`tests/fixtures/s3_with_versioning.tf`** (negative — does not trigger the rule):
```hcl
resource "aws_s3_bucket" "with_versioning" {
  bucket = "my-bucket-with-versioning"
}

resource "aws_s3_bucket_versioning" "example" {
  bucket = aws_s3_bucket.with_versioning.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

Then add the pair to `RULE_FIXTURES` in `tests/integration/test_rules.py`:

```python
RULE_FIXTURES = [
    # ... existing rules ...
    ("TMAC-AWS-S3-007", "s3_no_versioning.tf",    True),
    ("TMAC-AWS-S3-007", "s3_with_versioning.tf",  False),
]
```

---

## 4. Pull Request process

1. **Create a branch** from `main` with a descriptive name:
   ```bash
   git checkout -b feat/tmac-aws-s3-007-versioning
   ```

2. **Implement the changes** following the project conventions.

3. **Add or update tests** — every new rule requires fixtures and parametrized tests.

4. **Verify that the tests pass**:
   ```bash
   pytest --cov=tmac
   ruff check src/ tests/
   mypy src/tmac/
   ```

5. **Update `CHANGELOG.md`** by adding your change under `[Unreleased]`.

6. **Open the Pull Request** with a clear description of:
   - What threat the new rule detects
   - Why it is relevant (reference to CIS Benchmark, CVE, etc.)
   - How it was tested

### Acceptance criteria for new rules

- [ ] ID follows the format `TMAC-{CLOUD}-{SERVICE}-{NNN}`
- [ ] `resource_type` is a valid Terraform resource type
- [ ] `severity` and `stride` use the allowed values
- [ ] Positive fixture triggers exactly one `Finding` with the correct `rule_id`
- [ ] Negative fixture produces no `Finding`
- [ ] Tests pass with `pytest` without errors
- [ ] Code coverage does not drop below 90%
