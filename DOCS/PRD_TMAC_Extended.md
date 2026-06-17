# PRD: TMAC (Threat Modeling as Code)

**Document ID:** PRD-TMAC-2024-001  
**Version:** v1.0.0 Ixtla (Initial Release)  
**Status:** Draft / In Review  
**Author:** Security Architecture Team  
**Classification:** Internal / Confidential  
**Last Updated:** March 2026

---

## Table of Contents

1. [Introduction and Vision](#1-introduction-and-vision)
2. [Roadmap (Mexican National Cycle)](#2-roadmap-mexican-national-cycle)
3. [System Architecture (v1.0.0 Ixtla)](#3-system-architecture-v100-ixtla)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Threat Rule Schema Specification](#6-threat-rule-schema-specification)
7. [CLI Interface Specification](#7-cli-interface-specification)
8. [CI/CD Integration Specification](#8-cicd-integration-specification)
9. [Testing Strategy](#9-testing-strategy)
10. [Project Structure](#10-project-structure)
11. [User Stories](#11-user-stories)
12. [Risks and Mitigations](#12-risks-and-mitigations)
13. [Success Metrics and KPIs](#13-success-metrics-and-kpis)
14. [Release Acceptance Criteria (v1.0.0 Ixtla)](#14-release-acceptance-criteria-v100-ixtla)
15. [Appendices](#15-appendices)

---

## 1. Introduction and Vision

### 1.1. Executive Summary

TMAC (Threat Modeling as Code) is an open-source, command-line security tool that automates threat modeling for modern cloud infrastructure. By analyzing Infrastructure as Code (IaC) files and live cloud states, TMAC identifies security risks mapped to the STRIDE framework and compliance standards, enabling engineering teams to detect and remediate vulnerabilities before deployment.

### 1.2. Problem Statement

Traditional threat modeling suffers from critical limitations that create security gaps in modern DevOps environments:

- **Manual Process:** Threat modeling workshops consume 8–40 hours per system, creating bottlenecks that prevent security reviews from keeping pace with deployment velocity.
- **Late Detection:** Security analysis typically occurs post-deployment, when remediation costs are 6–15x higher than during the design phase (IBM Cost of a Data Breach Report, 2024).
- **Skill Gap:** Only 23% of DevOps teams have dedicated security engineers (SANS 2024 Survey), leaving infrastructure provisioned without systematic threat analysis.
- **No Automation:** Existing tools (Microsoft TMT, OWASP Threat Dragon) require manual diagram creation and do not integrate with CI/CD pipelines or IaC workflows.
- **Compliance Drift:** Organizations discover compliance violations reactively through audits rather than proactively during infrastructure provisioning.

### 1.3. Solution Overview

TMAC solves these problems by making threat modeling a native part of the CI/CD pipeline. It reads IaC files (`.tf`, `tfplan.json`, CloudFormation, Kubernetes manifests, Docker Compose), applies a YAML-based threat rule engine, and generates instant risk reports. The approach enables a **shift-left security posture** where teams can fail fast on insecure configurations before `terraform apply` or `kubectl apply`.

### 1.4. Value Proposition

- **Speed:** Automated analysis in under 3 seconds for 100 files vs. days of manual workshops.
- **Shift-Left:** Integrates directly into CI/CD pipelines as a quality gate.
- **Extensibility:** Custom rules via YAML files without code changes.
- **Standards-Based:** STRIDE-mapped threats with compliance references (CIS, NIST, SOC2).
- **Actionable Output:** Every finding includes specific remediation steps with code snippets.

### 1.5. Target Users and Personas

| Persona | Role | Pain Point | TMAC Value |
|---------|------|------------|------------|
| DevOps Engineer | Provisions infrastructure via Terraform/K8s | No security feedback before deploy | Instant risk analysis in PR workflow |
| Cloud Security Architect | Defines security policies and standards | Cannot enforce policies at scale | Automated policy-as-code enforcement |
| SRE | Maintains production reliability | Security incidents from misconfig | Pre-deployment risk scoring |
| AppSec Engineer | Conducts security reviews | Manual threat models are slow | Auto-generated STRIDE analysis |
| Compliance Officer | Ensures regulatory adherence | Reactive audit findings | Continuous compliance monitoring |

---

## 2. Roadmap (Mexican National Cycle)

Each release is named after significant elements of Mexican heritage, reflecting the project's cultural identity. The roadmap is structured in three phases: Foundation, Expansion, and Intelligence.

### 2.1. Phase 1: Foundation (v1.0.0 – v1.1.0)

| Version | Codename | Description | Key Deliverable | Timeline |
|---------|----------|-------------|-----------------|----------|
| v1.0.0 | **Ixtla** | Static analysis of Terraform (.tf) files | Functional CLI + HTML/MD/JSON Reports | Q1 2026 |
| v1.1.0 | **Mitla** | Future state analysis via tfplan.json | Risk change detection engine | Q2 2026 |

### 2.2. Phase 2: Expansion (v1.2.0 – v1.7.0)

| Version | Codename | Description | Key Deliverable | Timeline |
|---------|----------|-------------|-----------------|----------|
| v1.2.0 | **Ehécatl** | AWS CloudFormation support | YAML/JSON CFN Parser | Q3 2026 |
| v1.3.0 | **Cuauhtli** | Kubernetes security (RBAC, Pod Security) | K8s manifest analyzer | Q4 2026 |
| v1.4.0 | **Calpulli** | Microservices (Docker Compose) | Network and privilege scanner | Q1 2027 |
| v1.5.0 | **Cenote** | Multicloud expansion (Azure Bicep) | Azure ecosystem integration | Q2 2027 |
| v1.6.0 | **Tianguis** | Distribution and packaging | PyPI / Homebrew publication | Q3 2027 |
| v1.7.0 | **Xaman** | Live infrastructure (AWS Runtime) | SDK/Boto3 connection | Q4 2027 |

### 2.3. Phase 3: Intelligence (v1.8.0 – v2.1.0)

| Version | Codename | Description | Key Deliverable | Timeline |
|---------|----------|-------------|-----------------|----------|
| v1.8.0 | **Altar** | Visualization and Dashboard | Web compliance interface | Q1 2028 |
| v2.1.0 | **Nagual** | AI-Powered Auto-Remediation | AI agent for code patching | Q3 2028 |

---

## 3. System Architecture (v1.0.0 Ixtla)

### 3.1. High-Level Architecture

TMAC follows a modular pipeline architecture with four distinct processing stages. Each module is independently testable and replaceable, enabling the progressive expansion defined in the roadmap.

```
[IaC Files (.tf)]  →  [Parser Module]  →  [Rule Engine]  →  [Reporter Module]  →  [Output Files]
                            │                    │                                       │
                       python-hcl2          threats.yaml                          HTML / MD / JSON
                                           (Rule Database)
```

### 3.2. Module Breakdown

#### 3.2.1. CLI Entry Point (`tmac/cli.py`)

**Responsibilities:** Argument parsing, input validation, orchestration of the scan pipeline, exit code management. Built with Click framework for POSIX-compliant argument handling and colored terminal output.

**Key Functions:** `scan()` — Main entry point; `validate_inputs()` — Path and format validation; `orchestrate()` — Pipeline execution coordinator.

#### 3.2.2. Parser Module (`tmac/parsers/`)

**Responsibilities:** File discovery, HCL parsing, resource extraction, and normalization into a common internal data model. Designed with a **Strategy pattern** to support multiple IaC formats in future versions.

**v1.0.0 Scope:** `TerraformParser` — Parses `.tf` files using `python-hcl2` library. Extracts resource blocks, data sources, variables, and module references into a normalized `ResourceModel`.

**Extension Point:** `BaseParser` abstract class defines the interface. New parsers (CloudFormation, K8s) implement `parse(file_path) -> List[ResourceModel]`.

#### 3.2.3. Rule Engine (`tmac/engine/`)

**Responsibilities:** Loading threat rules from YAML, matching resources against rule conditions, evaluating complex check logic (including nested `and_check` conditions), and producing a list of findings with severity scores.

**Matching Algorithm:** For each parsed resource, iterate through rules where `resource_type` matches. Evaluate the `check` conditions against the resource attributes. Support for equality, containment, regex, and nested attribute path resolution.

#### 3.2.4. Reporter Module (`tmac/reporters/`)

**Responsibilities:** Transforming findings into formatted outputs. Each reporter implements the `BaseReporter` interface with a `generate(findings, metadata) -> str` method.

- **HTMLReporter:** Self-contained HTML with embedded CSS, severity distribution charts (SVG), STRIDE breakdown, and finding details. Uses Jinja2 templates.
- **MarkdownReporter:** Optimized for GitHub/GitLab PR comments. Includes summary table, findings grouped by severity, and collapsible details.
- **JSONReporter:** Machine-readable output for pipeline consumption. Follows SARIF-compatible schema for integration with GitHub Code Scanning and similar tools.

#### 3.2.5. Models (`tmac/models/`)

Pydantic data models that enforce type safety and validation throughout the pipeline:

- **ResourceModel:** Normalized representation of an IaC resource (type, name, attributes dict, source file, line number).
- **ThreatRule:** Parsed rule from threats.yaml (id, name, resource_type, check conditions, severity, stride category, description, mitigation).
- **Finding:** A matched threat (rule reference, affected resource, matched attribute, evidence, timestamp).
- **ScanResult:** Aggregate output (scan metadata, list of findings, statistics, execution time).

### 3.3. Data Flow Specification

The complete data flow from CLI invocation to output generation:

1. User invokes: `tmac scan --dir ./infra --report html --output report.html`
2. CLI validates input paths exist and output format is supported.
3. **File Discovery:** Recursively scans `--dir` for matching file extensions (`.tf` for v1.0.0). Applies `--exclude` filters.
4. **Parsing:** Each discovered file is passed to the appropriate parser. Parser returns `List[ResourceModel]` per file.
5. **Exclusion Filter:** Resources annotated with `# tmac:ignore` comments are removed from the resource list.
6. **Rule Loading:** `threats.yaml` files are loaded from the built-in `rules/` directory and any user-specified `--rules-dir`.
7. **Matching:** The Rule Engine iterates all resources against all applicable rules. For each match, a `Finding` is created.
8. **Aggregation:** Findings are grouped by severity and STRIDE category. Statistics are computed.
9. **Reporting:** The selected reporter generates the output file.
10. **Exit Code:** If any Critical findings exist, exit code `1` is returned. Otherwise, exit code `0`.

### 3.4. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Language | Python 3.10+ | Rich ecosystem for IaC parsing, strong typing with type hints, wide adoption in security tooling |
| CLI Framework | Click 8.x | POSIX-compliant arg parsing, colored output, composable commands, auto-generated help |
| IaC Parser | python-hcl2 | Native HCL2 parsing without Terraform binary dependency |
| Data Validation | Pydantic v2 | Runtime type checking, JSON schema generation, serialization |
| Templating | Jinja2 | Industry-standard Python templating for HTML reports |
| Testing | pytest + coverage | Fixture-based testing with parametrize for rule testing |
| Packaging | Poetry / setuptools | Dependency management and PyPI publication |
| Linting | ruff + mypy | Fast linting and static type checking |

---

## 4. Functional Requirements

### 4.1. FR-001: Multi-File Directory Scanning

**Priority:** P0 (Must Have)

The system shall recursively scan a specified directory for IaC files matching the target format. For v1.0.0, this includes all files with `.tf` extension. Symbolic links shall be followed with cycle detection. Hidden directories (prefixed with `.`) shall be excluded by default.

**Acceptance Criteria:** Given a directory with nested subdirectories containing `.tf` files, when `tmac scan --dir <path>` is executed, then all `.tf` files are discovered and parsed regardless of nesting depth.

### 4.2. FR-002: HCL2 Parsing Engine

**Priority:** P0 (Must Have)

The parser shall extract all resource blocks from Terraform HCL files, including: resource type and name, all attributes (including nested blocks), references to variables and locals (resolved where possible), module references (local modules parsed, remote modules flagged as unresolved). Parse errors shall be captured and reported without aborting the entire scan.

**Acceptance Criteria:** Given a `.tf` file with `resource`, `data`, `variable`, and `module` blocks, when parsed, then all resource blocks are extracted with their complete attribute trees. Parse errors in one file do not prevent analysis of other files.

### 4.3. FR-003: YAML-Based Threat Rule Engine

**Priority:** P0 (Must Have)

The engine shall load threat rules from YAML files conforming to the `threats.yaml` schema (see Section 6). Rules shall be matched against parsed resources by `resource_type`. The check evaluation shall support the following conditions: `equals`, `not_equals`, `in`, `not_in`, `contains`, `not_contains`, `regex`, `exists`, `not_exists`. Compound conditions via `and_check` (logical AND) shall be supported to arbitrary depth.

### 4.4. FR-004: Exclusion Mechanism

**Priority:** P1 (Should Have)

Users shall be able to exclude specific resources or files from analysis through two mechanisms:

- **Inline Comment:** Adding `# tmac:ignore` on the line before or on the same line as a resource block excludes that resource from all rules.
- **Rule-Specific Exclusion:** Adding `# tmac:ignore[TMAC-AWS-S3-001]` excludes only the specified rule ID.
- **CLI Flag:** `--exclude <pattern>` excludes files/directories matching the glob pattern.

### 4.5. FR-005: Multi-Format Reporting

**Priority:** P0 (Must Have)

The system shall generate reports in three formats:

- **HTML:** Self-contained file with embedded CSS/SVG. Includes executive summary, severity distribution chart, STRIDE breakdown, findings table with expandable details, and remediation guidance. No external dependencies.
- **Markdown:** Optimized for PR comments. Summary table, findings grouped by severity, code snippets showing affected lines.
- **JSON:** Machine-readable output following a SARIF-compatible schema. Includes scan metadata (tool version, timestamp, scanned directory), findings array, and summary statistics.

### 4.6. FR-006: Exit Code Management

**Priority:** P0 (Must Have)

The CLI shall return structured exit codes for CI/CD integration:

| Exit Code | Condition | CI/CD Behavior |
|-----------|-----------|----------------|
| `0` | No Critical or High findings | Pipeline continues |
| `1` | One or more Critical findings | Pipeline fails (hard stop) |
| `2` | One or more High findings (no Critical) | Pipeline warning (configurable) |
| `3` | Scan error (parse failure, invalid config) | Pipeline error state |

### 4.7. FR-007: Custom Rules Directory

**Priority:** P1 (Should Have)

Users shall be able to provide additional threat rules by specifying a `--rules-dir` path. Custom rules are merged with built-in rules. In case of ID conflicts, custom rules take precedence (override). This enables organizations to define company-specific security policies without forking the project.

---

## 5. Non-Functional Requirements

### 5.1. Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Scan 100 .tf files | < 3 seconds | wall-clock time, cold start |
| Scan 500 .tf files | < 10 seconds | wall-clock time, cold start |
| Memory usage (100 files) | < 256 MB RSS | peak memory during scan |
| Rule loading (200 rules) | < 500ms | YAML parse + validation |
| Report generation (HTML) | < 2 seconds | for 500 findings |

### 5.2. Portability

TMAC shall run on Linux (Ubuntu 20.04+, RHEL 8+), macOS (12+), and Windows (10/11, WSL2) with Python 3.10+ as the only runtime dependency. No compiled C extensions shall be required. The tool shall be installable via `pip install tmac` with all dependencies resolved automatically.

### 5.3. Extensibility

- Custom rules via YAML without code modification.
- Parser plugin system via entry points for new IaC formats.
- Reporter plugin system for custom output formats.
- Configuration file (`.tmac.yaml`) for project-level defaults.

### 5.4. Reliability

- **Graceful degradation:** Parse errors in individual files do not abort the scan.
- **Deterministic output:** Same input always produces same findings (no randomness).
- **Idempotent:** Multiple runs with same input produce identical results.

### 5.5. Security

TMAC shall not transmit any data externally. All analysis is performed locally. No telemetry, no cloud dependencies for core functionality. Threat rules are evaluated in a sandboxed context (no code execution from YAML). Sensitive values in `.tf` files (e.g., passwords in variables) shall be redacted in reports.

---

## 6. Threat Rule Schema Specification

### 6.1. Schema Definition

The `threats.yaml` file is the core knowledge base of TMAC. Each rule defines a security check against a specific IaC resource type.

```yaml
version: string          # Schema version (e.g., "1.0")
metadata:
  cloud: string          # Cloud provider (aws, azure, gcp)
  description: string    # Human-readable description
rules: List[Rule]        # Array of threat rules
```

### 6.2. Rule Object Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique ID following pattern: `TMAC-{CLOUD}-{SERVICE}-{NNN}` |
| `name` | string | Yes | Human-readable name of the threat |
| `resource_type` | string | Yes | Terraform resource type to match (e.g., `aws_s3_bucket`) |
| `check` | CheckObject | Yes | Primary condition to evaluate |
| `severity` | enum | Yes | `Critical` \| `High` \| `Medium` \| `Low` \| `Info` |
| `stride` | enum | Yes | STRIDE category of the threat |
| `description` | string | Yes | Detailed explanation of the risk |
| `mitigation` | string | Yes | Specific remediation steps with code examples |
| `references` | List[string] | No | URLs to CIS benchmarks, NIST controls, etc. |
| `tags` | List[string] | No | Classification tags (e.g., encryption, network, iam) |

### 6.3. Check Object Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `attribute` | string | Yes | Dot-notation path to resource attribute (e.g., `ingress.cidr_blocks`) |
| `condition` | enum | Yes | `equals` \| `not_equals` \| `in` \| `not_in` \| `contains` \| `not_contains` \| `regex` \| `exists` \| `not_exists` |
| `values` | List[any] | Conditional | Expected values for comparison (not required for `exists`/`not_exists`) |
| `and_check` | CheckObject | No | Additional condition that must also be true (logical AND, recursive) |

### 6.4. STRIDE Categories Reference

| Initial | Category | Description / IaC Examples |
|---------|----------|---------------------------|
| **S** | Spoofing | Impersonating a user or system. Ex: IAM role assumption without MFA. |
| **T** | Tampering | Modifying data or code. Ex: SSH port open to 0.0.0.0/0 allowing unauthorized access. |
| **R** | Repudiation | Denying actions. Ex: CloudTrail logging disabled, no audit trail. |
| **I** | Information Disclosure | Exposing data. Ex: S3 bucket with public ACL, unencrypted RDS. |
| **D** | Denial of Service | Disrupting availability. Ex: No rate limiting, no auto-scaling policies. |
| **E** | Elevation of Privilege | Gaining unauthorized access. Ex: IAM policy with `Resource: *` wildcard. |

### 6.5. Initial Rule Database (v1.0.0)

The v1.0.0 release ships with 10 built-in rules covering core AWS services:

| Rule ID | Severity | STRIDE | Description |
|---------|----------|--------|-------------|
| TMAC-AWS-S3-001 | Critical | Info Disclosure | S3 Bucket with public ACL (public-read, public-read-write) |
| TMAC-AWS-S3-002 | High | Info Disclosure | S3 Bucket without server-side encryption |
| TMAC-AWS-S3-003 | Medium | Repudiation | S3 Bucket without access logging enabled |
| TMAC-AWS-IAM-001 | High | Elev. of Privilege | IAM Policy with wildcard (*) Resource |
| TMAC-AWS-IAM-002 | Medium | Spoofing | IAM User with inline policy (should use managed) |
| TMAC-AWS-SG-001 | High | Tampering | Security Group with SSH (22) open to 0.0.0.0/0 |
| TMAC-AWS-SG-002 | Critical | Tampering | Security Group with RDP (3389) open to 0.0.0.0/0 |
| TMAC-AWS-RDS-001 | Medium | Info Disclosure | RDS instance without storage encryption |
| TMAC-AWS-RDS-002 | High | Info Disclosure | RDS instance publicly accessible |
| TMAC-AWS-CW-001 | Medium | Repudiation | CloudTrail not enabled for management events |

---

## 7. CLI Interface Specification

### 7.1. Command Structure

```bash
tmac scan --dir <path> --report <html|json|md> --output <filename> [options]
```

### 7.2. Global Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dir`, `-d` | PATH | `.` | Directory to scan (required) |
| `--report`, `-r` | CHOICE | `html` | Output format: `html`, `json`, `md` |
| `--output`, `-o` | PATH | `tmac-report.*` | Output file path |
| `--exclude`, `-e` | TEXT | none | Glob patterns to exclude (repeatable) |
| `--rules-dir` | PATH | none | Additional rules directory |
| `--config` | PATH | `.tmac.yaml` | Configuration file path |
| `--severity` | CHOICE | `all` | Minimum severity to report |
| `--fail-on` | CHOICE | `critical` | Severity threshold for exit code 1 |
| `--no-color` | FLAG | `false` | Disable colored terminal output |
| `--verbose`, `-v` | FLAG | `false` | Enable debug logging |
| `--quiet`, `-q` | FLAG | `false` | Suppress all output except errors |
| `--version` | FLAG | n/a | Show version and exit |

### 7.3. Configuration File (`.tmac.yaml`)

Project-level defaults can be stored in a `.tmac.yaml` file at the repository root. CLI flags override configuration file values.

```yaml
# .tmac.yaml
scan:
  dir: ./infrastructure
  exclude: [".terraform", "modules/deprecated"]
  rules_dir: ./custom-rules
report:
  format: html
  fail_on: high
  severity: medium
```

### 7.4. Example Usage Scenarios

```bash
# Basic scan
tmac scan --dir ./terraform

# CI/CD pipeline (JSON output, fail on high, quiet mode)
tmac scan --dir . --report json --output results.json --fail-on high --quiet

# PR comment generation
tmac scan --dir . --report md --output findings.md

# Custom rules with exclusions
tmac scan --dir . --rules-dir ./company-rules --exclude .terraform
```

---

## 8. CI/CD Integration Specification

### 8.1. GitHub Actions

```yaml
# .github/workflows/threat-model.yml
name: TMAC Threat Analysis
on: [pull_request]
jobs:
  tmac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install tmac
      - run: tmac scan --dir ./infra --report json --output results.json --fail-on critical
      - uses: actions/upload-artifact@v4
        with:
          name: tmac-report
          path: results.json
```

### 8.2. GitLab CI

```yaml
# .gitlab-ci.yml
tmac-scan:
  stage: test
  image: python:3.12-slim
  script:
    - pip install tmac
    - tmac scan --dir . --report json --output tmac-results.json --fail-on high
  artifacts:
    paths: [tmac-results.json]
```

### 8.3. Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/tmac-security/tmac
    hooks:
      - id: tmac-scan
        name: TMAC Threat Model
        entry: tmac scan --dir . --fail-on critical --quiet
        types: [terraform]
```

---

## 9. Testing Strategy

### 9.1. Test Pyramid

TMAC follows a standard test pyramid with emphasis on unit tests for the rule engine, given its critical role in security findings accuracy.

| Test Level | Coverage Target | Framework | Scope |
|------------|-----------------|-----------|-------|
| Unit Tests | 90%+ | pytest | Parsers, Rule Engine, Models, Reporters |
| Integration Tests | 80%+ | pytest + fixtures | CLI end-to-end, Parser→Engine chain |
| Regression Tests | 100% of bugs | pytest | One test per fixed bug, never removed |
| Performance Tests | All NFRs | pytest-benchmark | Scan time, memory, rule loading |
| E2E Tests | Critical paths | bash scripts | Full CLI invocation with real .tf files |

### 9.2. Test Data Strategy

A `fixtures/` directory shall contain sample Terraform files representing each rule scenario. Each rule in `threats.yaml` must have at least two corresponding test fixtures: one that triggers the rule (positive) and one that passes cleanly (negative). This ensures both true positive and true negative coverage.

### 9.3. Rule Testing Framework

Each threat rule shall be tested with parametrized test cases:

```python
@pytest.mark.parametrize("tf_fixture, expected_finding", [
    ("s3_public_acl.tf", True),
    ("s3_private_acl.tf", False),
    ("s3_no_acl.tf", False),
])
def test_s3_public_acl_rule(tf_fixture, expected_finding):
    findings = engine.scan(parse(tf_fixture), rules=["TMAC-AWS-S3-001"])
    assert bool(findings) == expected_finding
```

---

## 10. Project Structure

```
tmac/
├── pyproject.toml              # Project metadata and dependencies
├── .tmac.yaml                  # Default configuration
├── README.md
├── src/
│   └── tmac/
│       ├── __init__.py
│       ├── cli.py              # Click CLI entry point
│       ├── config.py           # Configuration loader
│       ├── models/
│       │   ├── __init__.py
│       │   ├── resource.py     # ResourceModel
│       │   ├── rule.py         # ThreatRule, CheckCondition
│       │   └── finding.py      # Finding, ScanResult
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py         # BaseParser (abstract)
│       │   └── terraform.py    # TerraformParser
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── rule_loader.py  # YAML loading + validation
│       │   ├── matcher.py      # Resource-to-rule matching
│       │   └── evaluator.py    # Check condition evaluation
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── base.py         # BaseReporter (abstract)
│       │   ├── html.py         # HTMLReporter + Jinja2 templates
│       │   ├── markdown.py     # MarkdownReporter
│       │   └── json_report.py  # JSONReporter (SARIF-compat)
│       ├── rules/
│       │   └── aws/
│       │       └── threats.yaml
│       └── templates/
│           ├── report.html.j2
│           └── report.md.j2
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/               # Sample .tf files for testing
└── docs/
```

---

## 11. User Stories

### 11.1. Epic: Core Scanning (v1.0.0)

| Story ID | User Story | Acceptance Criteria |
|----------|------------|---------------------|
| US-001 | As a DevOps engineer, I want to scan my Terraform directory so that I can find security issues before deploying. | CLI scans all .tf files recursively and produces findings. |
| US-002 | As a security architect, I want HTML reports with severity charts so that I can share findings with management. | HTML report is self-contained with CSS, SVG charts, STRIDE breakdown. |
| US-003 | As a CI/CD pipeline, I want a non-zero exit code on critical findings so that the pipeline fails automatically. | Exit code 1 on Critical, 2 on High, 0 otherwise. |
| US-004 | As a developer, I want to exclude specific resources with inline comments so known exceptions don't clutter reports. | `# tmac:ignore` excludes the resource from analysis. |
| US-005 | As a security team lead, I want custom rules so that I can enforce company-specific policies. | `--rules-dir` loads additional YAML rules and merges them. |
| US-006 | As an AppSec engineer, I want Markdown reports so that I can paste findings directly into PR comments. | MD output includes summary table and severity-grouped findings. |
| US-007 | As a compliance officer, I want JSON output compatible with SARIF so that findings integrate with GitHub Code Scanning. | JSON output follows SARIF schema with tool, results, and rules. |

---

## 12. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| python-hcl2 cannot parse complex HCL constructs (`for_each`, `dynamic` blocks) | High | Core parsing failures on real-world Terraform | Implement fallback regex parser for unresolvable blocks; contribute fixes upstream |
| False positives erode user trust | Medium | Users disable or ignore TMAC findings | Provide `tmac:ignore` mechanism; track false positive rate as KPI; community-reviewed rules |
| Rule database coverage too limited for adoption | Medium | Tool not useful for diverse infrastructure | Prioritize top-20 AWS resources by usage; accept community rule contributions |
| Performance degrades with large monorepos | Low | Exceeds 3-second target for enterprise repos | Implement parallel file parsing; add `--workers` flag for concurrency control |
| Competing tools (checkov, tfsec) have existing market share | High | Slower adoption and community growth | Differentiate with STRIDE mapping, self-contained HTML reports, and AI remediation roadmap |

---

## 13. Success Metrics and KPIs

### 13.1. Product Metrics

| Metric | Target (6 months post-launch) | Measurement |
|--------|-------------------------------|-------------|
| GitHub Stars | 500+ | GitHub API |
| PyPI Downloads (monthly) | 2,000+ | PyPI stats |
| Community-contributed rules | 20+ | PR count to rules/ directory |
| Average scan time (100 files) | < 3 seconds | Performance test suite |
| False positive rate | < 5% | Community-reported issues tagged `false-positive` |
| Rule coverage (CIS AWS top 50) | 80%+ | Rule count / CIS benchmark count |

### 13.2. Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Code coverage (unit) | > 90% | pytest-cov |
| Code coverage (integration) | > 80% | pytest-cov |
| Type checking | 0 mypy errors | `mypy --strict` |
| Linting | 0 ruff errors | `ruff check` |
| Documentation coverage | 100% public API | pydoc + Sphinx |

---

## 14. Release Acceptance Criteria (v1.0.0 Ixtla)

The following criteria must ALL be satisfied before v1.0.0 is tagged and released.

### 14.1. Functional Acceptance

1. `tmac scan --dir <path>` discovers and parses all `.tf` files recursively in the specified directory.
2. All 10 built-in rules in `threats.yaml` are functional and produce correct findings against test fixtures.
3. HTML report is self-contained (no external CSS/JS), renders correctly in Chrome, Firefox, and Safari.
4. JSON report validates against the defined SARIF-compatible schema.
5. Markdown report renders correctly in GitHub PR comments.
6. Exit code `1` is returned when Critical findings are present; exit code `0` when no Critical findings.
7. `# tmac:ignore` comments correctly exclude annotated resources from analysis.
8. `--exclude` flag correctly filters out matching files and directories.

### 14.2. Quality Acceptance

1. Unit test coverage >= 90% for all modules.
2. Zero mypy errors with `--strict` flag.
3. Zero ruff linting errors.
4. All performance NFRs met (scan 100 files < 3s, memory < 256MB).
5. `README.md` includes installation, quick start, configuration, and rule authoring guide.

### 14.3. Distribution Acceptance

1. `pip install tmac` installs cleanly on Python 3.10, 3.11, 3.12 on Linux, macOS, and Windows.
2. `tmac --version` returns correct version string.
3. `tmac --help` displays complete command documentation.

---

## 15. Appendices

### Appendix A: Glossary

| Term | Definition |
|------|------------|
| **IaC** | Infrastructure as Code — managing infrastructure through declarative configuration files |
| **HCL** | HashiCorp Configuration Language — the native language of Terraform |
| **STRIDE** | Threat modeling framework: Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation of Privilege |
| **SARIF** | Static Analysis Results Interchange Format — OASIS standard for static analysis tool output |
| **CIS** | Center for Internet Security — publishes security benchmarks for cloud platforms |
| **tfplan** | Terraform plan output — JSON representation of planned infrastructure changes |
| **ACL** | Access Control List — defines permissions for cloud resources |
| **RBAC** | Role-Based Access Control — permission model based on assigned roles |

### Appendix B: Reference Threat Rule (Full Example)

```yaml
- id: TMAC-AWS-S3-001
  name: "S3 Bucket with Public Access (ACL)"
  resource_type: "aws_s3_bucket"
  check:
    attribute: "acl"
    condition: "in"
    values: ["public-read", "public-read-write"]
  severity: "Critical"
  stride: "Information Disclosure"
  description: "A bucket with a public ACL was detected..."
  mitigation: "Change the 'acl' attribute to 'private' and enable 'block_public_access'."
  references:
    - "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html"
    - "CIS AWS Benchmark 2.1.5"
  tags: ["s3", "public-access", "encryption", "data-exposure"]
```

### Appendix C: Related Standards and Frameworks

- **OWASP Threat Modeling:** https://owasp.org/www-community/Threat_Modeling
- **STRIDE (Microsoft):** https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats
- **CIS AWS Foundations Benchmark:** https://www.cisecurity.org/benchmark/amazon_web_services
- **NIST SP 800-53:** Security and Privacy Controls for Information Systems
- **SARIF Specification:** https://sarifweb.azurewebsites.net/
