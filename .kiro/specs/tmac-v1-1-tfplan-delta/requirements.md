# Documento de Requisitos: TMAC v1.1.0 "Ixtla" — Análisis de Delta de Riesgo via tfplan.json

## Introducción

TMAC v1.1.0 extiende la herramienta CLI de análisis estático para IaC con una capacidad nueva:
el análisis de **delta de riesgo** a partir del plan de ejecución de Terraform (`tfplan.json`).

A diferencia del análisis estático de v1.0.0 (que evalúa el estado completo de los archivos `.tf`),
esta versión parsea el output de `terraform plan -out=plan.bin && terraform show -json plan.bin`
para detectar amenazas STRIDE **exclusivamente en los recursos que van a ser creados, modificados
o destruidos** por el PR. El diferenciador clave: no analiza el estado completo, sino el
**delta de riesgo** introducido por el cambio.

Ejemplo de amenaza detectable:
> "El plan modifica `aws_s3_bucket.data` cambiando `acl` de `private` a `public-read` —
> introducción de riesgo Critical (STRIDE-I)"

Esta capacidad sienta las bases para la integración con el agente de PR de v1.6.0, que usará
el delta para generar comentarios automáticos con solo las amenazas del diff.

## Glosario

- **TfplanParser**: Nuevo módulo que parsea `tfplan.json` y extrae `PlannedChange` objects.
- **tfplan.json**: Archivo JSON generado por `terraform show -json <planfile>`. Contiene el plan de ejecución completo con estado anterior y estado planificado de cada recurso.
- **PlannedChange**: Modelo de datos que representa un recurso con su acción planificada (`create`, `update`, `delete`, `no-op`) y los valores antes/después del cambio.
- **ChangeAction**: Enumeración de acciones posibles en un plan: `create`, `update`, `delete`, `no-op`, `replace`.
- **DeltaScanner**: Orquestador del pipeline de análisis de delta; análogo al `Scanner` de v1.0.0 pero orientado a `tfplan.json`.
- **DeltaFinding**: Extensión de `Finding` que incluye el contexto del cambio: acción, atributo modificado, valor anterior y valor nuevo.
- **DeltaScanResult**: Extensión de `ScanResult` que incluye estadísticas de delta: amenazas introducidas, amenazas resueltas, recursos creados/modificados/destruidos.
- **RiskDelta**: Diferencia neta de riesgo introducida por el plan: `findings_introduced - findings_resolved`.
- **Scanner**: Orquestador existente de v1.0.0 para análisis de archivos `.tf`.
- **TerraformParser**: Parser existente de v1.0.0 para archivos `.tf`.
- **Evaluator**: Motor de evaluación de condiciones STRIDE existente de v1.0.0.
- **Matcher**: Coordinador de evaluación existente de v1.0.0.
- **RuleLoader**: Cargador de reglas `threats.yaml` existente de v1.0.0.
- **Finding**: Modelo de datos existente de v1.0.0 que representa una amenaza detectada.
- **ScanResult**: Modelo de datos existente de v1.0.0 con metadata, estadísticas y findings.
- **ResourceModel**: Modelo de datos existente de v1.0.0 que representa un recurso IaC parseado.
- **STRIDE**: Framework de modelado de amenazas (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).
- **CLI**: Interfaz de línea de comandos (`tmac`), implementada con Click.
- **BaseParser**: Clase abstracta existente en `src/tmac/parsers/base.py` que define la interfaz de parsers.
- **Exit_Code**: Código de retorno del proceso CLI al sistema operativo.

---

## Requisitos

### Requisito 1: Parser de tfplan.json

**User Story:** Como ingeniero de seguridad, quiero que TMAC parsee el archivo `tfplan.json` generado por Terraform, para poder analizar los cambios planificados antes de ejecutar `terraform apply`.

#### Criterios de Aceptación

1. THE TfplanParser SHALL implementar la interfaz `BaseParser` definida en `src/tmac/parsers/base.py`.
2. WHEN el TfplanParser recibe la ruta a un `tfplan.json` válido, THE TfplanParser SHALL retornar una lista de `PlannedChange` objects con la acción, el tipo de recurso, el nombre, los atributos antes del cambio y los atributos después del cambio.
3. WHEN el `tfplan.json` contiene un recurso con acción `create`, THE TfplanParser SHALL producir un `PlannedChange` con `before` igual a `None` y `after` con los atributos del nuevo recurso.
4. WHEN el `tfplan.json` contiene un recurso con acción `delete`, THE TfplanParser SHALL producir un `PlannedChange` con `before` con los atributos del recurso existente y `after` igual a `None`.
5. WHEN el `tfplan.json` contiene un recurso con acción `update`, THE TfplanParser SHALL producir un `PlannedChange` con `before` y `after` ambos poblados con los atributos correspondientes.
6. WHEN el `tfplan.json` contiene recursos con acción `no-op`, THE TfplanParser SHALL omitir esos recursos de la lista retornada.
7. IF el archivo proporcionado no existe o no es JSON válido, THEN THE TfplanParser SHALL retornar una lista vacía y emitir un mensaje de error estructurado via `logging`.
8. IF el `tfplan.json` no contiene el campo `resource_changes`, THEN THE TfplanParser SHALL retornar una lista vacía y emitir un warning via `logging`.
9. THE TfplanParser SHALL extraer el campo `address` de cada `resource_change` para construir el nombre canónico del recurso (formato `resource_type.resource_name`).
10. FOR ALL `tfplan.json` válidos, parsear el archivo dos veces consecutivas SHALL producir listas de `PlannedChange` idénticas (propiedad de determinismo del parser).
11. THE Pretty_Printer SHALL serializar una lista de `PlannedChange` objects de vuelta a una representación JSON estructurada equivalente al subconjunto relevante del `tfplan.json` original.
12. FOR ALL listas de `PlannedChange` producidas por el TfplanParser, serializar con el Pretty_Printer y parsear nuevamente SHALL producir una lista equivalente (propiedad round-trip del parser).

---

### Requisito 2: Modelo de Datos PlannedChange y DeltaFinding

**User Story:** Como desarrollador que extiende TMAC, quiero modelos de datos bien definidos para representar cambios planificados y hallazgos de delta, para poder construir sobre ellos en versiones futuras.

#### Criterios de Aceptación

1. THE PlannedChange SHALL ser un modelo Pydantic con los campos: `address` (str), `resource_type` (str), `resource_name` (str), `action` (ChangeAction), `before` (Optional[Dict]), `after` (Optional[Dict]).
2. THE ChangeAction SHALL ser una enumeración con los valores: `create`, `update`, `delete`, `replace`.
3. THE DeltaFinding SHALL extender `Finding` con los campos adicionales: `change_action` (ChangeAction), `changed_attribute` (str), `value_before` (Optional[Any]), `value_after` (Optional[Any]).
4. THE DeltaScanResult SHALL extender `ScanResult` con los campos adicionales: `findings_introduced` (int), `findings_resolved` (int), `resources_created` (int), `resources_updated` (int), `resources_deleted` (int), `plan_file` (str).
5. WHEN un `DeltaFinding` representa una amenaza introducida por un recurso creado, THE DeltaFinding SHALL tener `change_action` igual a `create` y `value_before` igual a `None`.
6. WHEN un `DeltaFinding` representa una amenaza introducida por un cambio de atributo, THE DeltaFinding SHALL tener `change_action` igual a `update`, `value_before` con el valor anterior y `value_after` con el valor nuevo.
7. FOR ALL `DeltaFinding` objects, serializar con `model_dump()` y reconstruir con `DeltaFinding(**data)` SHALL producir un objeto equivalente con todos los campos preservados (propiedad round-trip de serialización).

---

### Requisito 3: Motor de Detección de Delta de Riesgo

**User Story:** Como ingeniero de seguridad, quiero que TMAC distinga entre amenazas introducidas y amenazas resueltas por el plan, para entender el impacto neto de seguridad del PR.

#### Criterios de Aceptación

1. THE DeltaScanner SHALL evaluar los atributos `after` de cada `PlannedChange` con acción `create` contra todas las reglas STRIDE, produciendo `DeltaFinding` objects para cada coincidencia.
2. WHEN un `PlannedChange` tiene acción `update`, THE DeltaScanner SHALL evaluar los atributos `after` contra las reglas STRIDE y producir `DeltaFinding` solo para las reglas que no se satisfacían con los atributos `before` (amenazas introducidas).
3. WHEN un `PlannedChange` tiene acción `update` y los atributos `before` satisfacían una regla pero los atributos `after` no la satisfacen, THE DeltaScanner SHALL registrar esa regla como resuelta en `DeltaScanResult.findings_resolved`.
4. WHEN un `PlannedChange` tiene acción `delete`, THE DeltaScanner SHALL evaluar los atributos `before` contra las reglas STRIDE y registrar las coincidencias como resueltas en `DeltaScanResult.findings_resolved`.
5. THE DeltaScanner SHALL poblar `DeltaScanResult.resources_created`, `resources_updated` y `resources_deleted` con el conteo de `PlannedChange` por acción.
6. THE DeltaScanner SHALL calcular `findings_introduced` como el número total de `DeltaFinding` producidos (amenazas nuevas o empeoradas).
7. IF el plan no introduce ninguna amenaza nueva, THEN THE DeltaScanner SHALL retornar un `DeltaScanResult` con `findings_introduced` igual a `0` y lista de findings vacía.
8. FOR ALL planes donde un recurso cambia de estado seguro a inseguro, THE DeltaScanner SHALL producir exactamente un `DeltaFinding` por regla violada en el estado `after` que no era violada en el estado `before`.

---

### Requisito 4: Nuevo Subcomando CLI `tmac plan`

**User Story:** Como ingeniero de DevSecOps, quiero un subcomando `tmac plan` que analice un `tfplan.json`, para poder integrarlo en pipelines de CI/CD antes de `terraform apply`.

#### Criterios de Aceptación

1. THE CLI SHALL implementar un subcomando `tmac plan` con el flag obligatorio `--plan-file` / `-p` que acepta la ruta al `tfplan.json`.
2. THE CLI SHALL implementar en `tmac plan` los mismos flags de salida que `tmac scan`: `--report`, `--output`, `--fail-on`, `--quiet`, `--no-color`, `--verbose`.
3. WHEN `tmac plan` es invocado con un `tfplan.json` válido, THE CLI SHALL ejecutar el análisis de delta y generar el reporte en el formato especificado.
4. WHEN `tmac plan` completa sin `DeltaFinding` con severidad Critical o High, THE CLI SHALL retornar exit code `0`.
5. WHEN `tmac plan` detecta `DeltaFinding` con severidad Critical, THE CLI SHALL retornar exit code `1`.
6. WHEN `tmac plan` detecta `DeltaFinding` con severidad High pero ninguno Critical, THE CLI SHALL retornar exit code `2`.
7. IF el archivo `--plan-file` no existe o no es un `tfplan.json` válido, THEN THE CLI SHALL retornar exit code `3` con un mensaje descriptivo en stderr.
8. WHEN `tmac plan` es invocado con `--verbose`, THE CLI SHALL emitir mensajes de debug que incluyan: número de cambios parseados, recursos por acción, y reglas evaluadas por recurso.
9. THE CLI SHALL mantener el subcomando `tmac scan` existente sin modificaciones (compatibilidad hacia atrás total).

---

### Requisito 5: Reportes de Delta

**User Story:** Como desarrollador revisando un PR, quiero que el reporte de TMAC muestre claramente qué amenazas introduce y qué amenazas resuelve el plan, para tomar decisiones informadas sobre el merge.

#### Criterios de Aceptación

1. THE HTMLReporter SHALL generar una sección de delta en el reporte HTML que muestre: número de amenazas introducidas, número de amenazas resueltas, y el `RiskDelta` neto.
2. THE HTMLReporter SHALL diferenciar visualmente los `DeltaFinding` por tipo de cambio: recursos creados (badge verde "NUEVO"), recursos modificados (badge amarillo "MODIFICADO"), recursos eliminados (badge gris "ELIMINADO").
3. THE MarkdownReporter SHALL generar una tabla de resumen de delta con columnas: Acción, Recurso, Regla, Severidad, STRIDE, Descripción del cambio.
4. THE MarkdownReporter SHALL incluir una línea de resumen ejecutivo al inicio del reporte: "Este plan introduce N amenazas nuevas y resuelve M".
5. THE JSONReporter SHALL extender el schema SARIF existente para incluir en cada `result` los campos adicionales: `changeAction`, `valueBefore`, `valueAfter` como propiedades en `properties`.
6. WHEN el `DeltaScanResult` tiene `findings_introduced` igual a `0`, THE HTMLReporter SHALL renderizar un estado de aprobación sin errores de template.
7. FOR ALL `DeltaScanResult` objects, el número de findings en el reporte SHALL ser igual a `DeltaScanResult.findings_introduced` (invariante de consistencia del reporte).

---

### Requisito 6: Integración con el Engine de Reglas Existente

**User Story:** Como mantenedor del proyecto, quiero que el análisis de delta reutilice el `Evaluator`, el `Matcher` y el `RuleLoader` existentes de v1.0.0, para no duplicar lógica de evaluación de reglas.

#### Criterios de Aceptación

1. THE DeltaScanner SHALL reutilizar el `RuleLoader` existente para cargar las reglas desde `threats.yaml` sin modificaciones al `RuleLoader`.
2. THE DeltaScanner SHALL reutilizar el `Evaluator` existente para evaluar condiciones STRIDE contra los atributos `after` de cada `PlannedChange`.
3. THE DeltaScanner SHALL reutilizar el `Evaluator` existente para evaluar condiciones STRIDE contra los atributos `before` de cada `PlannedChange` al calcular amenazas resueltas.
4. WHEN el `DeltaScanner` convierte un `PlannedChange` para evaluación, THE DeltaScanner SHALL construir un `ResourceModel` temporal con los atributos `after` (o `before`) para pasarlo al `Evaluator` sin modificar la interfaz del `Evaluator`.
5. THE DeltaScanner SHALL soportar el mecanismo `tmac:ignore` existente: si el `address` del recurso está en el `ignore_map`, THE DeltaScanner SHALL omitir ese recurso del análisis.
6. FOR ALL reglas en `threats.yaml`, el resultado de evaluarlas contra los atributos `after` de un `PlannedChange` SHALL ser idéntico al resultado de evaluarlas contra un `ResourceModel` con los mismos atributos (propiedad de equivalencia de evaluación).

---

### Requisito 7: Suite de Tests para v1.1.0

**User Story:** Como mantenedor del proyecto, quiero una suite de tests completa para las nuevas capacidades de v1.1.0, para garantizar la corrección del análisis de delta y prevenir regresiones.

#### Criterios de Aceptación

1. THE Test_Suite SHALL incluir fixtures `tfplan.json` de ejemplo en `tests/fixtures/plans/` que cubran los cuatro escenarios: recurso creado con amenaza, recurso modificado de seguro a inseguro, recurso modificado de inseguro a seguro, y recurso eliminado con amenaza.
2. THE Test_Suite SHALL incluir tests unitarios para el `TfplanParser` en `tests/unit/test_tfplan_parser.py` que verifiquen el parseo correcto de cada tipo de acción (`create`, `update`, `delete`, `no-op`).
3. THE Test_Suite SHALL incluir tests unitarios para el `DeltaScanner` en `tests/unit/test_delta_scanner.py` que verifiquen la clasificación correcta de amenazas introducidas y resueltas.
4. THE Test_Suite SHALL incluir tests de integración en `tests/integration/test_plan_cli.py` que invoquen `tmac plan` con `CliRunner` y verifiquen exit codes y contenido del reporte.
5. WHEN se ejecuta `pytest --cov=tmac`, THE Test_Suite SHALL mantener cobertura ≥ 90% en `src/tmac/` incluyendo los nuevos módulos de v1.1.0.
6. THE Test_Suite SHALL incluir property-based tests con Hypothesis para las propiedades de corrección del `TfplanParser` y el `DeltaScanner`.
7. THE Test_Suite SHALL incluir un test de no-regresión que verifique que `tmac scan` produce los mismos resultados antes y después de añadir los módulos de v1.1.0.

---

### Requisito 8: Documentación Actualizada

**User Story:** Como usuario de TMAC, quiero que el README y el CHANGELOG reflejen las nuevas capacidades de v1.1.0, para poder usar el subcomando `tmac plan` correctamente.

#### Criterios de Aceptación

1. THE README SHALL documentar el subcomando `tmac plan` con su sintaxis, flags disponibles y ejemplos de uso.
2. THE README SHALL incluir un ejemplo de integración en GitHub Actions que use `tmac plan` con el output de `terraform plan`.
3. THE README SHALL documentar el formato del `tfplan.json` esperado (output de `terraform show -json`).
4. THE CHANGELOG SHALL incluir una entrada para `v1.1.0 "Ixtla"` con las secciones `Added` y `Changed` que describan todas las nuevas capacidades.
5. THE README SHALL incluir una sección que explique el diferenciador de TMAC v1.1.0 vs herramientas que analizan el estado completo.
