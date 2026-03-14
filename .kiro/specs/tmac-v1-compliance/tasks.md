# Plan de Implementación: TMAC v1.0.0 "Ixtla" — Cumplimiento

## Overview

Implementación incremental del plan de cumplimiento TMAC v1.0.0. Las tareas siguen el orden de
dependencias del pipeline: modelos → parsers → engine → reporters → CLI/Scanner → tests → docs.
Cada tarea construye sobre las anteriores y termina con la integración completa del pipeline.

## Tasks

- [x] 1. Actualizar modelos de datos (Finding, ScanResult, ResourceModel)
  - [x] 1.1 Añadir campo `tags: List[str]` a `Finding` en `src/tmac/models/finding.py`
    - Añadir `tags: List[str] = Field(default_factory=list)` al modelo `Finding`
    - _Requirements: 9.1, 9.5_

  - [x] 1.2 Añadir campos `files_scanned` y `rules_loaded` a `ScanResult`
    - Añadir `files_scanned: int = 0` y `rules_loaded: int = 0` al modelo `ScanResult`
    - _Requirements: 9.2, 9.3_

  - [x] 1.3 Implementar método `to_dict()` en `ResourceModel` en `src/tmac/models/resource.py`
    - Añadir `def to_dict(self) -> Dict[str, Any]: return self.model_dump()`
    - _Requirements: 20.1, 20.3_

  - [x] 1.4 Escribir tests unitarios para los modelos actualizados en `tests/unit/test_models.py`
    - Test: `Finding` acepta `tags` y tiene valor por defecto lista vacía
    - Test: `ScanResult` acepta `files_scanned` y `rules_loaded`
    - Test: `ResourceModel.to_dict()` round-trip — serializar y reconstruir produce objeto equivalente
    - **Property 19: ResourceModel round-trip de serialización**
    - **Validates: Requirements 20.2, 20.3**
    - _Requirements: 9.1, 9.2, 9.3, 20.2_

- [x] 2. Corregir template Markdown y mejorar HTMLReporter
  - [x] 2.1 Corregir typo `{% elief %}` → `{% elif %}` en `src/tmac/templates/report.md.j2`
    - Localizar la línea con `elief` y reemplazar por `elif`
    - _Requirements: 8.3_

  - [x] 2.2 Corregir iteración de `stride` en el template HTML
    - En el template HTML, normalizar `finding.stride` a lista antes de iterar badges
    - Si `stride` es string, envolverlo en lista; si ya es lista, usarla directamente
    - _Requirements: 8.1, 8.2_

  - [x] 2.3 Escribir tests unitarios para reporters en `tests/unit/test_reporters.py`
    - Test: `HTMLReporter` genera HTML con `<!DOCTYPE html>` y `</html>`
    - Test: `HTMLReporter` renderiza badges STRIDE correctamente para stride como string y como lista
    - Test: `MarkdownReporter` genera tabla de resumen con findings
    - Test: `MarkdownReporter` renderiza emoji correcto por severidad (`🔴`, `🟠`, `🟡`, `🟢`, `🔵`)
    - Test: todos los reporters manejan `ScanResult` con findings vacíos sin error
    - **Property 15: HTMLReporter renderiza stride como lista de badges**
    - **Property 16: MarkdownReporter renderiza emoji correcto por severidad**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 3. Corregir RuleLoader — validación de schema y logging estructurado
  - [x] 3.1 Añadir validación de campos obligatorios en `src/tmac/engine/rule_loader.py`
    - Definir `REQUIRED_FILE_FIELDS = {"version", "rules"}` y `REQUIRED_RULE_FIELDS`
    - Implementar `_validate_file()` y `_validate_rule()` que emiten `logger.warning` y retornan bool
    - Reemplazar todos los `print()` por llamadas a `logging`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 3.2 Propagar `tags` desde `ThreatRule` al `Finding` en el Matcher
    - En `src/tmac/engine/matcher.py`, al construir `Finding`, asignar `tags=rule.tags`
    - _Requirements: 9.1_

  - [x] 3.3 Escribir tests unitarios para RuleLoader en `tests/unit/test_rule_loader.py`
    - Test: archivo YAML sin campo `version` emite warning y es omitido
    - Test: regla sin campo `id` emite warning y es omitida
    - Test: carga exitosa retorna lista de `ThreatRule` con todos los campos
    - Test: `tags` de la regla se propaga al `Finding` producido por el Matcher
    - **Property 11: RuleLoader es idempotente respecto al orden de archivos**
    - **Property 17: Finding.tags se propaga desde ThreatRule.tags**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 9.1**
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 9.1_

- [x] 4. Corregir Evaluator — soporte para listas de bloques múltiples
  - [x] 4.1 Modificar `_get_attribute_value` y `evaluate` en `src/tmac/engine/evaluator.py`
    - Cuando el valor resuelto es una lista de dicts, iterar todos los elementos
    - Retornar `True` si cualquier elemento satisface la condición (semántica `any`)
    - Añadir `logger.debug(...)` por cada condición evaluada cuando verbose está activo
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 4.2 Escribir tests unitarios para Evaluator y Matcher en `tests/unit/test_evaluator.py`
    - Tests parametrizados para cada operador: `equals`, `not_equals`, `in`, `not_in`, `contains`, `not_contains`, `regex`, `exists`, `not_exists`
    - Test: `and_check` compuesto evalúa correctamente (ambas condiciones verdaderas)
    - Test: SG con múltiples bloques `ingress` detecta regla cuando cualquier bloque la satisface
    - Test: Matcher omite recursos con `# tmac:ignore` global
    - Test: Matcher omite solo la regla especificada con `# tmac:ignore[RULE-ID]`
    - **Property 9: Evaluator detecta condición en cualquier elemento de lista de bloques**
    - **Property 10: Evaluator es correcto para todos los operadores**
    - **Validates: Requirements 5.1, 5.2, 5.4, 5.5, 13.1, 13.2, 13.3, 13.4, 13.5**
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5. Corregir TerraformParser — line numbers y tmac:ignore mejorado
  - [x] 5.1 Implementar `_prescan()` en `src/tmac/parsers/terraform.py`
    - Leer el archivo una sola vez y extraer `line_map: {(resource_type, resource_name): line_number}`
    - Extraer `ignore_map: {resource_name: ["*"] | ["RULE-ID-1", ...]}` desde comentarios `# tmac:ignore`
    - Soportar: ignore global (`# tmac:ignore`), por Rule ID (`# tmac:ignore[ID]`), en línea anterior y misma línea
    - Soportar múltiples `# tmac:ignore[RULE-ID]` consecutivos para excluir múltiples reglas
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 5.2 Integrar `line_map` e `ignore_map` en el método `parse()` del TerraformParser
    - Asignar `line_number` a cada `ResourceModel` desde `line_map`
    - Pasar `ignore_map` al Matcher para filtrar findings
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 5.3 Escribir tests unitarios para el Parser en `tests/unit/test_parser.py`
    - Test: archivo `.tf` válido con múltiples recursos retorna número correcto de `ResourceModel`
    - Test: archivo `.tf` con sintaxis inválida retorna lista vacía sin lanzar excepción
    - Test parametrizado: `# tmac:ignore` global, por Rule ID, en misma línea
    - Test: `line_number > 0` para todos los recursos de archivos con contenido real
    - **Property 5: TerraformParser captura line_number > 0 para todos los recursos**
    - **Property 6: tmac:ignore global suprime todos los findings del recurso**
    - **Property 7: tmac:ignore[RULE-ID] suprime solo la regla especificada**
    - **Property 8: Parsing es determinista (round-trip de extracción)**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 12.1, 12.2, 12.3, 12.4**
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 6. Checkpoint — Verificar correcciones de bugs
  - Asegurar que todos los tests unitarios de los pasos 1–5 pasan. Consultar al usuario si hay dudas.

- [x] 7. Implementar JSONReporter con schema SARIF completo
  - [x] 7.1 Reescribir `generate()` en `src/tmac/reporters/json_report.py`
    - Construir estructura SARIF 2.1.0 explícita con `version`, `$schema`, `runs`
    - Incluir `runs[0].tool.driver` con `name`, `version`, `informationUri`, `rules` (reglas únicas)
    - Incluir `runs[0].results` con un entry por `Finding`: `ruleId`, `level`, `message`, `locations`
    - Definir `SARIF_SEVERITY_MAP`: `critical/high → error`, `medium → warning`, `low → note`, `info → none`
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [x] 7.2 Escribir tests para JSONReporter en `tests/unit/test_reporters.py`
    - Test: output contiene campos SARIF de nivel superior `version`, `$schema`, `runs`
    - Test: `runs[0].tool.driver` contiene `name`, `version`, `informationUri`, `rules`
    - Test: cada resultado en `runs[0].results` contiene `ruleId`, `level`, `message`, `locations`
    - Test: round-trip — deserializar el JSON produce el mismo número de findings y `ruleId`
    - Test: mapeo de severidades TMAC → niveles SARIF es correcto para los 5 niveles
    - **Property 12: JSONReporter produce SARIF estructuralmente válido**
    - **Property 13: JSONReporter round-trip preserva findings**
    - **Property 14: JSONReporter mapea severidades a niveles SARIF correctamente**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 14.1, 14.2, 14.3, 14.4, 14.5**
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 8. Implementar validación de config en `src/tmac/config.py`
  - [x] 8.1 Añadir validación de claves permitidas y tipos en `load_config()`
    - Definir `ALLOWED_TOP_KEYS`, `ALLOWED_SCAN_KEYS`, `ALLOWED_REPORT_KEYS`, `ALLOWED_FORMATS`
    - Emitir `logger.warning` para claves desconocidas y continuar con claves válidas
    - Validar que `scan.exclude` es lista de strings; si no, emitir warning e ignorar
    - Validar que `report.format` es valor permitido; si no, emitir warning y usar default
    - Lanzar `ConfigError` (o `ScanError`) si el YAML tiene errores de sintaxis
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 8.2 Escribir tests unitarios para config en `tests/unit/test_config.py`
    - Test: `.tmac.yaml` con claves desconocidas emite warning y retorna solo claves válidas
    - Test: `scan.exclude` no-lista emite warning y es ignorado
    - Test: `report.format` inválido emite warning y usa default
    - Test: YAML con sintaxis inválida lanza excepción que resulta en exit code 3
    - **Property 18: Config valida claves desconocidas en .tmac.yaml**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 9. Crear `src/tmac/scanner.py` — módulo orquestador SRP
  - [x] 9.1 Implementar clase `Scanner` con método `run_scan()` en `src/tmac/scanner.py`
    - Definir `class ScanError(Exception)` en el mismo módulo
    - Implementar `run_scan(directory, rules_dir, exclude_patterns, min_severity, verbose) -> ScanResult`
    - Orquestar: `load_config()` → `TerraformParser.parse()` → `RuleLoader.load_rules()` → `Matcher.match()`
    - Poblar `ScanResult.files_scanned` y `ScanResult.rules_loaded` con valores correctos
    - Lanzar `ScanError` para directorio inaccesible, config inválida
    - Método principal ≤ 40 líneas
    - _Requirements: 1.1, 1.3, 9.2, 9.3, 9.4_

  - [x] 9.2 Escribir property test para Scanner en `tests/unit/test_scanner.py`
    - **Property 1: run_scan retorna ScanResult válido para cualquier directorio**
    - Test: `files_scanned` == número de archivos `.tf` encontrados
    - Test: `rules_loaded` == número de reglas cargadas
    - **Validates: Requirements 1.1, 9.2, 9.3, 9.4**
    - _Requirements: 1.1, 9.2, 9.3, 9.4_

- [x] 10. Refactorizar `src/tmac/cli.py` — SRP y nuevos flags
  - [x] 10.1 Añadir flags `--exclude`, `--no-color`, `--verbose` al comando `scan`
    - `--exclude` / `-e`: `multiple=True`, tipo `TEXT`, acepta glob patterns repetibles
    - `--no-color`: `is_flag=True`, deshabilita ANSI via `NO_COLOR` env var o `click.Context`
    - `--verbose` / `-v`: `is_flag=True`, configura `logging.basicConfig(level=DEBUG)`
    - Reemplazar filtro hardcodeado de `.terraform` por el mecanismo `--exclude`
    - _Requirements: 3.1, 3.3, 3.5, 3.7_

  - [x] 10.2 Delegar pipeline al Scanner y corregir exit codes en `cli.py`
    - La función `scan()` llama a `Scanner.run_scan()` y solo maneja presentación y exit code
    - Implementar exit codes: `0` (sin Critical/High), `1` (Critical), `2` (High sin Critical), `3` (ScanError)
    - Capturar `ScanError`, imprimir mensaje a stderr, llamar `sys.exit(3)`
    - Función `scan()` ≤ 30 líneas de código efectivo
    - _Requirements: 1.2, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 10.3 Escribir property tests para exit codes y flags en `tests/integration/test_cli.py`
    - **Property 2: Exit code respeta el threshold --fail-on**
    - **Property 3: --exclude omite archivos que coinciden con el patrón glob**
    - **Property 4: --no-color produce salida sin secuencias ANSI**
    - **Validates: Requirements 2.6, 3.2, 3.4**
    - _Requirements: 2.6, 3.2, 3.4_

- [x] 11. Crear infraestructura de tests — conftest, fixtures y estructura de directorios
  - [x] 11.1 Crear `tests/conftest.py` con fixtures compartidos
    - Implementar fixtures: `sample_finding`, `sample_scan_result`, `sample_rule`, `sample_resource`
    - Añadir fixture `fixtures_path` que retorna `Path("tests/fixtures")`
    - _Requirements: 11.1_

  - [x] 11.2 Crear archivos fixture `.tf` en `tests/fixtures/`
    - Crear los 22 archivos `.tf` positivos y negativos para las 10 reglas base:
      `s3_public_acl.tf`, `s3_private.tf`, `s3_no_encryption.tf`, `s3_encrypted.tf`,
      `s3_no_logging.tf`, `s3_with_logging.tf`, `iam_wildcard_resource.tf`, `iam_scoped_resource.tf`,
      `iam_inline_policy.tf`, `iam_managed_policy.tf`, `sg_ssh_open.tf`, `sg_ssh_restricted.tf`,
      `sg_rdp_open.tf`, `sg_rdp_restricted.tf`, `rds_no_encryption.tf`, `rds_encrypted.tf`,
      `rds_public.tf`, `rds_private.tf`, `cloudtrail_disabled.tf`, `cloudtrail_enabled.tf`
    - Crear `sg_multi_ingress.tf` (múltiples bloques ingress para test del Evaluator)
    - Crear `tmac_ignore_examples.tf` (patrones de tmac:ignore global, por ID, en misma línea)
    - _Requirements: 11.3, 15.4_

  - [x] 11.3 Crear estructura de directorios `tests/unit/` y `tests/integration/` con `__init__.py`
    - Crear `tests/unit/__init__.py` y `tests/integration/__init__.py`
    - _Requirements: 11.2_

- [x] 12. Implementar tests de integración CLI end-to-end
  - [x] 12.1 Escribir `tests/integration/test_cli.py` con CliRunner
    - Test: exit code `0` con directorio sin hallazgos
    - Test: exit code `1` con directorio que contiene hallazgos Critical
    - Test: exit code `2` con directorio que contiene hallazgos High pero no Critical
    - Test: exit code `3` con directorio inaccesible
    - Test: exit code `3` con `.tmac.yaml` con sintaxis inválida
    - Test: `--exclude *.tf` omite todos los archivos `.tf` del directorio
    - Test: `--report json` genera archivo JSON con campos SARIF `version` y `runs`
    - Test: `--no-color` produce salida sin secuencias ANSI (patrón `\x1b\[[\d;]*m`)
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7_

- [x] 13. Implementar tests parametrizados por regla
  - [x] 13.1 Escribir `tests/integration/test_rules.py` con parametrize
    - Implementar `RULE_FIXTURES` con los 20 pares (regla, fixture, expected) del diseño
    - Test parametrizado: fixture positivo produce exactamente un `Finding` con el `rule_id` correcto
    - Test parametrizado: fixture negativo no produce ningún `Finding`
    - Test: todos los `rule_id` en `threats.yaml` siguen el patrón `TMAC-{CLOUD}-{SERVICE}-{NNN}`
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [x] 14. Checkpoint — Suite de tests completa
  - Ejecutar `pytest --cov=tmac` y verificar cobertura ≥ 90% en `src/tmac/`.
  - Ejecutar `pytest tests/integration/` y verificar cobertura ≥ 80%.
  - Consultar al usuario si hay tests fallando o dudas antes de continuar.

- [x] 15. Actualizar documentación — README, CHANGELOG, CONTRIBUTING
  - [x] 15.1 Actualizar `README.md` con información correcta
    - Especificar Python 3.10+ como requisito mínimo
    - Documentar exit codes correctos: `0`, `1`, `2`, `3`
    - Mostrar schema correcto de `threats.yaml` con IDs `TMAC-AWS-{SERVICE}-{NNN}`
    - Incluir tabla completa de flags CLI con `--exclude`, `--no-color`, `--verbose`
    - Añadir ejemplos de CI/CD para GitHub Actions y GitLab CI
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

  - [x] 15.2 Crear `CHANGELOG.md` en la raíz del repositorio
    - Seguir formato Keep a Changelog con secciones `Added`, `Fixed`, `Changed`
    - Incluir entrada para `v1.0.0 "Ixtla"` con todos los cambios de este plan
    - _Requirements: 18.1, 18.2_

  - [x] 15.3 Crear `CONTRIBUTING.md` en la raíz del repositorio
    - Instrucciones para configurar entorno de desarrollo
    - Instrucciones para ejecutar los tests
    - Proceso para contribuir nuevas reglas con schema de `threats.yaml` y ejemplos
    - _Requirements: 18.3, 18.4_

- [x] 16. Sincronizar DOCS/threats.yaml con src/tmac/rules/aws/threats.yaml
  - [x] 16.1 Revisar y sincronizar `DOCS/threats.yaml` con las reglas reales
    - Asegurar que `DOCS/threats.yaml` contiene las mismas reglas que `src/tmac/rules/aws/threats.yaml`
    - Añadir nota indicando si es versión completa o subconjunto de referencia
    - _Requirements: 19.1, 19.2_

  - [x] 16.2 Actualizar `aws_stride_mapping` con IDs de reglas específicos
    - Referenciar IDs `TMAC-AWS-XXX-NNN` en la columna "Reglas TMAC Evaluadas"
    - Añadir sección que distingue reglas implementadas de servicios planificados
    - Corregir o documentar limitaciones de `TMAC-AWS-VPC-001`
    - _Requirements: 19.3, 19.4, 19.5_

- [x] 17. Checkpoint final — Verificar integración completa
  - Ejecutar suite completa de tests y verificar que todos pasan.
  - Verificar que el pipeline end-to-end funciona: `tmac scan --dir ./infra --exclude .terraform --verbose`.
  - Consultar al usuario si hay dudas antes de cerrar.

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints en las tareas 6, 14 y 17 aseguran validación incremental
- Los tests de propiedades usan Hypothesis con `@settings(max_examples=100)`
- Añadir `hypothesis = "^6.100.0"` a `[tool.poetry.group.dev.dependencies]` en `pyproject.toml`
