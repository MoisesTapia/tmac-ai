# TMAC (Threat Modeling as Code)

TMAC es una herramienta de análisis estático de seguridad para Infraestructura como Código (IaC).
Automatiza el modelado de amenazas identificando vulnerabilidades en código Terraform antes del despliegue,
usando el framework STRIDE.

## Características principales (v1.0.0 "Ixtla")

- **Análisis de Terraform:** Escaneo automático de archivos `.tf`.
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

### Opciones del CLI (`tmac scan`)

| Opción | Abreviación | Descripción | Por defecto |
| :--- | :--- | :--- | :--- |
| `--dir` | `-d` | Directorio a escanear con archivos `.tf`. | `.` |
| `--report` | `-r` | Formato del reporte: `html`, `json`, `md`. | `html` |
| `--output` | `-o` | Ruta del archivo de reporte. | `tmac-report.[fmt]` |
| `--rules-dir` | | Directorio de reglas YAML adicionales. | (reglas internas) |
| `--config` | | Ruta al archivo de configuración. | `.tmac.yaml` |
| `--fail-on` | | Severidad mínima para exit code 1. | `critical` |
| `--severity` | | Severidad mínima a incluir en el reporte. | `all` |
| `--exclude` | `-e` | Patrón glob a excluir (repetible). | — |
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

## Códigos de salida (Exit Codes)

| Código | Condición |
| :--- | :--- |
| `0` | Escaneo completado sin hallazgos Critical o High (o por debajo del threshold `--fail-on`). |
| `1` | Se detectaron hallazgos con severidad **Critical**. |
| `2` | Se detectaron hallazgos **High** pero ninguno Critical. |
| `3` | Error de ejecución: directorio inaccesible, configuración inválida, o error de parseo. |

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
  exclude:
    - ".terraform"
    - "**/.terraform/**"
    - "modules/third-party/**"

report:
  format: html
```

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
├── cli.py          # Interfaz CLI (Click) — parsea args, delega al Scanner
├── scanner.py      # Orquestador del pipeline de escaneo
├── config.py       # Carga y validación de .tmac.yaml
├── models/         # Modelos Pydantic (Finding, ScanResult, ResourceModel)
├── parsers/        # TerraformParser — extrae ResourceModel de archivos .tf
├── engine/         # RuleLoader, Matcher, Evaluator
├── reporters/      # HTMLReporter, MarkdownReporter, JSONReporter (SARIF)
└── templates/      # Plantillas Jinja2 para HTML y Markdown
```

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
