# TMAC (Threat Modeling as Code)

TMAC es una herramienta de análisis estático de seguridad para Infraestructura como Código (IaC).
Automatiza el modelado de amenazas identificando vulnerabilidades en código Terraform / OpenTofu y en
templates de AWS CloudFormation antes del despliegue,
usando el framework STRIDE.

## Características principales (v1.1.0 "Ixtla")

- **Análisis de Terraform y OpenTofu:** Escaneo automático de archivos `.tf` y `.tofu`.
- **Análisis de AWS CloudFormation (`tmac cfn`):** Templates YAML y JSON, con soporte de funciones
  intrínsecas (`!Ref`, `!Sub`, `!GetAtt`, …) y 43 reglas STRIDE propias.
- **Análisis de delta de riesgo (`tmac plan`):** Detecta amenazas STRIDE exclusivamente en los recursos que el plan de Terraform va a crear, modificar o destruir — sin analizar el estado completo.
- **Motor de reglas YAML:** Reglas de amenazas fuertemente tipadas y validadas con Pydantic.
- **Framework STRIDE:** Categorización automática de hallazgos (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).
- **Múltiples formatos de reporte:** HTML, Markdown y JSON/SARIF.
- **Integración CI/CD:** Exit codes estructurados basados en severidad para romper el pipeline ante amenazas críticas.
- **Ejecución offline:** Sin envío de datos a APIs externas.

## Requisitos

- **Python 3.10+**
- [Poetry](https://python-poetry.org/) (recomendado) o `pip`

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tmac-security/tmac.git
cd tmac

# Instalar con Poetry
poetry install

# O con pip en un entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -e .
```

## Uso

### Análisis básico

```bash
tmac scan
```

Escanea el directorio actual y genera un reporte HTML (`tmac-report.html`).

Se analizan los archivos `.tf` y `.tofu` (OpenTofu). Si existen `x.tf` y `x.tofu` en el mismo
directorio, se usa solo `x.tofu`, igual que OpenTofu. Nunca se recorren `.git`, `.terraform`,
`node_modules`, `.terragrunt-cache`, `.aws-sam`, entornos virtuales (`venv`, `.venv`) ni cachés de
herramientas; para analizar uno de ellos, pásalo directamente con `--dir`.

### Opciones del CLI (`tmac scan`)

| Opción | Abreviación | Descripción | Por defecto |
| :--- | :--- | :--- | :--- |
| `--dir` | `-d` | Directorio a escanear con archivos `.tf`. | `scan.dir` de `.tmac.yaml`, si no `.` |
| `--report` | `-r` | Formato del reporte: `html`, `json`, `md`. | `html` |
| `--output` | `-o` | Ruta del archivo de reporte. | `tmac-report.[fmt]` |
| `--rules-dir` | | Directorio de reglas YAML adicionales. | (reglas internas) |
| `--config` | | Ruta al archivo de configuración. Si se indica explícitamente y no existe → exit 3. | `.tmac.yaml` |
| `--fail-on` | | Severidad mínima para exit code 1. | `critical` |
| `--severity` | | Severidad mínima a incluir en el reporte. | `all` |
| `--exclude` | `-e` | Patrón glob a excluir (repetible). | — |
| `--lenient` | | No fallar con exit 3 si hay archivos que no se pudieron parsear o reglas inválidas (solo advierte). | `False` |
| `--no-color` | | Deshabilita colores ANSI en la salida. | `False` |
| `--verbose` | `-v` | Habilita logging de debug. | `False` |
| `--quiet` | `-q` | Suprime la salida de terminal. | `False` |

### Ejemplos prácticos

```bash
# Escanear carpeta específica, reporte Markdown, fallar en High o superior
tmac scan --dir ./infra/prod --report md --output security_report.md --fail-on high

# Excluir directorio .terraform y módulos de terceros
tmac scan --dir ./infra --exclude .terraform --exclude "**/.terraform/**"

# Salida sin colores para logs de CI
tmac scan --dir ./infra --no-color --report json

# Modo verbose para debugging
tmac scan --dir ./infra --verbose
```

## tmac plan — Análisis de Delta de Riesgo

Analiza un `tfplan.json` generado por Terraform para detectar amenazas STRIDE **exclusivamente en los recursos que el plan va a crear, modificar o destruir**. A diferencia de `tmac scan`, no evalúa el estado completo de la infraestructura — responde a la pregunta: *"¿Qué riesgo nuevo introduce este PR?"*.

### Generar el tfplan.json

```bash
terraform plan -out=plan.bin
terraform show -json plan.bin > plan.json
```

### Uso básico

```bash
tmac plan --plan-file plan.json
```

### Opciones del CLI (`tmac plan`)

| Opción | Abreviación | Descripción | Requerido |
| :--- | :--- | :--- | :--- |
| `--plan-file` | `-p` | Ruta al plan JSON generado por `terraform show -json` o `tofu show -json`. | **Sí** |
| `--report` | `-r` | Formato del reporte: `html`, `json`, `md`. | No |
| `--output` | `-o` | Ruta del archivo de reporte. | No |
| `--rules-dir` | | Directorio de reglas YAML adicionales. | No |
| `--config` | | Ruta al archivo de configuración (`report.format`, `report.fail_on`, `scan.rules_dir`). | No |
| `--source-dir` | | Directorio con los `.tf` del plan: aplica sus comentarios `tmac:ignore` (ver abajo). | No |
| `--fail-on` | | Severidad mínima para exit code 1: `critical`, `high`, `medium`, `low`, `info`. | No |
| `--lenient` | | No fallar con exit 3 si hay reglas inválidas (solo advierte). | No |
| `--quiet` | `-q` | Suprime la salida de terminal. | No |
| `--no-color` | | Deshabilita colores ANSI en la salida. | No |
| `--verbose` | `-v` | Habilita logging de debug (cambios parseados, recursos por acción, reglas evaluadas). | No |

### Ejemplos prácticos

```bash
# Análisis básico con reporte Markdown
tmac plan --plan-file plan.json --report md --output delta-report.md

# Fallar en amenazas Critical, salida JSON/SARIF
tmac plan --plan-file plan.json --report json --output delta.json --fail-on critical

# Pipeline completo en una línea
terraform plan -out=plan.bin && terraform show -json plan.bin > plan.json && tmac plan --plan-file plan.json

# Modo verbose para debugging
tmac plan --plan-file plan.json --verbose
```

### Códigos de salida de `tmac plan`

| Código | Condición |
| :--- | :--- |
| `0` | Sin `DeltaFinding` Critical o High (plan seguro). |
| `1` | Se detectó al menos un `DeltaFinding` con severidad **Critical**. |
| `2` | Se detectaron `DeltaFinding` **High** pero ninguno Critical. |
| `3` | Error de ejecución: archivo no existe, JSON inválido, `tfplan.json` sin `resource_changes`, o reglas inválidas (salvo `--lenient`). |

### Formato del reporte de delta

El reporte muestra el **RiskDelta** neto del plan (`amenazas introducidas − amenazas resueltas`):

- **Amenazas introducidas**: recursos creados o modificados que violan reglas STRIDE.
- **Amenazas resueltas**: recursos eliminados o modificados que ya no violan reglas STRIDE.

Ejemplo de resumen en Markdown:

```
> Este plan introduce 2 amenazas nuevas y resuelve 1.

| Acción    | Recurso              | Regla            | Severidad | STRIDE               | Descripción del cambio          |
|-----------|----------------------|------------------|-----------|----------------------|---------------------------------|
| NUEVO     | aws_s3_bucket.data   | TMAC-AWS-S3-001  | Critical  | Information Disclosure | acl: private → public-read    |
| MODIFICADO| aws_s3_bucket.logs   | TMAC-AWS-S3-002  | High      | Information Disclosure | server_side_encryption: AES256 → (none) |
```

---

## tmac cfn — AWS CloudFormation

Analiza templates de AWS CloudFormation (YAML y JSON) con las mismas severidades, categorías STRIDE,
reportes y códigos de salida que `tmac scan`:

```bash
tmac cfn --dir ./templates
tmac cfn --dir ./templates --report md --output cfn.md --fail-on high --severity medium
```

`tmac cfn` acepta las mismas opciones que `tmac scan` (`--dir`, `--report`, `--output`, `--rules-dir`,
`--config`, `--fail-on`, `--severity`, `--exclude`, `--lenient`, `--quiet`, `--no-color`, `--verbose`). El
reporte por defecto es `tmac-cfn-report.{fmt}`.

### Archivos analizados

Se recorren los archivos `.yaml`, `.yml`, `.json` y `.template`, y solo se analizan los que parecen
templates de CloudFormation (contienen `AWSTemplateFormatVersion` o un `Type: AWS::…`). Los manifiestos
de Kubernetes, los `package.json` o las plantillas de Helm se ignoran sin generar errores. El formato
(YAML o JSON) se detecta por el contenido, no por la extensión. Para analizar la salida de AWS CDK, usa
`tmac cfn --dir cdk.out`.

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Resources:
  DataBucket:                      # LogicalId → nombre del recurso en el reporte
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${Env}-data"
      AccessControl: PublicRead    # → TMAC-CFN-S3-001 (Critical)
```

Un template que parece de CloudFormation pero no se puede leer (YAML o JSON inválido, recurso sin
`Type`, más de 5 MB) hace que el escaneo termine con código `3` (ver *Códigos de salida*).

### Funciones intrínsecas

`!Ref`, `!Sub`, `!GetAtt`, `!If`, `!Join` y el resto (en forma corta o larga, `Fn::…`) se conservan
como valores cuyo contenido solo se conoce al desplegar: cuentan como **presentes** para `exists` /
`not_exists`, pero **ninguna comparación dispara un hallazgo** sobre ellos. Por ejemplo,
`Encrypted: !Ref EncryptVolumes` no se reporta como volumen sin cifrar.

### Ignorar hallazgos en CloudFormation

```yaml
Resources:
  # tmac:ignore                      ← todas las reglas de este recurso
  PublicAssets:
    Type: AWS::S3::Bucket

  # tmac:ignore[TMAC-CFN-S3-003]     ← solo esa regla (se pueden apilar varias líneas)
  Logs:
    Type: AWS::S3::Bucket

  Website:  # tmac:ignore[TMAC-CFN-S3-004]   ← también en la misma línea
    Type: AWS::S3::Bucket

  JsonFriendly:                      # Metadata funciona también en templates JSON
    Type: AWS::S3::Bucket
    Metadata:
      tmac:
        ignore: ["TMAC-CFN-S3-002"]  # o "*"
```

### Reglas CloudFormation y equivalencias con Terraform

| Servicio | Tipo CloudFormation | Tipo Terraform | Reglas |
| :--- | :--- | :--- | :--- |
| S3 | `AWS::S3::Bucket` | `aws_s3_bucket` | S3-001 … S3-005 |
| IAM | `AWS::IAM::Policy`, `AWS::IAM::ManagedPolicy` | `aws_iam_policy` | IAM-001, 002, 005, 007, 008 |
| IAM | `AWS::IAM::Role` | `aws_iam_role` | IAM-003, 004, 009 |
| IAM | `AWS::IAM::User` | `aws_iam_user` | IAM-006 |
| Security Groups | `AWS::EC2::SecurityGroup` | `aws_security_group` | SG-001 … SG-003 |
| VPC | `AWS::EC2::VPC` | `aws_vpc` | VPC-001 |
| EC2 | `AWS::EC2::Instance`, `AWS::EC2::LaunchTemplate`, `AWS::EC2::Volume` | `aws_instance`, `aws_launch_template`, `aws_ebs_volume` | EC2-001 … EC2-004 |
| RDS | `AWS::RDS::DBInstance` | `aws_db_instance` | RDS-001 … RDS-005 |
| DynamoDB | `AWS::DynamoDB::Table` | `aws_dynamodb_table` | DDB-001 … DDB-003 |
| KMS | `AWS::KMS::Key` | `aws_kms_key` | KMS-001 … KMS-003 |
| Lambda | `AWS::Lambda::Function` | `aws_lambda_function` | LMD-001 … LMD-003 |
| CloudTrail | `AWS::CloudTrail::Trail` | `aws_cloudtrail` | CW-001 … CW-003 |
| API Gateway | `AWS::ApiGateway::Method`, `AWS::ApiGateway::Stage` | `aws_api_gateway_method`, `aws_api_gateway_stage` | APIGW-001 … APIGW-003 |
| CloudFormation | `AWS::CloudFormation::Stack` | — | STACK-001 |

Todas las reglas tienen el prefijo `TMAC-CFN-` (por ejemplo `TMAC-CFN-S3-001`). El catálogo completo,
con descripción y mitigación, está en [`src/tmac/rules/cfn/threats.yaml`](src/tmac/rules/cfn/threats.yaml).

### GitHub Actions — `tmac cfn`

```yaml
- name: TMAC CloudFormation scan
  run: tmac cfn --dir ./templates --report json --output tmac-cfn.json --fail-on high
- uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: tmac-cfn.json
```

### Limitaciones conocidas

- **Funciones intrínsecas sin resolver:** los valores de `!Ref`, `!Sub`, `Parameters`, `Mappings` y
  `Conditions` no se evalúan (ver arriba); una configuración insegura que dependa de un parámetro no
  se detecta. La resolución llegará con el grafo de dependencias (v2.2.0).
- **Sin correlación entre recursos:** cada recurso se evalúa por separado. Por eso `TMAC-CFN-VPC-001`
  usa el tag `FlowLogs=enabled` como workaround (igual que `TMAC-AWS-VPC-001`), un
  `AWS::S3::BucketPolicy` no se relaciona con su bucket, y en Security Groups el puerto y el CIDR se
  comprueban por separado entre todas las reglas de ingreso del grupo.
- **Recursos no cubiertos en v1.2.0:** `AWS::IAM::AccessKey`, las políticas inline de
  `AWS::IAM::User`, `AWS::RDS::DBCluster`, `AWS::Serverless::*` (SAM) y los servicios fuera de los 11
  de la tabla.

---

## TMAC v1.1.0 vs análisis de estado completo

La mayoría de herramientas de seguridad para IaC analizan el **estado completo** de la infraestructura: evalúan todos los recursos definidos en los archivos `.tf` y reportan todas las amenazas existentes. Esto es útil para auditorías, pero genera ruido en revisiones de PR porque mezcla amenazas preexistentes con las introducidas por el cambio.

**TMAC v1.1.0 responde una pregunta diferente:**

| Herramienta | Pregunta que responde |
| :--- | :--- |
| `tmac scan` (v1.0.0) | *"¿Qué riesgo existe en la infraestructura completa?"* |
| `tmac plan` (v1.1.0) | *"¿Qué riesgo nuevo introduce este PR?"* |

`tmac plan` parsea el output de `terraform show -json` y evalúa **solo los recursos del diff**:
- Recursos **creados**: detecta amenazas en el estado final.
- Recursos **modificados**: detecta amenazas introducidas por el cambio (no las preexistentes).
- Recursos **eliminados**: registra amenazas resueltas al eliminar el recurso.

Esto lo hace ideal para pipelines de CI/CD donde el objetivo es **bloquear solo los cambios que degradan la postura de seguridad**, sin generar falsos positivos por deuda técnica preexistente.

---

## Códigos de salida (Exit Codes)

| Código | Condición |
| :--- | :--- |
| `0` | Escaneo completado sin hallazgos Critical o High (o por debajo del threshold `--fail-on`). |
| `1` | Se detectaron hallazgos con severidad **Critical**. |
| `2` | Se detectaron hallazgos **High** pero ninguno Critical. |
| `3` | Error de ejecución o **escaneo incompleto**: directorio inaccesible, configuración inválida, archivos `.tf` que no se pudieron parsear, o reglas inválidas. |

TMAC falla cerrado: si un archivo no se puede parsear o una regla es inválida, el resultado podría omitir hallazgos, así que el comando termina con `3` aunque el reporte se genera igual (con un aviso de *escaneo incompleto*; en SARIF, `invocations[0].executionSuccessful = false`). Usa `--lenient` para solo advertir y usar el código según los hallazgos.

## Ignorar falsos positivos (`tmac:ignore`)

Suprime hallazgos específicos con comentarios en tus archivos `.tf`:

```hcl
# Ignorar todas las reglas para este recurso
# tmac:ignore
resource "aws_s3_bucket" "public_assets" {
  bucket = "public-assets-bucket"
}

# Ignorar solo una regla específica
# tmac:ignore[TMAC-AWS-S3-001]
resource "aws_s3_bucket" "another_bucket" {
  bucket = "another-bucket"
}

# Ignorar múltiples reglas específicas
# tmac:ignore[TMAC-AWS-S3-001]
# tmac:ignore[TMAC-AWS-S3-002]
resource "aws_s3_bucket" "yet_another" {
  bucket = "yet-another-bucket"
}
```

Las supresiones aplican solo al recurso exacto (archivo + tipo + nombre).

**Con `tmac plan`:** el `tfplan.json` no conserva comentarios, así que pasa el directorio con los `.tf` usando `--source-dir`. Las supresiones se asocian a los cambios del plan por tipo y nombre de recurso (`aws_s3_bucket.data`), sin importar el módulo:

```bash
tmac plan --plan-file plan.json --source-dir ./infra
```

## Estructura de reglas (`threats.yaml`)

Las reglas siguen el formato `TMAC-{CLOUD}-{SERVICE}-{NNN}`:

```yaml
version: "1.0"
rules:
  - id: TMAC-AWS-S3-001
    name: "S3 Bucket con Acceso Público (ACL)"
    resource_type: "aws_s3_bucket"
    check:
      attribute: "acl"
      condition: "in"
      values: ["public-read", "public-read-write"]
    severity: "Critical"
    stride: "Information Disclosure"
    description: "Descripción de la amenaza."
    mitigation: "Pasos de mitigación."
    references:
      - "https://docs.aws.amazon.com/..."
    tags: ["s3", "public-access"]
```

### Operadores de condición disponibles

| Operador | Descripción |
| :--- | :--- |
| `equals` | El atributo es igual al valor. |
| `not_equals` | El atributo no es igual al valor. |
| `in` | El atributo está en la lista de valores. |
| `not_in` | El atributo no está en la lista de valores. |
| `contains` | El atributo contiene el valor (string o lista). |
| `not_contains` | El atributo no contiene el valor. |
| `regex` | El atributo coincide con la expresión regular. |
| `exists` | El atributo existe en el recurso. |
| `not_exists` | El atributo no existe en el recurso. |

## Configuración (`.tmac.yaml`)

```yaml
scan:
  dir: ./infra                 # directorio por defecto si no se pasa --dir
  rules_dir: ./custom-rules    # reglas YAML adicionales
  exclude:
    - ".terraform"
    - "**/.terraform/**"
    - "modules/third-party/**"

report:
  format: html                 # html | json | md
  fail_on: high                # critical | high | medium | low | info
  severity: all                # all | critical | high | medium | low | info
```

Precedencia: **flag del CLI > `.tmac.yaml` > valor por defecto**. Por defecto se lee `./.tmac.yaml`; usa `--config` para otra ruta. Las claves desconocidas o los valores inválidos se ignoran con un aviso.

## Integración CI/CD

### GitHub Actions

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

### GitHub Actions — `tmac plan` (análisis de delta en PRs)

Bloquea el merge si el plan de Terraform introduce amenazas Critical:

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
        # Exit code 1 = Critical findings → bloquea el PR
        # Exit code 2 = High findings → bloquea el PR (ajustar --fail-on según política)
        # Exit code 0 = plan seguro → permite el merge
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

### GitLab CI

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

## Arquitectura

```
src/tmac/
├── cli.py          # Interfaz CLI (Click) — subcomandos `scan`, `cfn` y `plan`
├── scanner.py      # Scanner genérico: recibe el parser (Terraform o CloudFormation)
├── config.py       # Carga y validación de .tmac.yaml
├── models/         # Modelos Pydantic (Finding, ScanResult, ResourceModel)
├── parsers/        # TerraformParser (.tf/.tofu), CloudFormationParser y TfplanParser
├── delta/          # DeltaScanner, DeltaFinding, DeltaScanResult, PlannedChange
├── engine/         # RuleLoader, Matcher, Evaluator
├── reporters/      # HTMLReporter, MarkdownReporter, JSONReporter (SARIF)
├── rules/          # aws/threats.yaml (Terraform) y cfn/threats.yaml (CloudFormation)
└── templates/      # Plantillas Jinja2 para HTML y Markdown (scan + delta)
```

Para soportar un formato de IaC nuevo basta con un parser que herede de `BaseParser` (declara
`file_patterns`, `can_parse()` y `parse_strict()`) y su archivo de reglas; el `Scanner`, el motor
de reglas y los reportes se reutilizan sin cambios.

## Reglas incluidas (v1.0.0)

| ID | Servicio | Nombre | Severidad |
| :--- | :--- | :--- | :--- |
| TMAC-AWS-S3-001 | S3 | Bucket con ACL pública | Critical |
| TMAC-AWS-S3-002 | S3 | Bucket sin encriptación SSE | High |
| TMAC-AWS-S3-003 | S3 | Bucket sin logging de acceso | Medium |
| TMAC-AWS-IAM-001 | IAM | Comodín `*` en Resource de política | High |
| TMAC-AWS-IAM-002 | IAM | Usuario con política inline | Medium |
| TMAC-AWS-SG-001 | Security Groups | Puerto SSH (22) abierto al mundo | High |
| TMAC-AWS-SG-002 | Security Groups | Puerto RDP (3389) abierto al mundo | Critical |
| TMAC-AWS-RDS-001 | RDS | Base de datos sin encriptación | Medium |
| TMAC-AWS-RDS-002 | RDS | Instancia con acceso público | High |
| TMAC-AWS-CW-001 | CloudTrail | Trail deshabilitado o sin logging | High |

## Licencia

MIT — ver [LICENSE](LICENSE) para más detalles.
