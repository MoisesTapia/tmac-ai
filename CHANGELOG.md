# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Planned

- v1.1.0: Análisis de `tfplan.json` para detectar amenazas en cambios antes de `terraform apply`.
- v1.2.0: Soporte para AWS CloudFormation templates.

---

[1.0.0]: https://github.com/tmac-security/tmac/releases/tag/v1.0.0
[Unreleased]: https://github.com/tmac-security/tmac/compare/v1.0.0...HEAD
