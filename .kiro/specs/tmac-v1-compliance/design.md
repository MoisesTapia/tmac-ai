# Diseño Técnico: TMAC v1.0.0 "Ixtla" — Plan de Cumplimiento

## Overview

Este documento describe el diseño técnico completo (High-Level + Low-Level) para llevar TMAC al
cumplimiento total del PRD v1.0.0 "Ixtla". La base de código ya es funcional; los cambios son
correcciones de bugs, features faltantes, refactorizaciones de SRP, y la suite de tests.

El pipeline de TMAC sigue el flujo:

```
CLI (click) → Scanner (orquestador) → TerraformParser → RuleLoader → Matcher/Evaluator → Reporter → salida
```

Los cambios se agrupan en cuatro áreas: (1) corrección de bugs, (2) features faltantes del PRD,
(3) mejoras de robustez/schema, y (4) suite de tests y documentación.


## Architecture

### High-Level: Módulos afectados y nuevas dependencias

```
src/tmac/
├── cli.py                  ← REFACTOR: delega a Scanner, añade --exclude/--no-color/--verbose
├── scanner.py              ← NUEVO: orquestador SRP del pipeline
├── config.py               ← EXTEND: validación de schema .tmac.yaml
├── models/
│   ├── finding.py          ← EXTEND: tags en Finding, files_scanned/rules_loaded en ScanResult
│   └── resource.py         ← EXTEND: método to_dict()
├── parsers/
│   └── terraform.py        ← FIX: line numbers via regex pre-scan, tmac:ignore[RULE-ID], single open
├── engine/
│   ├── evaluator.py        ← FIX: iterar todos los elementos de listas, logging verbose
│   └── rule_loader.py      ← FIX: validación de schema YAML, logging estructurado
├── reporters/
│   └── json_report.py      ← FIX: schema SARIF completo
└── templates/
    └── report.md.j2        ← FIX: typo elief→elif

tests/
├── conftest.py             ← NUEVO: fixtures compartidos
├── unit/                   ← NUEVO: tests por componente
├── integration/            ← NUEVO: tests CLI end-to-end
└── fixtures/               ← NUEVO: archivos .tf positivos/negativos por regla
```

### Flujo de datos con los cambios

```
tmac scan --dir ./infra --exclude .terraform --verbose --no-color
    │
    ▼
cli.py::scan()                          # ≤30 líneas: parsea args, llama Scanner, maneja exit code
    │
    ▼
scanner.py::Scanner.run_scan()          # ≤40 líneas: orquesta el pipeline completo
    ├── config.py::load_config()        # valida schema .tmac.yaml
    ├── TerraformParser.parse()         # regex pre-scan → line numbers + ignores, single open
    ├── RuleLoader.load_rules()         # valida schema YAML, logging estructurado
    ├── Matcher.match()
    │       └── Evaluator.evaluate()   # itera TODOS los elementos de listas
    └── ScanResult(files_scanned, rules_loaded, ...)
    │
    ▼
Reporter.generate(result)              # JSONReporter → SARIF completo
    │
    ▼
cli.py: exit code 0/1/2/3
```


## Components and Interfaces

### 1. `src/tmac/scanner.py` — Nuevo módulo orquestador

Responsabilidad única: ejecutar el pipeline completo y retornar un `ScanResult`.
El CLI solo llama a este módulo; no contiene lógica de negocio.

```python
class Scanner:
    def run_scan(
        self,
        directory: str,
        rules_dir: Optional[str] = None,
        exclude_patterns: List[str] = [],
        min_severity: str = "all",
        verbose: bool = False,
    ) -> ScanResult:
        ...
```

### 2. `src/tmac/cli.py` — Refactorizado

Añade los flags faltantes y delega al Scanner. La función `scan()` queda en ≤30 líneas.

Nuevos flags:
- `--exclude` / `-e`: `multiple=True`, tipo `TEXT`, acepta glob patterns repetibles
- `--no-color`: `is_flag=True`, deshabilita ANSI via `click.Context` o variable de entorno
- `--verbose` / `-v`: `is_flag=True`, habilita logging DEBUG

Exit codes:
- `0`: sin hallazgos Critical/High (o por debajo del threshold `--fail-on`)
- `1`: hallazgos Critical (o al nivel de `--fail-on`)
- `2`: hallazgos High sin Critical
- `3`: error de ejecución (excepción no controlada, config inválida, directorio inaccesible)

### 3. `src/tmac/parsers/terraform.py` — Fixes

**Line numbers via regex pre-scan**: antes de llamar a `hcl2.load()`, se hace un pre-scan
con regex para mapear `(resource_type, resource_name) → line_number`. Esto evita abrir
el archivo dos veces: se lee el contenido una vez, se extrae el mapa de líneas y los ignores,
luego se parsea con `hcl2` desde el string ya leído.

```python
def _prescan(self, content: str) -> tuple[dict[tuple, int], dict[str, list[str]]]:
    """
    Returns:
        line_map: {(resource_type, resource_name): line_number}
        ignore_map: {resource_name: ["*"] | ["RULE-ID-1", "RULE-ID-2"]}
    """
```

**tmac:ignore mejorado**: el `ignore_map` distingue entre ignore global (`["*"]`) e ignore
por Rule ID (`["TMAC-AWS-S3-001"]`). El Matcher consulta este mapa al crear findings.

### 4. `src/tmac/engine/evaluator.py` — Fix lista de bloques

El método `_get_attribute_value` actualmente toma solo `current[0]` cuando encuentra una lista.
El fix itera todos los elementos y retorna `True` si cualquiera satisface la condición.

```python
def _get_attribute_value(self, attribute_path: str, attributes: dict) -> Any:
    # Cuando encuentra una lista de dicts, retorna la lista completa
    # El caller (_evaluate_condition) itera sobre ella

def evaluate(self, condition: CheckCondition, attributes: dict) -> bool:
    val = self._get_attribute_value(condition.attribute, attributes)
    # Si val es lista, evalúa cada elemento y retorna True si alguno coincide
    if isinstance(val, list) and all(isinstance(v, dict) for v in val):
        matched = any(self._evaluate_condition(condition.condition, condition.values, item) for item in val)
    else:
        matched = self._evaluate_condition(condition.condition, condition.values, val)
    ...
```

### 5. `src/tmac/engine/rule_loader.py` — Validación de schema

Añade validación explícita antes de construir `ThreatRule`. Usa `logging` en lugar de `print()`.

```python
REQUIRED_FILE_FIELDS = {"version", "rules"}
REQUIRED_RULE_FIELDS = {"id", "name", "resource_type", "check", "severity", "stride"}

def _validate_file(self, data: dict, file_path: Path) -> bool:
    missing = REQUIRED_FILE_FIELDS - set(data.keys())
    if missing:
        logger.warning("File %s missing required fields: %s — skipping", file_path, missing)
        return False
    return True

def _validate_rule(self, rule_data: dict, file_path: Path) -> bool:
    missing = REQUIRED_RULE_FIELDS - set(rule_data.keys())
    if missing:
        rule_id = rule_data.get("id", "<unknown>")
        logger.warning("Rule %s in %s missing fields: %s — skipping", rule_id, file_path, missing)
        return False
    return True
```

### 6. `src/tmac/reporters/json_report.py` — Schema SARIF completo

Reemplaza el `model_dump_json()` directo por construcción explícita del schema SARIF 2.1.0.

```python
SARIF_SEVERITY_MAP = {
    "critical": "error", "high": "error",
    "medium": "warning", "low": "note", "info": "none"
}

def generate(self, result: ScanResult) -> str:
    sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": result.metadata.tool_name,
                    "version": result.metadata.version,
                    "informationUri": "https://github.com/tmac-security/tmac",
                    "rules": [...]   # reglas únicas de los findings
                }
            },
            "results": [...]         # un entry por Finding
        }]
    }
    return json.dumps(sarif, indent=2)
```

### 7. `src/tmac/templates/report.md.j2` — Fix typo

Línea con `{% elief %}` → `{% elif %}`.

### 8. `src/tmac/models/finding.py` — Campos faltantes

```python
class Finding(BaseModel):
    ...
    tags: List[str] = Field(default_factory=list)   # NUEVO: propagado desde ThreatRule.tags

class ScanResult(BaseModel):
    ...
    files_scanned: int = 0    # NUEVO
    rules_loaded: int = 0     # NUEVO
```

### 9. `src/tmac/models/resource.py` — Método to_dict()

```python
class ResourceModel(BaseModel):
    ...
    def to_dict(self) -> dict:
        return self.model_dump()
```

### 10. `src/tmac/config.py` — Validación de schema

```python
ALLOWED_TOP_KEYS = {"scan", "report"}
ALLOWED_SCAN_KEYS = {"dir", "exclude", "rules_dir"}
ALLOWED_REPORT_KEYS = {"format", "fail_on", "severity"}
ALLOWED_FORMATS = {"html", "json", "md"}

def load_config(config_path: str = ".tmac.yaml") -> dict:
    # Si hay error de sintaxis YAML → raise ConfigError (exit code 3)
    # Si hay claves desconocidas → logger.warning + continuar
    # Si scan.exclude no es lista → logger.warning + ignorar
    # Si report.format no es válido → logger.warning + usar default
```


## Data Models

### Finding (actualizado)

```python
class Finding(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    stride: str                              # puede ser str o List[str]; el template HTML normaliza
    resource_type: str
    resource_name: str
    file_path: str
    line_number: int
    matched_attribute: str
    description: str
    mitigation: str
    references: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)    # NUEVO
```

### ScanResult (actualizado)

```python
class ScanResult(BaseModel):
    metadata: ScanMetadata
    statistics: ScanStatistics
    findings: List[Finding]
    files_scanned: int = 0     # NUEVO
    rules_loaded: int = 0      # NUEVO
```

### ResourceModel (actualizado)

```python
class ResourceModel(BaseModel):
    resource_type: str
    name: str
    attributes: Dict[str, Any]
    source_file: str
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
```

### IgnoreMap (interno al TerraformParser)

```python
# Tipo interno, no es un modelo Pydantic
IgnoreMap = Dict[str, List[str]]
# Ejemplo:
# {"my_bucket": ["*"]}                          → ignore global
# {"my_sg": ["TMAC-AWS-SG-001"]}               → ignore por rule ID
# {"my_sg": ["TMAC-AWS-SG-001", "TMAC-AWS-SG-002"]}  → múltiples rules
```

### SARIF Output Schema (JSONReporter)

```json
{
  "version": "2.1.0",
  "$schema": "https://raw.githubusercontent.com/.../sarif-schema-2.1.0.json",
  "runs": [{
    "tool": {
      "driver": {
        "name": "TMAC",
        "version": "1.0.0",
        "informationUri": "https://github.com/tmac-security/tmac",
        "rules": [
          {
            "id": "TMAC-AWS-S3-001",
            "name": "S3 Bucket con Acceso Público (ACL)",
            "shortDescription": { "text": "..." },
            "helpUri": "https://..."
          }
        ]
      }
    },
    "results": [
      {
        "ruleId": "TMAC-AWS-S3-001",
        "level": "error",
        "message": { "text": "..." },
        "locations": [{
          "physicalLocation": {
            "artifactLocation": { "uri": "path/to/file.tf" },
            "region": { "startLine": 10 }
          }
        }]
      }
    ]
  }]
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: run_scan retorna ScanResult válido para cualquier directorio

*For any* directorio válido con archivos `.tf`, llamar a `Scanner.run_scan()` debe retornar un `ScanResult` con `files_scanned` igual al número de archivos `.tf` encontrados y `rules_loaded` igual al número de reglas cargadas.

**Validates: Requirements 1.1, 9.2, 9.3, 9.4**

---

### Property 2: Exit code respeta el threshold --fail-on

*For any* nivel de severidad configurado como `--fail-on` y cualquier conjunto de findings, el CLI debe retornar exit code `1` si y solo si existe al menos un finding con severidad igual o superior al threshold.

**Validates: Requirements 2.6**

---

### Property 3: --exclude omite archivos que coinciden con el patrón glob

*For any* patrón glob y cualquier conjunto de archivos `.tf`, los archivos cuyos paths coincidan con el patrón no deben aparecer en los recursos del `ScanResult`.

**Validates: Requirements 3.2**

---

### Property 4: --no-color produce salida sin secuencias ANSI

*For any* ejecución del CLI con `--no-color`, la salida de stdout y stderr no debe contener secuencias de escape ANSI (patrón `\x1b\[[\d;]*m`).

**Validates: Requirements 3.4**

---

### Property 5: TerraformParser captura line_number > 0 para todos los recursos

*For any* archivo `.tf` válido con al menos un bloque `resource`, todos los `ResourceModel` retornados deben tener `line_number > 0`.

**Validates: Requirements 4.1**

---

### Property 6: tmac:ignore global suprime todos los findings del recurso

*For any* recurso precedido por `# tmac:ignore` (en la línea anterior o en la misma línea), el Matcher no debe producir ningún `Finding` para ese recurso, independientemente de cuántas reglas apliquen.

**Validates: Requirements 4.3, 4.5**

---

### Property 7: tmac:ignore[RULE-ID] suprime solo la regla especificada

*For any* recurso precedido por `# tmac:ignore[RULE-ID]`, el Matcher no debe producir `Finding` para esa regla específica, pero sí debe producir findings para otras reglas que apliquen al mismo recurso.

**Validates: Requirements 4.4, 4.6**

---

### Property 8: Parsing es determinista (round-trip de extracción)

*For any* archivo `.tf` válido, parsear el archivo dos veces consecutivas debe producir conjuntos de `ResourceModel` idénticos (mismo número, mismos tipos, nombres y atributos).

**Validates: Requirements 4.7**

---

### Property 9: Evaluator detecta condición en cualquier elemento de una lista de bloques

*For any* recurso con un atributo que es una lista de bloques (ej. múltiples `ingress`), si cualquier elemento de la lista satisface la condición de la regla, el Evaluator debe retornar `True`. Reordenar los elementos de la lista no debe cambiar el resultado.

**Validates: Requirements 5.1, 5.2, 5.5**

---

### Property 10: Evaluator es correcto para todos los operadores

*For any* combinación de operador (`equals`, `not_equals`, `in`, `not_in`, `contains`, `not_contains`, `regex`, `exists`, `not_exists`) y valor de atributo, el Evaluator debe retornar el resultado lógicamente correcto según la semántica del operador.

**Validates: Requirements 5.4**

---

### Property 11: RuleLoader es idempotente respecto al orden de archivos

*For any* conjunto de archivos YAML de reglas válidos, cargarlos en cualquier orden debe producir el mismo conjunto de `ThreatRule` (mismos IDs, mismas propiedades).

**Validates: Requirements 6.5**

---

### Property 12: JSONReporter produce SARIF estructuralmente válido

*For any* `ScanResult`, el JSON generado por `JSONReporter` debe contener los campos de nivel superior `version`, `$schema`, y `runs`, y cada elemento de `runs[0].results` debe contener `ruleId`, `level`, `message`, y `locations`.

**Validates: Requirements 7.1, 7.2, 7.3**

---

### Property 13: JSONReporter round-trip preserva findings

*For any* `ScanResult`, serializar con `JSONReporter.generate()` y parsear el JSON resultante debe producir el mismo número de findings y los mismos `ruleId` en el mismo orden.

**Validates: Requirements 7.4**

---

### Property 14: JSONReporter mapea severidades a niveles SARIF correctamente

*For any* `Finding` con severidad TMAC, el nivel SARIF en el output debe ser: `Critical`/`High` → `error`, `Medium` → `warning`, `Low` → `note`, `Info` → `none`.

**Validates: Requirements 7.5**

---

### Property 15: HTMLReporter renderiza stride como lista de badges

*For any* `Finding` donde `stride` es una cadena de texto o una lista, el HTML generado debe contener al menos un elemento con clase `badge-stride` por cada categoría STRIDE del finding.

**Validates: Requirements 8.1, 8.2**

---

### Property 16: MarkdownReporter renderiza emoji correcto por severidad

*For any* `Finding` con severidad `Critical`, `High`, `Medium`, `Low`, o `Info`, el Markdown generado debe contener el emoji correspondiente (`🔴`, `🟠`, `🟡`, `🟢`, `🔵`).

**Validates: Requirements 8.5**

---

### Property 17: Finding.tags se propaga desde ThreatRule.tags

*For any* `ThreatRule` con campo `tags` no vacío, el `Finding` producido por el Matcher debe tener el mismo valor en su campo `tags`.

**Validates: Requirements 9.1**

---

### Property 18: Config valida claves desconocidas en .tmac.yaml

*For any* archivo `.tmac.yaml` que contenga claves de nivel superior distintas de `scan` y `report`, `load_config()` debe emitir un warning y retornar solo las claves válidas.

**Validates: Requirements 10.1, 10.2**

---

### Property 19: ResourceModel round-trip de serialización

*For any* `ResourceModel` producido por el `TerraformParser`, llamar a `to_dict()` y reconstruir con `ResourceModel(**data)` debe producir un objeto equivalente con todos los campos (`resource_type`, `name`, `attributes`, `source_file`, `line_number`) preservados.

**Validates: Requirements 20.2, 20.3**


## Error Handling

### Exit codes

| Código | Condición | Implementación |
|--------|-----------|----------------|
| `0` | Sin hallazgos Critical/High (o bajo el threshold `--fail-on`) | `sys.exit(0)` en `cli.py` |
| `1` | Hallazgos Critical (o al nivel de `--fail-on`) | `sys.exit(1)` en `cli.py` |
| `2` | Hallazgos High sin Critical | `sys.exit(2)` en `cli.py` |
| `3` | Error de ejecución | `sys.exit(3)` en `cli.py` tras capturar `ScanError` |

### Clase de excepción interna

```python
# src/tmac/scanner.py
class ScanError(Exception):
    """Raised when the scan pipeline cannot proceed."""
    pass
```

El `Scanner.run_scan()` lanza `ScanError` en casos como:
- Directorio no accesible (`PermissionError`, `FileNotFoundError`)
- Config YAML con sintaxis inválida
- Ningún archivo `.tf` encontrado (opcional: warning, no error)

El `cli.py` captura `ScanError`, imprime el mensaje a `stderr`, y llama `sys.exit(3)`.

### Degradación graceful

- **Parse error en un archivo `.tf`**: el `TerraformParser` captura la excepción, emite
  `logger.warning(...)`, y retorna lista vacía para ese archivo. El scan continúa.
- **Regla YAML inválida**: el `RuleLoader` omite la regla, emite `logger.warning(...)`,
  y continúa cargando el resto.
- **Template Jinja2 error**: si el template falla, el reporter lanza excepción que el CLI
  captura como `ScanError` → exit code `3`.

### Logging

Se usa el módulo estándar `logging` en todos los módulos internos. El nivel se configura
en `cli.py` según el flag `--verbose`:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG if verbose else logging.WARNING,
    format="%(levelname)s: %(message)s"
)
```

Con `--no-color`, se evita usar `click.style()` o `click.echo()` con colores.


## Testing Strategy

### Enfoque dual: unit tests + property-based tests

Los tests unitarios cubren ejemplos concretos, casos borde y condiciones de error.
Los tests de propiedades verifican invariantes universales con inputs generados aleatoriamente.
Ambos son complementarios y necesarios para cobertura completa.

La librería de property-based testing elegida es **[Hypothesis](https://hypothesis.readthedocs.io/)**,
que es el estándar de facto para Python. Cada test de propiedad debe ejecutar mínimo 100 iteraciones
(configurado con `@settings(max_examples=100)`).

### Estructura de tests

```
tests/
├── conftest.py                    # fixtures compartidos
├── unit/
│   ├── test_parser.py             # TerraformParser
│   ├── test_evaluator.py          # Evaluator + Matcher
│   ├── test_rule_loader.py        # RuleLoader
│   ├── test_reporters.py          # HTML, MD, JSON reporters
│   ├── test_models.py             # Finding, ScanResult, ResourceModel
│   └── test_config.py             # load_config validación
├── integration/
│   ├── test_cli.py                # CLI end-to-end con CliRunner
│   └── test_rules.py              # tests parametrizados por regla
└── fixtures/
    ├── s3_public_acl.tf           # positivo TMAC-AWS-S3-001
    ├── s3_private.tf              # negativo TMAC-AWS-S3-001
    ├── s3_no_encryption.tf        # positivo TMAC-AWS-S3-002
    ├── s3_encrypted.tf            # negativo TMAC-AWS-S3-002
    ├── s3_no_logging.tf           # positivo TMAC-AWS-S3-003
    ├── s3_with_logging.tf         # negativo TMAC-AWS-S3-003
    ├── iam_wildcard_resource.tf   # positivo TMAC-AWS-IAM-001
    ├── iam_scoped_resource.tf     # negativo TMAC-AWS-IAM-001
    ├── iam_inline_policy.tf       # positivo TMAC-AWS-IAM-002
    ├── iam_managed_policy.tf      # negativo TMAC-AWS-IAM-002
    ├── sg_ssh_open.tf             # positivo TMAC-AWS-SG-001
    ├── sg_ssh_restricted.tf       # negativo TMAC-AWS-SG-001
    ├── sg_rdp_open.tf             # positivo TMAC-AWS-SG-002
    ├── sg_rdp_restricted.tf       # negativo TMAC-AWS-SG-002
    ├── rds_no_encryption.tf       # positivo TMAC-AWS-RDS-001
    ├── rds_encrypted.tf           # negativo TMAC-AWS-RDS-001
    ├── rds_public.tf              # positivo TMAC-AWS-RDS-002
    ├── rds_private.tf             # negativo TMAC-AWS-RDS-002
    ├── cloudtrail_disabled.tf     # positivo TMAC-AWS-CW-001
    ├── cloudtrail_enabled.tf      # negativo TMAC-AWS-CW-001
    ├── sg_multi_ingress.tf        # múltiples bloques ingress (test Evaluator)
    └── tmac_ignore_examples.tf    # varios patrones de tmac:ignore
```

### conftest.py — Fixtures compartidos

```python
# tests/conftest.py
import pytest
from tmac.models.finding import Finding, ScanResult, ScanMetadata, ScanStatistics
from tmac.models.rule import ThreatRule, CheckCondition
from tmac.models.resource import ResourceModel

@pytest.fixture
def sample_finding():
    return Finding(
        rule_id="TMAC-AWS-S3-001", rule_name="S3 Public ACL",
        severity="Critical", stride="Information Disclosure",
        resource_type="aws_s3_bucket", resource_name="test_bucket",
        file_path="test.tf", line_number=5,
        matched_attribute="acl", description="...", mitigation="...",
        tags=["s3", "public-access"]
    )

@pytest.fixture
def sample_scan_result(sample_finding):
    return ScanResult(
        metadata=ScanMetadata(scanned_directory="/tmp/test"),
        statistics=ScanStatistics(total_resources=1, total_findings=1, critical=1),
        findings=[sample_finding],
        files_scanned=1, rules_loaded=10
    )

@pytest.fixture
def sample_rule():
    return ThreatRule(
        id="TMAC-AWS-S3-001", name="S3 Public ACL",
        resource_type="aws_s3_bucket",
        check=CheckCondition(attribute="acl", condition="in", values=["public-read"]),
        severity="Critical", stride="Information Disclosure",
        description="...", mitigation="...", tags=["s3"]
    )

@pytest.fixture
def sample_resource():
    return ResourceModel(
        resource_type="aws_s3_bucket", name="test_bucket",
        attributes={"acl": "public-read"}, source_file="test.tf", line_number=5
    )
```

### Tests de propiedades con Hypothesis

Cada propiedad del diseño se implementa como un test de Hypothesis con tag de referencia:

```python
# Feature: tmac-v1-compliance, Property 8: Parsing es determinista (round-trip)
from hypothesis import given, settings, strategies as st

@settings(max_examples=100)
@given(st.text(min_size=1))
def test_parser_deterministic(tmp_path, tf_content):
    # Genera contenido .tf arbitrario, parsea dos veces, compara resultados
    ...

# Feature: tmac-v1-compliance, Property 9: Evaluator detecta condición en lista de bloques
@settings(max_examples=100)
@given(st.lists(st.integers(min_value=0, max_value=65535), min_size=1, max_size=10))
def test_evaluator_list_any_match(ports):
    # Genera SG con múltiples bloques ingress, verifica que detecta si alguno es 22
    ...
```

### Tests de integración CLI

```python
# tests/integration/test_cli.py
from click.testing import CliRunner
from tmac.cli import cli

def test_exit_code_0_clean_dir(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--dir", str(tmp_path)])
    assert result.exit_code == 0

def test_exit_code_1_critical_finding(fixtures_dir):
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--dir", str(fixtures_dir / "critical")])
    assert result.exit_code == 1

def test_exit_code_3_invalid_dir():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--dir", "/nonexistent/path/xyz"])
    assert result.exit_code == 3

def test_exclude_flag(tmp_path, fixtures_dir):
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--dir", str(tmp_path), "--exclude", "*.tf"])
    assert result.exit_code == 0  # nada escaneado

def test_sarif_output(tmp_path, fixtures_dir):
    import json
    runner = CliRunner()
    out = tmp_path / "out.json"
    runner.invoke(cli, ["scan", "--dir", str(fixtures_dir), "--report", "json", "--output", str(out)])
    data = json.loads(out.read_text())
    assert "version" in data
    assert "runs" in data
```

### Tests parametrizados por regla

```python
# tests/integration/test_rules.py
import pytest
from tmac.parsers.terraform import TerraformParser
from tmac.engine.rule_loader import RuleLoader
from tmac.engine.matcher import Matcher

RULE_FIXTURES = [
    ("TMAC-AWS-S3-001",  "s3_public_acl.tf",       True),
    ("TMAC-AWS-S3-001",  "s3_private.tf",           False),
    ("TMAC-AWS-S3-002",  "s3_no_encryption.tf",     True),
    ("TMAC-AWS-S3-002",  "s3_encrypted.tf",         False),
    ("TMAC-AWS-S3-003",  "s3_no_logging.tf",        True),
    ("TMAC-AWS-S3-003",  "s3_with_logging.tf",      False),
    ("TMAC-AWS-IAM-001", "iam_wildcard_resource.tf", True),
    ("TMAC-AWS-IAM-001", "iam_scoped_resource.tf",  False),
    ("TMAC-AWS-IAM-002", "iam_inline_policy.tf",    True),
    ("TMAC-AWS-IAM-002", "iam_managed_policy.tf",   False),
    ("TMAC-AWS-SG-001",  "sg_ssh_open.tf",          True),
    ("TMAC-AWS-SG-001",  "sg_ssh_restricted.tf",    False),
    ("TMAC-AWS-SG-002",  "sg_rdp_open.tf",          True),
    ("TMAC-AWS-SG-002",  "sg_rdp_restricted.tf",    False),
    ("TMAC-AWS-RDS-001", "rds_no_encryption.tf",    True),
    ("TMAC-AWS-RDS-001", "rds_encrypted.tf",        False),
    ("TMAC-AWS-RDS-002", "rds_public.tf",           True),
    ("TMAC-AWS-RDS-002", "rds_private.tf",          False),
    ("TMAC-AWS-CW-001",  "cloudtrail_disabled.tf",  True),
    ("TMAC-AWS-CW-001",  "cloudtrail_enabled.tf",   False),
]

@pytest.mark.parametrize("rule_id,fixture,expected", RULE_FIXTURES)
def test_rule_fixture(rule_id, fixture, expected, fixtures_path):
    parser = TerraformParser()
    loader = RuleLoader()
    matcher = Matcher()
    resources = parser.parse(str(fixtures_path / fixture))
    rules = [r for r in loader.load_rules() if r.id == rule_id]
    findings = matcher.match(resources, rules)
    rule_findings = [f for f in findings if f.rule_id == rule_id]
    assert bool(rule_findings) == expected
```

### Cobertura objetivo

| Nivel | Target | Herramienta |
|-------|--------|-------------|
| Unit (src/tmac/) | ≥ 90% | `pytest --cov=tmac` |
| Integration (CLI→Engine→Reporter) | ≥ 80% | `pytest tests/integration/` |
| Regresión (una regla = dos fixtures) | 100% de las 10 reglas base | parametrize |

Añadir `hypothesis` a `[tool.poetry.group.dev.dependencies]` en `pyproject.toml`:

```toml
[tool.poetry.group.dev.dependencies]
hypothesis = "^6.100.0"
```

