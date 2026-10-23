# TMAC Documentation

Complete documentation for TMAC (Threat Modeling as Code).

## Getting Started

- [Installation](INSTALLATION.md) — pip, Poetry, Docker, and pre-commit.
- [Examples](EXAMPLES.md) — basic, intermediate, and advanced usage in the console and in CI/CD.
- [Command reference](COMMANDS.md) — complete guide to `scan`, `cfn`, `plan`, `ci`, and `diagram`.

## Reference

- [Rule catalog](RULES.md) — every built-in rule (Terraform and CloudFormation) by service and
  severity; generated from the rule YAML by `scripts/generate_rules_doc.py`.
- [Writing rules](WRITING_RULES.md) — rule format, condition operators, and custom rules.
- [AWS STRIDE mapping](aws_stride_mapping.md) — how AWS services map to STRIDE categories.

## Guides

- [CI/CD integration](CICD.md) — official GitHub Action, GitLab CI template, Docker, and pre-commit.
- [Architecture](ARCHITECTURE.md) — project layout, CI layer design, adding an IaC format, and
  the full-state vs. risk-delta model.

## Project

- [Product requirements (PRD)](PRD_TMAC_Extended.md) — extended product specification.
- [threats.yaml (v1.0 snapshot)](threats.yaml) — historical copy of the original 78 rules;
  the live rules are in `src/tmac/rules/`.
- [Roadmap](../ROADMAP.md) — vision and future versions.
- [Changelog](../CHANGELOG.md) — history of changes per version.
- [Contributing](../CONTRIBUTING.md) — how to add rules and run the tests.
