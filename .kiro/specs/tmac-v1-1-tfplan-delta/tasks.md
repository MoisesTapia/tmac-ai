# Plan de Implementación: TMAC v1.1.0 "Ixtla" — Análisis de Delta de Riesgo via tfplan.json

## Overview

Implementación incremental de TMAC v1.1.0. Las tareas siguen el orden de dependencias del pipeline:
modelos → parsers → engine (delta) → reporters → CLI → infraestructura de tests → tests unitarios →
tests de integración → property-based tests → no-regresión → documentación.
Cada tarea construye sobre las anteriores y termina con la integración completa del pipeline de delta.

## Tasks

- [x] 1. Crear módulo `src/tmac/delta/` con modelos de datos
  - [x] 1.1 Crear `src/tmac/delta/__init__.py` vacío
    - Crear el paquete Python para el módulo de delta
    - _Requirements: 2.1_

  - [x] 1.2 Implementar `ChangeAction` y `PlannedChange` en `src/tmac/delta/models.py`
    - Definir `class ChangeAction(str, Enum)` con valores: `create`, `update`, `delete`, `replace`
    - Definir `class PlannedChange(BaseModel)` con campos: `address` (str), `resource_type` (str), `resource_name` (str), `action` (ChangeAction), `before` (Optional[Dict[str, Any]]), `after` (Optional[Dict[str, Any]])`
    - Importar desde `pydantic`, `enum`, `typing`
    - _Requirements: 2.1, 2.2_

  - [x] 1.3 Implementar `DeltaFinding` en `src/tmac/delta/models.py`
    - Definir `class DeltaFinding(Finding)` extendiendo el modelo existente de `src/tmac/models/finding.py`
    - Añadir campos: `change_action` (ChangeAction), `changed_attribute` (str), `value_before` (Optional[Any] = None), `value_after` (Optional[Any] = None)
    - _Requirements: 2.3, 2.5, 2.6_

  - [x] 1.4 Implementar `DeltaScanResult` en `src/tmac/delta/models.py`
    - Definir `class DeltaScanResult(ScanResult)` extendiendo el modelo existente de `src/tmac/models/finding.py`
    - Añadir campos: `findings_introduced` (int = 0), `findings_resolved` (int = 0), `resources_created` (int = 0), `resources_updated` (int = 0), `resources_deleted` (int = 0), `plan_file` (str = "")
    - Documentar el invariante: `findings_introduced == len(findings)` siempre
    - _Requirements: 2.4_

  - [x] 1.5 Escribir tests unitarios para los modelos de delta en `tests/unit/test_delta_models.py`
    - Test: `PlannedChange` acepta todos los campos y los serializa correctamente con `model_dump()`
    - Test: `ChangeAction` tiene exactamente los valores `create`, `update`, `delete`, `replace`
    - Test: `DeltaFinding` hereda todos los campos de `Finding` y añade los campos de delta
    - Test: `DeltaScanResult` hereda todos los campos de `ScanResult` y añade los campos de delta
    - Test: `DeltaFinding` con `change_action=create` acepta `value_before=None`
    - Test: `DeltaFinding` con `change_action=update` acepta `value_before` y `value_after` poblados
    - **Property 6: Round-trip de serialización de DeltaFinding**
    - **Validates: Requirements 2.7**
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_


- [x] 2. Implementar `TfplanParser` en `src/tmac/parsers/tfplan.py`
  - [x] 2.1 Crear la clase `TfplanParser` que implementa `BaseParser`
    - Crear `src/tmac/parsers/tfplan.py` con `class TfplanParser(BaseParser)`
    - Implementar `parse(self, file_path: str) -> List[ResourceModel]` que retorna `ResourceModel` construidos desde los atributos `after` de cada `PlannedChange` (compatibilidad con `BaseParser`)
    - Implementar `parse_plan(self, file_path: str) -> List[PlannedChange]` como método principal usado por `DeltaScanner`
    - _Requirements: 1.1, 1.2_

  - [x] 2.2 Implementar `_extract_resource_type_and_name()` en `TfplanParser`
    - Extraer `resource_type` y `resource_name` del campo `address` del `resource_change`
    - Soportar formato simple: `'aws_s3_bucket.data'` → `('aws_s3_bucket', 'data')`
    - Soportar formato con módulo: `'module.vpc.aws_subnet.private'` → `('aws_subnet', 'private')` (últimos dos segmentos)
    - _Requirements: 1.9_

  - [x] 2.3 Implementar `_map_action()` en `TfplanParser`
    - Mapear la lista `change.actions` del tfplan al enum `ChangeAction`
    - `['create']` → `ChangeAction.create`
    - `['delete']` → `ChangeAction.delete`
    - `['update']` → `ChangeAction.update`
    - `['delete', 'create']` → `ChangeAction.replace`
    - `['no-op']` → `None` (recurso a omitir)
    - Acción desconocida → `None` + `logger.warning()`
    - _Requirements: 1.6_

  - [x] 2.4 Implementar lógica principal de `parse_plan()` con manejo de errores
    - Abrir y parsear el archivo JSON; si no existe o no es JSON válido, retornar `[]` + `logger.warning()`
    - Si el JSON no contiene el campo `resource_changes`, retornar `[]` + `logger.warning()`
    - Iterar `resource_changes`, omitir recursos con acción `no-op` o acción desconocida
    - Construir `PlannedChange` con `before=None` para `create`, `after=None` para `delete`, ambos poblados para `update`/`replace`
    - Emitir `logger.debug()` con el número de cambios parseados y el desglose por acción
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x] 2.5 Implementar `_prescan()` en `TfplanParser` para extraer `ignore_map`
    - Leer el campo `address` de cada `resource_change` para construir el `ignore_map`
    - Soportar el mecanismo `tmac:ignore` existente: si el `address` del recurso está en el `ignore_map`, el `DeltaScanner` lo omitirá
    - El `ignore_map` se construye desde los metadatos del plan (no desde comentarios HCL)
    - _Requirements: 6.5_

  - [x] 2.6 Escribir tests unitarios para `TfplanParser` en `tests/unit/test_tfplan_parser.py`
    - Test: `parse_plan()` con fixture `create_with_threat.json` retorna `PlannedChange` con `action=create`, `before=None`, `after` poblado
    - Test: `parse_plan()` con fixture `delete_with_threat.json` retorna `PlannedChange` con `action=delete`, `before` poblado, `after=None`
    - Test: `parse_plan()` con fixture `update_secure_to_insecure.json` retorna `PlannedChange` con `action=update`, `before` y `after` ambos poblados
    - Test: recursos con acción `no-op` no aparecen en el resultado
    - Test: JSON inválido retorna lista vacía sin lanzar excepción
    - Test: JSON sin campo `resource_changes` retorna lista vacía
    - Test: `address` simple `'aws_s3_bucket.data'` → `resource_type='aws_s3_bucket'`, `resource_name='data'`
    - Test: `address` con módulo `'module.vpc.aws_subnet.private'` → `resource_type='aws_subnet'`, `resource_name='private'`
    - Test: `parse()` (interfaz `BaseParser`) retorna `ResourceModel` construidos desde atributos `after`
    - **Property 1: Semántica before/after por acción del parser**
    - **Property 2: El parser omite recursos no-op**
    - **Property 3: El parser es determinista**
    - **Property 5: El parser maneja JSON inválido sin lanzar excepciones**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10**
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_


- [x] 3. Implementar `DeltaScanner` en `src/tmac/delta/scanner.py`
  - [x] 3.1 Crear la clase `DeltaScanError` y el esqueleto de `DeltaScanner`
    - Crear `src/tmac/delta/scanner.py`
    - Definir `class DeltaScanError(Exception)` en el mismo módulo
    - Definir `class DeltaScanner` con `__init__` que instancia `RuleLoader()` y `Evaluator()`
    - _Requirements: 3.1, 6.1, 6.2_

  - [x] 3.2 Implementar `_build_resource_model()` en `DeltaScanner`
    - Construir un `ResourceModel` temporal desde los atributos `before` o `after` de un `PlannedChange`
    - Parámetro `use_after: bool = True` para seleccionar qué atributos usar
    - Usar `change.address` como `source_file` y `0` como `line_number`
    - _Requirements: 6.4_

  - [x] 3.3 Implementar `_evaluate_change()` en `DeltaScanner`
    - Evaluar un `PlannedChange` contra todas las reglas según su acción:
      - `create`: evaluar `after` → findings en `after` son introducidos
      - `update`/`replace`: evaluar `after` y `before`; en `after` y no en `before` → introducido; en `before` y no en `after` → resuelto
      - `delete`: evaluar `before` → findings en `before` son resueltos
    - Retornar `(List[DeltaFinding], int)` donde el int es el conteo de amenazas resueltas
    - Para cada `DeltaFinding` producido, poblar `change_action`, `changed_attribute` (= `rule.check.attribute`), `value_before` y `value_after` desde los atributos del `PlannedChange`
    - Reutilizar `Evaluator.evaluate()` sin modificar su interfaz
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.8, 6.2, 6.3, 6.4_

  - [x] 3.4 Implementar `run()` en `DeltaScanner`
    - Orquestar el pipeline completo: `TfplanParser.parse_plan()` → `RuleLoader.load_rules()` → iterar `PlannedChange[]` con `_evaluate_change()` → construir `DeltaScanResult`
    - Lanzar `DeltaScanError` si el archivo no existe, no es JSON válido, o no tiene `resource_changes`
    - Poblar `resources_created`, `resources_updated` (include `replace`), `resources_deleted` con conteos por acción
    - Poblar `findings_introduced = len(findings)` y `findings_resolved` con el total acumulado
    - Soportar `ignore_map`: si el `address` del recurso está en el `ignore_map` con `["*"]`, omitir el recurso
    - Emitir `logger.debug()` con: número de cambios parseados, desglose por acción, reglas evaluadas por recurso
    - Método `run()` ≤ 50 líneas de código efectivo
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.1, 6.5_

  - [x] 3.5 Escribir tests unitarios para `DeltaScanner` en `tests/unit/test_delta_scanner.py`
    - Test: `PlannedChange` con `action=create` y atributo inseguro produce `DeltaFinding` con `change_action=create`
    - Test: `PlannedChange` con `action=update` de seguro a inseguro produce exactamente un `DeltaFinding`
    - Test: `PlannedChange` con `action=update` de inseguro a seguro incrementa `findings_resolved` y no produce `DeltaFinding`
    - Test: `PlannedChange` con `action=delete` con amenaza en `before` incrementa `findings_resolved`
    - Test: `resources_created`, `resources_updated`, `resources_deleted` son correctos para un plan mixto
    - Test: `findings_introduced == len(result.findings)` siempre
    - Test: recurso en `ignore_map` con `["*"]` no produce ningún `DeltaFinding`
    - Test: plan sin amenazas retorna `findings_introduced=0` y lista de findings vacía
    - Test: `DeltaScanError` se lanza para archivo inexistente
    - **Property 7: Semántica de DeltaFinding por tipo de cambio**
    - **Property 8: DeltaScanner produce exactamente los DeltaFinding correctos para updates**
    - **Property 9: DeltaScanner registra correctamente amenazas resueltas**
    - **Property 10: Invariantes de conteo del DeltaScanResult**
    - **Property 12: Equivalencia de evaluación entre DeltaScanner y Scanner**
    - **Property 13: tmac:ignore suprime recursos del análisis de delta**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 6.2, 6.3, 6.4, 6.5, 6.6**
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 4. Checkpoint — Verificar modelos, parser y scanner
  - Asegurar que todos los tests unitarios de los pasos 1–3 pasan sin errores.
  - Verificar que `DeltaScanner.run()` procesa correctamente los cuatro fixtures de planes.
  - Consultar al usuario si hay dudas antes de continuar con los reporters.


- [x] 5. Extender `HTMLReporter` con sección de delta
  - [x] 5.1 Crear template Jinja2 `src/tmac/templates/report_delta.html.j2`
    - Crear template HTML que extiende o incluye el template base `report.html.j2`
    - Añadir sección `<div class="delta-summary">` con badges para `findings_introduced`, `findings_resolved` y `RiskDelta` neto (`findings_introduced - findings_resolved`)
    - Añadir badge por tipo de cambio en cada finding: `NUEVO` (verde, `create`), `MODIFICADO` (amarillo, `update`/`replace`), `ELIMINADO` (gris, `delete`)
    - Manejar el caso `findings_introduced == 0` renderizando un estado de aprobación sin errores de template
    - _Requirements: 5.1, 5.2, 5.6_

  - [x] 5.2 Modificar `HTMLReporter.generate()` en `src/tmac/reporters/html.py`
    - Detectar si `result` es instancia de `DeltaScanResult` (duck-typing)
    - Si es `DeltaScanResult`, usar el template `report_delta.html.j2`; si no, usar `report.html.j2` (comportamiento v1.0.0 sin cambios)
    - Pasar al template las variables adicionales: `findings_introduced`, `findings_resolved`, `risk_delta`
    - _Requirements: 5.1, 5.2, 5.6_

  - [x] 5.3 Escribir tests unitarios para `HTMLReporter` con delta en `tests/unit/test_reporters.py`
    - Test: `HTMLReporter.generate()` con `DeltaScanResult` genera HTML con sección `delta-summary`
    - Test: HTML contiene badge `NUEVO` para `DeltaFinding` con `change_action=create`
    - Test: HTML contiene badge `MODIFICADO` para `DeltaFinding` con `change_action=update`
    - Test: HTML contiene badge `ELIMINADO` para `DeltaFinding` con `change_action=delete`
    - Test: `DeltaScanResult` con `findings_introduced=0` genera HTML válido sin errores de template
    - Test: `HTMLReporter.generate()` con `ScanResult` normal (no delta) sigue usando el template original
    - **Property 15: HTMLReporter renderiza sección de delta sin errores para cualquier DeltaScanResult**
    - **Validates: Requirements 5.1, 5.2, 5.6**
    - _Requirements: 5.1, 5.2, 5.6_

- [x] 6. Extender `MarkdownReporter` con tabla de delta y resumen ejecutivo
  - [x] 6.1 Crear template Jinja2 `src/tmac/templates/report_delta.md.j2`
    - Crear template Markdown para reportes de delta
    - Incluir línea de resumen ejecutivo al inicio: `> Este plan introduce N amenazas nuevas y resuelve M.`
    - Incluir tabla con columnas: `Acción | Recurso | Regla | Severidad | STRIDE | Descripción del cambio`
    - Cada fila de la tabla muestra la acción (`NUEVO`/`MODIFICADO`/`ELIMINADO`), el `address` del recurso, el `rule_id`, la severidad con emoji, el STRIDE y la descripción del cambio (`changed_attribute: value_before → value_after`)
    - _Requirements: 5.3, 5.4_

  - [x] 6.2 Modificar `MarkdownReporter.generate()` en `src/tmac/reporters/markdown.py`
    - Detectar si `result` es instancia de `DeltaScanResult`
    - Si es `DeltaScanResult`, usar el template `report_delta.md.j2`; si no, usar `report.md.j2`
    - _Requirements: 5.3, 5.4_

  - [x] 6.3 Escribir tests unitarios para `MarkdownReporter` con delta en `tests/unit/test_reporters.py`
    - Test: Markdown generado contiene la línea de resumen ejecutivo con los valores correctos de `findings_introduced` y `findings_resolved`
    - Test: Markdown contiene tabla con las columnas `Acción`, `Recurso`, `Regla`, `Severidad`, `STRIDE`, `Descripción del cambio`
    - Test: `DeltaScanResult` con `findings_introduced=0` genera Markdown válido con resumen ejecutivo correcto
    - Test: `MarkdownReporter.generate()` con `ScanResult` normal sigue usando el template original
    - **Property 16: MarkdownReporter genera tabla y resumen ejecutivo**
    - **Validates: Requirements 5.3, 5.4**
    - _Requirements: 5.3, 5.4_

- [x] 7. Extender `JSONReporter` con campos SARIF de delta
  - [x] 7.1 Modificar `JSONReporter.generate()` en `src/tmac/reporters/json_report.py`
    - Detectar si cada `finding` es instancia de `DeltaFinding`
    - Si es `DeltaFinding`, añadir al objeto `result` SARIF el campo `properties` con: `changeAction` (str), `valueBefore` (valor o `null`), `valueAfter` (valor o `null`)
    - Si no es `DeltaFinding`, el objeto `result` SARIF no incluye el campo `properties` (comportamiento v1.0.0 sin cambios)
    - _Requirements: 5.5_

  - [x] 7.2 Escribir tests unitarios para `JSONReporter` con delta en `tests/unit/test_reporters.py`
    - Test: JSON SARIF generado desde `DeltaScanResult` contiene `properties.changeAction` en cada `result`
    - Test: `properties.valueBefore` es `null` para `DeltaFinding` con `change_action=create`
    - Test: `properties.valueAfter` es `null` para `DeltaFinding` con `change_action=delete`
    - Test: `properties.valueBefore` y `properties.valueAfter` tienen los valores correctos para `change_action=update`
    - Test: `JSONReporter.generate()` con `ScanResult` normal no incluye `properties` en los resultados SARIF
    - **Property 17: JSONReporter incluye campos de delta en SARIF properties**
    - **Validates: Requirements 5.5**
    - _Requirements: 5.5_

  - [x] 7.3 Verificar invariante de consistencia del reporte para los tres formatos
    - Test: número de findings en HTML == `DeltaScanResult.findings_introduced`
    - Test: número de filas en tabla Markdown == `DeltaScanResult.findings_introduced`
    - Test: número de `results` en SARIF JSON == `DeltaScanResult.findings_introduced`
    - **Property 14: Invariante de consistencia del reporte**
    - **Validates: Requirements 5.7**
    - _Requirements: 5.7_


- [x] 8. Checkpoint — Verificar reporters extendidos
  - Asegurar que todos los tests unitarios de los pasos 5–7 pasan sin errores.
  - Verificar que los tres reporters generan salida correcta para `DeltaScanResult` con findings y sin findings.
  - Verificar que los reporters mantienen comportamiento v1.0.0 para `ScanResult` normal.
  - Consultar al usuario si hay dudas antes de continuar con el CLI.

- [x] 9. Añadir subcomando `tmac plan` al CLI en `src/tmac/cli.py`
  - [x] 9.1 Implementar el subcomando `plan` con todos sus flags
    - Añadir `@cli.command()` con nombre `plan` al grupo `cli` existente en `src/tmac/cli.py`
    - Implementar flag obligatorio `--plan-file` / `-p` (tipo `click.Path()`, requerido)
    - Implementar los mismos flags de salida que `tmac scan`: `--report` / `-r`, `--output` / `-o`, `--rules-dir`, `--fail-on`, `--quiet` / `-q`, `--no-color`, `--verbose` / `-v`
    - Docstring del comando: `"Analiza un tfplan.json para detectar el delta de riesgo STRIDE."`
    - _Requirements: 4.1, 4.2_

  - [x] 9.2 Implementar la lógica de ejecución del subcomando `plan`
    - Configurar logging si `--verbose` está activo
    - Configurar `NO_COLOR` si `--no-color` está activo
    - Llamar a `DeltaScanner().run(plan_file=plan_file, rules_dir=rules_dir, verbose=verbose)`
    - Capturar `DeltaScanError`, imprimir mensaje a `stderr` con `click.echo(..., err=True)`, llamar `sys.exit(3)`
    - Seleccionar reporter según `--report` (html/md/json), generar reporte, escribir al archivo de salida
    - Imprimir resumen en stdout si no `--quiet`: `"Delta scan complete: N amenazas introducidas, M resueltas. Reporte guardado en {out_file}"`
    - Llamar a `_exit_with_code()` con los findings del `DeltaScanResult`
    - Función `plan()` ≤ 35 líneas de código efectivo
    - _Requirements: 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 9.3 Verificar que el subcomando `scan` existente no fue modificado
    - Revisar que `cli.py::scan()` no tiene cambios respecto a v1.0.0
    - Verificar que `_exit_with_code()` es reutilizable por ambos subcomandos sin modificaciones
    - _Requirements: 4.9_

  - [x] 9.4 Escribir tests unitarios para el CLI `tmac plan` en `tests/unit/test_delta_models.py`
    - Test: `tmac plan --help` muestra el flag `--plan-file` como requerido
    - Test: `tmac plan` sin `--plan-file` retorna error de Click con mensaje descriptivo
    - Test: `tmac plan --plan-file /no/existe` retorna exit code `3`
    - _Requirements: 4.1, 4.7_


- [x] 10. Crear infraestructura de tests — fixtures tfplan.json y conftest actualizado
  - [x] 10.1 Crear directorio `tests/fixtures/plans/` y los cuatro fixtures `tfplan.json`
    - Crear `tests/fixtures/plans/create_with_threat.json`: plan con `aws_s3_bucket.data` acción `create`, `after.acl = "public-read"` (viola `TMAC-AWS-S3-001`)
    - Crear `tests/fixtures/plans/update_secure_to_insecure.json`: plan con `aws_s3_bucket.data` acción `update`, `before.acl = "private"`, `after.acl = "public-read"` (introduce amenaza)
    - Crear `tests/fixtures/plans/update_insecure_to_secure.json`: plan con `aws_s3_bucket.data` acción `update`, `before.acl = "public-read"`, `after.acl = "private"` (resuelve amenaza)
    - Crear `tests/fixtures/plans/delete_with_threat.json`: plan con `aws_s3_bucket.data` acción `delete`, `before.acl = "public-read"` (resuelve amenaza al eliminar)
    - Cada fixture debe tener estructura válida de `tfplan.json` con campos `format_version`, `resource_changes`
    - _Requirements: 7.1_

  - [x] 10.2 Crear fixture `tests/fixtures/plans/clean_plan.json`
    - Plan con `aws_s3_bucket.safe` acción `create`, `after.acl = "private"` (no viola ninguna regla)
    - Usado para verificar exit code `0` y `findings_introduced=0`
    - _Requirements: 7.1, 3.7_

  - [x] 10.3 Crear fixture `tests/fixtures/plans/mixed_plan.json`
    - Plan con múltiples recursos: un `create` con amenaza Critical, un `update` de inseguro a seguro, un `delete` con amenaza High
    - Usado para verificar conteos de `resources_created`, `resources_updated`, `resources_deleted` y `findings_resolved`
    - _Requirements: 7.1, 3.5_

  - [x] 10.4 Actualizar `tests/conftest.py` con fixtures compartidos para delta
    - Añadir fixture `fixtures_plans_path` que retorna `Path("tests/fixtures/plans")`
    - Añadir fixture `sample_planned_change` que retorna un `PlannedChange` de ejemplo con `action=update`
    - Añadir fixture `sample_delta_finding` que retorna un `DeltaFinding` de ejemplo con `change_action=update`
    - Añadir fixture `sample_delta_scan_result` que retorna un `DeltaScanResult` de ejemplo con un finding
    - _Requirements: 7.1_

  - [x] 10.5 Crear `tests/property/__init__.py` para el nuevo directorio de property tests
    - Crear el directorio `tests/property/` y su `__init__.py` vacío
    - _Requirements: 7.6_


- [x] 11. Completar tests unitarios de `TfplanParser` en `tests/unit/test_tfplan_parser.py`
  - [x] 11.1 Crear `tests/unit/test_tfplan_parser.py` con tests de parseo por acción
    - Test `test_parse_create_action`: fixture `create_with_threat.json` → `PlannedChange` con `action=create`, `before=None`, `after` poblado con `acl="public-read"`
    - Test `test_parse_delete_action`: fixture `delete_with_threat.json` → `PlannedChange` con `action=delete`, `before` poblado, `after=None`
    - Test `test_parse_update_action`: fixture `update_secure_to_insecure.json` → `PlannedChange` con `action=update`, `before.acl="private"`, `after.acl="public-read"`
    - Test `test_noop_resources_omitted`: JSON con recurso `no-op` → lista vacía
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 11.2 Crear tests de manejo de errores y casos borde en `test_tfplan_parser.py`
    - Test `test_invalid_json_returns_empty`: string no-JSON → lista vacía sin excepción
    - Test `test_missing_resource_changes_returns_empty`: JSON sin `resource_changes` → lista vacía
    - Test `test_nonexistent_file_returns_empty`: ruta inexistente → lista vacía sin excepción
    - Test `test_address_parsing_simple`: `'aws_s3_bucket.data'` → `resource_type='aws_s3_bucket'`, `resource_name='data'`
    - Test `test_address_parsing_module`: `'module.vpc.aws_subnet.private'` → `resource_type='aws_subnet'`, `resource_name='private'`
    - Test `test_parse_base_interface`: `parse()` retorna `ResourceModel` con atributos `after` del `PlannedChange`
    - _Requirements: 1.7, 1.8, 1.9_

  - [x] 11.3 Escribir property tests para `TfplanParser` en `tests/unit/test_tfplan_parser.py`
    - **Property 1: Semántica before/after por acción del parser**
    - **Property 2: El parser omite recursos no-op**
    - **Property 3: El parser es determinista**
    - **Property 4: Round-trip del parser (serializar + parsear)**
    - **Property 5: El parser maneja JSON inválido sin lanzar excepciones**
    - Cada test usa `@settings(max_examples=100)` y el comentario `# Feature: tmac-v1-1-tfplan-delta, Property N`
    - **Validates: Requirements 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.10, 1.11, 1.12**
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.10, 1.11, 1.12_

- [x] 12. Completar tests unitarios de `DeltaScanner` en `tests/unit/test_delta_scanner.py`
  - [x] 12.1 Crear `tests/unit/test_delta_scanner.py` con tests de clasificación de amenazas
    - Test `test_create_produces_delta_finding`: fixture `create_with_threat.json` → `DeltaFinding` con `change_action=create`, `findings_introduced=1`
    - Test `test_update_secure_to_insecure_produces_finding`: fixture `update_secure_to_insecure.json` → exactamente un `DeltaFinding`, `findings_introduced=1`, `findings_resolved=0`
    - Test `test_update_insecure_to_secure_increments_resolved`: fixture `update_insecure_to_secure.json` → `findings_introduced=0`, `findings_resolved=1`
    - Test `test_delete_with_threat_increments_resolved`: fixture `delete_with_threat.json` → `findings_introduced=0`, `findings_resolved=1`
    - Test `test_clean_plan_returns_zero_findings`: fixture `clean_plan.json` → `findings_introduced=0`, lista vacía
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7_

  - [x] 12.2 Crear tests de conteos y invariantes en `test_delta_scanner.py`
    - Test `test_resource_counts_correct`: fixture `mixed_plan.json` → `resources_created`, `resources_updated`, `resources_deleted` correctos
    - Test `test_findings_introduced_equals_len_findings`: para cualquier fixture, `findings_introduced == len(result.findings)`
    - Test `test_ignore_map_suppresses_resource`: recurso en `ignore_map` con `["*"]` → no produce `DeltaFinding`
    - Test `test_delta_scan_error_on_invalid_file`: archivo inexistente → `DeltaScanError`
    - Test `test_delta_finding_fields_populated`: `DeltaFinding` producido tiene `changed_attribute`, `value_before`, `value_after` correctos
    - _Requirements: 3.5, 3.6, 3.8, 6.5_

  - [x] 12.3 Escribir property tests para `DeltaScanner` en `tests/unit/test_delta_scanner.py`
    - **Property 7: Semántica de DeltaFinding por tipo de cambio**
    - **Property 8: DeltaScanner produce exactamente los DeltaFinding correctos para updates**
    - **Property 9: DeltaScanner registra correctamente amenazas resueltas**
    - **Property 10: Invariantes de conteo del DeltaScanResult**
    - **Property 12: Equivalencia de evaluación entre DeltaScanner y Scanner**
    - **Property 13: tmac:ignore suprime recursos del análisis de delta**
    - Cada test usa `@settings(max_examples=100)` y el comentario `# Feature: tmac-v1-1-tfplan-delta, Property N`
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 6.5, 6.6**
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 6.5, 6.6_


- [x] 13. Implementar tests de integración CLI en `tests/integration/test_plan_cli.py`
  - [x] 13.1 Crear `tests/integration/test_plan_cli.py` con tests de exit codes
    - Test `test_exit_code_0_clean_plan`: `tmac plan --plan-file clean_plan.json` → exit code `0`
    - Test `test_exit_code_1_critical_finding`: `tmac plan --plan-file create_with_threat.json` → exit code `1` (amenaza Critical en `TMAC-AWS-S3-001`)
    - Test `test_exit_code_2_high_finding`: `tmac plan --plan-file <plan_con_high_sin_critical>` → exit code `2`
    - Test `test_exit_code_3_invalid_file`: `tmac plan --plan-file /no/existe.json` → exit code `3`
    - Test `test_exit_code_3_invalid_json`: `tmac plan --plan-file <archivo_no_json>` → exit code `3`
    - _Requirements: 4.4, 4.5, 4.6, 4.7_

  - [x] 13.2 Crear tests de formatos de reporte en `test_plan_cli.py`
    - Test `test_markdown_report_generated`: `tmac plan --plan-file create_with_threat.json --report md --output /tmp/report.md` → archivo generado contiene tabla de delta y resumen ejecutivo
    - Test `test_html_report_generated`: `tmac plan --plan-file create_with_threat.json --report html --output /tmp/report.html` → archivo generado contiene sección `delta-summary`
    - Test `test_json_report_sarif_fields`: `tmac plan --plan-file create_with_threat.json --report json --output /tmp/report.json` → JSON contiene `properties.changeAction` en el resultado SARIF
    - Test `test_quiet_flag_suppresses_stdout`: `tmac plan --plan-file create_with_threat.json --quiet` → stdout vacío, archivo de reporte generado
    - _Requirements: 4.2, 4.3, 5.1, 5.3, 5.5_

  - [x] 13.3 Crear tests de flags adicionales en `test_plan_cli.py`
    - Test `test_verbose_flag_emits_debug_messages`: `tmac plan --plan-file create_with_threat.json --verbose` → stderr/stdout contiene mensajes de debug con número de cambios parseados
    - Test `test_no_color_flag`: `tmac plan --plan-file create_with_threat.json --no-color` → salida sin secuencias ANSI (patrón `\x1b\[[\d;]*m`)
    - Test `test_plan_help_shows_plan_file_flag`: `tmac plan --help` → output contiene `--plan-file`
    - _Requirements: 4.2, 4.8_

  - [x] 13.4 Escribir property tests para exit codes del CLI en `test_plan_cli.py`
    - **Property 11: Exit codes del CLI `tmac plan`**
    - Test parametrizado con `CliRunner` que verifica el mapeo correcto entre severidad máxima de findings y exit code
    - **Validates: Requirements 4.4, 4.5, 4.6, 4.7**
    - _Requirements: 4.4, 4.5, 4.6, 4.7_

- [x] 14. Checkpoint — Verificar suite de tests de integración
  - Asegurar que todos los tests de integración de `test_plan_cli.py` pasan sin errores.
  - Verificar que `tmac plan --help` muestra todos los flags documentados.
  - Verificar que `tmac scan` sigue funcionando correctamente (no hay regresiones).
  - Consultar al usuario si hay dudas antes de continuar con los property-based tests.


- [x] 15. Implementar estrategias Hypothesis y property-based tests
  - [x] 15.1 Crear `tests/property/strategies.py` con estrategias Hypothesis para modelos de delta
    - Implementar `planned_change_strategy()` que genera `PlannedChange` con valores arbitrarios válidos
      - `address`: regex `r'[a-z_]+\.[a-z_]+'`
      - `resource_type`: `st.sampled_from(["aws_s3_bucket", "aws_security_group", "aws_iam_role"])`
      - `resource_name`: regex `r'[a-z_]+'`
      - `action`: `st.sampled_from(list(ChangeAction))`
      - `before`/`after`: `st.one_of(st.none(), st.fixed_dictionaries({"acl": st.text()}))`
    - Implementar `delta_finding_strategy()` que genera `DeltaFinding` con valores arbitrarios válidos
    - Implementar `attributes_strategy()` que genera dicts de atributos de recursos AWS
    - Implementar `rule_strategy()` que genera `ThreatRule` con condiciones válidas
    - _Requirements: 7.6_

  - [x] 15.2 Crear `tests/property/test_delta_properties.py` con las 18 propiedades del diseño
    - Cada test incluye el comentario `# Feature: tmac-v1-1-tfplan-delta, Property N: <texto>`
    - Cada test usa `@settings(max_examples=100)`
    - **Property 1**: `test_parser_before_after_semantics_by_action` — semántica before/after por acción
    - **Property 2**: `test_parser_omits_noop_resources` — parser omite recursos no-op
    - **Property 3**: `test_parser_deterministic` — parsear el mismo JSON dos veces produce resultados idénticos
    - **Property 4**: `test_parser_round_trip` — serializar `PlannedChange[]` a JSON y re-parsear produce lista equivalente
    - **Property 5**: `test_parser_handles_invalid_json` — JSON inválido retorna lista vacía sin excepción
    - **Property 6**: `test_delta_finding_round_trip` — `model_dump()` + `DeltaFinding(**data)` preserva todos los campos
    - **Property 7**: `test_delta_finding_semantics_by_change_type` — semántica de `DeltaFinding` por tipo de cambio
    - **Property 8**: `test_delta_scanner_correct_findings_for_updates` — DeltaScanner produce exactamente los findings correctos para updates
    - **Property 9**: `test_delta_scanner_resolved_findings_correct` — DeltaScanner registra correctamente amenazas resueltas
    - **Property 10**: `test_delta_scan_result_count_invariants` — invariantes de conteo del `DeltaScanResult`
    - **Property 11**: `test_cli_exit_codes` — exit codes del CLI `tmac plan`
    - **Property 12**: `test_evaluation_equivalence` — equivalencia de evaluación entre DeltaScanner y Scanner
    - **Property 13**: `test_ignore_map_suppresses_resources` — tmac:ignore suprime recursos del análisis de delta
    - **Property 14**: `test_report_consistency_invariant` — invariante de consistencia del reporte
    - **Property 15**: `test_html_reporter_delta_no_errors` — HTMLReporter renderiza sección de delta sin errores
    - **Property 16**: `test_markdown_reporter_table_and_summary` — MarkdownReporter genera tabla y resumen ejecutivo
    - **Property 17**: `test_json_reporter_sarif_delta_properties` — JSONReporter incluye campos de delta en SARIF properties
    - **Property 18**: `test_scan_no_regression` — tmac scan produce resultados idénticos antes y después de añadir módulos v1.1.0
    - **Validates: Requirements 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.10, 1.11, 1.12, 2.7, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 4.4, 4.5, 4.6, 4.7, 4.9, 5.1, 5.3, 5.5, 5.7, 6.5, 6.6**
    - _Requirements: 7.6_

- [x] 16. Implementar test de no-regresión de `tmac scan`
  - [x] 16.1 Crear test de no-regresión en `tests/integration/test_plan_cli.py`
    - Test `test_scan_command_unaffected_by_v110_modules`: ejecutar `tmac scan --dir tests/fixtures` con `CliRunner` y verificar que produce los mismos findings que antes de añadir los módulos de v1.1.0
    - Verificar que el número de findings, los `rule_id` y los `resource_name` son idénticos a los esperados (hardcodeados desde la suite de v1.0.0)
    - Verificar que `tmac scan --help` no muestra el flag `--plan-file`
    - _Requirements: 4.9, 7.7_

  - [x] 16.2 Verificar cobertura de tests con `pytest --cov=tmac`
    - Cobertura ≥ 90% en `src/tmac/` incluyendo `src/tmac/delta/` y `src/tmac/parsers/tfplan.py`
    - Cobertura ≥ 80% en tests de integración
    - 100% de las 18 propiedades del diseño cubiertas por property-based tests
    - _Requirements: 7.5_

- [x] 17. Checkpoint — Suite de tests completa
  - Ejecutar `pytest --cov=tmac` y verificar cobertura ≥ 90% en `src/tmac/`.
  - Ejecutar `pytest tests/property/` y verificar que las 18 propiedades pasan con Hypothesis.
  - Ejecutar `pytest tests/integration/` y verificar que todos los tests de integración pasan.
  - Verificar que el test de no-regresión `test_scan_command_unaffected_by_v110_modules` pasa.
  - Consultar al usuario si hay tests fallando o dudas antes de continuar con la documentación.


- [x] 18. Actualizar documentación — README y CHANGELOG
  - [x] 18.1 Añadir sección `tmac plan` al `README.md`
    - Añadir sección con título `## tmac plan — Análisis de Delta de Riesgo` (o equivalente en inglés si el README está en inglés)
    - Documentar la sintaxis del subcomando: `tmac plan --plan-file plan.json [opciones]`
    - Incluir tabla completa de flags: `--plan-file`, `--report`, `--output`, `--rules-dir`, `--fail-on`, `--quiet`, `--no-color`, `--verbose`
    - Documentar los exit codes: `0` (sin Critical/High), `1` (Critical), `2` (High sin Critical), `3` (error)
    - Incluir ejemplo de uso básico: `terraform plan -out=plan.bin && terraform show -json plan.bin > plan.json && tmac plan --plan-file plan.json`
    - _Requirements: 8.1, 8.3_

  - [x] 18.2 Añadir ejemplo de integración en GitHub Actions al `README.md`
    - Incluir snippet YAML de GitHub Actions que ejecuta `terraform plan`, `terraform show -json`, y `tmac plan`
    - Mostrar cómo usar el exit code para bloquear el PR si hay amenazas Critical
    - _Requirements: 8.2_

  - [x] 18.3 Añadir sección diferenciadora al `README.md`
    - Añadir sección que explique el diferenciador de TMAC v1.1.0 vs herramientas que analizan el estado completo
    - Explicar la pregunta que responde: *"¿Qué riesgo nuevo introduce este PR?"* vs *"¿Qué riesgo existe en la infraestructura completa?"*
    - _Requirements: 8.5_

  - [x] 18.4 Añadir entrada `v1.1.0 "Ixtla"` al `CHANGELOG.md`
    - Añadir entrada con fecha y versión `v1.1.0 "Ixtla"` al inicio del `CHANGELOG.md`
    - Sección `Added`: `TfplanParser`, `DeltaScanner`, `DeltaFinding`, `DeltaScanResult`, `ChangeAction`, `PlannedChange`, subcomando `tmac plan`, extensiones de reporters HTML/MD/JSON, property-based tests con Hypothesis
    - Sección `Changed`: extensión de `HTMLReporter`, `MarkdownReporter` y `JSONReporter` para soportar `DeltaScanResult` con duck-typing (compatibilidad hacia atrás total)
    - _Requirements: 8.4_

- [x] 19. Checkpoint final — Verificar integración completa
  - Ejecutar suite completa de tests y verificar que todos pasan: `pytest --cov=tmac -v`.
  - Verificar el pipeline end-to-end manualmente: `tmac plan --plan-file tests/fixtures/plans/create_with_threat.json --report md --verbose`.
  - Verificar que `tmac scan --dir tests/fixtures` sigue produciendo los mismos resultados que en v1.0.0.
  - Consultar al usuario si hay dudas antes de cerrar.

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints en las tareas 4, 8, 14, 17 y 19 aseguran validación incremental
- Los tests de propiedades usan Hypothesis con `@settings(max_examples=100)`
- La dependencia `hypothesis = "^6.100.0"` ya está presente en `pyproject.toml` desde v1.0.0
- Los módulos `RuleLoader`, `Evaluator` y `Matcher` de v1.0.0 se reutilizan sin modificaciones
- El subcomando `tmac scan` existente no debe modificarse (compatibilidad hacia atrás total)
- Los reporters usan duck-typing para detectar `DeltaScanResult`: `isinstance(result, DeltaScanResult)`
- `DeltaScanner` lanza `DeltaScanError`; el CLI la captura y retorna exit code `3`
- El invariante `findings_introduced == len(findings)` debe mantenerse en todo momento
