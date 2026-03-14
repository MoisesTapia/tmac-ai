# TMAC Roadmap — Ciclo Nacional Mexicano

Cada release lleva el nombre de un elemento significativo del patrimonio mexicano.
El roadmap se estructura en seis fases: Foundation → CI/CD Native → Platform → Intelligence → MCP + Agente → Threat Modeling Real.

**Visión:** Convertir TMAC en la herramienta de threat modeling más integrada del ecosistema DevSecOps — no solo un linter que corres manualmente, sino un agente de seguridad que vive en tu repositorio, analiza cada push, comenta en tus PRs, y evoluciona hacia un threat modeler conversacional completo.

---

## Comparativa con la competencia

| Capacidad | ThreatMitigator | TMAC v1.x | TMAC v2.x | TMAC v3.x |
|---|---|---|---|---|
| Análisis estático Terraform | ✅ | ✅ | ✅ | ✅ |
| SARIF / GitHub Code Scanning | ✅ | ✅ | ✅ | ✅ |
| GitHub Action nativa | ✅ | ✅ (v1.6) | ✅ | ✅ |
| **Análisis de delta en tfplan** | ❌ | ✅ (v1.1) | ✅ | ✅ |
| **Agente en PR — comenta amenazas** | ❌ | ✅ (v1.6) | ✅ | ✅ |
| **Dashboard web multi-repo** | ❌ | ✅ (v1.8) | ✅ | ✅ |
| **MCP Server — agente conversacional** | ❌ | ❌ | ✅ (v2.0) | ✅ |
| **Grafo de dependencias IaC** | ❌ | ❌ | ✅ (v2.2) | ✅ |
| **STRIDE sobre flujos del DFD** | ❌ | ❌ | ❌ | ✅ (v3.0) |
| **TM completo automatizado** | ❌ | ❌ | ❌ | ✅ (v3.5) |

---

## Phase 1: Foundation — Ixtla (v1.0.0 – v1.1.0)

### v1.0.0 — Análisis estático de Terraform *(Ixtla, actual, Q1 2026)*

**Paradigma**: lint de seguridad por recurso individual.

Cada regla evalúa condiciones sobre los atributos de un solo bloque `resource`. No hay conocimiento de relaciones entre recursos.

Capacidades:
- Parseo de archivos `.tf` con extracción de `ResourceModel`
- Evaluación de condiciones STRIDE por recurso (10 reglas AWS base)
- Reportes HTML, Markdown, SARIF/JSON
- Mecanismo `tmac:ignore` por recurso y por regla
- Exit codes estructurados para CI/CD (0/1/2/3)
- Configuración via `.tmac.yaml`

Limitación fundamental: no construye grafo de dependencias. Una Lambda expuesta indirectamente por un rol IAM permisivo no es detectable en esta versión.

---

### v1.1.0 — Análisis de delta de riesgo via tfplan.json *(Ixtla, Q2 2026)*

**Paradigma**: análisis de cambios *antes* de `terraform apply` — lo que ningún competidor hace con STRIDE.

Parsea el plan de ejecución de Terraform (`tfplan.json`) para detectar amenazas en los recursos que van a ser creados, modificados o destruidos. El diferenciador clave: no analiza el estado completo, sino el **delta de riesgo** introducido por el PR.

Capacidades nuevas:
- Parser de `tfplan.json` (output de `terraform plan -out=plan.json`)
- Motor de detección de cambios de riesgo: recurso seguro → inseguro
- Diferenciación entre recursos nuevos, modificados y destruidos
- Reporte de delta: "este PR introduce 3 amenazas nuevas y resuelve 1"
- Integración con el agente de PR (v1.6): el comentario automático muestra solo las amenazas del diff

Ejemplo de amenaza detectable:
> "El plan modifica `aws_s3_bucket.data` cambiando `acl` de `private` a `public-read` — introducción de riesgo Critical (STRIDE-I)"

**Plus vs ThreatMitigator:** ellos analizan el estado completo. TMAC analiza el *cambio* — lo que importa en un PR review.

---

## Phase 2: CI/CD Native + Distribución — Ixtla (v1.2.0 – v1.6.0)

### v1.2.0 — AWS CloudFormation *(Ixtla, Q3 2026)*

Soporte para CloudFormation templates en YAML/JSON. Mismo engine de reglas, nuevo parser.

Capacidades nuevas:
- `CloudFormationParser` que implementa `BaseParser`
- Reglas específicas para recursos CFN (`AWS::S3::Bucket`, `AWS::IAM::Role`, etc.)
- Soporte para `!Ref` y `!Sub` en resolución de atributos

---

### v1.3.0 — Kubernetes Security *(Ixtla, Q4 2026)*

Análisis de manifiestos Kubernetes con foco en RBAC y Pod Security.

Capacidades nuevas:
- `KubernetesParser` para manifiestos YAML (`Deployment`, `Pod`, `ClusterRole`, etc.)
- Reglas para RBAC (ClusterRoleBindings con `*` en verbs/resources)
- Reglas para Pod Security (privileged containers, hostNetwork, hostPID)
- Reglas para Network Policies ausentes

---

### v1.4.0 — Multicloud: Azure Bicep *(Ixtla, Q1 2027)*

Expansión al ecosistema Azure con soporte para Bicep y ARM templates.

Capacidades nuevas:
- `BicepParser` para archivos `.bicep`
- Reglas para recursos Azure (`Microsoft.Storage/storageAccounts`, `Microsoft.Network/networkSecurityGroups`, etc.)
- Mapeo STRIDE para servicios Azure equivalentes a los AWS

---

### v1.5.0 — Docker Compose / Microservicios *(Ixtla, Q2 2027)*

Análisis de infraestructura de microservicios definida en Docker Compose.

Capacidades nuevas:
- `DockerComposeParser` para `docker-compose.yml`
- Detección de privilegios excesivos (`privileged: true`, `cap_add`)
- Análisis de exposición de puertos y redes
- Detección de secretos hardcodeados en variables de entorno

---

### v1.6.0 — TMAC como Agente Nativo de GitHub y GitLab *(Ixtla, Q3 2027)*

**Paradigma**: TMAC vive en tu repositorio. Cada push de código Terraform dispara un análisis automático y el agente comenta directamente en el PR con las amenazas encontradas.

**Este es el diferenciador más visible de la serie v1.x.** ThreatMitigator tiene una GitHub Action, pero no tiene un agente que razone sobre el diff y genere un comentario narrativo de threat modeling.

Capacidades nuevas:

**GitHub Action oficial:**
```yaml
# .github/workflows/tmac.yml
- uses: tmac-security/tmac-action@v1
  with:
    dir: ./infra
    fail-on: high
    comment-pr: true        # ← agente comenta en el PR
    delta-only: true        # ← analiza solo los archivos cambiados en el push
```

**GitLab CI template oficial:**
```yaml
# .gitlab-ci.yml
include:
  - project: tmac-security/tmac-ci
    file: /templates/tmac.gitlab-ci.yml
```

**Agente de PR — comentario automático:**
Cuando se hace push de archivos `.tf`, el agente:
1. Detecta qué archivos `.tf` cambiaron en el diff del PR
2. Ejecuta `tmac scan` solo sobre esos archivos (`--delta-only`)
3. Genera un comentario estructurado en el PR con:
   - Resumen ejecutivo: "Este PR introduce 2 amenazas nuevas (1 Critical, 1 High)"
   - Tabla de findings con severidad, recurso, categoría STRIDE y mitigación
   - Badge de estado: 🔴 BLOQUEADO / 🟡 ADVERTENCIA / ✅ APROBADO
   - Link al reporte HTML completo (subido como artifact)

**Ejemplo de comentario en PR:**

```
## 🔴 TMAC Security Review — 2 amenazas detectadas

Este PR modifica 3 archivos `.tf` e introduce las siguientes amenazas:

| Severidad | Recurso | Regla | STRIDE | Mitigación |
|---|---|---|---|---|
| 🔴 Critical | `aws_s3_bucket.uploads` | TMAC-AWS-S3-001 | Info Disclosure | Cambiar ACL a `private` |
| 🟠 High | `aws_security_group.web` | TMAC-AWS-SG-001 | Tampering | Restringir puerto 22 |

**Estado:** ❌ Bloqueado — se detectaron hallazgos Critical.
Revisa el [reporte completo](artifacts/tmac-report.html) para más detalles.
```

**Publicación y distribución:**
- Publicación en PyPI (`pip install tmac`)
- Fórmula Homebrew para macOS/Linux
- Imagen Docker oficial (`docker run tmac-security/tmac scan`)
- GitHub Action en el Marketplace
- GitLab CI template en el repositorio oficial
- Plugin para pre-commit hooks

**Plus vs ThreatMitigator:** ellos tienen una Action que genera SARIF. TMAC tiene un agente que *comenta en el PR* con un threat model narrativo del diff — no solo un archivo de resultados.

---

## Arquitectura de Plataforma — Modelo SonarQube para Threat Modeling

> Esta sección describe la arquitectura de la plataforma TMAC a partir de v1.6.0.
> El modelo de referencia es SonarQube/SonarCloud: un scanner ligero que corre en CI/CD
> y envía resultados a un servidor central que mantiene el historial completo.

### Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│  REPOSITORIO DEL USUARIO                                        │
│                                                                 │
│  push .tf → GitHub Actions / GitLab CI / Jenkins / cualquier   │
│                    │                                            │
│                    ▼                                            │
│         tmac-scanner (CLI ligero)                               │
│         ├── detecta archivos .tf cambiados en el diff           │
│         ├── ejecuta análisis STRIDE (delta-only o full)         │
│         ├── genera ScanResult (JSON/SARIF)                      │
│         └── envía resultado al TMAC Server via HTTP POST        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP POST /api/v1/scans
┌─────────────────────────────────────────────────────────────────┐
│  TMAC SERVER (self-hosted o SaaS)                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  API REST    │  │  Base de     │  │  Motor de            │  │
│  │  /api/v1/    │  │  datos       │  │  notificaciones      │  │
│  │  scans       │  │  (bitácora)  │  │  (Slack/Teams/email) │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TMAC DASHBOARD (panel web)                              │   │
│  │  ├── Vista organización: riesgo agregado multi-repo      │   │
│  │  ├── Vista repositorio: historial por rama y por push    │   │
│  │  ├── Vista push: threats encontrados en ese commit       │   │
│  │  ├── Bitácora de mitigaciones: qué se resolvió y cuándo  │   │
│  │  └── Tendencias: riesgo acumulado por sprint/semana      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Bitácora por repo / rama / push

Cada scan queda registrado con el siguiente modelo de datos:

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

El dashboard muestra esta bitácora como una línea de tiempo por rama:

```
main        ──●──────────●──────────●──────────●──
               push 1     push 2     push 3     push 4
               3 threats  +1 new     fix S3-001  clean ✅
                          1 resolved

feature/rds ──────────●──────────●──
                       push 1     push 2
                       5 threats  3 resolved
```

### tmac-scanner — Script compatible con cualquier CI/CD

Similar al `sonar-scanner`, TMAC provee un script ligero que se instala una vez
y se invoca desde cualquier pipeline. No requiere configuración compleja.

**Instalación:**
```bash
pip install tmac[scanner]
# o
docker pull tmac-security/tmac-scanner:latest
```

**Uso básico (cualquier CI/CD):**
```bash
tmac-scanner \
  --dir ./infra \
  --server https://tmac.miempresa.com \
  --token $TMAC_TOKEN \
  --repo $CI_PROJECT_PATH \
  --branch $CI_COMMIT_BRANCH \
  --commit $CI_COMMIT_SHA \
  --delta-only                    # analiza solo archivos cambiados en el push
```

**Variables de entorno (alternativa a flags):**
```bash
TMAC_SERVER_URL=https://tmac.miempresa.com
TMAC_TOKEN=<token-de-proyecto>
TMAC_REPO=org/infra-repo
TMAC_BRANCH=main
TMAC_COMMIT=abc123
```

**Compatibilidad CI/CD:**

| Plataforma | Método | Template oficial |
|---|---|---|
| GitHub Actions | `uses: tmac-security/tmac-action@v1` | ✅ Marketplace |
| GitLab CI | `include: tmac-security/tmac-ci` | ✅ Template |
| Jenkins | `sh 'tmac-scanner ...'` | ✅ Jenkinsfile example |
| CircleCI | `orb: tmac-security/tmac` | ✅ Orb |
| Azure DevOps | Task extension | ✅ Marketplace |
| Bitbucket Pipelines | `pipe: tmac-security/tmac-scanner` | ✅ Pipe |
| Pre-commit hook | `repo: tmac-security/tmac` | ✅ Hook |
| Docker (cualquier CI) | `docker run tmac-security/tmac-scanner` | ✅ Universal |

**Ejemplo GitHub Actions completo:**
```yaml
name: TMAC Threat Modeling
on: [push, pull_request]

jobs:
  threat-model:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # necesario para delta-only

      - uses: tmac-security/tmac-action@v1
        with:
          dir: ./infra
          server-url: ${{ secrets.TMAC_SERVER_URL }}
          token: ${{ secrets.TMAC_TOKEN }}
          fail-on: high
          delta-only: true
          comment-pr: true        # comenta en el PR con las amenazas del diff
```

**Ejemplo GitLab CI completo:**
```yaml
include:
  - project: tmac-security/tmac-ci
    file: /templates/tmac.gitlab-ci.yml

variables:
  TMAC_SERVER_URL: https://tmac.miempresa.com
  TMAC_FAIL_ON: high
  TMAC_DELTA_ONLY: "true"
  TMAC_COMMENT_MR: "true"         # comenta en el MR con las amenazas del diff
```

### Modelo de despliegue

**Self-hosted (como SonarQube):**
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

**SaaS (como SonarCloud):**
- `app.tmac.security` — plan gratuito para repos públicos
- Plan team para organizaciones privadas
- SSO via GitHub OAuth / GitLab OAuth / SAML

---

## Phase 3: Platform — Ixtla (v1.7.0 – v1.9.0)

### v1.7.0 — Live Infrastructure / AWS Runtime *(Ixtla, Q4 2027)*

Análisis de infraestructura en vivo via AWS SDK, sin necesidad de archivos IaC.

Capacidades nuevas:
- Conexión via Boto3 para leer el estado real de recursos AWS
- Detección de drift entre IaC y estado real en AWS
- Análisis de recursos creados manualmente (fuera de Terraform)
- Soporte para AWS Organizations (escaneo multi-cuenta)

---

### v1.8.0 — TMAC Dashboard — Panel Web Multi-Repositorio *(Ixtla, Q1 2028)*

**Paradigma**: TMAC como plataforma de seguridad centralizada para equipos.

Un panel web que agrega los resultados de todos los repositorios de la organización, muestra tendencias de riesgo, y permite a los equipos de seguridad tener visibilidad completa sin revisar cada PR manualmente.

**Plus vs ThreatMitigator:** ellos no tienen dashboard. TMAC se convierte en una plataforma, no solo una herramienta.

Capacidades nuevas:

**Backend (`tmac-server`):**
- API REST para recibir resultados de scans desde GitHub Actions / GitLab CI
- Almacenamiento de histórico de scans por repositorio y rama
- Autenticación via GitHub OAuth / GitLab OAuth
- Webhooks para notificaciones (Slack, Teams, PagerDuty)

**Frontend (`tmac-dashboard`):**
- Panel principal: resumen de riesgo por organización
- Vista por repositorio: histórico de findings, tendencia de riesgo
- Vista por regla: qué reglas se disparan más, en qué repos
- Vista por desarrollador: quién introduce más amenazas (gamificación opcional)
- Gráficas de tendencia: riesgo acumulado por sprint/semana
- Exportación a PDF para reportes ejecutivos y auditorías

**Integración con el agente de PR (v1.6):**
- El agente de PR envía los resultados al dashboard automáticamente
- El dashboard muestra el historial de cada PR con sus findings
- Alertas configurables: "si el riesgo del repo X supera umbral Y, notificar a Z"

**Self-hosted y SaaS:**
- Imagen Docker para self-hosting (`docker-compose up tmac-dashboard`)
- Opción SaaS en `app.tmac.security` (roadmap futuro)

---

### v1.9.0 — AI-Powered Auto-Remediation en PR *(Ixtla, Q2 2028)*

**Paradigma**: el agente no solo detecta amenazas, también propone el fix directamente en el PR.

Capacidades nuevas:
- Análisis de findings con LLM para generar código Terraform corregido
- Sugerencia de fix inline en el comentario del PR (GitHub Suggestions API)
- PR automático con el parche propuesto cuando el desarrollador lo aprueba
- Privacidad: solo se envía metadata del finding al LLM, nunca el código fuente
- Soporte para OpenAI GPT-4o, Anthropic Claude, y modelos locales via Ollama
- Integración con GitHub Copilot y Amazon Q

**Ejemplo de sugerencia inline en PR:**
```diff
- acl = "public-read"
+ acl = "private"
```
> 💡 TMAC sugiere este cambio para resolver TMAC-AWS-S3-001 (Critical).
> [Aplicar sugerencia] [Ver explicación completa]

---

## Phase 4: MCP Server + Agente Conversacional — Mitla (v2.0.0 – v2.1.0)

Esta fase convierte TMAC en una herramienta conversacional. Un MCP server expone las capacidades del engine como herramientas que cualquier agente LLM puede invocar. El agente razona sobre los resultados, hace preguntas, y construye el modelo de amenazas de forma interactiva.

---

### v2.0.0 — TMAC MCP Server *(Mitla, Q3 2028)*

**Paradigma**: TMAC como herramienta invocable por agentes LLM via Model Context Protocol.

El MCP server expone el engine de v1.x como tools estructuradas. Con solo los findings individuales como contexto, el LLM ya puede construir un TM narrativo útil, razonando sobre relaciones que el engine aún no detecta automáticamente.

Capacidades nuevas:
- `tmac-mcp` server implementado con el SDK oficial de MCP (Python)
- Tools expuestas:
  - `scan(directory, exclude, rules_dir)` → `ScanResult`
  - `get_findings(severity_filter, rule_id)` → `List[Finding]`
  - `get_rules(cloud, service)` → `List[ThreatRule]`
  - `explain_finding(finding_id)` → descripción detallada con mitigación
  - `generate_report(format, output_path)` → archivo de reporte
  - `get_dashboard_summary(repo)` → resumen del dashboard para el repo
- Compatible con Claude Desktop, Kiro, Cursor y cualquier cliente MCP
- Instalable via `uvx tmac-mcp` o `pip install tmac[mcp]`

Flujo de uso:
```
Usuario: "Haz un threat model de ./infra"
Agente:  scan("./infra") → 12 findings
         get_findings(severity="critical") → 3 findings críticos
         "Basado en los findings, tu arquitectura tiene estos riesgos..."
         [genera TM narrativo con STRIDE, mitigaciones y prioridades]
```

---

### v2.1.0 — MCP con grafo de dependencias *(Mitla, Q4 2028)*

Una vez que v2.2.0 construye el grafo de referencias, el MCP server lo expone como tools adicionales. El agente ya tiene datos estructurales reales y puede hacer TM completo sin inferir relaciones.

Capacidades nuevas (sobre v2.0.0):
- Tools adicionales:
  - `get_resource_graph()` → grafo dirigido de dependencias entre recursos
  - `get_dependencies(resource_id)` → recursos que dependen de / son usados por este recurso
  - `trace_path(source, target)` → todos los caminos entre dos recursos
  - `get_trust_boundaries()` → trust boundaries inferidos de la topología de red
  - `get_dfd()` → Data Flow Diagram en formato texto/JSON

Flujo de uso:
```
Usuario: "¿Puede alguien desde internet llegar a mi RDS?"
Agente:  get_resource_graph() → grafo completo
         trace_path("internet_gateway", "aws_db_instance.prod")
         → [IGW → ALB → Lambda → RDS] con SGs y roles en cada arista
         "Sí, existe este camino: IGW → ALB (puerto 443) → Lambda
          (rol con rds:Connect) → RDS. El SG del RDS permite
          tráfico desde la subnet de Lambda. Recomendación: ..."
```

---

## Phase 5: Threat Modeling Real — Mitla → Copal (v2.2.0 – v3.5.0)

Esta fase transforma TMAC de un linter de seguridad en una herramienta de **Threat Modeling real y automatizado**. El objetivo es detectar amenazas que emergen de la combinación de recursos, flujos de datos y trust boundaries.

---

### v2.2.0 — Resolución de referencias y grafo básico *(Mitla, post-Q4 2028)*

**Paradigma**: recursos conectados por referencias explícitas de Terraform.

Capacidades nuevas:
- Resolución de referencias HCL (`resource_type.name.attribute`) entre archivos
- Construcción de un grafo dirigido de dependencias entre recursos
- Reglas de dos nodos: condiciones que involucran un recurso y sus dependencias directas
- Visualización del grafo en el dashboard (v1.8) y en el reporte HTML

Ejemplo de amenaza detectable:
> "La función `aws_lambda_function.api` está asociada al `aws_security_group.open_sg` que permite tráfico desde `0.0.0.0/0`"

---

### v2.5.0 — Grafo completo + reglas multi-nodo *(Mitla)*

**Paradigma**: traversal de grafo para detectar amenazas emergentes.

Capacidades nuevas:
- Grafo completo con aristas tipadas (usa, depende-de, expone, accede-a)
- DSL de reglas multi-nodo (traversals sobre el grafo, inspirado en Cypher)
- Inferencia de trust boundaries desde topología de red (VPC, subnets, SGs)

Ejemplos de amenazas detectables:
> "La `aws_lambda_function.processor` tiene un rol IAM con `Resource: *` y acceso de red al `aws_db_instance.prod` — posible exfiltración de datos (STRIDE-I)"

---

### v2.8.0 — DFDs automáticos y trust boundaries *(Mitla)*

Capacidades nuevas:
- Generación automática de DFDs desde el grafo de recursos
- Trust boundaries inferidos desde VPCs, subnets públicas/privadas, SGs
- Export de DFDs en formato compatible con Threat Dragon / draw.io
- DFDs visibles en el dashboard (v1.8) por repositorio

---

### v3.0.0 — STRIDE sobre flujos: TM completo automatizado *(Copal)*

**Paradigma**: Threat Modeling completo equivalente a OWASP Threat Dragon o Microsoft TMT, pero automatizado desde el código. Lo que hace un threat modeler humano en 8-40 horas, ejecutado en segundos.

Capacidades nuevas:
- STRIDE aplicado a flujos entre componentes (no solo a recursos aislados)
- Generación de árbol de amenazas por flujo
- Integración con MITRE ATT&CK Cloud y CWE
- Reportes de TM formales compatibles con ISO 27001 / SOC2
- El agente de PR (v1.6) ahora comenta con TM completo sobre el diff

Ejemplo de amenaza detectable:
> "Flujo `aws_api_gateway_rest_api.public` → `aws_lambda_function.handler`: sin autenticación → Spoofing (STRIDE-S), Elevation of Privilege (STRIDE-E)"

---

### v3.5.0 — TM conversacional completo *(Copal)*

El MCP server (v2.1) + el grafo completo (v2.5) + STRIDE sobre flujos (v3.0) se combinan en la experiencia final: un agente conversacional que puede responder cualquier pregunta de threat modeling sobre tu infraestructura.

```
Usuario: "¿Cuáles son los 3 caminos de ataque más críticos en mi arquitectura?"
Agente:  [traversal del grafo completo]
         [STRIDE sobre cada flujo]
         "Los 3 caminos más críticos son:
          1. Internet → API GW → Lambda (sin auth) → RDS (sin cifrado en tránsito)
          2. S3 público → datos de clientes expuestos directamente
          3. IAM role con Resource:* → acceso irrestricto a todos los buckets"
```

---

## Codenames por versión mayor

| Versión mayor | Codename | Descripción |
|---|---|---|
| v1.x | **Ixtla** | Foundation, CI/CD Native, Platform |
| v2.x | **Mitla** | MCP + Agente, TM Real con grafo |
| v3.x | **Copal** | TM completo con STRIDE sobre flujos |

---

## Resumen de versiones

| Versión | Codename | Fase | Capacidad clave | Plus vs competencia | Timeline |
|---|---|---|---|---|---|
| v1.0.0 | Ixtla | Foundation | Análisis estático Terraform + SARIF | Base sólida con STRIDE nativo | Q1 2026 |
| v1.1.0 | Ixtla | Foundation | tfplan.json — delta de riesgo por PR | Nadie analiza el *cambio* con STRIDE | Q2 2026 |
| v1.2.0 | Ixtla | Expansion | AWS CloudFormation | Multi-IaC con mismo engine | Q3 2026 |
| v1.3.0 | Ixtla | Expansion | Kubernetes RBAC + Pod Security | STRIDE en K8s | Q4 2026 |
| v1.4.0 | Ixtla | Expansion | Azure Bicep / multicloud | Multi-cloud con STRIDE | Q1 2027 |
| v1.5.0 | Ixtla | Expansion | Docker Compose / microservicios | STRIDE en compose | Q2 2027 |
| v1.6.0 | Ixtla | CI/CD Native | **Agente en PR — comenta amenazas del diff** | Nadie comenta TM narrativo en PRs | Q3 2027 |
| v1.7.0 | Ixtla | Platform | AWS Runtime / live infra + drift | IaC vs estado real | Q4 2027 |
| v1.8.0 | Ixtla | Platform | **Dashboard web multi-repo** | Panel centralizado de riesgo | Q1 2028 |
| v1.9.0 | Ixtla | Platform | AI auto-remediation en PR | Fix sugerido inline en el PR | Q2 2028 |
| v2.0.0 | Mitla | MCP + Agente | MCP server — agente conversacional | TMAC invocable por cualquier LLM | Q3 2028 |
| v2.1.0 | Mitla | MCP + Agente | MCP con grafo de dependencias | TM conversacional con datos reales | Q4 2028 |
| v2.2.0 | Mitla | TM Real | Resolución de referencias + grafo básico | Amenazas emergentes de combinaciones | post-2028 |
| v2.5.0 | Mitla | TM Real | Grafo completo + reglas multi-nodo | Traversal de grafo para TM | post-2028 |
| v2.8.0 | Mitla | TM Real | DFDs automáticos + trust boundaries | DFDs desde código, no desde diagramas | post-2028 |
| v3.0.0 | Copal | TM Real | STRIDE sobre flujos — TM completo | Workshop de TM en segundos | post-2028 |
| v3.5.0 | Copal | TM Real | TM conversacional completo | Cualquier pregunta de TM respondida | post-2028 |
