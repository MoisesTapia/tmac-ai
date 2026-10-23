# Diseño Técnico: TMAC v1.2.0 "Ixtla" — AWS CloudFormation Support

## Revisión 2026-10-23 — Ajustes al implementar

Esta revisión alinea el diseño con la arquitectura vigente tras el refactor de v1.1.x y con lo
que el motor de reglas puede expresar. Prevalece sobre el texto original donde se contradigan.

| Tema | Diseño original | Implementado | Motivo |
| :--- | :--- | :--- | :--- |
| Orquestador | `CfnScanner` nuevo en `src/tmac/cfn/scanner.py` | `Scanner(parser=CloudFormationParser())` (sin módulo `cfn/`) | El `Scanner` ya es independiente del formato; un tercer orquestador duplicaría estadísticas, severidad, ignores y descubrimiento. |
| Detección de templates | `CfnScanner._is_cfn_template()` (parseo completo de cada YAML/JSON) | `CloudFormationParser.can_parse()`: búsqueda de `AWSTemplateFormatVersion` o `Type: AWS::` en el primer MB | Barato, y no descarta en silencio un template roto: si parece CFN y no parsea, se reporta. |
| Errores de parseo | `[]` + log | `parse_strict()` lanza `ParseError` → incidencia en `ScanResult.issues` → exit 3 (salvo `--lenient`); `parse()` conserva el contrato `[]` + log | Fail closed (v1.1.x). |
| Intrinsic functions | Loader que modifica `yaml.SafeLoader` global; tags desconocidos → `{"CFNTag": tag}` | Subclase `_CfnLoader`; toda forma corta `!X v` → `{"Fn::X": v}` y se normaliza igual que la forma larga a `{"X": v}` (`GetAtt` → `"Res.Attr"`) | No contaminar PyYAML global; equivalencia YAML/JSON; no perder el valor de tags desconocidos. |
| Semántica de un RefSentinel | `exists` → True, `not_exists` → False, `equals` → False | Igual, y además **ninguna** comparación (`not_equals`, `not_in`, `regex`, …) produce hallazgo | Con `not_equals [true]`, `Encrypted: !Ref P` sería un falso positivo seguro. |
| `tmac:ignore` | Pre-scan por indentación de 2 espacios | Líneas del LogicalId tomadas del árbol YAML (`yaml.compose`) o de la posición en el JSON; comentario arriba o en la misma línea; además `Metadata.tmac.ignore` (sirve en JSON) | Robusto ante cualquier indentación; JSON no admite comentarios. |
| Ignores en el pipeline | `get_ignore_map()` + `combined_ignore_map` en el scanner | Las supresiones viajan en `ResourceModel.ignored_rules`; `get_ignore_map()` se mantiene | Mismo mecanismo que Terraform desde v1.1.x (sin colisiones por nombre entre archivos). |
| `RuleLoader` | Cambio dentro de `_load_file()` | `BUILTIN_RULE_FILES = (aws/threats.yaml, cfn/threats.yaml)` en `load_rules()` | Más simple; interfaz pública sin cambios. |
| Reglas "`== false` o ausente" | — (el DSL no tiene OR) | `not_equals: [true, "true"]` | Cubre ambos casos; CFN acepta booleanos como string. |
| `TMAC-CFN-IAM-006` | "Existe un `AWS::IAM::User`" | `LoginProfile exists` (usuario con contraseña de consola) | Sin atributo obligatorio no hay condición expresable; el riesgo concreto es la credencial de consola. |
| `TMAC-CFN-KMS-002` | `PendingWindowInDays < 7` o ausente | `Enabled == false` (equivalente a `TMAC-AWS-KMS-002`) | CFN no admite valores < 7 y el DSL no tiene comparaciones numéricas; "ausente" usa el default seguro de 30 días. |
| `TMAC-CFN-LMD-001` | Nombre con `password/secret/key/token` | Nombre sensible (`password`, `secret`, `token`, `api_key`, `access_key`, `private_key`, …) **con valor literal** (no `{{resolve:…}}` ni `!Ref`) | `key` sola marcaba `KMS_KEY_ARN`; las referencias dinámicas son la mitigación recomendada. |
| `TMAC-CFN-VPC-001` | `Tags.FlowLogs` not_exists | `Tags not_contains {Key: FlowLogs, Value: enabled}` | En CFN `Tags` es una lista `{Key, Value}`; `not_contains` pasa a evaluar la colección completa. |
| `TMAC-CFN-EC2-001` | Solo `AWS::EC2::Instance` | Además `TMAC-CFN-EC2-004` para `AWS::EC2::LaunchTemplate` | IMDS se configura habitualmente en la plantilla de lanzamiento. |
| `TMAC-CFN-APIGW-001` | `AuthorizationType == NONE` | Excluye `HttpMethod: OPTIONS` | Preflight CORS es público por diseño. |
| Reglas extra | — | `IAM-007/008` (`AWS::IAM::ManagedPolicy`), `IAM-009` (políticas inline de rol), `STACK-001` (nested stack por HTTP) | Formas habituales de IAM en CFN; Requisito 24.5. |
| Descubrimiento | `rglob` + filtro | `os.walk` que no entra en `.git`, `.terraform`, `node_modules`, `venv`, … | Con `*.json`/`*.yaml` recorrer dependencias vendorizadas es costoso y ruidoso. |
| Seguridad del parser | — | Límite de 5 MB por template y de 1 M nodos al normalizar (bombas de alias YAML) | Un template malicioso en un PR no debe colgar el CI. |
| OpenTofu | Tareas 13.x | `TerraformParser.file_patterns = ("*.tf", "*.tofu")`, `x.tofu` sustituye a `x.tf`; `tofu show -json` sin cambios en `plan` | — |

Total implementado: **43 reglas CFN** (S3 5, IAM 9, SG 3, VPC 1, EC2 4, RDS 5, DDB 3, KMS 3,
Lambda 3, CloudTrail 3, API Gateway 3, Stack 1).

## Overview

Este documento describe el diseño técnico completo (High-Level + Low-Level) para TMAC v1.2.0 "Ixtla".
La nueva capacidad central es el **soporte nativo para AWS CloudFormation templates** en formato YAML
y JSON. El mismo engine de reglas STRIDE (Evaluator, Matcher, RuleLoader) que analiza Terraform en
v1.0.0 ahora también analiza CloudFormation, sin modificaciones al núcleo.

El diferenciador arquitectónico de esta versión es la separación limpia entre parsers e engine:
el `CloudFormationParser` implementa `BaseParser` y produce `ResourceModel` objects con el mismo
esquema que el `TerraformParser`, permitiendo que el pipeline de análisis existente funcione sin
cambios. Las reglas CFN son un nuevo conjunto YAML con `resource_type` en formato CloudFormation
(`AWS::S3::Bucket`, `AWS::IAM::Role`, etc.) y IDs con prefijo `TMAC-CFN-`.

El pipeline de v1.2.0 es paralelo al de v1.0.0:

```
CLI (tmac cfn) → Scanner(parser=CloudFormationParser()) → RuleLoader → Matcher/Evaluator → Reporter → salida
```

Los módulos `RuleLoader`, `Evaluator`, `Matcher` y todos los reporters de v1.0.0 se reutilizan
sin modificaciones.


## Architecture

### High-Level: Módulos nuevos y dependencias

```
src/tmac/
├── cli.py                              ← EXTEND: añade subcomando `tmac cfn`
├── parsers/
│   └── cloudformation.py              ← NUEVO: CloudFormationParser (implementa BaseParser)
└── rules/
    ├── aws/
    │   └── threats.yaml               ← EXISTENTE: reglas Terraform (sin cambios)
    └── cfn/
        ├── __init__.py                ← NUEVO: paquete de reglas CFN
        └── threats.yaml              ← NUEVO: reglas STRIDE para recursos CFN

tests/
├── unit/
│   ├── test_cfn_parser.py             ← NUEVO: tests unitarios del CloudFormationParser
│   └── test_cfn_rules.py              ← NUEVO: tests unitarios de reglas CFN por servicio
├── integration/
│   ├── test_cfn_cli.py                ← NUEVO: tests CLI end-to-end con CliRunner
│   ├── test_cfn_scanner.py            ← NUEVO: Scanner(parser=CloudFormationParser()) con fixtures
│   ├── test_opentofu.py               ← NUEVO: .tofu, planes de OpenTofu y directorios excluidos
│   └── test_regression.py            ← EXTEND: no-regresión de tmac scan y tmac plan
├── property/
│   └── test_cfn_parser_properties.py  ← NUEVO: property-based tests con Hypothesis
└── fixtures/
    └── cfn/                           ← NUEVO: templates CFN de ejemplo por escenario
        ├── valid_multi_resource.yaml
        ├── valid_template.json
        ├── intrinsic_functions.yaml
        ├── tmac_ignore.yaml
        ├── empty_resources.yaml
        ├── invalid_yaml.yaml
        ├── invalid_json.json
        └── services/
            ├── s3_insecure.yaml
            ├── s3_secure.yaml
            ├── iam_insecure.yaml
            ├── iam_secure.yaml
            ├── sg_insecure.yaml
            ├── sg_secure.yaml
            ├── vpc_insecure.yaml
            ├── vpc_secure.yaml
            ├── ec2_insecure.yaml
            ├── ec2_secure.yaml
            ├── rds_insecure.yaml
            ├── rds_secure.yaml
            ├── ddb_insecure.yaml
            ├── ddb_secure.yaml
            ├── kms_insecure.yaml
            ├── kms_secure.yaml
            ├── lambda_insecure.yaml
            ├── lambda_secure.yaml
            ├── cloudtrail_insecure.yaml
            ├── cloudtrail_secure.yaml
            ├── apigw_insecure.yaml
            └── apigw_secure.yaml
```

### Flujo de datos del subcomando `tmac cfn`

```
tmac cfn --dir ./infra --report html --fail-on critical
    │
    ▼
cli.py::cfn() → _run_directory_scan()       # mismas opciones y lógica que `scan`
    │
    ▼
Scanner(parser=CloudFormationParser()).run_scan()
    ├── config (.tmac.yaml / --config)
    ├── os.walk: *.yaml/*.yml/*.json/*.template, sin DEFAULT_EXCLUDED_DIRS ni --exclude
    ├── CloudFormationParser.can_parse()       # ¿parece un template CFN?
    ├── CloudFormationParser.parse_strict()    # ResourceModel[] con ignored_rules;
    │                                          # ParseError → ScanResult.issues
    ├── RuleLoader.load_rules()                # aws/threats.yaml + cfn/threats.yaml (+ --rules-dir)
    ├── Matcher.match()                        # reglas por resource_type
    └── ScanResult(..., issues)
    │
    ▼
Reporter.generate(result) → cli: exit 0/1/2/3
```

### Relación con los pipelines de v1.0.0 y v1.1.0

```
                    ┌──────────────────────────────────────────────────────────┐
                    │  Compartido: Scanner · RuleLoader · Matcher · Evaluator  │
                    │              Reporters · severidad · ignores · issues    │
                    └──────┬─────────────────────┬─────────────────────┬───────┘
                           ▼                     ▼                     ▼
                  tmac scan (v1.0)       tmac cfn (v1.2)        tmac plan (v1.1)
                  TerraformParser        CloudFormationParser   TfplanParser + DeltaScanner
                  *.tf, *.tofu           *.yaml/*.json CFN      plan JSON (terraform/tofu)
```

## Components and Interfaces

### 1. `src/tmac/parsers/cloudformation.py` — CloudFormationParser

Responsabilidad única: parsear un template CFN (YAML o JSON) y retornar una lista de `ResourceModel`.
Implementa `BaseParser`. También expone `get_ignore_map()` para el mecanismo `tmac:ignore`.

```python
class CloudFormationParser(BaseParser):
    def parse(self, file_path: str) -> List[ResourceModel]:
        """
        Parsea un template CFN (YAML o JSON) y retorna ResourceModel[].
        - Detecta formato por contenido (no solo extensión).
        - Mapea LogicalId → ResourceModel.name
        - Mapea Type → ResourceModel.resource_type
        - Mapea Properties → ResourceModel.attributes
        - Sustituye Intrinsic Functions por RefSentinel.
        - Retorna [] con logger.warning() si el archivo no existe,
          no es válido, o no tiene sección Resources.
        """

    def get_ignore_map(self, file_path: str) -> Dict[str, List[str]]:
        """
        Retorna el mapa de supresiones {LogicalId: ["*"] | ["RULE-ID-1", ...]}.
        Detecta comentarios YAML '# tmac:ignore' y '# tmac:ignore[RULE-ID]'
        en la línea inmediatamente anterior al LogicalId del recurso.
        Solo aplica a templates YAML (los templates JSON no soportan comentarios).
        """

    def serialize(self, resources: List[ResourceModel]) -> dict:
        """
        Serializa ResourceModel[] a dict con estructura CFN:
        {"Resources": {name: {"Type": resource_type, "Properties": attributes}}}
        Preserva RefSentinel como valores sin resolverlos.
        """

    def serialize_to_yaml(self, resources: List[ResourceModel]) -> str:
        """
        Serializa ResourceModel[] a string YAML en formato de template CFN.
        Usa yaml.dump() con default_flow_style=False.
        """

    def _detect_format(self, content: str) -> str:
        """
        Detecta si el contenido es YAML o JSON.
        Intenta json.loads() primero; si falla, asume YAML.
        Retorna 'json' o 'yaml'.
        """

    def _resolve_intrinsic(self, value: Any) -> Any:
        """
        Recorre recursivamente el valor y sustituye Intrinsic Functions:
        - {"Ref": "X"} → {"Ref": "X"} (ya es RefSentinel, preservar)
        - {"Fn::Sub": "..."} → {"Sub": "..."}
        - {"Fn::GetAtt": "..."} → {"GetAtt": "..."}
        - Valores escalares y listas se procesan recursivamente.
        - Nunca lanza excepción.
        """

    def _parse_yaml_with_sentinels(self, content: str) -> dict:
        """
        Parsea YAML usando yaml.safe_load() con un Loader personalizado
        que convierte los constructores !Ref, !Sub, !GetAtt a dicts
        (RefSentinel) en lugar de lanzar excepciones por tags desconocidos.
        """
```

**Manejo de Intrinsic Functions — YAML custom Loader:**

CloudFormation usa constructores YAML especiales (`!Ref`, `!Sub`, `!GetAtt`) que `yaml.safe_load()`
rechaza por defecto. La solución es registrar constructores personalizados:

```python
def _build_cfn_loader() -> type:
    """Construye un Loader YAML que convierte tags CFN a RefSentinel dicts."""
    loader = yaml.SafeLoader

    def ref_constructor(loader, node):
        return {"Ref": loader.construct_scalar(node)}

    def sub_constructor(loader, node):
        return {"Sub": loader.construct_scalar(node)}

    def getatt_constructor(loader, node):
        return {"GetAtt": loader.construct_scalar(node)}

    def select_constructor(loader, node):
        return {"Select": loader.construct_sequence(node)}

    def join_constructor(loader, node):
        return {"Join": loader.construct_sequence(node)}

    loader.add_constructor("!Ref", ref_constructor)
    loader.add_constructor("!Sub", sub_constructor)
    loader.add_constructor("!GetAtt", getatt_constructor)
    loader.add_constructor("!Select", select_constructor)
    loader.add_constructor("!Join", join_constructor)
    # Registrar constructor genérico para cualquier otro tag CFN
    loader.add_multi_constructor("!", lambda l, t, n: {"CFNTag": t})
    return loader
```

**Mecanismo `tmac:ignore` en YAML:**

El parser lee el archivo YAML línea por línea para detectar comentarios antes de los LogicalIds.
Esto se hace en un pre-scan separado del parseo estructural:

```python
def _prescan_ignore_comments(self, file_path: str) -> Dict[str, List[str]]:
    """
    Lee el archivo línea por línea buscando el patrón:
      # tmac:ignore           → supresión global para el siguiente LogicalId
      # tmac:ignore[RULE-ID]  → supresión específica para el siguiente LogicalId

    El LogicalId se detecta como una línea con indentación de 2 espacios
    seguida de ':' (patrón de clave YAML en la sección Resources).
    """
```

### 2. Orquestación — `Scanner(parser=CloudFormationParser())` (sustituye a `CfnScanner`)

No hay módulo `src/tmac/cfn/`. El `Scanner` genérico recibe el parser; el contrato de
`BaseParser` cubre lo que `CfnScanner` hacía a mano:

```python
class BaseParser(ABC):
    file_patterns: ClassVar[tuple[str, ...]] = ()   # ("*.yaml", "*.yml", "*.json", "*.template")
    def can_parse(self, file_path: str) -> bool      # sustituye a _is_cfn_template()
    def parse(self, file_path: str) -> list[ResourceModel]          # lenient: [] + log
    def parse_strict(self, file_path: str) -> list[ResourceModel]   # lanza ParseError
```

`Scanner.run_scan(directory, rules_dir, exclude_patterns, min_severity, verbose, config)` es la
firma pedida en el Requisito 18.1; `files_scanned`, `rules_loaded`, estadísticas y filtro de
severidad son los mismos que para Terraform (Requisito 18.6–18.7).

### 3. `src/tmac/rules/cfn/threats.yaml` — Reglas CFN

Archivo YAML con las reglas STRIDE para recursos CloudFormation. Mismo schema que `aws/threats.yaml`.
Contiene ≥ 30 reglas cubriendo los 11 servicios AWS especificados.

**Schema de una regla CFN:**

```yaml
- id: TMAC-CFN-S3-001
  name: "S3 Bucket con Acceso Público (AccessControl)"
  resource_type: "AWS::S3::Bucket"
  check:
    attribute: "AccessControl"
    condition: "in"
    values: ["PublicRead", "PublicReadWrite"]
  severity: "Critical"
  stride: "Information Disclosure"
  description: >
    Se detectó un bucket S3 con AccessControl pública en CloudFormation.
    Esto permite que cualquier usuario en internet lea o escriba archivos
    en el bucket, exponiendo datos sensibles a acceso no autorizado.
  mitigation: >
    Elimina la propiedad AccessControl o establécela en 'Private'.
    Añade AWS::S3::BucketPolicy con restricciones explícitas.
  references:
    - "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html"
  tags: ["s3", "public-access", "data-exposure", "cfn"]
```

**Tabla de mapeo de tipos de recursos CFN ↔ Terraform:**

| Servicio | Tipo CFN | Tipo Terraform |
|----------|----------|----------------|
| S3 | `AWS::S3::Bucket` | `aws_s3_bucket` |
| IAM Policy | `AWS::IAM::Policy` | `aws_iam_policy` |
| IAM Role | `AWS::IAM::Role` | `aws_iam_role` |
| IAM User | `AWS::IAM::User` | `aws_iam_user` |
| Security Group | `AWS::EC2::SecurityGroup` | `aws_security_group` |
| VPC | `AWS::EC2::VPC` | `aws_vpc` |
| EC2 Instance | `AWS::EC2::Instance` | `aws_instance` |
| EBS Volume | `AWS::EC2::Volume` | `aws_ebs_volume` |
| RDS | `AWS::RDS::DBInstance` | `aws_db_instance` |
| DynamoDB | `AWS::DynamoDB::Table` | `aws_dynamodb_table` |
| KMS | `AWS::KMS::Key` | `aws_kms_key` |
| Lambda | `AWS::Lambda::Function` | `aws_lambda_function` |
| CloudTrail | `AWS::CloudTrail::Trail` | `aws_cloudtrail` |
| API GW Method | `AWS::ApiGateway::Method` | `aws_api_gateway_method` |
| API GW Stage | `AWS::ApiGateway::Stage` | `aws_api_gateway_stage` |


### 4. `src/tmac/cli.py` — Extensión con subcomando `tmac cfn`

Se añade el subcomando `cfn` al grupo `cli` existente. Los subcomandos `scan` y `plan` no se modifican.

```python
@cli.command()
@click.option("--dir", "-d", "directory", default=".", type=click.Path(exists=True),
              help="Directorio con templates CloudFormation.")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]),
              help="Formato de salida.")
@click.option("--output", "-o", type=click.Path(), help="Ruta del archivo de salida.")
@click.option("--rules-dir", type=click.Path(exists=True),
              help="Directorio de reglas adicionales.")
@click.option("--config", type=click.Path(), default=".tmac.yaml",
              help="Archivo de configuración.")
@click.option("--fail-on", type=click.Choice(["critical", "high", "medium", "low", "info"]),
              help="Umbral de severidad para exit 1.")
@click.option("--severity", type=click.Choice(["all", "critical", "high", "medium", "low", "info"]),
              help="Severidad mínima a mostrar.")
@click.option("--quiet", "-q", is_flag=True, help="Suprime salida stdout.")
@click.option("--exclude", "-e", "exclude", multiple=True, type=click.STRING,
              help="Patrones glob a excluir (repetible).")
@click.option("--no-color", "no_color", is_flag=True, help="Deshabilita colores ANSI.")
@click.option("--verbose", "-v", is_flag=True, help="Habilita logging de debug.")
def cfn(directory, report, output, rules_dir, config, fail_on, severity,
        quiet, exclude, no_color, verbose) -> None:
    """Analiza templates CloudFormation para detectar amenazas STRIDE."""
```

**Exit codes del subcomando `tmac cfn`** (idénticos a `tmac scan`):

| Código | Condición |
|--------|-----------|
| `0` | Sin findings con severidad ≥ umbral `--fail-on` |
| `1` | Al menos un finding Critical |
| `2` | Finding High sin ninguno Critical |
| `3` | Error de ejecución (directorio no existe, error de parseo fatal) |

**Nombre de archivo de reporte por defecto:** `tmac-cfn-report.{fmt}` (distinto de `tmac-report.{fmt}` de `scan`).

**Implementación:** `scan` y `cfn` comparten el decorador `_directory_scan_options` y la función
`_run_directory_scan(ctx, parser, default_report_name, done_message, **opts)`; solo cambian el parser,
el nombre del reporte y el mensaje (`CFN scan complete: …`). También heredan `--lenient`.

### 5. Extensión del `RuleLoader` para cargar `cfn/threats.yaml`

```python
RULES_DIR = Path(__file__).parent.parent / "rules"
BUILTIN_RULE_FILES = (RULES_DIR / "aws" / "threats.yaml", RULES_DIR / "cfn" / "threats.yaml")
```

`load_rules()` carga ambos archivos (un archivo ausente se registra como incidencia) y después
`--rules-dir`. La interfaz pública no cambia. Como cada regla solo aplica a su `resource_type`,
`tmac scan` produce los mismos hallazgos que antes (verificado por el test de no-regresión).

### 6. Reporters — Sin modificaciones

Los tres reporters (`HTMLReporter`, `MarkdownReporter`, `JSONReporter`) funcionan sin cambios
porque el `CfnScanner` retorna un `ScanResult` estándar con `Finding` objects estándar.
La única diferencia visible es que los `rule_id` tienen prefijo `TMAC-CFN-` en lugar de `TMAC-AWS-`.

```
HTMLReporter.generate(ScanResult)    → HTML con findings CFN (rule_id: TMAC-CFN-S3-001)
MarkdownReporter.generate(ScanResult) → MD con findings CFN
JSONReporter.generate(ScanResult)    → SARIF con findings CFN (ruleId: TMAC-CFN-S3-001)
```


## Data Models

No se introducen nuevos modelos de datos en v1.2.0. El `CloudFormationParser` produce
`ResourceModel` objects estándar y el `CfnScanner` retorna `ScanResult` estándar.

### ResourceModel — Mapeo desde template CFN

```python
# Template CFN de entrada:
# Resources:
#   MyBucket:                          ← LogicalId → ResourceModel.name = "MyBucket"
#     Type: AWS::S3::Bucket            ← Type → ResourceModel.resource_type = "AWS::S3::Bucket"
#     Properties:                      ← Properties → ResourceModel.attributes = {...}
#       AccessControl: PublicRead
#       BucketEncryption: ...

ResourceModel(
    resource_type = "AWS::S3::Bucket",
    name          = "MyBucket",
    attributes    = {"AccessControl": "PublicRead", "BucketEncryption": {...}},
    source_file   = "/path/to/template.yaml",
    line_number   = 3,   # línea del LogicalId "MyBucket:" en el archivo
)
```

### RefSentinel — Representación de Intrinsic Functions

```python
# Forma corta y larga producen lo mismo:
#   BucketName: !Ref EnvParam          / {"Ref": "EnvParam"}           → {"Ref": "EnvParam"}
#   RoleArn: !GetAtt MyRole.Arn        / {"Fn::GetAtt": [MyRole, Arn]} → {"GetAtt": "MyRole.Arn"}
#   LogBucket: !Sub "${Env}-logs"      / {"Fn::Sub": "${Env}-logs"}    → {"Sub": "${Env}-logs"}
#   Encrypted: !If [C, true, false]                                    → {"If": ["C", True, False]}

# tmac.models.resource.is_unresolved_reference(value) identifica estos valores
# (dict de una sola clave en INTRINSIC_FUNCTIONS). En el Evaluator:
# - exists → True, not_exists → False
# - cualquier comparación (equals, not_equals, in, not_in, contains, not_contains, regex) → False
```

### IgnoreMap — Estructura del mapa de supresiones

```python
# Tipo: Dict[str, List[str]]
# Clave: LogicalId del recurso
# Valor: ["*"] para supresión global, o lista de RULE-IDs para supresión específica

ignore_map = {
    "MyBucket": ["*"],                              # suprime todos los findings
    "WebServerRole": ["TMAC-CFN-IAM-001"],          # suprime solo esta regla
    "AppSG": ["TMAC-CFN-SG-001", "TMAC-CFN-SG-002"], # suprime dos reglas
}
```

### ScanResult — Campos relevantes para CFN

```python
ScanResult(
    metadata=ScanMetadata(
        tool_name="TMAC",
        version="1.2.0",
        scanned_directory="/path/to/infra",
        execution_time_seconds=0.42,
    ),
    statistics=ScanStatistics(
        total_resources=15,   # total de ResourceModel parseados de todos los templates
        total_findings=7,
        critical=1,
        high=3,
        medium=2,
        low=1,
        info=0,
    ),
    findings=[Finding(rule_id="TMAC-CFN-S3-001", ...)],
    files_scanned=3,          # número de templates CFN procesados
    rules_loaded=45,          # reglas Terraform + reglas CFN
)
```


## Reglas CFN — Catálogo Implementado

Condiciones tal como están en `src/tmac/rules/cfn/threats.yaml`. `STAR` es la regex
`^\*$|'\*'` (un `"*"` literal, solo o dentro de una lista; no coincide con `s3:*` ni `arn:…/*`).
`not_equals [true]` significa `not_equals: [true, "true"]` (false **o ausente**).

| ID | Tipo CFN | Condición | Sev. | STRIDE |
|----|----------|-----------|------|--------|
| S3-001 | `AWS::S3::Bucket` | `AccessControl` in `[PublicRead, PublicReadWrite]` | Critical | Information Disclosure |
| S3-002 | `AWS::S3::Bucket` | `BucketEncryption` not_exists | High | Information Disclosure |
| S3-003 | `AWS::S3::Bucket` | `LoggingConfiguration` not_exists | Medium | Repudiation |
| S3-004 | `AWS::S3::Bucket` | `WebsiteConfiguration` exists | Medium | Information Disclosure |
| S3-005 | `AWS::S3::Bucket` | `ObjectLockEnabled` not_equals [true] | High | Tampering |
| IAM-001 | `AWS::IAM::Policy` | `PolicyDocument.Statement.Resource` regex STAR | High | Elevation of Privilege |
| IAM-002 | `AWS::IAM::Policy` | `PolicyDocument.Statement.Action` regex STAR | Critical | Elevation of Privilege |
| IAM-003 | `AWS::IAM::Role` | `AssumeRolePolicyDocument.Statement.Principal` regex STAR | Critical | Spoofing |
| IAM-004 | `AWS::IAM::Role` | `AssumeRolePolicyDocument` regex `^(?!.*sts:ExternalId)(?!.*AWS::AccountId).*arn:aws:iam::` | High | Spoofing |
| IAM-005 | `AWS::IAM::Policy` | `PolicyDocument` regex `iam:PassRole` AND `Statement.Resource` regex STAR | Critical | Elevation of Privilege |
| IAM-006 | `AWS::IAM::User` | `LoginProfile` exists | Medium | Spoofing |
| IAM-007 | `AWS::IAM::ManagedPolicy` | `PolicyDocument.Statement.Action` regex STAR | Critical | Elevation of Privilege |
| IAM-008 | `AWS::IAM::ManagedPolicy` | `PolicyDocument.Statement.Resource` regex STAR | High | Elevation of Privilege |
| IAM-009 | `AWS::IAM::Role` | `Policies` regex `'Action': ('\*'\|\[…'\*')` | Critical | Elevation of Privilege |
| SG-001 | `AWS::EC2::SecurityGroup` | `SecurityGroupIngress.FromPort` equals 22 AND `.CidrIp` equals `0.0.0.0/0` | High | Tampering |
| SG-002 | `AWS::EC2::SecurityGroup` | ídem con 3389 | Critical | Tampering |
| SG-003 | `AWS::EC2::SecurityGroup` | `SecurityGroupEgress.CidrIp` equals `0.0.0.0/0` | Medium | Information Disclosure |
| VPC-001 | `AWS::EC2::VPC` | `Tags` not_contains `{Key: FlowLogs, Value: enabled\|Enabled\|true}` | Medium | Repudiation |
| EC2-001 | `AWS::EC2::Instance` | `MetadataOptions.HttpTokens` equals `optional` | Critical | Spoofing |
| EC2-002 | `AWS::EC2::Volume` | `Encrypted` not_equals [true] | High | Information Disclosure |
| EC2-003 | `AWS::EC2::Instance` | `NetworkInterfaces.AssociatePublicIpAddress` equals true | High | Tampering |
| EC2-004 | `AWS::EC2::LaunchTemplate` | `LaunchTemplateData.MetadataOptions.HttpTokens` equals `optional` | Critical | Spoofing |
| RDS-001 | `AWS::RDS::DBInstance` | `StorageEncrypted` not_equals [true] | Medium | Information Disclosure |
| RDS-002 | `AWS::RDS::DBInstance` | `PubliclyAccessible` equals true | High | Information Disclosure |
| RDS-003 | `AWS::RDS::DBInstance` | `MultiAZ` not_equals [true] | High | Denial of Service |
| RDS-004 | `AWS::RDS::DBInstance` | `DeletionProtection` not_equals [true] | High | Denial of Service |
| RDS-005 | `AWS::RDS::DBInstance` | `EnableCloudwatchLogsExports` not_exists | Medium | Repudiation |
| DDB-001 | `AWS::DynamoDB::Table` | `SSESpecification.SSEEnabled` not_equals [true] | High | Information Disclosure |
| DDB-002 | `AWS::DynamoDB::Table` | `PointInTimeRecoverySpecification.PointInTimeRecoveryEnabled` not_equals [true] | Medium | Denial of Service |
| DDB-003 | `AWS::DynamoDB::Table` | `DeletionProtectionEnabled` not_equals [true] | High | Denial of Service |
| KMS-001 | `AWS::KMS::Key` | `EnableKeyRotation` not_equals [true] | High | Information Disclosure |
| KMS-002 | `AWS::KMS::Key` | `Enabled` equals false | Medium | Denial of Service |
| KMS-003 | `AWS::KMS::Key` | `KeyPolicy.Statement.Principal` regex STAR | Critical | Information Disclosure |
| LMD-001 | `AWS::Lambda::Function` | `Environment.Variables`: nombre sensible con valor literal (regex) | High | Information Disclosure |
| LMD-002 | `AWS::Lambda::Function` | `TracingConfig.Mode` not_equals `Active` | Low | Repudiation |
| LMD-003 | `AWS::Lambda::Function` | `ReservedConcurrentExecutions` equals 0 | Medium | Denial of Service |
| CW-001 | `AWS::CloudTrail::Trail` | `IsLogging` not_equals [true] | High | Repudiation |
| CW-002 | `AWS::CloudTrail::Trail` | `EnableLogFileValidation` not_equals [true] | Medium | Tampering |
| CW-003 | `AWS::CloudTrail::Trail` | `IsMultiRegionTrail` not_equals [true] | Medium | Repudiation |
| APIGW-001 | `AWS::ApiGateway::Method` | `AuthorizationType` equals `NONE` AND `HttpMethod` not_equals `OPTIONS` | High | Spoofing |
| APIGW-002 | `AWS::ApiGateway::Stage` | `MethodSettings.LoggingLevel` not_exists | Medium | Repudiation |
| APIGW-003 | `AWS::ApiGateway::Stage` | `ClientCertificateId` not_exists | Medium | Information Disclosure |
| STACK-001 | `AWS::CloudFormation::Stack` | `TemplateURL` regex `(?i)^http://` | Medium | Tampering |

**Total: 43 reglas CFN.** Limitación heredada de Terraform: en SG-001/002 el puerto y el CIDR se
comprueban por separado entre todas las reglas de ingreso del grupo (sin correlación por regla).

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

---

### Property 1: Determinismo del Parser

*For any* template CFN válido (YAML o JSON), parsear el archivo dos veces consecutivas con el
`CloudFormationParser` debe producir listas de `ResourceModel` idénticas (mismo número, mismos
`name`, `resource_type` y `attributes`).

**Validates: Requisito 1.12, 2.5, P1**

---

### Property 2: Round-Trip YAML

*For any* lista de `ResourceModel` con `resource_type` en formato `AWS::*` y `attributes` sin
`RefSentinel`, serializar con `serialize_to_yaml()` y parsear nuevamente debe producir una lista
de `ResourceModel` con los mismos `resource_type`, `name` y `attributes`.

**Validates: Requisito 21.3, P2**

---

### Property 3: Round-Trip JSON

*For any* lista de `ResourceModel` con `resource_type` en formato `AWS::*` y `attributes` sin
`RefSentinel`, serializar con `serialize()` y parsear el diccionario resultante debe producir
una lista de `ResourceModel` equivalente.

**Validates: Requisito 21.4, P3**

---

### Property 4: Invariante de Conteo

*For any* template CFN válido con N recursos en la sección `Resources`, el `CloudFormationParser`
debe retornar exactamente N `ResourceModel` objects. No se pierden ni se duplican recursos.

**Validates: Requisito 1.2, P4**

---

### Property 5: No-Crash con Intrinsic Functions

*For any* template CFN con valores `!Ref`, `!Sub`, `!GetAtt` o cualquier otro tag CFN en
cualquier posición de `Properties`, el `CloudFormationParser` debe retornar una lista de
`ResourceModel` sin lanzar excepciones, y el número de `ResourceModel` debe ser igual al
número de recursos en la sección `Resources`.

**Validates: Requisito 3.8, P5**

---

### Property 6: Equivalencia YAML/JSON

*For any* template CFN semánticamente equivalente en YAML y JSON (sin Intrinsic Functions),
el `CloudFormationParser` debe producir listas de `ResourceModel` con los mismos `resource_type`,
`name` y `attributes`, independientemente del formato de entrada.

**Validates: Requisito 2.6, P6**

---

### Property 7: Consistencia de Estadísticas del ScanResult

*For any* `ScanResult` producido por el `CfnScanner`:
- `statistics.critical + statistics.high + statistics.medium + statistics.low + statistics.info == statistics.total_findings`
- `len(findings) == statistics.total_findings`

**Validates: Requisito 18.7, P7**

---

### Property 8: Monotonía del Filtro de Severidad

*For any* directorio D y severidades s1 ≤ s2 (Critical > High > Medium > Low > Info):
`len(CfnScanner().run_scan(D, min_severity=s2).findings) ≤ len(CfnScanner().run_scan(D, min_severity=s1).findings)`

Aumentar el umbral de severidad mínima nunca incrementa el número de findings.

**Validates: Requisito 18.6, P8**

---

### Property 9: Idempotencia del ignore_map

*For any* template CFN, llamar a `get_ignore_map()` dos veces debe retornar el mismo mapa.
El `ignore_map` es determinista.

**Validates: Requisito 4.4, P9**

---

### Property 10: Round-Trip de Serialización de Finding

*For any* `Finding` producido por el análisis CFN:
`Finding(**f.model_dump()) == f`

Los `Finding` objects son completamente serializables y reconstruibles sin pérdida de información.

**Validates: Requisito 20.3, P10**

---

### Property 11: Supresión Correcta por ignore_map

*For any* template CFN con un recurso R que tiene `# tmac:ignore[RULE-ID]`:
`RULE-ID ∉ {f.rule_id for f in CfnScanner().run_scan(T).findings where f.resource_name == R.LogicalId}`

Un recurso con `tmac:ignore[RULE-ID]` nunca aparece en los findings con ese `rule_id`.

**Validates: Requisito 4.5, 4.6, P11**

---

### Property 12: Separación de Reglas por Framework

*For any* `ScanResult` producido por `CfnScanner`:
`∀ f ∈ findings: f.rule_id.startswith("TMAC-CFN-")`

*For any* `ScanResult` producido por `Scanner` (Terraform):
`∀ f ∈ findings: f.rule_id.startswith("TMAC-AWS-")`

No hay mezcla de prefijos entre los dos pipelines.

**Validates: Requisito 19.7, P12**


## Error Handling

No hay `CfnScanError`: el `Scanner` lanza `ScanError` (directorio inaccesible, `.tmac.yaml`
inválido) y la CLI termina con exit 3.

### CloudFormationParser

| Condición | `parse_strict()` | `parse()` (lenient) |
|-----------|------------------|---------------------|
| Archivo no existe / no legible / > 5 MB | `ParseError` | `[]` + warning |
| YAML o JSON sintácticamente inválido | `ParseError` | `[]` + warning |
| Raíz que no es un mapping, `Resources` que no es un mapping | `ParseError` | `[]` + warning |
| Recurso sin `Type`, o `Properties` que no es un mapping | `ParseError` | `[]` + warning |
| Más de 1 M nodos al normalizar (bomba de alias) o anidamiento excesivo | `ParseError` | `[]` + warning |
| Template sin sección `Resources` | `[]` + warning | `[]` + warning |
| `Resources` vacío | `[]` | `[]` |
| Recurso sin `Properties` | `ResourceModel` con `attributes={}` | ídem |
| Intrinsic function desconocida (`!Foo v`) | `{"Foo": v}`, sin excepción | ídem |

### Scanner

| Condición | Comportamiento |
|-----------|----------------|
| Directorio sin templates CFN | `files_scanned=0`, sin findings ni incidencias |
| YAML/JSON que no parece CFN (`can_parse` = False) | Se omite (no es error) |
| `ParseError` en un template | `ScanIssue(kind="parse")`; el resto continúa; exit 3 salvo `--lenient` |
| Regla inválida o archivo de reglas ausente | `ScanIssue(kind="rules")`; exit 3 salvo `--lenient` |
| Directorio no existe | `ScanError` → exit 3 |

## Testing Strategy

### Enfoque dual: unit tests + property-based tests

Los tests unitarios cubren ejemplos concretos, casos borde y condiciones de error.
Los tests de propiedades verifican invariantes universales con inputs generados aleatoriamente.
Ambos son complementarios y necesarios para cobertura completa.

La librería de property-based testing es **Hypothesis**. Cada test de propiedad ejecuta mínimo
100 iteraciones (`@settings(max_examples=100)`). Cada test debe incluir un comentario con el tag:

```
# Feature: tmac-v1-2-cloudformation, Property N: <texto de la propiedad>
```

### Estructura de tests

```
tests/
├── unit/
│   ├── test_cfn_parser.py              # CloudFormationParser: YAML, JSON, Intrinsic, ignore, errores
│   └── test_cfn_rules.py               # Reglas CFN: disparo/no-disparo por servicio
├── integration/
│   ├── test_cfn_cli.py                 # CLI end-to-end: exit codes, formatos de reporte
│   ├── test_cfn_scanner.py             # Scanner(parser=CloudFormationParser()) con fixtures
│   ├── test_opentofu.py                # .tofu, planes de OpenTofu, directorios excluidos
│   └── test_regression.py             # No-regresión de tmac scan y tmac plan
├── property/
│   └── test_cfn_parser_properties.py   # Hypothesis: todas las propiedades del diseño
└── fixtures/
    └── cfn/
        ├── valid_multi_resource.yaml    # Template YAML con múltiples recursos
        ├── valid_template.json          # Template JSON equivalente
        ├── intrinsic_functions.yaml     # Template con !Ref, !Sub, !GetAtt
        ├── tmac_ignore.yaml             # Template con comentarios tmac:ignore
        ├── empty_resources.yaml         # Template con Resources vacío
        ├── no_resources.yaml            # Template sin sección Resources
        ├── invalid/                     # YAML y JSON sintácticamente inválidos
        ├── not_cfn/                     # k8s, package.json, Helm (deben ignorarse)
        └── services/                    # Templates por servicio (seguro e inseguro)
            ├── s3_insecure.yaml / s3_secure.yaml
            ├── iam_insecure.yaml / iam_secure.yaml
            ├── sg_insecure.yaml / sg_secure.yaml
            ├── vpc_insecure.yaml / vpc_secure.yaml
            ├── ec2_insecure.yaml / ec2_secure.yaml
            ├── rds_insecure.yaml / rds_secure.yaml
            ├── ddb_insecure.yaml / ddb_secure.yaml
            ├── kms_insecure.yaml / kms_secure.yaml
            ├── lambda_insecure.yaml / lambda_secure.yaml
            ├── cloudtrail_insecure.yaml / cloudtrail_secure.yaml
            ├── apigw_insecure.yaml / apigw_secure.yaml
            └── stack_insecure.yaml / stack_secure.yaml
```

### Tests unitarios — `test_cfn_parser.py`

```python
def test_parse_yaml_valid_template():
    """Template YAML válido retorna ResourceModel[] con todos los campos correctos."""

def test_parse_json_valid_template():
    """Template JSON válido retorna ResourceModel[] equivalentes al YAML."""

def test_logical_id_mapped_to_name():
    """LogicalId del recurso CFN se mapea a ResourceModel.name."""

def test_resource_type_mapped_correctly():
    """Type del recurso CFN se mapea a ResourceModel.resource_type."""

def test_properties_mapped_to_attributes():
    """Properties del recurso CFN se mapean a ResourceModel.attributes."""

def test_line_number_recorded():
    """line_number del ResourceModel corresponde a la línea del LogicalId en el archivo."""

def test_intrinsic_ref_becomes_sentinel():
    """!Ref X se convierte en {"Ref": "X"} en los attributes."""

def test_intrinsic_sub_becomes_sentinel():
    """!Sub "..." se convierte en {"Sub": "..."} en los attributes."""

def test_intrinsic_getatt_becomes_sentinel():
    """!GetAtt R.A se convierte en {"GetAtt": "R.A"} en los attributes."""

def test_nested_intrinsic_no_exception():
    """Intrinsic Functions anidadas no lanzan excepción."""

def test_no_resources_section_returns_empty():
    """Template sin sección Resources retorna lista vacía."""

def test_empty_resources_returns_empty():
    """Template con Resources vacío retorna lista vacía."""

def test_invalid_yaml_returns_empty():
    """YAML inválido retorna lista vacía sin excepción."""

def test_invalid_json_returns_empty():
    """JSON inválido retorna lista vacía sin excepción."""

def test_nonexistent_file_returns_empty():
    """Archivo inexistente retorna lista vacía sin excepción."""

def test_tmac_ignore_global():
    """# tmac:ignore antes de LogicalId suprime todos los findings para ese recurso."""

def test_tmac_ignore_specific_rule():
    """# tmac:ignore[RULE-ID] suprime solo esa regla para ese recurso."""

def test_tmac_ignore_multiple_rules():
    """Múltiples # tmac:ignore[RULE-ID] consecutivos acumulan todos los IDs."""

def test_serialize_produces_cfn_structure():
    """serialize() produce dict con estructura {"Resources": {...}}."""

def test_serialize_to_yaml_round_trip():
    """serialize_to_yaml() + parse() produce ResourceModel[] equivalentes."""

def test_format_detection_by_content():
    """Formato detectado por contenido, no solo por extensión."""
```

### Tests unitarios — `test_cfn_rules.py`

Para cada uno de los 37 reglas CFN, dos tests:

```python
def test_TMAC_CFN_S3_001_fires_on_public_read():
    """TMAC-CFN-S3-001 se dispara cuando AccessControl == PublicRead."""

def test_TMAC_CFN_S3_001_no_fire_on_private():
    """TMAC-CFN-S3-001 no se dispara cuando AccessControl == Private."""

# ... (patrón repetido para las 37 reglas)
```

### Tests de integración — `test_cfn_cli.py`

```python
def test_exit_code_0_clean_template(tmp_path):
    """tmac cfn con template seguro → exit code 0."""

def test_exit_code_1_critical_finding(fixtures_cfn):
    """tmac cfn con template que tiene Critical → exit code 1."""

def test_exit_code_2_high_finding(fixtures_cfn):
    """tmac cfn con template que tiene High
 sin Critical → exit code 2."""

def test_exit_code_3_invalid_directory():
    """tmac cfn con directorio inexistente → exit code 3."""

def test_html_report_generated(fixtures_cfn, tmp_path):
    """tmac cfn --report html genera archivo HTML con findings CFN."""

def test_markdown_report_generated(fixtures_cfn, tmp_path):
    """tmac cfn --report md genera archivo Markdown con findings CFN."""

def test_json_report_sarif_fields(fixtures_cfn, tmp_path):
    """tmac cfn --report json genera SARIF con rule_id TMAC-CFN-* en ruleId."""

def test_quiet_flag_suppresses_stdout(fixtures_cfn):
    """tmac cfn --quiet → stdout vacío, reporte generado."""

def test_default_report_name(fixtures_cfn, tmp_path):
    """tmac cfn sin --output genera tmac-cfn-report.html por defecto."""

def test_scan_command_unaffected(fixtures_tf):
    """tmac scan produce los mismos resultados que antes de v1.2.0."""

def test_plan_command_unaffected(fixtures_plans):
    """tmac plan produce los mismos resultados que antes de v1.2.0."""
```

### Tests de integración — `test_cfn_scanner.py`

```python
def test_scanner_discovers_yaml_files(tmp_path):
    """CfnScanner descubre archivos .yaml en el directorio."""

def test_scanner_discovers_json_files(tmp_path):
    """CfnScanner descubre archivos .json en el directorio."""

def test_scanner_ignores_non_cfn_yaml(tmp_path):
    """CfnScanner ignora archivos YAML que no son templates CFN."""

def test_scanner_mixed_directory(tmp_path):
    """CfnScanner en directorio con .tf y .yaml procesa solo los CFN."""

def test_scanner_empty_directory(tmp_path):
    """CfnScanner en directorio sin CFN retorna ScanResult con files_scanned=0."""

def test_scanner_statistics_correct(fixtures_cfn):
    """ScanResult.statistics es consistente con la lista de findings."""

def test_scanner_ignore_map_applied(fixtures_cfn):
    """Recursos con tmac:ignore no aparecen en los findings."""

def test_scanner_exclude_patterns(fixtures_cfn, tmp_path):
    """Archivos que coinciden con --exclude no se procesan."""
```

### Property-based tests — `test_cfn_parser_properties.py`

```python
from hypothesis import given, settings, strategies as st

# Feature: tmac-v1-2-cloudformation, Property 1: Determinismo del Parser
@settings(max_examples=100)
@given(cfn_template_strategy())
def test_parser_deterministic(template_content):
    """Parsear el mismo template dos veces produce listas idénticas."""

# Feature: tmac-v1-2-cloudformation, Property 2: Round-Trip YAML
@settings(max_examples=100)
@given(resource_model_list_strategy())
def test_round_trip_yaml(resources):
    """serialize_to_yaml() + parse() produce lista equivalente."""

# Feature: tmac-v1-2-cloudformation, Property 3: Round-Trip JSON
@settings(max_examples=100)
@given(resource_model_list_strategy())
def test_round_trip_json(resources):
    """serialize() + parse_dict() produce lista equivalente."""

# Feature: tmac-v1-2-cloudformation, Property 4: Invariante de Conteo
@settings(max_examples=100)
@given(cfn_template_strategy(min_resources=1, max_resources=10))
def test_resource_count_invariant(template_content, expected_count):
    """len(parse(T)) == número de recursos en T.Resources."""

# Feature: tmac-v1-2-cloudformation, Property 5: No-Crash con Intrinsic Functions
@settings(max_examples=100)
@given(cfn_template_with_intrinsics_strategy())
def test_no_crash_intrinsic_functions(template_content):
    """Parser nunca lanza excepción con Intrinsic Functions."""

# Feature: tmac-v1-2-cloudformation, Property 6: Equivalencia YAML/JSON
@settings(max_examples=100)
@given(cfn_template_strategy())
def test_yaml_json_equivalence(template_dict):
    """parse(yaml_version) ≡ parse(json_version) para templates equivalentes."""

# Feature: tmac-v1-2-cloudformation, Property 7: Consistencia de Estadísticas
@settings(max_examples=50)
@given(cfn_directory_strategy())
def test_statistics_consistency(directory):
    """ScanResult.statistics es siempre consistente con findings."""

# Feature: tmac-v1-2-cloudformation, Property 8: Monotonía de Severidad
@settings(max_examples=50)
@given(cfn_directory_strategy(), severity_pair_strategy())
def test_severity_monotonicity(directory, s1, s2):
    """Aumentar min_severity nunca incrementa el número de findings."""

# Feature: tmac-v1-2-cloudformation, Property 9: Idempotencia del ignore_map
@settings(max_examples=100)
@given(cfn_template_strategy())
def test_ignore_map_idempotent(template_path):
    """get_ignore_map() dos veces retorna el mismo resultado."""

# Feature: tmac-v1-2-cloudformation, Property 10: Round-Trip de Finding
@settings(max_examples=100)
@given(finding_strategy())
def test_finding_round_trip(finding):
    """Finding(**f.model_dump()) == f para cualquier Finding CFN."""

# Feature: tmac-v1-2-cloudformation, Property 11: Supresión por ignore_map
@settings(max_examples=100)
@given(cfn_template_with_ignore_strategy())
def test_ignore_map_suppression(template_path, suppressed_rule_id, logical_id):
    """Recurso con tmac:ignore[RULE-ID] nunca aparece en findings con ese rule_id."""

# Feature: tmac-v1-2-cloudformation, Property 12: Separación de Reglas
@settings(max_examples=50)
@given(cfn_directory_strategy())
def test_cfn_findings_have_cfn_prefix(directory):
    """Todos los findings de CfnScanner tienen rule_id con prefijo TMAC-CFN-."""
```

### Estrategias Hypothesis para v1.2.0

```python
# tests/property/strategies_cfn.py

CFN_RESOURCE_TYPES = [
    "AWS::S3::Bucket", "AWS::IAM::Role", "AWS::IAM::Policy",
    "AWS::EC2::SecurityGroup", "AWS::EC2::VPC", "AWS::EC2::Instance",
    "AWS::RDS::DBInstance", "AWS::DynamoDB::Table", "AWS::KMS::Key",
    "AWS::Lambda::Function", "AWS::CloudTrail::Trail",
    "AWS::ApiGateway::Method", "AWS::ApiGateway::Stage",
]

def cfn_resource_strategy():
    """Genera un recurso CFN con LogicalId, Type y Properties arbitrarios."""
    return st.fixed_dictionaries({
        "logical_id": st.from_regex(r"[A-Za-z][A-Za-z0-9]{1,20}", fullmatch=True),
        "resource_type": st.sampled_from(CFN_RESOURCE_TYPES),
        "properties": st.dictionaries(
            keys=st.from_regex(r"[A-Za-z][A-Za-z0-9]{1,15}", fullmatch=True),
            values=st.one_of(st.text(max_size=50), st.booleans(), st.integers()),
            max_size=5,
        ),
    })

def cfn_template_strategy(min_resources=0, max_resources=5):
    """Genera un template CFN completo como string YAML."""
    return st.lists(
        cfn_resource_strategy(), min_size=min_resources, max_size=max_resources
    ).map(lambda resources: _build_cfn_yaml(resources))

def resource_model_list_strategy():
    """Genera una lista de ResourceModel sin RefSentinel para round-trip tests."""
    return st.lists(
        st.builds(
            ResourceModel,
            resource_type=st.sampled_from(CFN_RESOURCE_TYPES),
            name=st.from_regex(r"[A-Za-z][A-Za-z0-9]{1,20}", fullmatch=True),
            attributes=st.dictionaries(
                keys=st.from_regex(r"[A-Za-z][A-Za-z0-9]{1,15}", fullmatch=True),
                values=st.one_of(st.text(max_size=30), st.booleans()),
                max_size=4,
            ),
            source_file=st.just("test.yaml"),
            line_number=st.integers(min_value=1, max_value=1000),
        ),
        min_size=1, max_size=5,
    )
```

