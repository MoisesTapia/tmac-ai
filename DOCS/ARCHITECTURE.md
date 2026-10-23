# Architecture

## Project layout

```
src/tmac/
├── cli.py          # CLI interface (Click) — scan, cfn, plan, ci, and diagram subcommands
├── scanner.py      # Format-agnostic scan pipeline: Scanner(parser=...) + discover_files()
├── config.py       # Loading and validation of .tmac.yaml
├── models/         # Pydantic models (Finding, ScanResult, ResourceModel)
├── parsers/        # TerraformParser (.tf/.tofu), CloudFormationParser, TfplanParser
├── delta/          # DeltaScanner, DeltaFinding, DeltaScanResult, PlannedChange
├── engine/         # RuleLoader, Matcher, Evaluator
├── graph/          # GraphBuilder, filters, grouping, metadata, and diagram renderers
├── reporters/      # HTMLReporter, MarkdownReporter, JSONReporter (SARIF)
├── rules/          # aws/threats*.yaml (Terraform) and cfn/threats.yaml (CloudFormation)
└── templates/      # Jinja2 templates for HTML and Markdown (scan + delta)
```

### Adding an IaC format

`Scanner` does not know about formats: it walks the directory and delegates to a `BaseParser`
subclass, which declares `file_patterns`, can reject files with `can_parse()`, and implements
`parse_strict()` (raising `ParseError`, so the scan is reported as incomplete instead of silently
treating the file as empty). Inline suppressions travel on `ResourceModel.ignored_rules`. A new
format is a parser plus a rules file; the rule engine and reporters are reused unchanged.

## Full-state analysis vs. risk delta

Most IaC security tools analyze the **full state** of the infrastructure: they
evaluate every resource defined in the `.tf` files and report all existing
threats. This is useful for audits, but it generates noise in PR reviews because
it mixes pre-existing threats with those introduced by the change.

TMAC supports both models:

| Command | Question it answers |
| :--- | :--- |
| `tmac scan` | *"What risk exists in the full infrastructure?"* |
| `tmac plan` | *"What new risk does this PR introduce?"* |

### How `tmac plan` works

`tmac plan` parses the output of `terraform show -json` and evaluates **only the
resources in the diff**:

- **Created** resources: detects threats in the final state.
- **Modified** resources: detects threats introduced by the change (not pre-existing ones).
- **Removed** resources: records threats resolved by removing the resource.

The report shows the net **RiskDelta** of the plan:

```
RiskDelta = threats introduced − threats resolved
```

This makes `tmac plan` ideal for CI/CD pipelines that should **block only the
changes that degrade the security posture**, without raising false positives
from pre-existing technical debt.

## STRIDE framework

Findings are automatically categorized using the STRIDE model: Spoofing,
Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation
of Privilege. See the [AWS STRIDE mapping](aws_stride_mapping.md) for how AWS
services map to each category.
