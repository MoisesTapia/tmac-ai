<div align="center">

# 🛡️ TMAC — Threat Modeling as Code

**Static security analysis for Infrastructure as Code, powered by the STRIDE framework.**

![Version](https://img.shields.io/badge/version-1.6.0%20%22Ixtla%22-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Rules](https://img.shields.io/badge/rules-560%2B-orange)

</div>

TMAC automates threat modeling by identifying vulnerabilities in Terraform / OpenTofu code and AWS
CloudFormation templates **before deployment**. It scans the full infrastructure state, analyzes the risk delta of a plan, renders architecture diagrams, and now lives directly in your repository as a native CI/CD security agent — all offline, with no data sent to external APIs.

## Table of Contents

- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Examples](#examples)
- [Rule Catalog](#rule-catalog)
- [Contributing](#contributing)
- [License](#license)

## Key Features

- **Terraform & OpenTofu analysis (`tmac scan`)** — static scan of `.tf` and `.tofu` files against **520+ STRIDE rules** covering **105 AWS resource types**.
- **CloudFormation analysis (`tmac cfn`)** — YAML and JSON templates (intrinsic functions included) against **43 STRIDE rules** for 11 AWS services.
- **Risk delta analysis (`tmac plan`)** — detects threats only in the resources a Terraform plan will create, modify, or destroy. Answers: *"what new risk does this PR introduce?"*
- **Native CI/CD agent (`tmac ci`)** — analyzes only the `.tf`/`.tofu` files changed in a push/PR, posts a narrative comment on the PR/MR, and uploads the report as an artifact.
- **Architecture diagrams (`tmac diagram`)** — builds the dependency graph between resources and exports it to Mermaid, Graphviz (DOT), draw.io (XML), or image (PNG/SVG/PDF).
- **YAML rule engine** — declarative, strongly-typed threat rules validated with Pydantic.
- **STRIDE categorization** — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege.
- **Multiple report formats** — HTML, Markdown, and JSON/SARIF 2.1.0.
- **Structured exit codes, fail closed** — breaks the pipeline on critical threats, and on scans that could not read every file or rule.
- **Offline by design** — no telemetry, no external API calls.

## Installation

```bash
# From the repository (pin a tag or commit SHA instead of main for CI)
pip install "https://github.com/MoisesTapia/tmac-ai/archive/main.tar.gz"

# From source, with hash-verified dependencies
git clone https://github.com/MoisesTapia/tmac-ai.git && cd tmac-ai
pip install --require-hashes -r requirements.txt && pip install --no-deps -e .

# Docker (build the image from the repository Dockerfile)
docker build -t tmac . && docker run --rm -v $(pwd)/infra:/scan tmac scan --dir /scan
```

> **Note:** the PyPI package named `tmac` is an **unrelated project** — do not
> `pip install tmac`. Install TMAC from this repository (pin a tag or commit SHA in CI).

> Full installation options (Poetry, Docker, pre-commit) in [DOCS/INSTALLATION.md](DOCS/INSTALLATION.md).

## Quick Start

```bash
# Scan a Terraform directory
tmac scan --dir ./infra

# Scan AWS CloudFormation templates
tmac cfn --dir ./templates

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
| [Command reference](DOCS/COMMANDS.md) | Complete guide to `scan`, `plan`, `ci`, and `diagram`. |
| [Examples](DOCS/EXAMPLES.md) | Basic, intermediate, and advanced usage — console and CI/CD. |
| [CI/CD integration](DOCS/CICD.md) | GitHub Actions, GitLab CI, Docker, and pre-commit pipelines. |
| [Rule catalog](DOCS/RULES.md) | The 520 rules by service and severity. |
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

TMAC v1.6.0 includes **520 rules** covering **105 AWS resource types**.

| Severity | Rules |
| :--- | :--- |
| 🔴 Critical | 24 |
| 🟠 High | 56 |
| 🟡 Medium | 121 |
| 🟢 Low | 106 |
| 🔵 Info | 213 |

See the [complete rule catalog](DOCS/RULES.md) for the full breakdown by service.

## Contributing

Contributions are welcome. See the [contribution guide](CONTRIBUTING.md) for how to add rules and run the tests, and [Writing rules](DOCS/WRITING_RULES.md) for the rule format.

## License

MIT — see [LICENSE](LICENSE) for details.
