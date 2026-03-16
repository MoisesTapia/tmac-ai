# Diseño Técnico: TMAC v1.1.0 "Ixtla" — Análisis de Delta de Riesgo via tfplan.json

## Overview

Este documento describe el diseño técnico completo (High-Level + Low-Level) para TMAC v1.1.0 "Ixtla".
La nueva capacidad central es el **análisis de delta de riesgo**: en lugar de evaluar el estado
completo de los archivos `.tf`, TMAC v1.1.0 parsea el output de `terraform show -json` para detectar
amenazas STRIDE **exclusivamente en los recursos que van a ser creados, modificados o destruidos**
por el plan de ejecución.

El diferenciador clave respecto a herramientas que analizan el estado completo es que TMAC v1.1.0
responde a la pregunta: *"¿Qué riesgo nuevo introduce este PR?"*, no *"¿Qué riesgo existe en la
infraestructura completa?"*. Esto lo hace ideal para pipelines de CI/CD donde el objetivo es
bloquear solo los cambios que degradan la postura de seguridad.

El pipeline de v1.1.0 extiende el de v1.0.0 con un flujo paralelo orientado a planes:

```
CLI (tmac plan) → DeltaScanner → TfplanParser → RuleLoader → Evaluator/Matcher → DeltaReporter → salida
```

Los módulos `RuleLoader`, `Evaluator` y `Matcher` de v1.0.0 se reutilizan sin modificaciones.


## Architecture

### High-Level: Módulos nuevos y dependencias

```
src/tmac/
├── cli.py                          ← EXTEND: añade subcomando `tmac plan`
├── parsers/
│   └── tfplan.py                   ← NUEVO: TfplanParser (implementa BaseParser)
├── delta/
│   ├── __init__.py
│   ├── scanner.py                  ← NUEVO: DeltaScanner (orquestador del pipeline de delta)
│   └── models.py                   ← NUEVO: PlannedChange, ChangeAction, DeltaFinding, DeltaScanResult
└── reporters/
    ├── html.py                     ← EXTEND: sección de delta en el reporte HTML
    ├── markdown.py                 ← EXTEND: tabla de delta y resumen ejecutivo
    └── json_report.py              ← EXTEND: campos SARIF adicionales para DeltaFinding

tests/
├── unit/
│   ├── test_tfplan_parser.py       ← NUEVO: tests unitarios del TfplanParser
│   └── test_delta_scanner.py       ← NUEVO: tests unitarios del DeltaScanner
├── integration/
│   └── test_plan_cli.py            ← NUEVO: tests CLI end-to-end con CliRunner
├── property/
│   └── test_delta_properties.py    ← NUEVO: property-based tests con Hypothesis
└── fixtures/
    └── plans/                      ← NUEVO: tfplan.json de ejemplo por escenario
        ├── create_with_threat.json
        ├── update_secure_to_insecure.json
        ├── update_insecure_to_secure.json
        └── delete_with_threat.json
```

### Flujo de datos del subcomando `tmac plan`

```
tmac plan --plan-file plan.json --report md --fail-on critical
    │
    ▼
cli.py::plan()                          # parsea args, llama DeltaScanner, maneja exit code
    │
    ▼
delta/scanner.py::DeltaScanner.run()    # orquesta el pipeline de delta
    ├── TfplanParser.parse(plan_file)   # extrae PlannedChange[] del tfplan.json
    ├── RuleLoader.load_rules()         # reutiliza el loader existente sin cambios
    ├── Para cada PlannedChange:
    │   ├── Si acción == create:
    │   │   └── Evaluator.evaluate(rule.check, change.after) → DeltaFinding si match
    │   ├── Si acción == update:
    │   │   ├── Evaluator.evaluate(rule.check, change.after) → candidato introducido
    │   │   └── Evaluator.evaluate(rule.check, change.before) → si era True, es resuelto
    │   └── Si acción == delete:
    │       └── Evaluator.evaluate(rule.check, change.before) → si True, es resuelto
    └── DeltaScanResult(findings_introduced, findings_resolved, resources_*, ...)
    │
    ▼
DeltaReporter.generate(delta_result)    # HTML / MD / JSON con sección de delta
    │
    ▼
cli.py: exit code 0/1/2/3
```

### Relación con el pipeline de v1.0.0

```
                    ┌─────────────────────────────────────────┐
                    │           Módulos compartidos            │
                    │  RuleLoader  │  Evaluator  │  Matcher   │
                    └──────┬───────────────┬──────────────────┘
                           │               │
          ┌────────────────┘               └────────────────┐
          ▼                                                  ▼
  tmac scan (v1.0.0)                              tmac plan (v1.1.0)
  TerraformParser → ResourceModel[]       TfplanParser → PlannedChange[]
  Scanner.run_scan()                      DeltaScanner.run()
  ScanResult                              DeltaScanResult
```


## Components and Interfaces

### 1. `src/tmac/parsers/tfplan.py` — TfplanParser

Responsabilidad única: parsear un `tfplan.json` y retornar una lista de `PlannedChange`.
Implementa `BaseParser` para mantener consistencia con el ecosistema de parsers de TMAC,
aunque el tipo de retorno es `List[PlannedChange]` en lugar de `List[ResourceModel]`.

> **Nota de diseño**: `BaseParser.parse()` retorna `List[ResourceModel]`. `TfplanParser`
> implementa la interfaz pero también expone `parse_plan()` que retorna `List[PlannedChange]`
> directamente. El `DeltaScanner` usa `parse_plan()`. La implementación de `parse()` retorna
> los `ResourceModel` construidos desde los atributos `after` de cada `PlannedChange` para
> compatibilidad con la interfaz base.

```python
class TfplanParser(BaseParser):
    def parse(self, file_path: str) -> List[ResourceModel]:
        """Implementa BaseParser. Retorna ResourceModel desde atributos after."""

    def parse_plan(self, file_path: str) -> List[PlannedChange]:
        """Parsea tfplan.json y retorna PlannedChange[]. Método principal."""

    def _extract_resource_type_and_name(self, address: str) -> tuple[str, str]:
        """Extrae resource_type y resource_name del campo address.
        Ejemplo: 'aws_s3_bucket.data' → ('aws_s3_bucket', 'data')
        Ejemplo: 'module.vpc.aws_subnet.private' → ('aws_subnet', 'private')
        """

    def _map_action(self, actions: List[str]) -> Optional[ChangeAction]:
        """Mapea la lista de acciones del tfplan al enum ChangeAction.
        ['create'] → ChangeAction.create
        ['delete'] → ChangeAction.delete
        ['update'] → ChangeAction.update
        ['delete', 'create'] → ChangeAction.replace
        ['no-op'] → None (se omite)
        """
```

**Estructura del `tfplan.json` relevante**:

```json
{
  "format_version": "1.2",
  "resource_changes": [
    {
      "address": "aws_s3_bucket.data",
      "type": "aws_s3_bucket",
      "name": "data",
      "change": {
        "actions": ["update"],
        "before": { "acl": "private", "bucket": "my-bucket" },
        "after":  { "acl": "public-read", "bucket": "my-bucket" }
      }
    }
  ]
}
```

### 2. `src/tmac/delta/scanner.py` — DeltaScanner

Orquestador del pipeline de análisis de delta. Análogo al `Scanner` de v1.0.0 pero orientado
a `PlannedChange[]` en lugar de archivos `.tf`.

```python
class DeltaScanner:
    def __init__(self) -> None:
        self._rule_loader = RuleLoader()
        self._evaluator = Evaluator()

    def run(
        self,
        plan_file: str,
        rules_dir: Optional[str] = None,
        ignore_map: Optional[IgnoreMap] = None,
        min_severity: str = "all",
        verbose: bool = False,
    ) -> DeltaScanResult:
        """Ejecuta el pipeline completo de análisis de delta."""

    def _evaluate_change(
        self,
        change: PlannedChange,
        rules: List[ThreatRule],
    ) -> tuple[List[DeltaFinding], int]:
        """
        Evalúa un PlannedChange contra todas las reglas.
        Retorna (findings_introducidos, count_resueltos).
        """

    def _build_resource_model(
        self,
        change: PlannedChange,
        use_after: bool = True,
    ) -> ResourceModel:
        """Construye un ResourceModel temporal desde los atributos before o after."""
```

**Lógica de evaluación por acción**:

| Acción | Evalúa `after` | Evalúa `before` | Resultado |
|--------|---------------|-----------------|-----------|
| `create` | Sí | No | Findings en `after` → introducidos |
| `update` | Sí | Sí | En `after` y no en `before` → introducido; en `before` y no en `after` → resuelto |
| `delete` | No | Sí | Findings en `before` → resueltos |
| `replace` | Sí | Sí | Igual que `update` |

### 3. `src/tmac/delta/models.py` — Modelos de datos

```python
class ChangeAction(str, Enum):
    create  = "create"
    update  = "update"
    delete  = "delete"
    replace = "replace"

class PlannedChange(BaseModel):
    address:       str
    resource_type: str
    resource_name: str
    action:        ChangeAction
    before:        Optional[Dict[str, Any]] = None
    after:         Optional[Dict[str, Any]] = None

class DeltaFinding(Finding):
    change_action:     ChangeAction
    changed_attribute: str
    value_before:      Optional[Any] = None
    value_after:       Optional[Any] = None

class DeltaScanResult(ScanResult):
    findings_introduced: int = 0
    findings_resolved:   int = 0
    resources_created:   int = 0
    resources_updated:   int = 0
    resources_deleted:   int = 0
    plan_file:           str = ""
```

### 4. `src/tmac/cli.py` — Extensión con subcomando `tmac plan`

Se añade el subcomando `plan` al grupo `cli` existente. El subcomando `scan` no se modifica.

```python
@cli.command()
@click.option("--plan-file", "-p", required=True, type=click.Path(), help="Ruta al tfplan.json.")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), help="Formato de salida.")
@click.option("--output", "-o", type=click.Path(), help="Ruta del archivo de salida.")
@click.option("--rules-dir", type=click.Path(exists=True), help="Directorio de reglas adicionales.")
@click.option("--fail-on", type=click.Choice(["critical", "high", "medium", "low", "info"]))
@click.option("--quiet", "-q", is_flag=True)
@click.option("--no-color", "no_color", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
def plan(plan_file, report, output, rules_dir, fail_on, quiet, no_color, verbose) -> None:
    """Analiza un tfplan.json para detectar el delta de riesgo STRIDE."""
```

**Exit codes del subcomando `tmac plan`**:

| Código | Condición |
|--------|-----------|
| `0` | Sin `DeltaFinding` Critical o High |
| `1` | Al menos un `DeltaFinding` Critical |
| `2` | `DeltaFinding` High sin ninguno Critical |
| `3` | Error de ejecución (archivo no existe, JSON inválido, etc.) |

### 5. Extensiones de Reporters

Los tres reporters existentes se extienden para manejar `DeltaScanResult` y `DeltaFinding`.
La estrategia es duck-typing: si el `result` es instancia de `DeltaScanResult`, se renderiza
la sección de delta; si no, se comporta como en v1.0.0.

**HTMLReporter** — nueva sección de delta:
```html
<div class="delta-summary">
  <span class="badge badge-introduced">{{ findings_introduced }} introducidas</span>
  <span class="badge badge-resolved">{{ findings_resolved }} resueltas</span>
  <span class="badge badge-delta">RiskDelta: {{ findings_introduced - findings_resolved }}</span>
</div>
<!-- Badge por tipo de cambio en cada finding -->
<span class="badge badge-create">NUEVO</span>      <!-- change_action == create -->
<span class="badge badge-update">MODIFICADO</span> <!-- change_action == update -->
<span class="badge badge-delete">ELIMINADO</span>  <!-- change_action == delete -->
```

**MarkdownReporter** — resumen ejecutivo y tabla de delta:
```markdown
> Este plan introduce 3 amenazas nuevas y resuelve 1.

| Acción | Recurso | Regla | Severidad | STRIDE | Descripción del cambio |
|--------|---------|-------|-----------|--------|------------------------|
| NUEVO  | aws_s3_bucket.data | TMAC-AWS-S3-001 | Critical | Information Disclosure | acl: private → public-read |
```

**JSONReporter** — campos adicionales en SARIF `properties`:
```json
{
  "ruleId": "TMAC-AWS-S3-001",
  "level": "error",
  "properties": {
    "changeAction": "update",
    "valueBefore": "private",
    "valueAfter": "public-read"
  }
}
```


## Data Models

### PlannedChange

```python
class PlannedChange(BaseModel):
    address:       str                    # "aws_s3_bucket.data" o "module.vpc.aws_subnet.private"
    resource_type: str                    # "aws_s3_bucket"
    resource_name: str                    # "data"
    action:        ChangeAction           # create | update | delete | replace
    before:        Optional[Dict[str, Any]] = None   # None para create
    after:         Optional[Dict[str, Any]] = None   # None para delete
```

### ChangeAction

```python
class ChangeAction(str, Enum):
    create  = "create"   # Recurso nuevo, no existía antes
    update  = "update"   # Recurso existente con atributos modificados
    delete  = "delete"   # Recurso existente que será eliminado
    replace = "replace"  # Terraform destruye y recrea (delete + create atómico)
```

### DeltaFinding

Extiende `Finding` con el contexto del cambio que introdujo la amenaza:

```python
class DeltaFinding(Finding):
    change_action:     ChangeAction          # Acción que introdujo la amenaza
    changed_attribute: str                   # Atributo que cambió (ej: "acl")
    value_before:      Optional[Any] = None  # Valor anterior (None para create)
    value_after:       Optional[Any] = None  # Valor nuevo (None para delete)
```

### DeltaScanResult

Extiende `ScanResult` con estadísticas de delta:

```python
class DeltaScanResult(ScanResult):
    findings_introduced: int = 0   # Total de DeltaFinding producidos
    findings_resolved:   int = 0   # Amenazas que el plan resuelve
    resources_created:   int = 0   # PlannedChange con acción create
    resources_updated:   int = 0   # PlannedChange con acción update o replace
    resources_deleted:   int = 0   # PlannedChange con acción delete
    plan_file:           str = ""  # Ruta al tfplan.json analizado
```

**Invariante**: `findings_introduced == len(findings)` siempre.

**RiskDelta** (calculado, no almacenado): `findings_introduced - findings_resolved`.
Un valor positivo indica degradación de la postura de seguridad; negativo indica mejora.

### Estructura del tfplan.json esperado

El parser soporta el formato generado por `terraform show -json <planfile>` (Terraform ≥ 0.13):

```json
{
  "format_version": "1.2",
  "resource_changes": [
    {
      "address": "aws_s3_bucket.data",
      "type": "aws_s3_bucket",
      "name": "data",
      "change": {
        "actions": ["update"],
        "before": { "acl": "private", "bucket": "my-bucket", "tags": {} },
        "after":  { "acl": "public-read", "bucket": "my-bucket", "tags": {} },
        "after_unknown": {}
      }
    }
  ]
}
```

Campos relevantes extraídos por el `TfplanParser`:
- `address`: nombre canónico del recurso
- `type` / `name`: tipo y nombre del recurso (también derivables de `address`)
- `change.actions`: lista de acciones → mapeada a `ChangeAction`
- `change.before`: estado anterior (puede ser `null` para recursos nuevos)
- `change.after`: estado planificado (puede ser `null` para recursos eliminados)

Campos ignorados: `provider_name`, `module_address`, `after_unknown`, `after_sensitive`,
`before_sensitive`, `replace_paths`.


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

---

### Property 1: Semántica before/after por acción del parser

*For any* `tfplan.json` válido, para cada `PlannedChange` retornado por el `TfplanParser`:
- Si `action == create`, entonces `before` debe ser `None` y `after` debe ser un dict no nulo.
- Si `action == delete`, entonces `before` debe ser un dict no nulo y `after` debe ser `None`.
- Si `action == update` o `action == replace`, entonces tanto `before` como `after` deben ser dicts no nulos.

**Validates: Requirements 1.3, 1.4, 1.5**

---

### Property 2: El parser omite recursos no-op

*For any* `tfplan.json` válido que contenga recursos con acción `no-op`, ninguno de esos recursos debe aparecer en la lista de `PlannedChange` retornada por el `TfplanParser`.

**Validates: Requirements 1.6**

---

### Property 3: El parser es determinista

*For any* `tfplan.json` válido, parsear el archivo dos veces consecutivas debe producir listas de `PlannedChange` idénticas (mismo número, mismos `address`, mismas acciones, mismos atributos).

**Validates: Requirements 1.10**

---

### Property 4: Round-trip del parser (serializar + parsear)

*For any* lista de `PlannedChange` producida por el `TfplanParser`, serializar la lista a JSON estructurado y parsear nuevamente debe producir una lista equivalente con todos los campos preservados (`address`, `resource_type`, `resource_name`, `action`, `before`, `after`).

**Validates: Requirements 1.11, 1.12**

---

### Property 5: El parser maneja JSON inválido sin lanzar excepciones

*For any* string que no sea JSON válido o cualquier ruta a un archivo inexistente, el `TfplanParser` debe retornar una lista vacía sin lanzar excepciones no controladas.

**Validates: Requirements 1.7, 1.8**

---

### Property 6: Round-trip de serialización de DeltaFinding

*For any* `DeltaFinding` con valores arbitrarios en sus campos, serializar con `model_dump()` y reconstruir con `DeltaFinding(**data)` debe producir un objeto equivalente con todos los campos preservados, incluyendo `change_action`, `changed_attribute`, `value_before` y `value_after`.

**Validates: Requirements 2.7**

---

### Property 7: Semántica de DeltaFinding por tipo de cambio

*For any* `PlannedChange` con acción `create` que viola una regla STRIDE, el `DeltaFinding` producido debe tener `change_action == ChangeAction.create` y `value_before == None`. Para `PlannedChange` con acción `update`, el `DeltaFinding` debe tener `change_action == ChangeAction.update`, `value_before` con el valor del atributo en `before`, y `value_after` con el valor del atributo en `after`.

**Validates: Requirements 2.5, 2.6**

---

### Property 8: DeltaScanner produce exactamente los DeltaFinding correctos para updates

*For any* `PlannedChange` con acción `update` donde los atributos `before` son seguros (no violan ninguna regla) y los atributos `after` son inseguros (violan N reglas), el `DeltaScanner` debe producir exactamente N `DeltaFinding` — uno por cada regla violada en `after` que no era violada en `before`.

**Validates: Requirements 3.2, 3.8**

---

### Property 9: DeltaScanner registra correctamente amenazas resueltas

*For any* `PlannedChange` con acción `update` donde los atributos `before` violan M reglas y los atributos `after` no las violan, `DeltaScanResult.findings_resolved` debe incrementarse en M. Para `PlannedChange` con acción `delete` donde `before` viola K reglas, `findings_resolved` debe incrementarse en K.

**Validates: Requirements 3.3, 3.4**

---

### Property 10: Invariantes de conteo del DeltaScanResult

*For any* lista de `PlannedChange`, el `DeltaScanResult` producido por el `DeltaScanner` debe satisfacer:
- `resources_created == count(changes where action == create)`
- `resources_updated == count(changes where action in [update, replace])`
- `resources_deleted == count(changes where action == delete)`
- `findings_introduced == len(findings)`

**Validates: Requirements 3.5, 3.6**

---

### Property 11: Exit codes del CLI `tmac plan`

*For any* `DeltaScanResult`, el exit code del CLI debe ser:
- `0` si `findings_introduced == 0` o si ningún finding tiene severidad Critical o High.
- `1` si existe al menos un `DeltaFinding` con severidad Critical.
- `2` si existe al menos un `DeltaFinding` con severidad High y ninguno Critical.
- `3` si el archivo `--plan-file` no existe o no es un `tfplan.json` válido.

**Validates: Requirements 4.4, 4.5, 4.6, 4.7**

---

### Property 12: Equivalencia de evaluación entre DeltaScanner y Scanner

*For any* regla en `threats.yaml` y cualquier conjunto de atributos, el resultado de evaluar la regla contra los atributos `after` de un `PlannedChange` debe ser idéntico al resultado de evaluar la misma regla contra un `ResourceModel` construido con esos mismos atributos.

**Validates: Requirements 6.6**

---

### Property 13: tmac:ignore suprime recursos del análisis de delta

*For any* `PlannedChange` cuyo `address` está en el `ignore_map` con ignore global (`["*"]`), el `DeltaScanner` no debe producir ningún `DeltaFinding` para ese recurso, independientemente de cuántas reglas apliquen.

**Validates: Requirements 6.5**

---

### Property 14: Invariante de consistencia del reporte

*For any* `DeltaScanResult`, el número de findings renderizados en cualquier formato de reporte (HTML, Markdown, JSON) debe ser igual a `DeltaScanResult.findings_introduced`.

**Validates: Requirements 5.7**

---

### Property 15: HTMLReporter renderiza sección de delta sin errores para cualquier DeltaScanResult

*For any* `DeltaScanResult`, incluyendo el caso donde `findings_introduced == 0`, el `HTMLReporter` debe generar HTML válido que contenga los valores correctos de `findings_introduced`, `findings_resolved` y el `RiskDelta` neto, sin lanzar excepciones de template.

**Validates: Requirements 5.1, 5.6**

---

### Property 16: MarkdownReporter genera tabla y resumen ejecutivo

*For any* `DeltaScanResult` con al menos un `DeltaFinding`, el Markdown generado debe contener una línea de resumen ejecutivo con los valores de `findings_introduced` y `findings_resolved`, y una tabla con las columnas: Acción, Recurso, Regla, Severidad, STRIDE, Descripción del cambio.

**Validates: Requirements 5.3, 5.4**

---

### Property 17: JSONReporter incluye campos de delta en SARIF properties

*For any* `DeltaFinding`, el JSON SARIF generado debe contener en el objeto `properties` del `result` correspondiente los campos `changeAction`, `valueBefore` y `valueAfter` con los valores correctos.

**Validates: Requirements 5.5**

---

### Property 18: No-regresión de `tmac scan`

*For any* directorio con archivos `.tf`, el resultado de `tmac scan` debe ser idéntico antes y después de añadir los módulos de v1.1.0 (`TfplanParser`, `DeltaScanner`, `delta/models.py`).

**Validates: Requirements 4.9**


## Error Handling

### Clase de excepción interna

```python
# src/tmac/delta/scanner.py
class DeltaScanError(Exception):
    """Raised when the delta scan pipeline cannot proceed."""
    pass
```

El `DeltaScanner.run()` lanza `DeltaScanError` en casos como:
- Archivo `plan_file` no accesible (`PermissionError`, `FileNotFoundError`)
- Contenido del archivo no es JSON válido
- JSON válido pero sin el campo `resource_changes`

El `cli.py::plan()` captura `DeltaScanError`, imprime el mensaje a `stderr`, y llama `sys.exit(3)`.

### Exit codes

| Código | Condición | Implementación |
|--------|-----------|----------------|
| `0` | Sin `DeltaFinding` Critical o High | `sys.exit(0)` en `cli.py` |
| `1` | Al menos un `DeltaFinding` Critical | `sys.exit(1)` en `cli.py` |
| `2` | `DeltaFinding` High sin ninguno Critical | `sys.exit(2)` en `cli.py` |
| `3` | Error de ejecución (archivo inválido, JSON malformado) | `sys.exit(3)` tras capturar `DeltaScanError` |

### Degradación graceful

- **Campo `resource_changes` ausente**: retorna lista vacía + `logger.warning()`. No es error fatal.
- **Recurso con `change.before` o `change.after` igual a `null`**: el parser lo mapea a `None` en el modelo. El `DeltaScanner` maneja `None` explícitamente según la acción.
- **Acción desconocida en `change.actions`**: el parser omite el recurso y emite `logger.warning()`.
- **Atributo `after_unknown` con valores `true`**: los atributos con valor desconocido en el plan se ignoran durante la evaluación (el `Evaluator` retorna `False` para atributos `None`).
- **Módulos de Terraform** (`address` con prefijo `module.`): el parser extrae el tipo y nombre del último segmento del `address`. Ejemplo: `module.vpc.aws_subnet.private` → `resource_type=aws_subnet`, `resource_name=private`.

### Logging

```python
# Nivel DEBUG (--verbose): número de cambios parseados, recursos por acción, reglas evaluadas
logger.debug("Parsed %d planned changes from %s", len(changes), plan_file)
logger.debug("Actions breakdown: create=%d, update=%d, delete=%d", ...)
logger.debug("Evaluating %d rules against %s (%s)", len(rules), change.address, change.action)

# Nivel WARNING: condiciones de degradación graceful
logger.warning("No 'resource_changes' field in %s — returning empty result", plan_file)
logger.warning("Unknown action %s for resource %s — skipping", actions, address)
logger.warning("Failed to parse plan file %s: %s", plan_file, error)
```


## Testing Strategy

### Enfoque dual: unit tests + property-based tests

Los tests unitarios cubren ejemplos concretos, casos borde y condiciones de error.
Los tests de propiedades verifican invariantes universales con inputs generados aleatoriamente.
Ambos son complementarios y necesarios para cobertura completa.

La librería de property-based testing es **[Hypothesis](https://hypothesis.readthedocs.io/)** (estándar de facto para Python). Cada test de propiedad ejecuta mínimo 100 iteraciones (`@settings(max_examples=100)`). Cada test debe incluir un comentario con el tag de referencia al diseño:

```
# Feature: tmac-v1-1-tfplan-delta, Property N: <texto de la propiedad>
```

### Estructura de tests

```
tests/
├── unit/
│   ├── test_tfplan_parser.py       # TfplanParser: parseo por acción, address, errores
│   └── test_delta_scanner.py       # DeltaScanner: introduced/resolved, conteos, ignore_map
├── integration/
│   └── test_plan_cli.py            # CLI end-to-end: exit codes, formatos de reporte
├── property/
│   └── test_delta_properties.py    # Hypothesis: todas las propiedades del diseño
└── fixtures/
    └── plans/
        ├── create_with_threat.json          # S3 con acl=public-read (create)
        ├── update_secure_to_insecure.json   # S3 acl: private → public-read (update)
        ├── update_insecure_to_secure.json   # S3 acl: public-read → private (update)
        └── delete_with_threat.json          # S3 con acl=public-read (delete)
```

### Tests unitarios — `test_tfplan_parser.py`

```python
def test_parse_create_action():
    """PlannedChange con create tiene before=None y after poblado."""

def test_parse_delete_action():
    """PlannedChange con delete tiene before poblado y after=None."""

def test_parse_update_action():
    """PlannedChange con update tiene before y after ambos poblados."""

def test_noop_resources_omitted():
    """Recursos con acción no-op no aparecen en el resultado."""

def test_invalid_json_returns_empty():
    """JSON inválido retorna lista vacía sin excepción."""

def test_missing_resource_changes_returns_empty():
    """JSON sin campo resource_changes retorna lista vacía."""

def test_address_parsing_simple():
    """'aws_s3_bucket.data' → resource_type='aws_s3_bucket', resource_name='data'."""

def test_address_parsing_module():
    """'module.vpc.aws_subnet.private' → resource_type='aws_subnet', resource_name='private'."""
```

### Tests unitarios — `test_delta_scanner.py`

```python
def test_create_produces_delta_finding():
    """PlannedChange create con amenaza produce DeltaFinding con change_action=create."""

def test_update_secure_to_insecure_produces_finding():
    """PlannedChange update de seguro a inseguro produce exactamente un DeltaFinding."""

def test_update_insecure_to_secure_increments_resolved():
    """PlannedChange update de inseguro a seguro incrementa findings_resolved."""

def test_delete_with_threat_increments_resolved():
    """PlannedChange delete con amenaza en before incrementa findings_resolved."""

def test_resource_counts_correct():
    """resources_created, resources_updated, resources_deleted son correctos."""

def test_findings_introduced_equals_len_findings():
    """findings_introduced == len(result.findings) siempre."""

def test_ignore_map_suppresses_resource():
    """Recurso en ignore_map con '*' no produce DeltaFinding."""

def test_clean_plan_returns_zero_findings():
    """Plan sin amenazas retorna findings_introduced=0 y lista vacía."""
```

### Tests de integración — `test_plan_cli.py`

```python
def test_exit_code_0_clean_plan(tmp_path):
    """Plan sin amenazas → exit code 0."""

def test_exit_code_1_critical_finding(fixtures_plans):
    """Plan con amenaza Critical → exit code 1."""

def test_exit_code_2_high_finding(fixtures_plans):
    """Plan con amenaza High sin Critical → exit code 2."""

def test_exit_code_3_invalid_file():
    """Archivo inexistente → exit code 3."""

def test_markdown_report_generated(fixtures_plans, tmp_path):
    """tmac plan --report md genera archivo con tabla de delta."""

def test_json_report_sarif_fields(fixtures_plans, tmp_path):
    """tmac plan --report json genera SARIF con changeAction en properties."""

def test_scan_command_unaffected(fixtures_dir):
    """tmac scan produce los mismos resultados que antes de v1.1.0."""
```

### Property-based tests — `test_delta_properties.py`

```python
from hypothesis import given, settings, strategies as st

# Feature: tmac-v1-1-tfplan-delta, Property 3: El parser es determinista
@settings(max_examples=100)
@given(st.lists(planned_change_strategy(), min_size=0, max_size=10))
def test_parser_deterministic(planned_changes):
    """Parsear el mismo tfplan.json dos veces produce resultados idénticos."""
    ...

# Feature: tmac-v1-1-tfplan-delta, Property 4: Round-trip del parser
@settings(max_examples=100)
@given(st.lists(planned_change_strategy(), min_size=1, max_size=10))
def test_parser_round_trip(planned_changes):
    """Serializar PlannedChange[] a JSON y re-parsear produce lista equivalente."""
    ...

# Feature: tmac-v1-1-tfplan-delta, Property 6: Round-trip de serialización de DeltaFinding
@settings(max_examples=100)
@given(delta_finding_strategy())
def test_delta_finding_round_trip(delta_finding):
    """model_dump() + DeltaFinding(**data) preserva todos los campos."""
    ...

# Feature: tmac-v1-1-tfplan-delta, Property 10: Invariantes de conteo del DeltaScanResult
@settings(max_examples=100)
@given(st.lists(planned_change_strategy(), min_size=0, max_size=20))
def test_delta_scan_result_count_invariants(planned_changes):
    """resources_created/updated/deleted y findings_introduced == len(findings)."""
    ...

# Feature: tmac-v1-1-tfplan-delta, Property 12: Equivalencia de evaluación
@settings(max_examples=100)
@given(attributes_strategy(), rule_strategy())
def test_evaluation_equivalence(attributes, rule):
    """Evaluar regla contra after de PlannedChange == evaluar contra ResourceModel con mismos attrs."""
    ...

# Feature: tmac-v1-1-tfplan-delta, Property 18: No-regresión de tmac scan
@settings(max_examples=50)
@given(tf_directory_strategy())
def test_scan_no_regression(tf_dir):
    """tmac scan produce resultados idénticos antes y después de añadir módulos v1.1.0."""
    ...
```

### Estrategias Hypothesis para los modelos de delta

```python
# tests/property/strategies.py
from hypothesis import strategies as st
from tmac.delta.models import PlannedChange, ChangeAction, DeltaFinding

def planned_change_strategy():
    return st.builds(
        PlannedChange,
        address=st.from_regex(r'[a-z_]+\.[a-z_]+', fullmatch=True),
        resource_type=st.sampled_from(["aws_s3_bucket", "aws_security_group", "aws_iam_role"]),
        resource_name=st.from_regex(r'[a-z_]+', fullmatch=True),
        action=st.sampled_from(list(ChangeAction)),
        before=st.one_of(st.none(), st.fixed_dictionaries({"acl": st.text()})),
        after=st.one_of(st.none(), st.fixed_dictionaries({"acl": st.text()})),
    )

def delta_finding_strategy():
    return st.builds(
        DeltaFinding,
        rule_id=st.text(min_size=1),
        rule_name=st.text(min_size=1),
        severity=st.sampled_from(["Critical", "High", "Medium", "Low", "Info"]),
        stride=st.text(min_size=1),
        resource_type=st.text(min_size=1),
        resource_name=st.text(min_size=1),
        file_path=st.text(min_size=1),
        line_number=st.integers(min_value=0),
        matched_attribute=st.text(min_size=1),
        description=st.text(),
        mitigation=st.text(),
        change_action=st.sampled_from(list(ChangeAction)),
        changed_attribute=st.text(min_size=1),
        value_before=st.one_of(st.none(), st.text()),
        value_after=st.one_of(st.none(), st.text()),
    )
```

### Cobertura objetivo

| Nivel | Target | Herramienta |
|-------|--------|-------------|
| Unit (src/tmac/delta/, src/tmac/parsers/tfplan.py) | ≥ 90% | `pytest --cov=tmac` |
| Integration (CLI→DeltaScanner→Reporter) | ≥ 80% | `pytest tests/integration/` |
| Property-based (18 propiedades del diseño) | 100% de propiedades testables | Hypothesis |
| No-regresión (tmac scan) | 100% | test_plan_cli.py |

Dependencia adicional en `pyproject.toml` (ya presente desde v1.0.0):

```toml
[tool.poetry.group.dev.dependencies]
hypothesis = "^6.100.0"
```
