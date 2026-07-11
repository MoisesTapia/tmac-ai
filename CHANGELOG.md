# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.6.0] — "Ixtla" — 2026-07-09

### Added

- **`tmac ci` subcommand**: new CLI command that orchestrates the complete CI/CD flow: detects changed `.tf` files between two git refs → scans only those files → writes the report artifact → formats a narrative comment → publishes it on the GitHub or GitLab PR/MR.
- **`src/tmac/ci/` package**: new CI layer package with the following modules:
  - `git_diff.py`: `changed_tf_files(base_ref, head_ref)` + `GitRefError` to detect which `.tf` files changed between two refs.
  - `secrets.py`: `read_token()` reads `GITHUB_TOKEN` / `CI_JOB_TOKEN` / `TMAC_TOKEN` from the environment; `redact(text)` replaces any token occurrence in output strings with `***REDACTED***`.
  - `comment.py`: `CommentFormatter.format()` renders the idempotent Markdown comment with the MARKER, executive summary, severity breakdown, findings table, `BLOCKED/WARNING/APPROVED` badge, and artifact reference. Supports intelligent size-based truncation.
  - `publisher.py`: `GitHubCommentPublisher` and `GitLabCommentPublisher` with idempotent find-or-update behavior through an injectable `HttpTransport`.
  - `runner.py`: `CIRunner.run()` orchestrates the complete flow. Handles `PublishError`, `PublishPermissionError`, and `NoPullRequestContext` without altering the findings-based exit code.
- **`action.yml`**: official composite GitHub Action with inputs `dir`, `fail-on`, `delta-only`, `comment`, `report-format`, `output`; permissions limited to `pull-requests: write, contents: read`; artifact uploaded with `if: always()`.
- **`ci/github/entrypoint.sh`**: Action entrypoint; validates inputs (invalid values → descriptive error + exit 3), maps flags, publishes comment only on `pull_request` events, propagates the `tmac ci` exit code unchanged.
- **`ci/gitlab/tmac.gitlab-ci.yml`**: includable GitLab CI template with `TMAC_DIR/FAIL_ON/DELTA_ONLY/COMMENT` variables, `artifacts: when: always`, `rules:` that gate comments to `merge_request_event`.
- **`Dockerfile`**: official image based on `python:3.11-slim`, `ENTRYPOINT ["tmac"]`, non-root user.
- **`.pre-commit-hooks.yaml`**: hook `id: tmac` running `tmac scan` against staged `.tf` files; automatically skipped when no `.tf` files are staged.
- **`Scanner.include_paths`**: new optional parameter in `Scanner.run_scan()` to restrict analysis to a subset of paths — fully backward-compatible (default `None`).
- **Tests**: `tests/property/test_ci_properties.py` with Properties 5–19 from the design; `tests/test_distribution_artifacts.py` with 28 configuration smoke tests; `tests/test_integration_distribution.py` with pre-commit and Docker integration tests.
- **`pyproject.toml`**: version bumped to `1.6.0`; `ScanMetadata.version` updated to `"1.6.0"`.

### Changed

- **`src/tmac/cli.py`**: added the `ci` subcommand; `@click.version_option` updated to `"1.6.0"`.
- **`src/tmac/scanner.py`**: added `include_paths: Optional[List[str]] = None` to `run_scan()`.

---

## [1.1.0] — "Ixtla" — 2026-03-16

### Added

- **`src/tmac/delta/models.py`**: New Pydantic models `PlannedChange`, `ChangeAction`, `DeltaFinding` (extends `Finding`), and `DeltaScanResult` (extends `ScanResult`) to represent planned changes and delta findings.
- **`src/tmac/parsers/tfplan.py`**: New `TfplanParser` that implements `BaseParser` and parses the output of `terraform show -json`, extracting `PlannedChange[]` with correct `before`/`after` semantics per action (`create`, `update`, `delete`, `replace`, `no-op`).
- **`src/tmac/delta/scanner.py`**: New `DeltaScanner` that orchestrates the delta analysis pipeline: `TfplanParser → RuleLoader → Evaluator → DeltaScanResult`. Reuses `RuleLoader` and `Evaluator` from v1.0.0 without modifications. Raises `DeltaScanError` on invalid files.
- **`tmac plan` subcommand**: New CLI subcommand with the mandatory `--plan-file` flag and the same output flags as `tmac scan` (`--report`, `--output`, `--rules-dir`, `--fail-on`, `--quiet`, `--no-color`, `--verbose`). Exit codes: `0` (no Critical/High), `1` (Critical), `2` (High without Critical), `3` (error).
- **`src/tmac/templates/report_delta.html.j2`**: HTML template with a `delta-summary` section that shows `findings_introduced`, `findings_resolved`, and net `RiskDelta`, with badges per change type (`NEW`, `MODIFIED`, `REMOVED`).
- **`src/tmac/templates/report_delta.md.j2`**: Markdown template with an executive summary and a delta table with columns: Action, Resource, Rule, Severity, STRIDE, Change description.
- **`tests/unit/test_tfplan_parser.py`**: Unit tests for the `TfplanParser` covering parsing by action, `address` extraction, error handling, and property-based tests (Properties 1–5).
- **`tests/unit/test_delta_scanner.py`**: Unit tests for the `DeltaScanner` covering classification of introduced/resolved threats, counts, `ignore_map`, and property-based tests (Properties 7–10, 12–13).
- **`tests/integration/test_plan_cli.py`**: End-to-end integration tests with `CliRunner` for exit codes, report formats, flags, and a non-regression test for `tmac scan`.
- **`tests/property/test_delta_properties.py`**: 18 property-based tests with Hypothesis (`@settings(max_examples=100)`) covering all the correctness properties of the design.
- **`tests/fixtures/plans/`**: `tfplan.json` fixtures for the four scenarios: `create_with_threat.json`, `update_secure_to_insecure.json`, `update_insecure_to_secure.json`, `delete_with_threat.json`, `clean_plan.json`, `mixed_plan.json`.

### Changed

- **`src/tmac/reporters/html.py`**: `HTMLReporter.generate()` detects `DeltaScanResult` via duck-typing and uses `report_delta.html.j2`; v1.0.0 behavior unchanged for a normal `ScanResult`.
- **`src/tmac/reporters/markdown.py`**: `MarkdownReporter.generate()` detects `DeltaScanResult` via duck-typing and uses `report_delta.md.j2`; v1.0.0 behavior unchanged for a normal `ScanResult`.
- **`src/tmac/reporters/json_report.py`**: `JSONReporter.generate()` adds a `properties` field with `changeAction`, `valueBefore`, `valueAfter` in each SARIF `result` when the finding is a `DeltaFinding`; v1.0.0 behavior unchanged for a normal `Finding`.
- **`src/tmac/cli.py`**: Added the `plan` subcommand; the existing `scan` subcommand was not modified (full backward compatibility).
- **`README.md`**: Documented the `tmac plan` subcommand, an integration example in GitHub Actions, and a differentiating section vs full-state analysis tools.

---

## [1.0.0] — "Ixtla" — 2026-03-14

### Added

- **`src/tmac/scanner.py`**: New orchestrator module `Scanner` with a `run_scan()` method that encapsulates the complete pipeline (parsing → rule loading → matching → statistics). Complies with SRP: the CLI only handles presentation and exit codes.
- **`ScanError`**: Internal exception raised by `Scanner` on inaccessible directories or invalid configuration; the CLI catches it and returns exit code `3`.
- **`Finding.tags`**: `List[str]` field defaulting to an empty list, propagated from `ThreatRule.tags`.
- **`ScanResult.files_scanned`**: `int` field with the number of `.tf` files processed in the scan.
- **`ScanResult.rules_loaded`**: `int` field with the number of rules loaded from the YAML files.
- **`ResourceModel.to_dict()`**: Serialization method that returns `model_dump()` to ease debugging and reports.
- **`--exclude` / `-e` flag**: Accepts repeatable glob patterns to exclude files and directories from the scan.
- **`--no-color` flag**: Disables ANSI escape sequences in the terminal output.
- **`--verbose` / `-v` flag**: Enables DEBUG-level logging with details of discovered files, loaded rules, and evaluated conditions.
- **Exit code `2`**: Returned when `High` findings are detected but none `Critical`.
- **Exit code `3`**: Returned on execution errors (inaccessible directory, invalid config, parsing error).
- **Schema validation in `RuleLoader`**: Mandatory `version` and `rules` fields in YAML files; mandatory `id`, `name`, `resource_type`, `check`, `severity`, `stride` fields in each rule.
- **Schema validation in `load_config()`**: Allowed keys `scan` and `report`; type validation for `scan.exclude` and `report.format`; `ConfigError` on YAML with invalid syntax.
- **JSONReporter with SARIF 2.1.0 schema**: Output with `version`, `$schema`, `runs`, `tool.driver` (with `name`, `version`, `informationUri`, `rules`), and `results` (with `ruleId`, `level`, `message`, `locations`) fields.
- **SARIF severity mapping**: `Critical`/`High` → `error`, `Medium` → `warning`, `Low` → `note`, `Info` → `none`.
- **`tests/conftest.py`**: Shared fixtures `sample_finding`, `sample_scan_result`, `sample_rule`, `sample_resource`, `fixtures_path`.
- **`tests/fixtures/`**: 22 positive and negative `.tf` files for the 10 base rules, plus `sg_multi_ingress.tf` and `tmac_ignore_examples.tf`.
- **`tests/unit/`**: Unit tests for all modules: `test_models.py`, `test_reporters.py`, `test_rule_loader.py`, `test_evaluator.py`, `test_parser.py`, `test_config.py`, `test_scanner.py`.
- **`tests/integration/`**: End-to-end tests with `CliRunner`: `test_cli.py` and `test_rules.py` (parametrized per rule).
- **Property-based tests with Hypothesis**: 19 correctness properties verified with `@settings(max_examples=100)`.
- **`CHANGELOG.md`**: This file.
- **`CONTRIBUTING.md`**: Guide for contributors.

### Fixed

- **Typo `{% elief %}` → `{% elif %}`** in `src/tmac/templates/report.md.j2` that caused a rendering error in the Markdown report.
- **Iteration of `finding.stride` in the HTML template**: Normalized to a list before iterating STRIDE badges; if `stride` is a string, it is wrapped in a list.
- **`Evaluator._get_attribute_value`**: Now iterates over all elements of a list of blocks (e.g., multiple `ingress` rules in a Security Group) instead of only the first, eliminating false negatives.
- **`RuleLoader`**: Replaced all `print()` calls with structured `logging` calls.
- **`TerraformParser`**: Implemented `_prescan()` that extracts `line_map` and `ignore_map` in a single read of the file, assigning the correct `line_number` to each `ResourceModel`.
- **`tmac:ignore[RULE-ID]`**: Support for exclusion by specific Rule ID, multiple consecutive IDs, and comments on the same line as the `resource` block.
- **`Matcher`**: Propagates `tags` from `ThreatRule` to the produced `Finding`.
- **CLI**: Replaced the hardcoded `.terraform` filter with the configurable `--exclude` mechanism.

### Changed

- **`cli.py`**: Refactored to delegate the pipeline to the `Scanner`; the `scan()` function reduced to ≤30 effective lines of code.
- **Exit codes**: Redefined per PRD FR-006: `0` (no Critical/High), `1` (Critical), `2` (High without Critical), `3` (execution error). Exit code `2` no longer means "generic warning".
- **`RuleLoader`**: Uses `logging` instead of `print()` for all warning and error messages.
- **`README.md`**: Updated with Python 3.10+ as a requirement, correct exit codes, rule schema with `TMAC-AWS-{SERVICE}-{NNN}` IDs, a complete table of CLI flags, and CI/CD examples for GitHub Actions and GitLab CI.

---

## [Unreleased]

### Added

- **`tmac diagram`**: New command that reads all the Terraform code in a repo, builds the dependency graph between resources (from the `${type.name.attribute}` references), and generates an architecture diagram.
- **`src/tmac/graph/` module**: `GraphBuilder` (edge extraction), `filters` (hide plumbing resources with transitive reconnection), `grouping` (group by microservice), `metadata` (configuration extraction), and `diagrams` (renderers).
- **Diagram formats**: `mermaid`, `dot` (Graphviz), `drawio` (editable XML), and `png`/`svg`/`pdf` images (via Graphviz).
- **`--simplify` / `-s` flag** of `tmac diagram`: hides plumbing resources (IAM, permissions, policies, stages) while preserving real connectivity.
- **`--group` / `-g` flag** of `tmac diagram`: groups resources by microservice into subgraphs/clusters.
- **`--exclude-type` flag** of `tmac diagram`: hides arbitrary resource types (repeatable).
- **`--metadata` flag** of `tmac diagram`: generates `tmac-metadata.md`/`.json` with the configuration of each resource (security attributes, configuration, connections, nested blocks, and satellite resources) to support threat modeling.
- **`--diagram` flag** of `tmac scan`: embeds the simplified Mermaid diagram in the HTML and Markdown reports.
- **`src/tmac/rules/aws/security_attrs.yaml`**: curated and editable layer of security-relevant attributes per resource type, plus satellite resources (e.g., `aws_flow_log` → "VPC Flow Logs").
- **`examples/ecommerce/`**: example serverless architecture (API Gateway → Lambda → DynamoDB, EventBridge, SQS) to try out the tool.
- **Tests**: `test_graph.py`, `test_filters.py`, `test_grouping.py`, `test_metadata.py`.
- **8 new security rules** in `src/tmac/rules/aws/threats.yaml`:
  - `TMAC-AWS-AURORA-002`: Aurora cluster with `storage_encrypted = false`.
  - `TMAC-AWS-AURORA-003`: Aurora cluster with `master_password` in cleartext.
  - `TMAC-AWS-KDF-001`: Kinesis Firehose without `server_side_encryption`.
  - `TMAC-AWS-RDSPROXY-001`: RDS Proxy without `require_tls`.
  - `TMAC-AWS-CB-001`: CodeBuild in `privileged_mode`.
  - `TMAC-AWS-LB-003`: Load Balancer exposed to the internet (`internal = false`).
  - `TMAC-AWS-EB-002`: Elastic Beanstalk without log streaming to CloudWatch.
  - `TMAC-AWS-FIREHOSE-002`: Firehose without `kms_key_arn` on delivery to S3.
- **`examples/enterprise/`**: multi-AZ and multi-region enterprise architecture (VPC, ALB+WAF, Auto Scaling, Aurora Serverless, RDS Proxy, Cognito, DevOps, VPC endpoints, Kinesis/S3/Glacier, Pinpoint, Route53 failover, CloudTrail, warm standby) for large-scale testing.
- **`src/tmac/rules/aws/threats_extended.yaml`**: extended rule catalog that brings it to **a minimum of 8 rules for each resource type** present in the examples (~520 rules in total). Covers VPC, subnets, security groups, ALB/listener/target group, WAF, ACM, VPC endpoints, flow logs, launch templates, ASG, Aurora/RDS, RDS Proxy, IAM roles/policies, KMS, Secrets Manager, Cognito (pool/client/domain), ECR, Elastic Beanstalk, CloudTrail, CloudWatch logs/alarms, AWS Config, CodeBuild/CodeCommit/CodePipeline/CodeDeploy, Kinesis Firehose, S3 (bucket/SSE/lifecycle/website), Pinpoint, QuickSight, Route53 (zone/record), and structural resources (NAT, EIP, IGW, KMS alias, instance profile, route tables, etc.).
- **`RuleLoader`**: now loads all `threats*.yaml` files in the rules directory, allowing rules to be organized across multiple files.
- **`DOCS/COMMANDS.md`**: complete reference for the `scan`, `plan`, and `diagram` commands (options, examples, exit codes).
- **`DOCS/RULES.md`**: complete catalog of the 520+ rules, grouped by service and severity (generated from the real catalog).

### Changed

- **`README.md`**: updated the features section (520+ rules, 105 resource types, `diagram` command), added documentation, included examples, and rule catalog sections; replaced the v1.0.0 "included rules" table with a summary of the current catalog.
- **`tests/integration/test_plan_cli.py`**: the `test_scan_command_unaffected_by_v110_modules` test now validates that the v1.0.0 baseline detections are still present (subset) instead of requiring an exact count, making it robust to the addition of rules.
- **`.gitignore`**: ignores generated artifacts (`tmac-diagram.*`, `tmac-metadata.*`, `tmac-delta-report.*`) and the local `.kiro/` folder.

### Removed

- **`.kiro/`**: no longer versioned in any remote branches (remains only locally).
- Loose generated artifacts from the repository (`arch.png`, `tmac-diagram.mmd`, `tmac-metadata.md`, `tmac-delta-report.md`).

### Planned

- v1.2.0: Support for AWS CloudFormation templates.

---

[1.6.0]: https://github.com/MoisesTapia/tmac-ai/releases/tag/v1.6.0
[1.1.0]: https://github.com/MoisesTapia/tmac-ai/releases/tag/v1.1.0
[1.0.0]: https://github.com/MoisesTapia/tmac-ai/releases/tag/v1.0.0
[Unreleased]: https://github.com/MoisesTapia/tmac-ai/compare/v1.6.0...HEAD
