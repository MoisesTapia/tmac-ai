# TMAC Roadmap — Mexican National Cycle

Each release is named after a significant element of Mexican heritage.
The roadmap is structured into six phases: Foundation → CI/CD Native → Platform → Intelligence → MCP + Agent → Real Threat Modeling.

**Vision:** Turn TMAC into the most integrated threat modeling tool in the DevSecOps ecosystem — not just a linter you run manually, but a security agent that lives in your repository, analyzes every push, comments on your PRs, and evolves into a complete conversational threat modeler.

---

## Comparison with the competition

| Capability | ThreatMitigator | TMAC v1.x | TMAC v2.x | TMAC v3.x |
|---|---|---|---|---|
| Static Terraform analysis | ✅ | ✅ | ✅ | ✅ |
| SARIF / GitHub Code Scanning | ✅ | ✅ | ✅ | ✅ |
| Native GitHub Action | ✅ | ✅ (v1.6) | ✅ | ✅ |
| **Delta analysis on tfplan** | ❌ | ✅ (v1.1) | ✅ | ✅ |
| **Agent in PR — comments threats** | ❌ | ✅ (v1.6) | ✅ | ✅ |
| **Multi-repo web dashboard** | ❌ | ✅ (v1.8) | ✅ | ✅ |
| **MCP Server — conversational agent** | ❌ | ❌ | ✅ (v2.0) | ✅ |
| **IaC dependency graph** | ❌ | ❌ | ✅ (v2.2) | ✅ |
| **STRIDE over DFD flows** | ❌ | ❌ | ❌ | ✅ (v3.0) |
| **Complete automated TM** | ❌ | ❌ | ❌ | ✅ (v3.5) |

---

## Phase 1: Foundation — Ixtla (v1.0.0 – v1.1.0)

### v1.0.0 — Static Terraform analysis *(Ixtla, current, Q1 2026)*

**Paradigm**: security lint per individual resource.

Each rule evaluates conditions on the attributes of a single `resource` block. There is no knowledge of relationships between resources.

Capabilities:
- Parsing of `.tf` files with `ResourceModel` extraction
- Evaluation of STRIDE conditions per resource (10 base AWS rules)
- HTML, Markdown, SARIF/JSON reports
- `tmac:ignore` mechanism per resource and per rule
- Structured exit codes for CI/CD (0/1/2/3)
- Configuration via `.tmac.yaml`

Fundamental limitation: it does not build a dependency graph. A Lambda indirectly exposed by a permissive IAM role is not detectable in this version.

---

### v1.1.0 — Risk delta analysis via tfplan.json *(Ixtla, Q2 2026)*

**Paradigm**: analysis of changes *before* `terraform apply` — something no competitor does with STRIDE.

Parses the Terraform execution plan (`tfplan.json`) to detect threats in the resources that will be created, modified, or destroyed. The key differentiator: it does not analyze the full state, but the **risk delta** introduced by the PR.

New capabilities:
- Parser for `tfplan.json` (output of `terraform plan -out=plan.json`)
- Risk change detection engine: secure → insecure resource
- Differentiation between new, modified, and destroyed resources
- Delta report: "this PR introduces 3 new threats and resolves 1"
- Integration with the PR agent (v1.6): the automatic comment shows only the threats in the diff

Example of a detectable threat:
> "The plan modifies `aws_s3_bucket.data`, changing `acl` from `private` to `public-read` — introduction of Critical risk (STRIDE-I)"

**Plus vs ThreatMitigator:** they analyze the full state. TMAC analyzes the *change* — what matters in a PR review.

---

## Phase 2: CI/CD Native + Distribution — Ixtla (v1.2.0 – v1.6.0)

### v1.2.0 — AWS CloudFormation *(Ixtla, Q3 2026)*

Support for CloudFormation templates in YAML/JSON. Same rule engine, new parser.

New capabilities:
- `CloudFormationParser` that implements `BaseParser`
- Specific rules for CFN resources (`AWS::S3::Bucket`, `AWS::IAM::Role`, etc.)
- Support for `!Ref` and `!Sub` in attribute resolution

---

### v1.3.0 — Kubernetes Security *(Ixtla, Q4 2026)*

Analysis of Kubernetes manifests with a focus on RBAC and Pod Security.

New capabilities:
- `KubernetesParser` for YAML manifests (`Deployment`, `Pod`, `ClusterRole`, etc.)
- Rules for RBAC (ClusterRoleBindings with `*` in verbs/resources)
- Rules for Pod Security (privileged containers, hostNetwork, hostPID)
- Rules for missing Network Policies

---

### v1.4.0 — Multicloud: Azure Bicep *(Ixtla, Q1 2027)*

Expansion to the Azure ecosystem with support for Bicep and ARM templates.

New capabilities:
- `BicepParser` for `.bicep` files
- Rules for Azure resources (`Microsoft.Storage/storageAccounts`, `Microsoft.Network/networkSecurityGroups`, etc.)
- STRIDE mapping for Azure services equivalent to the AWS ones

---

### v1.5.0 — Docker Compose / Microservices *(Ixtla, Q2 2027)*

Analysis of microservices infrastructure defined in Docker Compose.

New capabilities:
- `DockerComposeParser` for `docker-compose.yml`
- Detection of excessive privileges (`privileged: true`, `cap_add`)
- Analysis of port and network exposure
- Detection of hardcoded secrets in environment variables

---

### v1.6.0 — TMAC as a Native GitHub and GitLab Agent *(Ixtla, Q3 2027)*

**Paradigm**: TMAC lives in your repository. Every push of Terraform code triggers an automatic analysis, and the agent comments directly on the PR with the threats found.

**This is the most visible differentiator of the v1.x series.** ThreatMitigator has a GitHub Action, but it does not have an agent that reasons about the diff and generates a narrative threat modeling comment.

New capabilities:

**Official GitHub Action:**
```yaml
# .github/workflows/tmac.yml
- uses: tmac-security/tmac-action@v1
  with:
    dir: ./infra
    fail-on: high
    comment-pr: true        # ← the agent comments on the PR
    delta-only: true        # ← analyzes only the files changed in the push
```

**Official GitLab CI template:**
```yaml
# .gitlab-ci.yml
include:
  - project: tmac-security/tmac-ci
    file: /templates/tmac.gitlab-ci.yml
```

**PR agent — automatic comment:**
When `.tf` files are pushed, the agent:
1. Detects which `.tf` files changed in the PR diff
2. Runs `tmac scan` only on those files (`--delta-only`)
3. Generates a structured comment on the PR with:
   - Executive summary: "This PR introduces 2 new threats (1 Critical, 1 High)"
   - Table of findings with severity, resource, STRIDE category, and mitigation
   - Status badge: 🔴 BLOCKED / 🟡 WARNING / ✅ APPROVED
   - Link to the full HTML report (uploaded as an artifact)

**Example PR comment:**

```
## 🔴 TMAC Security Review — 2 threats detected

This PR modifies 3 `.tf` files and introduces the following threats:

| Severity | Resource | Rule | STRIDE | Mitigation |
|---|---|---|---|---|
| 🔴 Critical | `aws_s3_bucket.uploads` | TMAC-AWS-S3-001 | Info Disclosure | Change ACL to `private` |
| 🟠 High | `aws_security_group.web` | TMAC-AWS-SG-001 | Tampering | Restrict port 22 |

**Status:** ❌ Blocked — Critical findings were detected.
Review the [full report](artifacts/tmac-report.html) for more details.
```

**Publishing and distribution:**
- Publishing on PyPI (`pip install tmac`)
- Homebrew formula for macOS/Linux
- Official Docker image (`docker run tmac-security/tmac scan`)
- GitHub Action on the Marketplace
- GitLab CI template in the official repository
- Plugin for pre-commit hooks

**Plus vs ThreatMitigator:** they have an Action that generates SARIF. TMAC has an agent that *comments on the PR* with a narrative threat model of the diff — not just a results file.

---

## Platform Architecture — SonarQube Model for Threat Modeling

> This section describes the TMAC platform architecture starting from v1.6.0.
> The reference model is SonarQube/SonarCloud: a lightweight scanner that runs in CI/CD
> and sends results to a central server that maintains the complete history.

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│  USER REPOSITORY                                                │
│                                                                 │
│  push .tf → GitHub Actions / GitLab CI / Jenkins / any          │
│                    │                                            │
│                    ▼                                            │
│         tmac-scanner (lightweight CLI)                          │
│         ├── detects .tf files changed in the diff               │
│         ├── runs STRIDE analysis (delta-only or full)           │
│         ├── generates ScanResult (JSON/SARIF)                   │
│         └── sends result to the TMAC Server via HTTP POST       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP POST /api/v1/scans
┌─────────────────────────────────────────────────────────────────┐
│  TMAC SERVER (self-hosted or SaaS)                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  API REST    │  │  Database    │  │  Notifications       │   │
│  │  /api/v1/    │  │              │  │  engine              │   │
│  │  scans       │  │  (log)       │  │  (Slack/Teams/email) │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TMAC DASHBOARD (web panel)                              │   │
│  │  ├── Organization view: aggregated multi-repo risk       │   │
│  │  ├── Repository view: history per branch and per push    │   │
│  │  ├── Push view: threats found in that commit             │   │
│  │  ├── Mitigation log: what was resolved and when          │   │
│  │  └── Trends: accumulated risk per sprint/week            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Log by repo / branch / push

Each scan is recorded with the following data model:

```json
{
  "scan_id": "uuid",
  "repo": "org/infra-repo",
  "branch": "feature/add-rds",
  "commit_sha": "abc123",
  "pushed_by": "dev@example.com",
  "timestamp": "2026-03-14T10:00:00Z",
  "mode": "delta",
  "files_changed": ["modules/rds/main.tf", "modules/vpc/sg.tf"],
  "findings": [...],
  "findings_new": 3,
  "findings_resolved": 1,
  "risk_delta": "+2 Critical",
  "mitigations": [
    {
      "finding_id": "...",
      "rule_id": "TMAC-AWS-S3-001",
      "resolved_at": "2026-03-14T10:00:00Z",
      "resolved_by": "dev@example.com",
      "commit_sha": "abc123"
    }
  ]
}
```

The dashboard shows this log as a timeline per branch:

```
main        ──●──────────●──────────●──────────●──
               push 1     push 2     push 3     push 4
               3 threats  +1 new     fix S3-001  clean ✅
                          1 resolved

feature/rds ──────────●──────────●──
                       push 1     push 2
                       5 threats  3 resolved
```

### tmac-scanner — Script compatible with any CI/CD

Similar to `sonar-scanner`, TMAC provides a lightweight script that is installed once
and is invoked from any pipeline. It does not require complex configuration.

**Installation:**
```bash
pip install tmac[scanner]
# o
docker pull tmac-security/tmac-scanner:latest
```

**Basic usage (any CI/CD):**
```bash
tmac-scanner \
  --dir ./infra \
  --server https://tmac.miempresa.com \
  --token $TMAC_TOKEN \
  --repo $CI_PROJECT_PATH \
  --branch $CI_COMMIT_BRANCH \
  --commit $CI_COMMIT_SHA \
  --delta-only                    # analyzes only files changed in the push
```

**Environment variables (alternative to flags):**
```bash
TMAC_SERVER_URL=https://tmac.miempresa.com
TMAC_TOKEN=<project-token>
TMAC_REPO=org/infra-repo
TMAC_BRANCH=main
TMAC_COMMIT=abc123
```

**CI/CD compatibility:**

| Platform | Method | Official template |
|---|---|---|
| GitHub Actions | `uses: tmac-security/tmac-action@v1` | ✅ Marketplace |
| GitLab CI | `include: tmac-security/tmac-ci` | ✅ Template |
| Jenkins | `sh 'tmac-scanner ...'` | ✅ Jenkinsfile example |
| CircleCI | `orb: tmac-security/tmac` | ✅ Orb |
| Azure DevOps | Task extension | ✅ Marketplace |
| Bitbucket Pipelines | `pipe: tmac-security/tmac-scanner` | ✅ Pipe |
| Pre-commit hook | `repo: tmac-security/tmac` | ✅ Hook |
| Docker (any CI) | `docker run tmac-security/tmac-scanner` | ✅ Universal |

**Complete GitHub Actions example:**
```yaml
name: TMAC Threat Modeling
on: [push, pull_request]

jobs:
  threat-model:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # required for delta-only

      - uses: tmac-security/tmac-action@v1
        with:
          dir: ./infra
          server-url: ${{ secrets.TMAC_SERVER_URL }}
          token: ${{ secrets.TMAC_TOKEN }}
          fail-on: high
          delta-only: true
          comment-pr: true        # comments on the PR with the threats in the diff
```

**Complete GitLab CI example:**
```yaml
include:
  - project: tmac-security/tmac-ci
    file: /templates/tmac.gitlab-ci.yml

variables:
  TMAC_SERVER_URL: https://tmac.miempresa.com
  TMAC_FAIL_ON: high
  TMAC_DELTA_ONLY: "true"
  TMAC_COMMENT_MR: "true"         # comments on the MR with the threats in the diff
```

### Deployment model

**Self-hosted (like SonarQube):**
```bash
# docker-compose.yml
services:
  tmac-server:
    image: tmac-security/tmac-server:latest
    ports: ["8080:8080"]
    environment:
      DATABASE_URL: postgresql://...
      SECRET_KEY: ...

  tmac-dashboard:
    image: tmac-security/tmac-dashboard:latest
    ports: ["3000:3000"]
    environment:
      API_URL: http://tmac-server:8080
```

**SaaS (like SonarCloud):**
- `app.tmac.security` — free plan for public repos
- Team plan for private organizations
- SSO via GitHub OAuth / GitLab OAuth / SAML

---

## Phase 3: Platform — Ixtla (v1.7.0 – v1.9.0)

### v1.7.0 — Live Infrastructure / AWS Runtime *(Ixtla, Q4 2027)*

Analysis of live infrastructure via the AWS SDK, without the need for IaC files.

New capabilities:
- Connection via Boto3 to read the real state of AWS resources
- Drift detection between IaC and the real state in AWS
- Analysis of manually created resources (outside Terraform)
- Support for AWS Organizations (multi-account scanning)

---

### v1.8.0 — TMAC Dashboard — Multi-Repository Web Panel *(Ixtla, Q1 2028)*

**Paradigm**: TMAC as a centralized security platform for teams.

A web panel that aggregates the results of all the organization's repositories, shows risk trends, and lets security teams have complete visibility without reviewing each PR manually.

**Plus vs ThreatMitigator:** they do not have a dashboard. TMAC becomes a platform, not just a tool.

New capabilities:

**Backend (`tmac-server`):**
- REST API to receive scan results from GitHub Actions / GitLab CI
- Storage of scan history per repository and branch
- Authentication via GitHub OAuth / GitLab OAuth
- Webhooks for notifications (Slack, Teams, PagerDuty)

**Frontend (`tmac-dashboard`):**
- Main panel: risk summary per organization
- Per-repository view: history of findings, risk trend
- Per-rule view: which rules trigger the most, in which repos
- Per-developer view: who introduces the most threats (optional gamification)
- Trend charts: accumulated risk per sprint/week
- PDF export for executive reports and audits

**Integration with the PR agent (v1.6):**
- The PR agent sends the results to the dashboard automatically
- The dashboard shows the history of each PR with its findings
- Configurable alerts: "if the risk of repo X exceeds threshold Y, notify Z"

**Self-hosted and SaaS:**
- Docker image for self-hosting (`docker-compose up tmac-dashboard`)
- SaaS option at `app.tmac.security` (future roadmap)

---

### v1.9.0 — AI-Powered Auto-Remediation in PR *(Ixtla, Q2 2028)*

**Paradigm**: the agent not only detects threats, it also proposes the fix directly in the PR.

New capabilities:
- Analysis of findings with an LLM to generate corrected Terraform code
- Inline fix suggestion in the PR comment (GitHub Suggestions API)
- Automatic PR with the proposed patch when the developer approves it
- Privacy: only the finding metadata is sent to the LLM, never the source code
- Support for OpenAI GPT-4o, Anthropic Claude, and local models via Ollama
- Integration with GitHub Copilot and Amazon Q

**Example of an inline suggestion in a PR:**
```diff
- acl = "public-read"
+ acl = "private"
```
> 💡 TMAC suggests this change to resolve TMAC-AWS-S3-001 (Critical).
> [Apply suggestion] [See full explanation]

---

## Phase 4: MCP Server + Conversational Agent — Mitla (v2.0.0 – v2.1.0)

This phase turns TMAC into a conversational tool. An MCP server exposes the engine capabilities as tools that any LLM agent can invoke. The agent reasons about the results, asks questions, and builds the threat model interactively.

---

### v2.0.0 — TMAC MCP Server *(Mitla, Q3 2028)*

**Paradigm**: TMAC as a tool invokable by LLM agents via the Model Context Protocol.

The MCP server exposes the v1.x engine as structured tools. With only the individual findings as context, the LLM can already build a useful narrative TM, reasoning about relationships that the engine does not yet detect automatically.

New capabilities:
- `tmac-mcp` server implemented with the official MCP SDK (Python)
- Exposed tools:
  - `scan(directory, exclude, rules_dir)` → `ScanResult`
  - `get_findings(severity_filter, rule_id)` → `List[Finding]`
  - `get_rules(cloud, service)` → `List[ThreatRule]`
  - `explain_finding(finding_id)` → detailed description with mitigation
  - `generate_report(format, output_path)` → report file
  - `get_dashboard_summary(repo)` → dashboard summary for the repo
- Compatible with Claude Desktop, Kiro, Cursor, and any MCP client
- Installable via `uvx tmac-mcp` or `pip install tmac[mcp]`

Usage flow:
```
User:  "Do a threat model of ./infra"
Agent:  scan("./infra") → 12 findings
         get_findings(severity="critical") → 3 critical findings
         "Based on the findings, your architecture has these risks..."
         [generates narrative TM with STRIDE, mitigations, and priorities]
```

---

### v2.1.0 — MCP with dependency graph *(Mitla, Q4 2028)*

Once v2.2.0 builds the reference graph, the MCP server exposes it as additional tools. The agent then has real structural data and can do complete TM without inferring relationships.

New capabilities (on top of v2.0.0):
- Additional tools:
  - `get_resource_graph()` → directed graph of dependencies between resources
  - `get_dependencies(resource_id)` → resources that depend on / are used by this resource
  - `trace_path(source, target)` → all paths between two resources
  - `get_trust_boundaries()` → trust boundaries inferred from the network topology
  - `get_dfd()` → Data Flow Diagram in text/JSON format

Usage flow:
```
User:  "Can anyone from the internet reach my RDS?"
Agent:  get_resource_graph() → complete graph
         trace_path("internet_gateway", "aws_db_instance.prod")
         → [IGW → ALB → Lambda → RDS] with SGs and roles on each edge
         "Yes, this path exists: IGW → ALB (port 443) → Lambda
          (role with rds:Connect) → RDS. The RDS SG allows
          traffic from the Lambda subnet. Recommendation: ..."
```

---

## Phase 5: Real Threat Modeling — Mitla → Copal (v2.2.0 – v3.5.0)

This phase transforms TMAC from a security linter into a **real and automated Threat Modeling** tool. The goal is to detect threats that emerge from the combination of resources, data flows, and trust boundaries.

---

### v2.2.0 — Reference resolution and basic graph *(Mitla, post-Q4 2028)*

**Paradigm**: resources connected by explicit Terraform references.

New capabilities:
- Resolution of HCL references (`resource_type.name.attribute`) across files
- Construction of a directed dependency graph between resources
- Two-node rules: conditions that involve a resource and its direct dependencies
- Visualization of the graph in the dashboard (v1.8) and in the HTML report

Example of a detectable threat:
> "The function `aws_lambda_function.api` is associated with the `aws_security_group.open_sg` that allows traffic from `0.0.0.0/0`"

---

### v2.5.0 — Complete graph + multi-node rules *(Mitla)*

**Paradigm**: graph traversal to detect emergent threats.

New capabilities:
- Complete graph with typed edges (uses, depends-on, exposes, accesses)
- Multi-node rule DSL (traversals over the graph, inspired by Cypher)
- Inference of trust boundaries from network topology (VPC, subnets, SGs)

Examples of detectable threats:
> "The `aws_lambda_function.processor` has an IAM role with `Resource: *` and network access to `aws_db_instance.prod` — possible data exfiltration (STRIDE-I)"

---

### v2.8.0 — Automatic DFDs and trust boundaries *(Mitla)*

New capabilities:
- Automatic generation of DFDs from the resource graph
- Trust boundaries inferred from VPCs, public/private subnets, SGs
- Export of DFDs in a format compatible with Threat Dragon / draw.io
- DFDs visible in the dashboard (v1.8) per repository

---

### v3.0.0 — STRIDE over flows: complete automated TM *(Copal)*

**Paradigm**: Complete Threat Modeling equivalent to OWASP Threat Dragon or Microsoft TMT, but automated from the code. What a human threat modeler does in 8-40 hours, executed in seconds.

New capabilities:
- STRIDE applied to flows between components (not just to isolated resources)
- Generation of a threat tree per flow
- Integration with MITRE ATT&CK Cloud and CWE
- Formal TM reports compatible with ISO 27001 / SOC2
- The PR agent (v1.6) now comments with a complete TM over the diff

Example of a detectable threat:
> "Flow `aws_api_gateway_rest_api.public` → `aws_lambda_function.handler`: without authentication → Spoofing (STRIDE-S), Elevation of Privilege (STRIDE-E)"

---

### v3.5.0 — Complete conversational TM *(Copal)*

The MCP server (v2.1) + the complete graph (v2.5) + STRIDE over flows (v3.0) combine into the final experience: a conversational agent that can answer any threat modeling question about your infrastructure.

```
User:  "What are the 3 most critical attack paths in my architecture?"
Agent:  [traversal of the complete graph]
         [STRIDE over each flow]
         "The 3 most critical paths are:
          1. Internet → API GW → Lambda (no auth) → RDS (no encryption in transit)
          2. Public S3 → customer data exposed directly
          3. IAM role with Resource:* → unrestricted access to all buckets"
```

---

## Codenames per major version

| Major version | Codename | Description |
|---|---|---|
| v1.x | **Ixtla** | Foundation, CI/CD Native, Platform |
| v2.x | **Mitla** | MCP + Agent, Real TM with graph |
| v3.x | **Copal** | Complete TM with STRIDE over flows |

---

## Summary of versions

| Version | Codename | Phase | Key capability | Plus vs competition | Timeline |
|---|---|---|---|---|---|
| v1.0.0 | Ixtla | Foundation | Static Terraform analysis + SARIF | Solid base with native STRIDE | Q1 2026 |
| v1.1.0 | Ixtla | Foundation | tfplan.json — risk delta per PR | No one analyzes the *change* with STRIDE | Q2 2026 |
| v1.2.0 | Ixtla | Expansion | AWS CloudFormation | Multi-IaC with the same engine | Q3 2026 |
| v1.3.0 | Ixtla | Expansion | Kubernetes RBAC + Pod Security | STRIDE in K8s | Q4 2026 |
| v1.4.0 | Ixtla | Expansion | Azure Bicep / multicloud | Multi-cloud with STRIDE | Q1 2027 |
| v1.5.0 | Ixtla | Expansion | Docker Compose / microservices | STRIDE in compose | Q2 2027 |
| v1.6.0 | Ixtla | CI/CD Native | **Agent in PR — comments threats in the diff** | No one comments narrative TM on PRs | Q3 2027 |
| v1.7.0 | Ixtla | Platform | AWS Runtime / live infra + drift | IaC vs real state | Q4 2027 |
| v1.8.0 | Ixtla | Platform | **Multi-repo web dashboard** | Centralized risk panel | Q1 2028 |
| v1.9.0 | Ixtla | Platform | AI auto-remediation in PR | Suggested fix inline in the PR | Q2 2028 |
| v2.0.0 | Mitla | MCP + Agent | MCP server — conversational agent | TMAC invokable by any LLM | Q3 2028 |
| v2.1.0 | Mitla | MCP + Agent | MCP with dependency graph | Conversational TM with real data | Q4 2028 |
| v2.2.0 | Mitla | Real TM | Reference resolution + basic graph | Threats emerging from combinations | post-2028 |
| v2.5.0 | Mitla | Real TM | Complete graph + multi-node rules | Graph traversal for TM | post-2028 |
| v2.8.0 | Mitla | Real TM | Automatic DFDs + trust boundaries | DFDs from code, not from diagrams | post-2028 |
| v3.0.0 | Copal | Real TM | STRIDE over flows — complete TM | TM workshop in seconds | post-2028 |
| v3.5.0 | Copal | Real TM | Complete conversational TM | Any TM question answered | post-2028 |
