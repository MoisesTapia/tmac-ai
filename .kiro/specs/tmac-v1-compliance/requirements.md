# Documento de Requisitos: TMAC v1.0.0 "Ixtla" — Plan de Cumplimiento

## Introducción

TMAC (Threat Modeling as Code) es una herramienta CLI de análisis estático para IaC (Terraform).
El proyecto tiene una base de código funcional pero presenta brechas significativas respecto al PRD v1.0.0.
Este documento captura todos los requisitos necesarios para llevar el proyecto a su versión v1.0.0 "Ixtla",
cubriendo corrección de bugs, implementación de features faltantes, suite de tests completa,
y corrección de documentación.

## Glosario

- **CLI**: Interfaz de línea de comandos (`tmac scan`), implementada con Click.
- **Scanner**: Orquestador del pipeline de escaneo; actualmente la función `scan()` en `cli.py`.
- **TerraformParser**: Módulo que parsea archivos `.tf` usando `python-hcl2` y extrae `ResourceModel`.
- **RuleLoader**: Módulo que carga y valida reglas desde archivos `threats.yaml`.
- **Evaluator**: Módulo que evalúa condiciones de reglas contra atributos de recursos.
- **Matcher**: Módulo que coordina la evaluación de recursos contra reglas y produce `Finding` objects.
- **Reporter**: Módulo que transforma `ScanResult` en salida formateada (HTML, Markdown, JSON/SARIF).
- **Finding**: Modelo Pydantic que representa una amenaza detectada en un recurso.
- **ScanResult**: Modelo Pydantic agregado con metadata, estadísticas y lista de `Finding`.
- **ResourceModel**: Modelo Pydantic que representa un recurso IaC parseado.
- **ThreatRule**: Modelo Pydantic que representa una regla de amenaza cargada desde YAML.
- **SARIF**: Static Analysis Results Interchange Format — schema JSON estándar para resultados de análisis.
- **STRIDE**: Framework de modelado de amenazas (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).
- **Exit_Code**: Código de retorno del proceso CLI al sistema operativo.
- **tmac_ignore**: Mecanismo de supresión de hallazgos mediante comentarios en archivos `.tf`.
- **Fixture**: Archivo `.tf` de prueba que representa un escenario específico (positivo o negativo).
- **conftest**: Archivo `conftest.py` de pytest con fixtures compartidos entre tests.

---

## Requisitos


### Requisito 1: Refactorización del CLI — Separación de Responsabilidades (SRP)

**User Story:** Como mantenedor del proyecto, quiero que la función `scan()` en `cli.py` delegue la lógica de orquestación a un módulo separado, para que el CLI solo maneje argumentos y salida, cumpliendo el Principio de Responsabilidad Única.

#### Criterios de Aceptación

1. THE Scanner SHALL implementar un método `run_scan(directory, rules_dir, exclude_patterns, min_severity) -> ScanResult` que encapsule todo el pipeline (parseo, carga de reglas, matching, estadísticas).
2. WHEN la función `scan()` del CLI es invocada, THE CLI SHALL delegar la ejecución del pipeline al Scanner y solo manejar la presentación de resultados y el exit code.
3. THE Scanner SHALL tener menos de 40 líneas de código en su método principal de orquestación.
4. THE CLI SHALL mantener la función `scan()` con menos de 30 líneas de código efectivo.

---

### Requisito 2: Exit Codes Correctos según PRD FR-006

**User Story:** Como pipeline de CI/CD, quiero que el CLI retorne exit codes estructurados y correctos, para que pueda distinguir entre hallazgos críticos, altos, y errores de ejecución.

#### Criterios de Aceptación

1. WHEN el escaneo completa sin hallazgos Critical o High, THE CLI SHALL retornar exit code `0`.
2. WHEN el escaneo detecta uno o más hallazgos con severidad Critical, THE CLI SHALL retornar exit code `1`.
3. WHEN el escaneo detecta hallazgos High pero ninguno Critical, THE CLI SHALL retornar exit code `2`.
4. WHEN el escaneo falla por error de parseo completo, configuración inválida, o directorio inaccesible, THE CLI SHALL retornar exit code `3`.
5. THE CLI SHALL emitir un mensaje descriptivo a stderr cuando retorne exit code `3`.
6. IF el flag `--fail-on` está configurado a un nivel de severidad, THEN THE CLI SHALL retornar exit code `1` cuando se detecten hallazgos que igualen o superen ese nivel.

---

### Requisito 3: Flags CLI Faltantes del PRD (FR-004, Sección 7.2)

**User Story:** Como usuario del CLI, quiero disponer de los flags `--exclude`, `--no-color` y `--verbose` documentados en el PRD, para poder controlar el comportamiento del escaneo desde la línea de comandos.

#### Criterios de Aceptación

1. THE CLI SHALL implementar el flag `--exclude` / `-e` que acepta patrones glob y puede repetirse múltiples veces.
2. WHEN `--exclude` es especificado, THE Scanner SHALL omitir archivos y directorios cuyos paths coincidan con el patrón glob proporcionado.
3. THE CLI SHALL implementar el flag `--no-color` que deshabilita el color ANSI en la salida de terminal.
4. WHEN `--no-color` es especificado, THE CLI SHALL producir salida de texto plano sin secuencias de escape ANSI.
5. THE CLI SHALL implementar el flag `--verbose` / `-v` que habilita logging de debug.
6. WHEN `--verbose` es especificado, THE CLI SHALL emitir mensajes de debug que incluyan: archivos descubiertos, reglas cargadas, y condiciones evaluadas por el Evaluator.
7. THE CLI SHALL reemplazar el filtro hardcodeado de `.terraform` por el mecanismo `--exclude` configurable.

---

### Requisito 4: Parser Terraform — Line Numbers y tmac:ignore Mejorado

**User Story:** Como usuario de TMAC, quiero que los hallazgos incluyan el número de línea correcto y que el mecanismo `tmac:ignore` soporte exclusión por Rule ID, para poder navegar rápidamente al código afectado y suprimir reglas específicas.

#### Criterios de Aceptación

1. WHEN el TerraformParser parsea un archivo `.tf`, THE TerraformParser SHALL capturar el número de línea de inicio de cada bloque `resource` y almacenarlo en `ResourceModel.line_number`.
2. THE TerraformParser SHALL abrir cada archivo `.tf` una sola vez para extraer tanto los ignores como el contenido parseado.
3. WHEN un comentario `# tmac:ignore` aparece en la línea inmediatamente anterior a un bloque `resource`, THE TerraformParser SHALL excluir ese recurso de todos los hallazgos.
4. WHEN un comentario `# tmac:ignore[TMAC-AWS-S3-001]` aparece en la línea inmediatamente anterior a un bloque `resource`, THE TerraformParser SHALL excluir ese recurso únicamente de la regla especificada.
5. WHEN un comentario `# tmac:ignore` aparece en la misma línea que la declaración del bloque `resource`, THE TerraformParser SHALL excluir ese recurso de todos los hallazgos.
6. THE TerraformParser SHALL soportar múltiples comentarios `# tmac:ignore[RULE-ID]` en líneas consecutivas antes de un bloque `resource` para excluir múltiples reglas específicas.
7. FOR ALL archivos `.tf` válidos, parsear el archivo y serializar los recursos de vuelta a su representación SHALL producir el mismo conjunto de recursos al parsear nuevamente (propiedad round-trip de extracción de recursos).

---

### Requisito 5: Evaluator — Soporte para Listas de Bloques Múltiples

**User Story:** Como usuario de TMAC, quiero que el Evaluator evalúe todos los bloques de una lista (ej. múltiples reglas `ingress` en un Security Group), para que no se produzcan falsos negativos cuando solo el primer elemento de la lista es evaluado.

#### Criterios de Aceptación

1. WHEN el Evaluator resuelve un atributo cuyo path atraviesa una lista de bloques, THE Evaluator SHALL evaluar la condición contra todos los elementos de la lista, no solo el primero.
2. WHEN cualquier elemento de la lista satisface la condición de la regla, THE Evaluator SHALL retornar `True` (hallazgo detectado).
3. WHEN `--verbose` está activo, THE Evaluator SHALL emitir un mensaje de debug por cada condición evaluada, indicando el atributo, la condición, el valor esperado y el valor actual.
4. THE Evaluator SHALL mantener compatibilidad con todas las condiciones existentes: `equals`, `not_equals`, `in`, `not_in`, `contains`, `not_contains`, `regex`, `exists`, `not_exists`.
5. FOR ALL recursos con múltiples bloques `ingress`, si algún bloque `ingress` satisface la condición de la regla, THE Evaluator SHALL producir el mismo resultado que si ese bloque fuera el único (propiedad de invarianza de orden de evaluación).

---

### Requisito 6: RuleLoader — Validación de Schema YAML

**User Story:** Como mantenedor del proyecto, quiero que el RuleLoader valide el schema de los archivos `threats.yaml` antes de cargar las reglas, para detectar errores de configuración tempranamente con mensajes descriptivos.

#### Criterios de Aceptación

1. WHEN el RuleLoader carga un archivo `threats.yaml`, THE RuleLoader SHALL validar que el archivo contiene los campos obligatorios: `version` y `rules`.
2. IF un archivo `threats.yaml` no contiene el campo `version`, THEN THE RuleLoader SHALL emitir un warning estructurado con el path del archivo y omitir ese archivo.
3. IF una regla individual dentro de `rules` no contiene los campos obligatorios (`id`, `name`, `resource_type`, `check`, `severity`, `stride`), THEN THE RuleLoader SHALL omitir esa regla y emitir un warning con el ID de la regla afectada.
4. THE RuleLoader SHALL usar `logging` estructurado en lugar de `print()` para todos los mensajes de advertencia y error.
5. WHEN el RuleLoader carga reglas exitosamente, THE RuleLoader SHALL retornar la misma lista de reglas independientemente del orden de los archivos YAML procesados (propiedad de idempotencia de carga).

---

### Requisito 7: JSONReporter — Schema SARIF Compatible

**User Story:** Como ingeniero de CI/CD, quiero que el reporte JSON siga el schema SARIF, para poder integrarlo con GitHub Code Scanning y otras herramientas de análisis estático.

#### Criterios de Aceptación

1. THE JSONReporter SHALL generar un objeto JSON con los campos de nivel superior: `version`, `$schema`, `runs`.
2. THE JSONReporter SHALL incluir dentro de `runs[0].tool.driver` los campos: `name`, `version`, `informationUri`, y `rules` (array de reglas únicas detectadas).
3. THE JSONReporter SHALL incluir dentro de `runs[0].results` un array donde cada elemento representa un `Finding` con los campos: `ruleId`, `level`, `message`, `locations`.
4. WHEN el JSONReporter serializa un `ScanResult` y el resultado es deserializado nuevamente, THE JSONReporter SHALL producir el mismo número de findings y los mismos `ruleId` (propiedad round-trip de serialización).
5. THE JSONReporter SHALL mapear los niveles de severidad de TMAC a niveles SARIF: `Critical` → `error`, `High` → `error`, `Medium` → `warning`, `Low` → `note`, `Info` → `none`.

---

### Requisito 8: Corrección de Bugs en Templates Jinja2

**User Story:** Como usuario de TMAC, quiero que los reportes HTML y Markdown se generen sin errores de template, para poder visualizar los hallazgos correctamente.

#### Criterios de Aceptación

1. THE HTMLReporter SHALL iterar el campo `finding.stride` como una lista de categorías STRIDE, no como una cadena de caracteres.
2. WHEN `finding.stride` es una cadena de texto (ej. `"Information Disclosure"`), THE HTMLReporter SHALL tratarla como un elemento único de lista para el renderizado de badges.
3. THE MarkdownReporter SHALL usar la sintaxis correcta `{% elif %}` en lugar de `{% elief %}` en el template `report.md.j2`.
4. WHEN el HTMLReporter genera un reporte con 0 findings, THE HTMLReporter SHALL renderizar el estado vacío sin errores de template.
5. WHEN el MarkdownReporter genera un reporte con findings de cualquier severidad, THE MarkdownReporter SHALL renderizar el emoji de severidad correcto para cada nivel.

---

### Requisito 9: Modelos de Datos — Campos Faltantes

**User Story:** Como desarrollador que consume la API de TMAC, quiero que los modelos `Finding` y `ScanResult` incluyan todos los campos definidos en el PRD, para tener información completa en los reportes.

#### Criterios de Aceptación

1. THE Finding SHALL incluir el campo `tags` de tipo `List[str]` con valor por defecto de lista vacía, propagado desde `ThreatRule.tags`.
2. THE ScanResult SHALL incluir el campo `files_scanned` de tipo `int` con el número de archivos `.tf` procesados.
3. THE ScanResult SHALL incluir el campo `rules_loaded` de tipo `int` con el número de reglas cargadas.
4. WHEN el Scanner completa un escaneo, THE Scanner SHALL poblar `ScanResult.files_scanned` y `ScanResult.rules_loaded` con los valores correctos.
5. THE Finding SHALL mantener compatibilidad hacia atrás: todos los campos existentes conservan su tipo y semántica.

---

### Requisito 10: Config — Validación de Estructura `.tmac.yaml`

**User Story:** Como usuario de TMAC, quiero que el CLI detecte y reporte claves inválidas en `.tmac.yaml`, para evitar configuraciones silenciosamente ignoradas.

#### Criterios de Aceptación

1. THE Config SHALL validar que el archivo `.tmac.yaml` solo contiene las claves de nivel superior permitidas: `scan` y `report`.
2. IF el archivo `.tmac.yaml` contiene claves no reconocidas, THEN THE Config SHALL emitir un warning con las claves desconocidas y continuar con las claves válidas.
3. THE Config SHALL validar que `scan.exclude` es una lista de strings cuando está presente.
4. THE Config SHALL validar que `report.format` es uno de los valores permitidos (`html`, `json`, `md`) cuando está presente.
5. IF el archivo `.tmac.yaml` tiene errores de sintaxis YAML, THEN THE CLI SHALL retornar exit code `3` con un mensaje descriptivo.

---

### Requisito 11: Suite de Tests — Infraestructura Base

**User Story:** Como mantenedor del proyecto, quiero una infraestructura de tests completa con `conftest.py`, directorios `unit/` e `integration/`, para poder ejecutar y mantener la suite de tests del PRD.

#### Criterios de Aceptación

1. THE Test_Suite SHALL incluir un archivo `tests/conftest.py` con fixtures compartidos: `sample_finding`, `sample_scan_result`, `sample_rule`, `sample_resource`.
2. THE Test_Suite SHALL organizar los tests en `tests/unit/` para tests de componentes individuales y `tests/integration/` para tests end-to-end del pipeline.
3. THE Test_Suite SHALL incluir fixtures `.tf` positivos (que disparan la regla) y negativos (que no disparan la regla) para cada una de las 10 reglas base del PRD.
4. WHEN se ejecuta `pytest --cov=tmac`, THE Test_Suite SHALL alcanzar cobertura ≥ 90% en código de producción de `src/tmac/`.
5. WHEN se ejecuta `pytest tests/integration/`, THE Test_Suite SHALL alcanzar cobertura ≥ 80% en los flujos de integración CLI → Parser → Engine → Reporter.

---

### Requisito 12: Tests Unitarios — Parser

**User Story:** Como mantenedor del proyecto, quiero tests unitarios para el TerraformParser, para verificar que el parseo de archivos `.tf` es correcto y robusto.

#### Criterios de Aceptación

1. THE Parser_Tests SHALL incluir un test que verifica que un archivo `.tf` válido con múltiples recursos retorna el número correcto de `ResourceModel` objects.
2. THE Parser_Tests SHALL incluir un test que verifica que un archivo `.tf` con sintaxis inválida retorna una lista vacía sin lanzar excepción.
3. THE Parser_Tests SHALL incluir un test parametrizado que verifica el mecanismo `# tmac:ignore` para cada variante: ignore global, ignore por Rule ID, ignore en misma línea.
4. THE Parser_Tests SHALL incluir un test que verifica que `line_number` es mayor que 0 para recursos parseados de archivos con contenido real.
5. FOR ALL archivos `.tf` en `tests/fixtures/`, THE Parser_Tests SHALL verificar que el parser retorna al menos un `ResourceModel` (test de no-regresión de fixtures existentes).

---

### Requisito 13: Tests Unitarios — Evaluator y Matcher

**User Story:** Como mantenedor del proyecto, quiero tests unitarios para el Evaluator y el Matcher, para verificar que la evaluación de condiciones es correcta para todos los operadores soportados.

#### Criterios de Aceptación

1. THE Evaluator_Tests SHALL incluir tests parametrizados para cada condición: `equals`, `not_equals`, `in`, `not_in`, `contains`, `not_contains`, `regex`, `exists`, `not_exists`.
2. THE Evaluator_Tests SHALL incluir un test que verifica que `and_check` compuesto evalúa correctamente (ambas condiciones deben ser verdaderas).
3. THE Evaluator_Tests SHALL incluir un test que verifica que un Security Group con múltiples bloques `ingress` detecta la regla cuando cualquiera de los bloques la satisface.
4. THE Matcher_Tests SHALL incluir un test que verifica que recursos con `# tmac:ignore` no producen findings.
5. THE Matcher_Tests SHALL incluir un test que verifica que recursos con `# tmac:ignore[RULE-ID]` no producen findings solo para la regla especificada.

---

### Requisito 14: Tests Unitarios — Reporters

**User Story:** Como mantenedor del proyecto, quiero tests unitarios para los tres reporters, para verificar que generan salida válida y correcta.

#### Criterios de Aceptación

1. THE Reporter_Tests SHALL incluir un test que verifica que el HTMLReporter genera HTML válido (contiene `<!DOCTYPE html>` y `</html>`).
2. THE Reporter_Tests SHALL incluir un test que verifica que el MarkdownReporter genera Markdown con la tabla de resumen cuando hay findings.
3. THE Reporter_Tests SHALL incluir un test que verifica que el JSONReporter genera JSON válido parseable con `json.loads()`.
4. THE Reporter_Tests SHALL incluir un test que verifica que el JSONReporter produce output con los campos SARIF: `version`, `runs`.
5. WHEN el JSONReporter serializa un `ScanResult` y el resultado es deserializado, THE Reporter_Tests SHALL verificar que el número de findings es idéntico (round-trip test).
6. THE Reporter_Tests SHALL incluir un test que verifica que todos los reporters manejan correctamente un `ScanResult` con lista de findings vacía.

---

### Requisito 15: Tests de Reglas Parametrizados (PRD Sección 9.3)

**User Story:** Como mantenedor del proyecto, quiero tests parametrizados por regla con fixtures positivos y negativos, para garantizar que cada regla detecta correctamente los casos que debe detectar y no produce falsos positivos.

#### Criterios de Aceptación

1. THE Rule_Tests SHALL incluir un test parametrizado con al menos un fixture positivo y uno negativo para cada una de las 10 reglas base del PRD.
2. WHEN un fixture positivo es evaluado contra su regla correspondiente, THE Rule_Tests SHALL verificar que se produce exactamente un `Finding` con el `rule_id` correcto.
3. WHEN un fixture negativo es evaluado contra su regla correspondiente, THE Rule_Tests SHALL verificar que no se produce ningún `Finding`.
4. THE Rule_Tests SHALL incluir fixtures para: `TMAC-AWS-S3-001`, `TMAC-AWS-S3-002`, `TMAC-AWS-S3-003`, `TMAC-AWS-IAM-001`, `TMAC-AWS-IAM-002`, `TMAC-AWS-SG-001`, `TMAC-AWS-SG-002`, `TMAC-AWS-RDS-001`, `TMAC-AWS-RDS-002`, `TMAC-AWS-CW-001`.
5. FOR ALL reglas en `threats.yaml`, THE Rule_Tests SHALL verificar que el `rule_id` sigue el patrón `TMAC-{CLOUD}-{SERVICE}-{NNN}` (test de invarianza de schema).

---

### Requisito 16: Tests de Integración — CLI End-to-End

**User Story:** Como mantenedor del proyecto, quiero tests de integración que invoquen el CLI completo con `click.testing.CliRunner`, para verificar el comportamiento end-to-end incluyendo exit codes y generación de reportes.

#### Criterios de Aceptación

1. THE Integration_Tests SHALL usar `click.testing.CliRunner` para invocar el comando `scan` sin dependencias externas.
2. THE Integration_Tests SHALL incluir un test que verifica exit code `0` cuando el directorio escaneado no contiene hallazgos.
3. THE Integration_Tests SHALL incluir un test que verifica exit code `1` cuando el directorio contiene hallazgos Critical.
4. THE Integration_Tests SHALL incluir un test que verifica exit code `2` cuando el directorio contiene hallazgos High pero no Critical.
5. THE Integration_Tests SHALL incluir un test que verifica exit code `3` cuando se proporciona un directorio inaccesible o configuración inválida.
6. THE Integration_Tests SHALL incluir un test que verifica que el flag `--exclude` omite los archivos que coinciden con el patrón.
7. THE Integration_Tests SHALL incluir un test que verifica que el flag `--report json` genera un archivo JSON con schema SARIF válido.

---

### Requisito 17: Corrección de Documentación — README

**User Story:** Como usuario nuevo de TMAC, quiero que el README refleje la información correcta sobre versión de Python, exit codes y schema de reglas, para no ser inducido a error por documentación desactualizada.

#### Criterios de Aceptación

1. THE README SHALL especificar Python 3.10+ como requisito mínimo (consistente con `pyproject.toml`).
2. THE README SHALL documentar los exit codes correctos del PRD: `0` (sin hallazgos), `1` (Critical), `2` (High sin Critical), `3` (error de ejecución).
3. THE README SHALL mostrar el schema correcto de `threats.yaml` con IDs en formato `TMAC-AWS-{SERVICE}-{NNN}`.
4. THE README SHALL incluir la tabla completa de flags CLI incluyendo `--exclude`, `--no-color`, y `--verbose`.
5. THE README SHALL incluir ejemplos de uso de CI/CD (GitHub Actions y GitLab CI) consistentes con el PRD Sección 8.

---

### Requisito 18: Documentación Adicional — CHANGELOG y CONTRIBUTING

**User Story:** Como contribuidor del proyecto, quiero un `CHANGELOG.md` y un `CONTRIBUTING.md`, para entender el historial de cambios y cómo contribuir al proyecto.

#### Criterios de Aceptación

1. THE Project SHALL incluir un archivo `CHANGELOG.md` en la raíz del repositorio con la entrada de la versión `v1.0.0 "Ixtla"`.
2. THE CHANGELOG SHALL seguir el formato Keep a Changelog (https://keepachangelog.com) con secciones: `Added`, `Fixed`, `Changed`.
3. THE Project SHALL incluir un archivo `CONTRIBUTING.md` con instrucciones para: configurar el entorno de desarrollo, ejecutar los tests, y el proceso para contribuir nuevas reglas.
4. THE CONTRIBUTING SHALL documentar el schema de `threats.yaml` con ejemplos de reglas válidas.

---

### Requisito 19: Sincronización de threats.yaml — DOCS vs src

**User Story:** Como mantenedor del proyecto, quiero que `DOCS/threats.yaml` y `src/tmac/rules/aws/threats.yaml` estén sincronizados, para que la documentación refleje las reglas reales implementadas.

#### Criterios de Aceptación

1. THE DOCS_threats_yaml SHALL contener exactamente las mismas reglas que `src/tmac/rules/aws/threats.yaml` o ser un subconjunto documentado explícitamente.
2. THE DOCS_threats_yaml SHALL incluir una nota que indique si es la versión completa o un subconjunto de referencia.
3. THE aws_stride_mapping SHALL referenciar los IDs de regla específicos (`TMAC-AWS-XXX-NNN`) en la columna "Reglas TMAC Evaluadas" para cada servicio que tenga reglas implementadas.
4. THE aws_stride_mapping SHALL incluir una sección que distinga entre reglas implementadas y servicios planificados para versiones futuras.
5. THE DOCS_threats_yaml SHALL corregir la regla `TMAC-AWS-VPC-001` para que use un mecanismo de detección técnicamente correcto o incluya documentación explícita del workaround y sus limitaciones.

---

### Requisito 20: Parser — Serialización y Pretty Printer

**User Story:** Como desarrollador que extiende TMAC, quiero que el TerraformParser tenga una función de serialización de ResourceModel a representación legible, para facilitar el debugging y la generación de reportes detallados.

#### Criterios de Aceptación

1. THE ResourceModel SHALL implementar un método `to_dict()` que retorna una representación de diccionario serializable a JSON.
2. FOR ALL `ResourceModel` objects producidos por el TerraformParser, serializar con `to_dict()` y deserializar con `ResourceModel(**data)` SHALL producir un objeto equivalente (propiedad round-trip de serialización de modelos).
3. THE ResourceModel SHALL incluir todos los campos en la serialización: `resource_type`, `name`, `attributes`, `source_file`, `line_number`.
