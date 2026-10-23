# Plan de Implementación: TMAC v1.2.0 "Ixtla" — AWS CloudFormation + OpenTofu Support

## Overview

Plan revisado el 2026-10-23 sobre la arquitectura de v1.1.x: el `Scanner` ya es independiente del
formato (`Scanner(parser=...)`), así que CloudFormation se añade como **un parser + un archivo de
reglas**, sin `CfnScanner` ni módulo `src/tmac/cfn/`. Las decisiones y sus motivos están en
`design.md` → *Revisión 2026-10-23*.

Orden: motor → parser → reglas → descubrimiento/OpenTofu → CLI → fixtures → tests → CI → docs.

## Tasks

- [x] 1. Preparar el motor para CloudFormation
  - [x] 1.1 `tmac.models.resource.INTRINSIC_FUNCTIONS` e `is_unresolved_reference()` para identificar RefSentinels
  - [x] 1.2 `Evaluator`: un RefSentinel cuenta para `exists`/`not_exists` pero ninguna comparación dispara hallazgo
  - [x] 1.3 `Evaluator`: `not_contains` evalúa la colección completa y trata un atributo ausente como "no contiene" (necesario para `Tags` de CFN)
  - [x] 1.4 Verificar que la línea base de Terraform no cambia (123 hallazgos en `tests/fixtures`)
  - _Requirements: 3.5, 3.6, 19.5_

- [x] 2. `CloudFormationParser` en `src/tmac/parsers/cloudformation.py`
  - [x] 2.1 `_CfnLoader` (subclase de `SafeLoader`, sin tocar el loader global): tags cortos `!X` → `{"Fn::X": v}`, `!Ref` → `{"Ref": v}`; fechas como string
  - [x] 2.2 Detección de formato por contenido (JSON si empieza con `{`), `parse_strict()` con `ParseError` y `parse()` lenient
  - [x] 2.3 Normalización de intrinsics a `{"Ref"|"Sub"|"GetAtt"|...: v}` (`GetAtt` lista → `"Res.Attr"`), con presupuesto de 1 M nodos (bombas de alias) y límite de 5 MB
  - [x] 2.4 Números de línea del LogicalId desde `yaml.compose` (YAML) o posición en el texto (JSON)
  - [x] 2.5 `tmac:ignore` por comentario (arriba o en la misma línea) y por `Metadata.tmac.ignore`; resultado en `ResourceModel.ignored_rules`; `get_ignore_map()`
  - [x] 2.6 `can_parse()`: `AWSTemplateFormatVersion` o `Type: AWS::` en el primer MB
  - [x] 2.7 `serialize()`, `serialize_to_yaml()` (intrinsics en forma larga) y `parse_template()`
  - _Requirements: 1, 2, 3, 4, 21_

- [x] 3. Reglas CFN en `src/tmac/rules/cfn/threats.yaml`
  - [x] 3.1 Metadata (`cloud`, `framework`, `description`, `last_updated`) y tabla `resource_type_mapping` CFN ↔ Terraform
  - [x] 3.2 43 reglas: S3 (5), IAM (9), SG (3), VPC (1), EC2 (4), RDS (5), DDB (3), KMS (3), Lambda (3), CloudTrail (3), API Gateway (3), Stack (1)
  - [x] 3.3 Comentarios para reglas Terraform sin equivalente (IAM-002, IAM-005, IAM-009)
  - [x] 3.4 `RuleLoader.BUILTIN_RULE_FILES` carga `aws/` y `cfn/`
  - _Requirements: 5–16, 19.3, 24_

- [x] 4. Descubrimiento de archivos y OpenTofu
  - [x] 4.1 `Scanner._discover_files()` con `os.walk` y `DEFAULT_EXCLUDED_DIRS` (`.git`, `.terraform`, `node_modules`, `venv`, ...)
  - [x] 4.2 `TerraformParser.file_patterns = ("*.tf", "*.tofu")`; `x.tofu` sustituye a `x.tf` (`can_parse`)
  - [x] 4.3 `collect_resource_ignores()` (`plan --source-dir`) también lee `.tofu`
  - [x] 4.4 `tmac plan`: ayuda de `--plan-file` menciona `tofu show -json` (formato idéntico, sin cambios en el parser)
  - _Requirements: OpenTofu-1, OpenTofu-2_

- [x] 5. Subcomando `tmac cfn`
  - [x] 5.1 Decorador `_directory_scan_options` compartido por `scan` y `cfn` (mismas opciones, más `--lenient`)
  - [x] 5.2 `_run_directory_scan()` común; `cfn` usa `CloudFormationParser`, reporte `tmac-cfn-report.{fmt}` y mensaje `CFN scan complete: ...`
  - [x] 5.3 `scan` y `plan` sin cambios de comportamiento (tests existentes en verde)
  - _Requirements: 17, 18_

- [x] 6. Fixtures en `tests/fixtures/cfn/`
  - [x] 6.1 Generales: `valid_multi_resource.yaml`, `valid_template.json` (equivalentes), `intrinsic_functions.yaml`, `tmac_ignore.yaml`, `empty_resources.yaml`, `no_resources.yaml`
  - [x] 6.2 `invalid/` (YAML y JSON rotos) y `not_cfn/` (k8s, `package.json`, Helm)
  - [x] 6.3 `services/{s3,iam,sg,vpc,ec2,rds,ddb,kms,lambda,cloudtrail,apigw,stack}_{insecure,secure}.yaml`
  - [x] 6.4 `tests/fixtures/plans/tofu_create_with_threat.json`
  - _Requirements: 22.1, 22.2_

- [x] 7. Tests
  - [x] 7.1 `tests/unit/test_cfn_parser.py`: YAML/JSON, líneas, intrinsics, ignores, errores, límites, round-trip
  - [x] 7.2 `tests/unit/test_cfn_rules.py`: cada fixture inseguro dispara exactamente las reglas de su servicio, el seguro ninguna; toda regla cubierta; casos de regex
  - [x] 7.3 `tests/integration/test_cfn_scanner.py`: `Scanner(parser=CloudFormationParser())`, mezcla `.tf`/CFN, incidencias, severidad, reporters
  - [x] 7.4 `tests/integration/test_cfn_cli.py`: exit codes 0/1/2/3, `--lenient`, reporte por defecto, `--exclude`/`--severity`, separación `TMAC-AWS-`/`TMAC-CFN-`
  - [x] 7.5 `tests/property/test_cfn_parser_properties.py`: P1–P12
  - [x] 7.6 `tests/integration/test_opentofu.py`: `.tofu`, mezcla, sustitución, `--exclude`, plan de OpenTofu, directorios excluidos
  - [x] 7.7 `tests/unit/test_evaluator.py`: `not_contains` sobre colecciones y RefSentinels
  - [x] 7.8 No-regresión: línea base de `tmac scan` (`tests/integration/test_plan_cli.py`) y suite de `tmac plan` sin cambios
  - _Requirements: 22, 23_

- [x] 8. CI: el smoke test de Python 3.10 ejecuta también `tmac cfn` y exige hallazgos

- [x] 9. Documentación
  - [x] 9.1 README: `tmac cfn`, formato soportado, intrinsics, `tmac:ignore` en CFN, tabla CFN ↔ Terraform, GitHub Actions, limitaciones, OpenTofu y directorios excluidos
  - [x] 9.2 CHANGELOG: entrada v1.2.0 con reglas por servicio
  - [x] 9.3 Spec: revisión de `design.md` y nota en `requirements.md`
  - _Requirements: 25_

- [ ] 10. Release v1.2.0
  - [ ] 10.1 Subir `tmac.__version__` y `pyproject.toml` a `1.2.0` y fechar la entrada del CHANGELOG
  - [ ] 10.2 Tag `v1.2.0`

- [ ] 11. Pendientes detectados (fuera del alcance de v1.2.0)
  - [ ] 11.1 Reglas para `AWS::IAM::AccessKey`, políticas inline de `AWS::IAM::User` y `AWS::RDS::DBCluster`
  - [ ] 11.2 Correlación puerto/CIDR por regla de ingreso en Security Groups (Terraform y CFN)
  - [ ] 11.3 Resolución de `Parameters`/`Mappings`/`Conditions` (llega con el grafo de dependencias, v2.2.0)
