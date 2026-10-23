# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — "Ixtla" — 2026-03-16

### Added

- **`src/tmac/delta/models.py`**: Nuevos modelos Pydantic `PlannedChange`, `ChangeAction`, `DeltaFinding` (extiende `Finding`) y `DeltaScanResult` (extiende `ScanResult`) para representar cambios planificados y hallazgos de delta.
- **`src/tmac/parsers/tfplan.py`**: Nuevo `TfplanParser` que implementa `BaseParser` y parsea el output de `terraform show -json` extrayendo `PlannedChange[]` con semántica correcta de `before`/`after` por acción (`create`, `update`, `delete`, `replace`, `no-op`).
- **`src/tmac/delta/scanner.py`**: Nuevo `DeltaScanner` que orquesta el pipeline de análisis de delta: `TfplanParser → RuleLoader → Evaluator → DeltaScanResult`. Reutiliza `RuleLoader` y `Evaluator` de v1.0.0 sin modificaciones. Lanza `DeltaScanError` ante archivos inválidos.
- **Subcomando `tmac plan`**: Nuevo subcomando CLI con flag obligatorio `--plan-file` y los mismos flags de salida que `tmac scan` (`--report`, `--output`, `--rules-dir`, `--fail-on`, `--quiet`, `--no-color`, `--verbose`). Exit codes: `0` (sin Critical/High), `1` (Critical), `2` (High sin Critical), `3` (error).
- **`src/tmac/templates/report_delta.html.j2`**: Template HTML con sección `delta-summary` que muestra `findings_introduced`, `findings_resolved` y `RiskDelta` neto, con badges por tipo de cambio (`NUEVO`, `MODIFICADO`, `ELIMINADO`).
- **`src/tmac/templates/report_delta.md.j2`**: Template Markdown con resumen ejecutivo y tabla de delta con columnas: Acción, Recurso, Regla, Severidad, STRIDE, Descripción del cambio.
- **`tests/unit/test_tfplan_parser.py`**: Tests unitarios del `TfplanParser` cubriendo parseo por acción, extracción de `address`, manejo de errores y property-based tests (Properties 1–5).
- **`tests/unit/test_delta_scanner.py`**: Tests unitarios del `DeltaScanner` cubriendo clasificación de amenazas introducidas/resueltas, conteos, `ignore_map` y property-based tests (Properties 7–10, 12–13).
- **`tests/integration/test_plan_cli.py`**: Tests de integración end-to-end con `CliRunner` para exit codes, formatos de reporte, flags y test de no-regresión de `tmac scan`.
- **`tests/property/test_delta_properties.py`**: 18 property-based tests con Hypothesis (`@settings(max_examples=100)`) cubriendo todas las propiedades de corrección del diseño.
- **`tests/fixtures/plans/`**: Fixtures `tfplan.json` para los cuatro escenarios: `create_with_threat.json`, `update_secure_to_insecure.json`, `update_insecure_to_secure.json`, `delete_with_threat.json`, `clean_plan.json`, `mixed_plan.json`.

### Changed

- **`src/tmac/reporters/html.py`**: `HTMLReporter.generate()` detecta `DeltaScanResult` via duck-typing y usa `report_delta.html.j2`; comportamiento v1.0.0 sin cambios para `ScanResult` normal.
- **`src/tmac/reporters/markdown.py`**: `MarkdownReporter.generate()` detecta `DeltaScanResult` via duck-typing y usa `report_delta.md.j2`; comportamiento v1.0.0 sin cambios para `ScanResult` normal.
- **`src/tmac/reporters/json_report.py`**: `JSONReporter.generate()` añade campo `properties` con `changeAction`, `valueBefore`, `valueAfter` en cada `result` SARIF cuando el finding es `DeltaFinding`; comportamiento v1.0.0 sin cambios para `Finding` normal.
- **`src/tmac/cli.py`**: Añadido subcomando `plan`; el subcomando `scan` existente no fue modificado (compatibilidad hacia atrás total).
- **`README.md`**: Documentado subcomando `tmac plan`, ejemplo de integración en GitHub Actions, y sección diferenciadora vs herramientas de análisis de estado completo.

---

## [1.0.0] — "Ixtla" — 2026-03-14

### Added

- **`src/tmac/scanner.py`**: Nuevo módulo orquestador `Scanner` con método `run_scan()` que encapsula el pipeline completo (parseo → carga de reglas → matching → estadísticas). Cumple SRP: el CLI solo maneja presentación y exit codes.
- **`ScanError`**: Excepción interna lanzada por `Scanner` ante directorios inaccesibles o configuración inválida; el CLI la captura y retorna exit code `3`.
- **`Finding.tags`**: Campo `List[str]` con valor por defecto lista vacía, propagado desde `ThreatRule.tags`.
- **`ScanResult.files_scanned`**: Campo `int` con el número de archivos `.tf` procesados en el escaneo.
- **`ScanResult.rules_loaded`**: Campo `int` con el número de reglas cargadas desde los archivos YAML.
- **`ResourceModel.to_dict()`**: Método de serialización que retorna `model_dump()` para facilitar debugging y reportes.
- **Flag `--exclude` / `-e`**: Acepta patrones glob repetibles para excluir archivos y directorios del escaneo.
- **Flag `--no-color`**: Deshabilita secuencias de escape ANSI en la salida de terminal.
- **Flag `--verbose` / `-v`**: Habilita logging de nivel DEBUG con detalles de archivos descubiertos, reglas cargadas y condiciones evaluadas.
- **Exit code `2`**: Retornado cuando se detectan hallazgos `High` pero ninguno `Critical`.
- **Exit code `3`**: Retornado ante errores de ejecución (directorio inaccesible, config inválida, error de parseo).
- **Validación de schema en `RuleLoader`**: Campos obligatorios `version` y `rules` en archivos YAML; campos obligatorios `id`, `name`, `resource_type`, `check`, `severity`, `stride` en cada regla.
- **Validación de schema en `load_config()`**: Claves permitidas `scan` y `report`; validación de tipos para `scan.exclude` y `report.format`; `ConfigError` ante YAML con sintaxis inválida.
- **JSONReporter con schema SARIF 2.1.0**: Output con campos `version`, `$schema`, `runs`, `tool.driver` (con `name`, `version`, `informationUri`, `rules`), y `results` (con `ruleId`, `level`, `message`, `locations`).
- **Mapeo de severidades SARIF**: `Critical`/`High` → `error`, `Medium` → `warning`, `Low` → `note`, `Info` → `none`.
- **`tests/conftest.py`**: Fixtures compartidos `sample_finding`, `sample_scan_result`, `sample_rule`, `sample_resource`, `fixtures_path`.
- **`tests/fixtures/`**: 22 archivos `.tf` positivos y negativos para las 10 reglas base, más `sg_multi_ingress.tf` y `tmac_ignore_examples.tf`.
- **`tests/unit/`**: Tests unitarios para todos los módulos: `test_models.py`, `test_reporters.py`, `test_rule_loader.py`, `test_evaluator.py`, `test_parser.py`, `test_config.py`, `test_scanner.py`.
- **`tests/integration/`**: Tests end-to-end con `CliRunner`: `test_cli.py` y `test_rules.py` (parametrizados por regla).
- **Property-based tests con Hypothesis**: 19 propiedades de corrección verificadas con `@settings(max_examples=100)`.
- **`CHANGELOG.md`**: Este archivo.
- **`CONTRIBUTING.md`**: Guía para contribuidores.

### Fixed

- **Typo `{% elief %}` → `{% elif %}`** en `src/tmac/templates/report.md.j2` que causaba error de renderizado en el reporte Markdown.
- **Iteración de `finding.stride` en template HTML**: Normalizado a lista antes de iterar badges STRIDE; si `stride` es string, se envuelve en lista.
- **`Evaluator._get_attribute_value`**: Ahora itera todos los elementos de una lista de bloques (ej. múltiples reglas `ingress` en un Security Group) en lugar de solo el primero, eliminando falsos negativos.
- **`RuleLoader`**: Reemplazados todos los `print()` por llamadas a `logging` estructurado.
- **`TerraformParser`**: Implementado `_prescan()` que extrae `line_map` e `ignore_map` en una sola lectura del archivo, asignando `line_number` correcto a cada `ResourceModel`.
- **`tmac:ignore[RULE-ID]`**: Soporte para exclusión por Rule ID específico, múltiples IDs consecutivos, y comentarios en la misma línea del bloque `resource`.
- **`Matcher`**: Propaga `tags` desde `ThreatRule` al `Finding` producido.
- **CLI**: Reemplazado el filtro hardcodeado de `.terraform` por el mecanismo `--exclude` configurable.

### Changed

- **`cli.py`**: Refactorizado para delegar el pipeline al `Scanner`; función `scan()` reducida a ≤30 líneas de código efectivo.
- **Exit codes**: Redefinidos según PRD FR-006: `0` (sin Critical/High), `1` (Critical), `2` (High sin Critical), `3` (error de ejecución). El exit code `2` ya no significa "advertencia genérica".
- **`RuleLoader`**: Usa `logging` en lugar de `print()` para todos los mensajes de advertencia y error.
- **`README.md`**: Actualizado con Python 3.10+ como requisito, exit codes correctos, schema de reglas con IDs `TMAC-AWS-{SERVICE}-{NNN}`, tabla completa de flags CLI, y ejemplos de CI/CD para GitHub Actions y GitLab CI.

---

## [Unreleased]

### Security

- Reporte HTML: escape automático (Jinja2 `autoescape`) de todos los valores — nombres de recurso, rutas y textos de reglas personalizadas se insertaban sin escapar (XSS). Los enlaces de `references` solo aceptan `http(s)` y usan `rel="noopener noreferrer"`.
- Dependencias fijadas con hash SHA-256 (`requirements*.txt` generados desde `requirements*.in` con `uv pip compile`), auditadas con `pip-audit`. `python-hcl2` limitado a `<5` (v5+ cambia el formato de salida y producía 0 hallazgos sin error).
- **Fail closed**: si un `.tf` no se puede parsear o una regla es inválida, `tmac scan` / `tmac plan` terminan con exit `3` (antes el archivo se trataba como vacío y el escaneo pasaba como limpio). El reporte se genera igual, con aviso de *escaneo incompleto* y `executionSuccessful: false` en SARIF.

### Added

- `--lenient` en `scan` y `plan`: solo advierte sobre escaneos incompletos.
- `tmac plan --source-dir DIR`: aplica los comentarios `tmac:ignore` de los `.tf` a los cambios del plan (global y por regla).
- `tmac plan --config`: aplica `report.format`, `report.fail_on` y `scan.rules_dir`.
- Validación de reglas al cargarlas: `severity`, `stride` y `condition` restringidos a valores válidos (sin distinguir mayúsculas), `regex` compilado y valores obligatorios salvo `exists`/`not_exists`.
- `Scanner(parser=...)`: escáner independiente del formato; los parsers declaran `file_patterns`, `can_parse()` y `parse_strict()`.
- CI en GitHub Actions (tests 3.11–3.13 + Windows, smoke test 3.10, `pip-audit` semanal, lint informativo) y Dependabot para Actions.

### Fixed

- `--config` se ignoraba; ahora se usa, y si se indica explícitamente y no existe → exit `3`.
- La sección `report` de `.tmac.yaml` (`format`, `fail_on`, `severity`) y `scan.dir` no se aplicaban. Precedencia: flag > `.tmac.yaml` > default. Valores inválidos de `fail_on`/`severity` se ignoran con aviso.
- `--dir` inexistente devolvía exit `2` (error de uso de click) en lugar del `3` documentado.
- `tmac:ignore` se aplicaba por nombre de recurso a todos los archivos y tipos (ignorar `aws_s3_bucket.main` silenciaba también `aws_security_group.main`).
- Una regla inválida en un archivo YAML descartaba todas las reglas siguientes del archivo.
- `value_before` / `value_after` de `DeltaFinding` salían vacíos para atributos anidados (`ingress.cidr_blocks`).
- La versión reportada (CLI y SARIF) seguía en `1.0.0`; ahora sale de `tmac.__version__`.
- `datetime.utcnow()` deprecado.

### Planned

- v1.2.0: Soporte para AWS CloudFormation templates.

---

[1.1.0]: https://github.com/tmac-security/tmac/releases/tag/v1.1.0
[1.0.0]: https://github.com/tmac-security/tmac/releases/tag/v1.0.0
[Unreleased]: https://github.com/tmac-security/tmac/compare/v1.1.0...HEAD
