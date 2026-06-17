<div align="center">

# 🛡️ TMAC — Threat Modeling as Code

**Static security analysis for Infrastructure as Code, powered by the STRIDE framework.**

![Version](https://img.shields.io/badge/version-1.1.0%20%22Ixtla%22-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Rules](https://img.shields.io/badge/rules-520%2B-orange)

</div>

TMAC automates threat modeling by identifying vulnerabilities in Terraform code
**before deployment**. It scans the full infrastructure state, analyzes the risk
delta of a plan, and renders architecture diagrams — all offline, with no data
sent to external APIs.

## Table of Contents

- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Examples](#examples)
- [Rule Catalog](#rule-catalog)
- [Contributing](#contributing)
- [License](#license)

## Key Features

- **Terraform analysis (`tmac scan`)** — static scanning of `.tf` files against a catalog of **520+ STRIDE rules** covering **105 AWS resource types**.
- **Risk delta analysis (`tmac plan`)** — detects STRIDE threats only in the resources a Terraform plan will create, modify, or destroy, answering *"what new risk does this PR introduce?"*.
- **Architecture diagrams (`tmac diagram`)** — builds the dependency graph between resources and exports it to Mermaid, Graphviz (DOT), draw.io (XML), or image (PNG/SVG/PDF), with noise filtering, grouping by microservice, and metadata extraction.
- **YAML rule engine** — strongly typed threat rules validated with Pydantic.
- **STRIDE categorization** — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege.
- **Multiple report formats** — HTML, Markdown, and JSON/SARIF 2.1.0.
- **CI/CD ready** — structured exit codes that break the pipeline on critical threats.
- **Offline by design** — no telemetry, no external API calls.

## Quick Start

```bash
# 1. Install (see DOCS/INSTALLATION.md for Poetry and Graphviz options)
git clone https://github.com/MoisesTapia/tmac-ai.git
cd tmac-ai
python -m venv venv && source venv/bin/activate
pip install -e .

# 2. Scan a Terraform directory (generates tmac-report.html)
tmac scan --dir ./infra

# 3. Analyze the risk delta of a plan
terraform plan -out=plan.bin && terraform show -json plan.bin > plan.json
tmac plan --plan-file plan.json --fail-on critical

# 4. Render an architecture diagram
tmac diagram --dir ./infra --simplify --group --format png --output arch.png
```

> Full installation instructions are in [DOCS/INSTALLATION.md](DOCS/INSTALLATION.md).

## Documentation

Full documentation lives in the [`DOCS/`](DOCS/README.md) directory.

| Document | Description |
| :--- | :--- |
| [Installation](DOCS/INSTALLATION.md) | Requirements and setup with Poetry or pip. |
| [Command reference](DOCS/COMMANDS.md) | Complete guide to `scan`, `plan`, and `diagram` (options, exit codes, `tmac:ignore`, `.tmac.yaml`). |
| [Rule catalog](DOCS/RULES.md) | The 520 rules by service and severity. |
| [Writing rules](DOCS/WRITING_RULES.md) | Rule format, condition operators, and custom rules. |
| [CI/CD integration](DOCS/CICD.md) | GitHub Actions and GitLab CI pipelines. |
| [Examples](DOCS/EXAMPLES.md) | Sample Terraform architectures to try the tool. |
| [Architecture](DOCS/ARCHITECTURE.md) | Project layout and the full-state vs. risk-delta model. |
| [AWS STRIDE mapping](DOCS/aws_stride_mapping.md) | How AWS services map to STRIDE categories. |
| [Roadmap](ROADMAP.md) | Vision and future versions. |

## Examples

The [`examples/`](examples/) directory contains ready-to-use Terraform architectures:

| Example | Description |
| :--- | :--- |
| `examples/ecommerce/` | Serverless microservices: API Gateway → Lambda → DynamoDB, EventBridge, and SQS. |
| `examples/enterprise/` | Multi-AZ, multi-region enterprise architecture: VPC, ALB+WAF, Aurora, Cognito, Route53 failover, and more. |

```bash
tmac scan --dir examples/enterprise --report html --output report.html --diagram
```

See [DOCS/EXAMPLES.md](DOCS/EXAMPLES.md) for more.

## Rule Catalog

TMAC v1.1.0 includes **520 rules** covering **105 AWS resource types**, with a
minimum of 8 rules per resource type present in the reference examples.

| Severity | Rules |
| :--- | :--- |
| 🔴 Critical | 24 |
| 🟠 High | 56 |
| 🟡 Medium | 121 |
| 🟢 Low | 106 |
| 🔵 Info | 213 |

See the [complete rule catalog](DOCS/RULES.md) for the breakdown by service.

## Contributing

Contributions are welcome. See the [contribution guide](CONTRIBUTING.md) for how
to add rules and run the tests, and [Writing rules](DOCS/WRITING_RULES.md) for
the rule format.

## License

MIT — see [LICENSE](LICENSE) for details.
