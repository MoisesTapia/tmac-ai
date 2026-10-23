# Documento de Requisitos: TMAC v1.2.0 "Ixtla" — AWS CloudFormation

## Introducción

TMAC v1.2.0 extiende la herramienta CLI de análisis estático para IaC con soporte nativo para
**AWS CloudFormation templates** en formato YAML y JSON. Esta versión es la primera expansión
multi-IaC del proyecto: el mismo engine de reglas STRIDE (Evaluator, Matcher, RuleLoader) que
analiza Terraform en v1.0.0 ahora también analiza CloudFormation, sin modificaciones al núcleo.

El diferenciador arquitectónico de esta versión es la separación limpia entre parsers e engine:
el `CloudFormationParser` implementa `BaseParser` y produce `ResourceModel` objects con el mismo
esquema que el `TerraformParser`, permitiendo que el pipeline de análisis existente funcione sin
cambios. Las reglas CFN son un nuevo conjunto YAML con `resource_type` en formato CloudFormation
(`AWS::S3::Bucket`, `AWS::IAM::Role`, etc.) y IDs con prefijo `TMAC-CFN-`.

**Lugar en el roadmap:** v1.2.0 es la segunda release de la Phase 2 (CI/CD Native + Distribución)
del ciclo Ixtla. Sienta las bases para el soporte multi-IaC que continuará con Kubernetes (v1.3.0),
Azure Bicep (v1.4.0) y Docker Compose (v1.5.0). La cobertura de servicios AWS en CFN es equivalente
a la de Terraform: S3, IAM, Security Groups, VPC, EC2, RDS, DynamoDB, KMS, Lambda, CloudTrail y
API Gateway.

**Limitación conocida heredada:** El motor evalúa cada recurso de forma independiente. No correlaciona
recursos distintos entre sí. Esta limitación, documentada desde v1.0.0 (workaround en VPC-001), se
mantiene en v1.2.0 y se resolverá en v2.2.0 con el grafo de dependencias.

**Limitación nueva de v1.2.0:** La resolución de constructores YAML intrínsecos de CloudFormation
(`!Ref`, `!Sub`, `!GetAtt`) es parcial: el parser detecta la presencia de referencias pero no las
resuelve a valores concretos. La resolución completa requiere el grafo de dependencias de v2.2.0.


## Nota de revisión (2026-10-23)

Al implementar se adoptaron los ajustes descritos en `design.md` → *Revisión 2026-10-23*. En
resumen: el `CfnScanner` (Requisito 18) se implementa como `Scanner(parser=CloudFormationParser())`;
los errores de parseo (Requisitos 1.10, 1.11, 2.4) siguen devolviendo `[]` en `parse()` pero el
escaneo los reporta como incidencias y termina con exit 3 (fail closed); `TMAC-CFN-IAM-006` y
`TMAC-CFN-KMS-002` cambian de condición (no expresables tal cual); el catálogo final tiene 43
reglas (Requisito 16.5: ≥ 30). Los criterios de aceptación se cumplen con esas adaptaciones.

## Glosario

- **CloudFormationParser**: Nuevo módulo en `src/tmac/parsers/cloudformation.py` que implementa `BaseParser` y parsea templates CFN en YAML y JSON, produciendo `ResourceModel` objects.
- **CFN Template**: Archivo de definición de infraestructura de AWS CloudFormation en formato YAML (`.yaml`, `.yml`) o JSON (`.json`, `.template`). Contiene una sección `Resources` con los recursos a desplegar.
- **LogicalId**: Identificador lógico de un recurso dentro de un template CFN (ej. `MyBucket`, `WebServerRole`). Es el nombre del recurso en el `ResourceModel.name`.
- **ResourceType CFN**: Tipo de recurso en formato CloudFormation (ej. `AWS::S3::Bucket`, `AWS::IAM::Role`). Es el valor de `ResourceModel.resource_type` para recursos CFN.
- **Properties**: Sección de atributos de un recurso CFN. Equivalente a los atributos de un bloque `resource` en Terraform. Se mapea a `ResourceModel.attributes`.
- **Intrinsic Function**: Constructor YAML especial de CloudFormation para referencias dinámicas. Los tres relevantes para v1.2.0 son `!Ref`, `!Sub` y `!GetAtt`.
- **!Ref**: Constructor YAML que referencia el valor de otro recurso o parámetro del template por su LogicalId. Ejemplo: `!Ref MyBucket`.
- **!Sub**: Constructor YAML que interpola strings con referencias a recursos o parámetros. Ejemplo: `!Sub "arn:aws:s3:::${BucketName}"`.
- **!GetAtt**: Constructor YAML que obtiene un atributo específico de otro recurso. Ejemplo: `!GetAtt MyRole.Arn`.
- **RefSentinel**: Valor placeholder que el `CloudFormationParser` inserta cuando encuentra una Intrinsic Function no resoluble. Formato: `{"Ref": "LogicalId"}`, `{"Sub": "template-string"}`, `{"GetAtt": "Resource.Attribute"}`.
- **CFN Rules File**: Archivo YAML de reglas STRIDE para recursos CFN, ubicado en `src/tmac/rules/cfn/threats.yaml`. Mismo formato que `src/tmac/rules/aws/threats.yaml` pero con `resource_type` en formato CFN.
- **CfnScanner**: Orquestador del pipeline CFN. *Implementado como* `Scanner(parser=CloudFormationParser())` — el `Scanner` genérico con el parser de CloudFormation.
- **tmac cfn**: Nuevo subcomando CLI que analiza templates CloudFormation en un directorio.
- **Scanner**: Orquestador genérico (desde v1.1.x recibe el parser). En v1.2.0 analiza `.tf`/`.tofu` con `TerraformParser` y templates CFN con `CloudFormationParser`.
- **TerraformParser**: Parser existente de v1.0.0 para archivos `.tf`. No se modifica en v1.2.0.
- **BaseParser**: Clase abstracta en `src/tmac/parsers/base.py` que define la interfaz `parse(file_path) -> List[ResourceModel]`.
- **Evaluator**: Motor de evaluación de condiciones STRIDE existente. Reutilizado sin cambios.
- **Matcher**: Coordinador de evaluación existente. Reutilizado sin cambios.
- **RuleLoader**: Cargador de reglas YAML existente. Extendido para cargar también `cfn/threats.yaml`.
- **ResourceModel**: Modelo de datos existente que representa un recurso IaC parseado con campos `resource_type`, `name`, `attributes`, `source_file`, `line_number`.
- **Finding**: Modelo de datos existente que representa una amenaza detectada.
- **ScanResult**: Modelo de datos existente con metadata, estadísticas y findings.
- **STRIDE**: Framework de modelado de amenazas (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).
- **CLI**: Interfaz de línea de comandos (`tmac`), implementada con Click.
- **tmac:ignore**: Mecanismo de supresión de hallazgos existente. En CFN se implementa como comentario YAML `# tmac:ignore` o `# tmac:ignore[RULE-ID]` en la línea anterior al LogicalId del recurso.
- **AWSTemplateFormatVersion**: Campo opcional en el template CFN que indica la versión del formato. No es requerido para el parseo.
- **Parameters**: Sección opcional del template CFN con parámetros de entrada. Los valores de parámetros no se resuelven en v1.2.0.
- **Outputs**: Sección opcional del template CFN con valores de salida. No se parsea en v1.2.0.


---

## Requisitos

### Requisito 1: CloudFormationParser — Parseo de Templates YAML

**User Story:** Como ingeniero de seguridad, quiero que TMAC parsee templates CloudFormation en formato YAML, para poder analizar amenazas STRIDE en infraestructura definida con CFN.

#### Criterios de Aceptación

1. THE CloudFormationParser SHALL implementar la interfaz `BaseParser` definida en `src/tmac/parsers/base.py`.
2. WHEN el CloudFormationParser recibe la ruta a un template CFN en YAML válido, THE CloudFormationParser SHALL retornar una lista de `ResourceModel` objects, uno por cada recurso en la sección `Resources` del template.
3. THE CloudFormationParser SHALL mapear el `LogicalId` de cada recurso CFN al campo `ResourceModel.name`.
4. THE CloudFormationParser SHALL mapear el campo `Type` de cada recurso CFN al campo `ResourceModel.resource_type` (ej. `AWS::S3::Bucket`).
5. THE CloudFormationParser SHALL mapear el contenido de la sección `Properties` de cada recurso CFN al campo `ResourceModel.attributes`.
6. THE CloudFormationParser SHALL registrar la ruta del archivo template en `ResourceModel.source_file`.
7. THE CloudFormationParser SHALL registrar el número de línea del `LogicalId` del recurso en `ResourceModel.line_number` (1-indexed).
8. WHEN un template CFN no contiene la sección `Resources`, THE CloudFormationParser SHALL retornar una lista vacía y emitir un warning via `logging`.
9. WHEN un template CFN contiene la sección `Resources` vacía, THE CloudFormationParser SHALL retornar una lista vacía sin emitir error.
10. IF el archivo proporcionado no existe, THEN THE CloudFormationParser SHALL retornar una lista vacía y emitir un mensaje de error via `logging`.
11. IF el archivo YAML no es sintácticamente válido, THEN THE CloudFormationParser SHALL retornar una lista vacía y emitir un mensaje de error via `logging` con la descripción del error de parseo.
12. FOR ALL templates CFN YAML válidos, parsear el archivo dos veces consecutivas SHALL producir listas de `ResourceModel` idénticas (propiedad de determinismo del parser).

---

### Requisito 2: CloudFormationParser — Parseo de Templates JSON

**User Story:** Como ingeniero de seguridad, quiero que TMAC parsee templates CloudFormation en formato JSON, para poder analizar infraestructura definida en ambos formatos soportados por CFN.

#### Criterios de Aceptación

1. THE CloudFormationParser SHALL parsear templates CFN en formato JSON (extensiones `.json` y `.template`) aplicando las mismas reglas de extracción que para YAML.
2. WHEN el CloudFormationParser recibe un template JSON válido con sección `Resources`, THE CloudFormationParser SHALL producir `ResourceModel` objects equivalentes a los que produciría si el mismo template estuviera en YAML.
3. THE CloudFormationParser SHALL detectar el formato del template (YAML vs JSON) por el contenido del archivo, no solo por la extensión.
4. IF el archivo JSON no es sintácticamente válido, THEN THE CloudFormationParser SHALL retornar una lista vacía y emitir un mensaje de error via `logging` con la descripción del error de parseo.
5. FOR ALL templates CFN JSON válidos, parsear el archivo dos veces consecutivas SHALL producir listas de `ResourceModel` idénticas (propiedad de determinismo del parser).
6. FOR ALL templates CFN que sean semánticamente equivalentes en YAML y JSON, el CloudFormationParser SHALL producir listas de `ResourceModel` con los mismos `resource_type`, `name` y `attributes` independientemente del formato de entrada.

---

### Requisito 3: Resolución Parcial de Intrinsic Functions

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte la presencia de referencias dinámicas en templates CFN, para que el análisis no falle silenciosamente cuando los atributos contienen `!Ref`, `!Sub` o `!GetAtt`.

#### Criterios de Aceptación

1. WHEN el CloudFormationParser encuentra un valor `!Ref LogicalId` en las `Properties` de un recurso, THE CloudFormationParser SHALL sustituir ese valor por un `RefSentinel` con formato `{"Ref": "LogicalId"}` en los `attributes` del `ResourceModel`.
2. WHEN el CloudFormationParser encuentra un valor `!Sub "template-string"` en las `Properties` de un recurso, THE CloudFormationParser SHALL sustituir ese valor por un `RefSentinel` con formato `{"Sub": "template-string"}` en los `attributes` del `ResourceModel`.
3. WHEN el CloudFormationParser encuentra un valor `!GetAtt "Resource.Attribute"` en las `Properties` de un recurso, THE CloudFormationParser SHALL sustituir ese valor por un `RefSentinel` con formato `{"GetAtt": "Resource.Attribute"}` en los `attributes` del `ResourceModel`.
4. THE CloudFormationParser SHALL preservar los `RefSentinel` como valores en el `ResourceModel.attributes` sin intentar resolverlos a valores concretos.
5. WHEN el Evaluator evalúa una condición `exists` sobre un atributo que contiene un `RefSentinel`, THE Evaluator SHALL tratar el `RefSentinel` como un valor presente (no nulo), retornando `True` para la condición `exists`.
6. WHEN el Evaluator evalúa una condición `not_exists` sobre un atributo que contiene un `RefSentinel`, THE Evaluator SHALL retornar `False` (el atributo existe, aunque su valor sea dinámico).
7. THE CloudFormationParser SHALL manejar Intrinsic Functions anidadas (ej. `!Sub` que contiene `!Ref`) preservando la estructura completa como `RefSentinel` sin lanzar excepciones.
8. FOR ALL templates CFN con Intrinsic Functions, el CloudFormationParser SHALL producir `ResourceModel` objects sin lanzar excepciones, independientemente de la complejidad de las referencias.


---

### Requisito 4: Mecanismo tmac:ignore para CloudFormation

**User Story:** Como desarrollador, quiero poder suprimir hallazgos específicos en templates CFN con comentarios `# tmac:ignore`, para gestionar falsos positivos de la misma forma que en Terraform.

#### Criterios de Aceptación

1. THE CloudFormationParser SHALL reconocer el comentario `# tmac:ignore` en la línea inmediatamente anterior al `LogicalId` de un recurso como supresión global de todos los hallazgos para ese recurso.
2. THE CloudFormationParser SHALL reconocer el comentario `# tmac:ignore[RULE-ID]` en la línea inmediatamente anterior al `LogicalId` de un recurso como supresión del hallazgo con ese `RULE-ID` específico para ese recurso.
3. THE CloudFormationParser SHALL soportar múltiples comentarios `# tmac:ignore[RULE-ID]` consecutivos antes de un `LogicalId`, acumulando todos los IDs de reglas suprimidas.
4. THE CloudFormationParser SHALL exponer un método `get_ignore_map(file_path: str) -> IgnoreMap` que retorne el mapa de supresiones `{LogicalId: ["*"] | ["RULE-ID-1", ...]}` para un template dado.
5. WHEN el `CfnScanner` procesa los findings, THE CfnScanner SHALL consultar el `ignore_map` del `CloudFormationParser` y omitir los findings cuyo `resource_name` y `rule_id` estén suprimidos.
6. IF un `LogicalId` tiene supresión global (`["*"]`), THEN THE CfnScanner SHALL omitir todos los findings para ese recurso independientemente del `rule_id`.
7. FOR ALL templates CFN, el mecanismo `tmac:ignore` SHALL funcionar de forma idéntica al mecanismo equivalente del `TerraformParser` en términos de semántica de supresión.

---

### Requisito 5: Reglas CFN — S3 (AWS::S3::Bucket)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte las mismas amenazas STRIDE en buckets S3 definidos con CloudFormation que en los definidos con Terraform, para tener cobertura equivalente entre IaC frameworks.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-S3-001` WHEN un recurso `AWS::S3::Bucket` tiene la propiedad `AccessControl` con valor `PublicRead` o `PublicReadWrite` (equivalente a TMAC-AWS-S3-001, severidad Critical, STRIDE: Information Disclosure).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-S3-002` WHEN un recurso `AWS::S3::Bucket` no tiene la propiedad `BucketEncryption` definida (equivalente a TMAC-AWS-S3-002, severidad High, STRIDE: Information Disclosure).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-S3-003` WHEN un recurso `AWS::S3::Bucket` no tiene la propiedad `LoggingConfiguration` definida (equivalente a TMAC-AWS-S3-003, severidad Medium, STRIDE: Repudiation).
4. THE RuleEngine SHALL detectar la regla `TMAC-CFN-S3-004` WHEN un recurso `AWS::S3::Bucket` tiene la propiedad `WebsiteConfiguration` definida (equivalente a TMAC-AWS-S3-006, severidad Medium, STRIDE: Information Disclosure).
5. THE RuleEngine SHALL detectar la regla `TMAC-CFN-S3-005` WHEN un recurso `AWS::S3::Bucket` no tiene la propiedad `ObjectLockEnabled` definida (equivalente a TMAC-AWS-S3-005, severidad High, STRIDE: Tampering).
6. FOR ALL reglas CFN de S3, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::S3::Bucket`.
7. FOR ALL reglas CFN de S3, el formato del `id` SHALL seguir el patrón `TMAC-CFN-S3-{NNN}`.

---

### Requisito 6: Reglas CFN — IAM (AWS::IAM::Role, AWS::IAM::Policy, AWS::IAM::User)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte configuraciones IAM inseguras en templates CFN, para prevenir escalación de privilegios y suplantación de identidad en infraestructura CloudFormation.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-IAM-001` WHEN un recurso `AWS::IAM::Policy` tiene en su `PolicyDocument.Statement` un elemento con `Resource` igual a `"*"` (equivalente a TMAC-AWS-IAM-001, severidad High, STRIDE: Elevation of Privilege).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-IAM-002` WHEN un recurso `AWS::IAM::Policy` tiene en su `PolicyDocument` el string `"Action": "*"` (equivalente a TMAC-AWS-IAM-003, severidad Critical, STRIDE: Elevation of Privilege).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-IAM-003` WHEN un recurso `AWS::IAM::Role` tiene en su `AssumeRolePolicyDocument.Statement` un elemento con `Principal` igual a `"*"` o `{"AWS": "*"}` (equivalente a TMAC-AWS-IAM-004, severidad Critical, STRIDE: Spoofing).
4. THE RuleEngine SHALL detectar la regla `TMAC-CFN-IAM-004` WHEN un recurso `AWS::IAM::Role` tiene en su `AssumeRolePolicyDocument` una referencia a una cuenta AWS externa (`arn:aws:iam::`) pero no contiene la condición `sts:ExternalId` (equivalente a TMAC-AWS-IAM-006, severidad High, STRIDE: Spoofing).
5. THE RuleEngine SHALL detectar la regla `TMAC-CFN-IAM-005` WHEN un recurso `AWS::IAM::Policy` contiene la acción `iam:PassRole` con `Resource` igual a `"*"` (equivalente a TMAC-AWS-IAM-007, severidad Critical, STRIDE: Elevation of Privilege).
6. THE RuleEngine SHALL detectar la regla `TMAC-CFN-IAM-006` WHEN existe un recurso `AWS::IAM::User` en el template (equivalente a TMAC-AWS-IAM-008, severidad Medium, STRIDE: Spoofing).
7. FOR ALL reglas CFN de IAM, el formato del `id` SHALL seguir el patrón `TMAC-CFN-IAM-{NNN}`.


---

### Requisito 7: Reglas CFN — Security Groups (AWS::EC2::SecurityGroup)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte Security Groups inseguros en templates CFN, para prevenir exposición de puertos críticos a internet.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-SG-001` WHEN un recurso `AWS::EC2::SecurityGroup` tiene en su `SecurityGroupIngress` un elemento con `FromPort` igual a `22` y `CidrIp` igual a `"0.0.0.0/0"` (equivalente a TMAC-AWS-SG-001, severidad High, STRIDE: Tampering).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-SG-002` WHEN un recurso `AWS::EC2::SecurityGroup` tiene en su `SecurityGroupIngress` un elemento con `FromPort` igual a `3389` y `CidrIp` igual a `"0.0.0.0/0"` (equivalente a TMAC-AWS-SG-002, severidad Critical, STRIDE: Tampering).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-SG-003` WHEN un recurso `AWS::EC2::SecurityGroup` tiene en su `SecurityGroupEgress` un elemento con `CidrIp` igual a `"0.0.0.0/0"` (equivalente a TMAC-AWS-SG-003, severidad Medium, STRIDE: Information Disclosure).
4. FOR ALL reglas CFN de Security Groups, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::EC2::SecurityGroup`.
5. FOR ALL reglas CFN de Security Groups, el formato del `id` SHALL seguir el patrón `TMAC-CFN-SG-{NNN}`.

---

### Requisito 8: Reglas CFN — VPC (AWS::EC2::VPC)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte VPCs sin trazabilidad de red en templates CFN, para garantizar visibilidad ante tráfico anómalo.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-VPC-001` WHEN un recurso `AWS::EC2::VPC` no tiene el tag `FlowLogs` con valor `"enabled"` en su propiedad `Tags` (equivalente a TMAC-AWS-VPC-001, severidad Medium, STRIDE: Repudiation).
2. THE RuleEngine SHALL incluir en la descripción de `TMAC-CFN-VPC-001` la misma nota de limitación técnica que TMAC-AWS-VPC-001: el motor no correlaciona recursos distintos, por lo que la detección se basa en el tag como workaround.
3. FOR ALL reglas CFN de VPC, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::EC2::VPC`.
4. FOR ALL reglas CFN de VPC, el formato del `id` SHALL seguir el patrón `TMAC-CFN-VPC-{NNN}`.

---

### Requisito 9: Reglas CFN — EC2 (AWS::EC2::Instance, AWS::EC2::Volume)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte instancias EC2 y volúmenes EBS inseguros en templates CFN, para prevenir exposición de metadatos y datos en reposo.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-EC2-001` WHEN un recurso `AWS::EC2::Instance` tiene la propiedad `MetadataOptions.HttpTokens` con valor `"optional"` (equivalente a TMAC-AWS-EC2-001, severidad Critical, STRIDE: Spoofing).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-EC2-002` WHEN un recurso `AWS::EC2::Volume` tiene la propiedad `Encrypted` con valor `false` o no tiene la propiedad `Encrypted` definida (equivalente a TMAC-AWS-EC2-002, severidad High, STRIDE: Information Disclosure).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-EC2-003` WHEN un recurso `AWS::EC2::Instance` tiene la propiedad `NetworkInterfaces` con un elemento que tiene `AssociatePublicIpAddress` igual a `true`, o tiene la propiedad `NetworkInterfaces` ausente y `SubnetId` apunta a una subred pública (equivalente a TMAC-AWS-EC2-003, severidad High, STRIDE: Tampering).
4. FOR ALL reglas CFN de EC2, el formato del `id` SHALL seguir el patrón `TMAC-CFN-EC2-{NNN}`.

---

### Requisito 10: Reglas CFN — RDS (AWS::RDS::DBInstance)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte instancias RDS inseguras en templates CFN, para prevenir exposición de bases de datos y pérdida de disponibilidad.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-RDS-001` WHEN un recurso `AWS::RDS::DBInstance` tiene la propiedad `StorageEncrypted` con valor `false` o no tiene la propiedad `StorageEncrypted` definida (equivalente a TMAC-AWS-RDS-001, severidad Medium, STRIDE: Information Disclosure).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-RDS-002` WHEN un recurso `AWS::RDS::DBInstance` tiene la propiedad `PubliclyAccessible` con valor `true` (equivalente a TMAC-AWS-RDS-002, severidad High, STRIDE: Information Disclosure).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-RDS-003` WHEN un recurso `AWS::RDS::DBInstance` no tiene la propiedad `MultiAZ` definida o tiene `MultiAZ` con valor `false` (equivalente a TMAC-AWS-RDS-003, severidad High, STRIDE: Denial of Service).
4. THE RuleEngine SHALL detectar la regla `TMAC-CFN-RDS-004` WHEN un recurso `AWS::RDS::DBInstance` tiene la propiedad `DeletionProtection` con valor `false` o no tiene la propiedad `DeletionProtection` definida (equivalente a TMAC-AWS-RDS-004, severidad High, STRIDE: Denial of Service).
5. THE RuleEngine SHALL detectar la regla `TMAC-CFN-RDS-005` WHEN un recurso `AWS::RDS::DBInstance` no tiene la propiedad `EnableCloudwatchLogsExports` definida (equivalente a TMAC-AWS-RDS-005, severidad Medium, STRIDE: Repudiation).
6. FOR ALL reglas CFN de RDS, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::RDS::DBInstance`.
7. FOR ALL reglas CFN de RDS, el formato del `id` SHALL seguir el patrón `TMAC-CFN-RDS-{NNN}`.


---

### Requisito 11: Reglas CFN — DynamoDB (AWS::DynamoDB::Table)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte tablas DynamoDB inseguras en templates CFN, para prevenir exposición de datos y pérdida de disponibilidad.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-DDB-001` WHEN un recurso `AWS::DynamoDB::Table` no tiene la propiedad `SSESpecification` definida o tiene `SSESpecification.SSEEnabled` con valor `false` (equivalente a TMAC-AWS-DDB-001, severidad High, STRIDE: Information Disclosure).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-DDB-002` WHEN un recurso `AWS::DynamoDB::Table` no tiene la propiedad `PointInTimeRecoverySpecification` definida o tiene `PointInTimeRecoverySpecification.PointInTimeRecoveryEnabled` con valor `false` (equivalente a TMAC-AWS-DDB-002, severidad Medium, STRIDE: Denial of Service).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-DDB-003` WHEN un recurso `AWS::DynamoDB::Table` no tiene la propiedad `DeletionProtectionEnabled` definida o tiene `DeletionProtectionEnabled` con valor `false` (equivalente a TMAC-AWS-DDB-003, severidad High, STRIDE: Denial of Service).
4. FOR ALL reglas CFN de DynamoDB, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::DynamoDB::Table`.
5. FOR ALL reglas CFN de DynamoDB, el formato del `id` SHALL seguir el patrón `TMAC-CFN-DDB-{NNN}`.

---

### Requisito 12: Reglas CFN — KMS (AWS::KMS::Key)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte claves KMS inseguras en templates CFN, para prevenir pérdida de claves criptográficas y acceso irrestricto.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-KMS-001` WHEN un recurso `AWS::KMS::Key` tiene la propiedad `EnableKeyRotation` con valor `false` o no tiene la propiedad `EnableKeyRotation` definida (equivalente a TMAC-AWS-KMS-001, severidad High, STRIDE: Information Disclosure).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-KMS-002` WHEN un recurso `AWS::KMS::Key` tiene la propiedad `PendingWindowInDays` con valor menor a `7` o no tiene la propiedad `PendingWindowInDays` definida (equivalente a TMAC-AWS-KMS-002, severidad Medium, STRIDE: Denial of Service).
3. FOR ALL reglas CFN de KMS, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::KMS::Key`.
4. FOR ALL reglas CFN de KMS, el formato del `id` SHALL seguir el patrón `TMAC-CFN-KMS-{NNN}`.

---

### Requisito 13: Reglas CFN — Lambda (AWS::Lambda::Function)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte funciones Lambda inseguras en templates CFN, para prevenir exposición de código y ejecución no autorizada.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-LMD-001` WHEN un recurso `AWS::Lambda::Function` tiene la propiedad `Environment.Variables` definida con algún valor que contenga el string `"password"`, `"secret"`, `"key"` o `"token"` en el nombre de la variable (case-insensitive) (equivalente a TMAC-AWS-LMD-001, severidad High, STRIDE: Information Disclosure).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-LMD-002` WHEN un recurso `AWS::Lambda::Function` no tiene la propiedad `TracingConfig` definida o tiene `TracingConfig.Mode` con valor `"PassThrough"` (equivalente a TMAC-AWS-LMD-002, severidad Low, STRIDE: Repudiation).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-LMD-003` WHEN un recurso `AWS::Lambda::Function` tiene la propiedad `ReservedConcurrentExecutions` con valor `0` (equivalente a TMAC-AWS-LMD-003, severidad Medium, STRIDE: Denial of Service).
4. FOR ALL reglas CFN de Lambda, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::Lambda::Function`.
5. FOR ALL reglas CFN de Lambda, el formato del `id` SHALL seguir el patrón `TMAC-CFN-LMD-{NNN}`.

---

### Requisito 14: Reglas CFN — CloudTrail (AWS::CloudTrail::Trail)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte trails de CloudTrail inseguros en templates CFN, para garantizar la trazabilidad de acciones en la cuenta AWS.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-CW-001` WHEN un recurso `AWS::CloudTrail::Trail` tiene la propiedad `IsLogging` con valor `false` o no tiene la propiedad `IsLogging` definida (equivalente a TMAC-AWS-CW-001, severidad High, STRIDE: Repudiation).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-CW-002` WHEN un recurso `AWS::CloudTrail::Trail` tiene la propiedad `EnableLogFileValidation` con valor `false` o no tiene la propiedad `EnableLogFileValidation` definida (severidad Medium, STRIDE: Tampering).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-CW-003` WHEN un recurso `AWS::CloudTrail::Trail` tiene la propiedad `IsMultiRegionTrail` con valor `false` o no tiene la propiedad `IsMultiRegionTrail` definida (severidad Medium, STRIDE: Repudiation).
4. FOR ALL reglas CFN de CloudTrail, el campo `resource_type` en el archivo `cfn/threats.yaml` SHALL ser `AWS::CloudTrail::Trail`.
5. FOR ALL reglas CFN de CloudTrail, el formato del `id` SHALL seguir el patrón `TMAC-CFN-CW-{NNN}`.

---

### Requisito 15: Reglas CFN — API Gateway (AWS::ApiGateway::Method, AWS::ApiGateway::Stage)

**User Story:** Como ingeniero de seguridad, quiero que TMAC detecte configuraciones inseguras de API Gateway en templates CFN, para prevenir acceso no autenticado y exposición de datos en tránsito.

#### Criterios de Aceptación

1. THE RuleEngine SHALL detectar la regla `TMAC-CFN-APIGW-001` WHEN un recurso `AWS::ApiGateway::Method` tiene la propiedad `AuthorizationType` con valor `"NONE"` (equivalente a TMAC-AWS-APIGW-001, severidad High, STRIDE: Spoofing).
2. THE RuleEngine SHALL detectar la regla `TMAC-CFN-APIGW-002` WHEN un recurso `AWS::ApiGateway::Stage` no tiene la propiedad `MethodSettings` definida o tiene `MethodSettings` sin `LoggingLevel` configurado (equivalente a TMAC-AWS-APIGW-002, severidad Medium, STRIDE: Repudiation).
3. THE RuleEngine SHALL detectar la regla `TMAC-CFN-APIGW-003` WHEN un recurso `AWS::ApiGateway::Stage` tiene la propiedad `ClientCertificateId` ausente (severidad Medium, STRIDE: Information Disclosure).
4. FOR ALL reglas CFN de API Gateway, el formato del `id` SHALL seguir el patrón `TMAC-CFN-APIGW-{NNN}`.


---

### Requisito 16: Archivo de Reglas CFN (cfn/threats.yaml)

**User Story:** Como mantenedor del proyecto, quiero que las reglas CFN estén en un archivo YAML separado del de Terraform, para mantener una separación clara entre frameworks IaC y facilitar el mantenimiento independiente.

#### Criterios de Aceptación

1. THE RuleLoader SHALL cargar las reglas CFN desde `src/tmac/rules/cfn/threats.yaml` además de las reglas Terraform desde `src/tmac/rules/aws/threats.yaml`.
2. THE cfn/threats.yaml SHALL seguir exactamente el mismo schema que `aws/threats.yaml`: campos `version`, `metadata` y `rules`, donde cada regla tiene `id`, `name`, `resource_type`, `check`, `severity`, `stride`, `description`, `mitigation`, `references` y `tags`.
3. THE RuleLoader SHALL cargar ambos archivos de reglas sin modificaciones a su interfaz pública `load_rules(extra_rules_dir)`.
4. WHEN el `RuleLoader` carga reglas de ambos archivos y existe un `id` duplicado, THE RuleLoader SHALL usar la regla del archivo cargado más recientemente (comportamiento de sobreescritura existente).
5. THE cfn/threats.yaml SHALL incluir al menos 30 reglas cubriendo los 11 servicios AWS especificados en los Requisitos 5 al 15.
6. FOR ALL reglas en `cfn/threats.yaml`, el campo `id` SHALL seguir el patrón `TMAC-CFN-{SERVICE}-{NNN}` donde `{SERVICE}` es el código de servicio (S3, IAM, SG, VPC, EC2, RDS, DDB, KMS, LMD, CW, APIGW).
7. FOR ALL reglas en `cfn/threats.yaml`, el campo `resource_type` SHALL usar el formato de tipo de recurso CloudFormation (`AWS::{Service}::{Resource}`).
8. THE cfn/threats.yaml SHALL incluir en su sección `metadata` los campos `cloud: aws`, `framework: STRIDE`, `description` y `last_updated`.

---

### Requisito 17: Nuevo Subcomando CLI `tmac cfn`

**User Story:** Como ingeniero de DevSecOps, quiero un subcomando `tmac cfn` que analice templates CloudFormation en un directorio, para poder integrarlo en pipelines de CI/CD junto con `tmac scan`.

#### Criterios de Aceptación

1. THE CLI SHALL implementar un subcomando `tmac cfn` con el flag `--dir` / `-d` que acepta la ruta al directorio con templates CFN (default: `.`).
2. THE CLI SHALL implementar en `tmac cfn` los mismos flags de salida que `tmac scan`: `--report`, `--output`, `--rules-dir`, `--config`, `--fail-on`, `--severity`, `--quiet`, `--exclude`, `--no-color`, `--verbose`.
3. WHEN `tmac cfn` es invocado con un directorio válido, THE CLI SHALL descubrir todos los archivos con extensiones `.yaml`, `.yml`, `.json` y `.template` en el directorio y subdirectorios, excluyendo los que coincidan con los patrones `--exclude`.
4. THE CLI SHALL filtrar los archivos descubiertos para procesar solo aquellos que contengan una sección `Resources` con al menos un recurso de tipo `AWS::*`, ignorando archivos YAML/JSON que no sean templates CFN.
5. WHEN `tmac cfn` completa sin findings con severidad igual o superior al umbral `--fail-on`, THE CLI SHALL retornar exit code `0`.
6. WHEN `tmac cfn` detecta findings con severidad Critical, THE CLI SHALL retornar exit code `1`.
7. WHEN `tmac cfn` detecta findings con severidad High pero ninguno Critical, THE CLI SHALL retornar exit code `2`.
8. IF el directorio especificado no existe o no es accesible, THEN THE CLI SHALL retornar exit code `3` con un mensaje descriptivo en stderr.
9. WHEN `tmac cfn` es invocado con `--verbose`, THE CLI SHALL emitir mensajes de debug que incluyan: número de archivos CFN descubiertos, número de recursos parseados por archivo, y reglas evaluadas por recurso.
10. THE CLI SHALL mantener los subcomandos `tmac scan` y `tmac plan` existentes sin modificaciones (compatibilidad hacia atrás total).
11. WHEN `tmac cfn` completa, THE CLI SHALL emitir en stdout el mensaje: `"CFN scan complete: {N} findings. Report saved to {output_file}"` a menos que `--quiet` esté activo.
12. THE CLI SHALL generar el reporte de salida con el nombre por defecto `tmac-cfn-report.{fmt}` cuando no se especifica `--output`.


---

### Requisito 18: CfnScanner — Orquestador del Pipeline CFN

**User Story:** Como mantenedor del proyecto, quiero un `CfnScanner` que orqueste el pipeline de análisis CFN de forma análoga al `Scanner` de Terraform, para mantener consistencia arquitectónica entre los dos pipelines.

#### Criterios de Aceptación

1. THE CfnScanner SHALL implementar un método `run_scan(directory, rules_dir, exclude_patterns, min_severity, verbose) -> ScanResult` con la misma firma que `Scanner.run_scan`.
2. THE CfnScanner SHALL descubrir archivos CFN en el directorio usando las extensiones `.yaml`, `.yml`, `.json` y `.template`, aplicando los patrones de exclusión.
3. THE CfnScanner SHALL usar el `CloudFormationParser` para parsear cada archivo CFN descubierto y acumular los `ResourceModel` objects.
4. THE CfnScanner SHALL usar el `RuleLoader` existente para cargar las reglas (incluyendo las CFN de `cfn/threats.yaml`).
5. THE CfnScanner SHALL usar el `Matcher` existente para evaluar los `ResourceModel` contra las reglas, pasando el `ignore_map` del `CloudFormationParser`.
6. THE CfnScanner SHALL filtrar los findings por `min_severity` usando la misma lógica que el `Scanner` de Terraform.
7. THE CfnScanner SHALL retornar un `ScanResult` con `metadata`, `statistics`, `findings`, `files_scanned` y `rules_loaded` poblados correctamente.
8. WHEN el `CfnScanner` procesa un directorio con archivos CFN y Terraform mezclados, THE CfnScanner SHALL procesar solo los archivos CFN y no intentar parsear los archivos `.tf`.
9. THE CfnScanner SHALL cargar la configuración desde `.tmac.yaml` usando el `load_config()` existente, respetando los patrones de exclusión y el directorio de reglas adicionales configurados.
10. IF el directorio no contiene ningún archivo CFN válido, THEN THE CfnScanner SHALL retornar un `ScanResult` con `files_scanned` igual a `0` y lista de findings vacía, sin lanzar excepción.

---

### Requisito 19: Integración con el Engine Existente (Sin Modificaciones)

**User Story:** Como mantenedor del proyecto, quiero que el análisis CFN reutilice el `Evaluator`, el `Matcher` y el `RuleLoader` existentes sin modificaciones, para garantizar que el engine de evaluación STRIDE es el mismo para todos los IaC frameworks.

#### Criterios de Aceptación

1. THE CfnScanner SHALL reutilizar el `Evaluator` existente sin modificaciones para evaluar condiciones STRIDE contra los atributos de recursos CFN.
2. THE CfnScanner SHALL reutilizar el `Matcher` existente sin modificaciones para coordinar la evaluación y producir `Finding` objects.
3. THE RuleLoader SHALL cargar las reglas CFN sin modificaciones a su método `load_rules()`, únicamente añadiendo la carga del archivo `cfn/threats.yaml` en el método `_load_file()` interno.
4. FOR ALL reglas CFN, el resultado de evaluarlas contra un `ResourceModel` con `resource_type` `AWS::S3::Bucket` SHALL ser idéntico al resultado que produciría el mismo engine si el `resource_type` fuera `aws_s3_bucket` con los mismos atributos (propiedad de equivalencia del engine).
5. THE Evaluator SHALL evaluar condiciones sobre atributos de recursos CFN usando la misma lógica de traversal de paths que para recursos Terraform (ej. `SecurityGroupIngress.FromPort` se resuelve igual que `ingress.from_port`).
6. WHEN el `Matcher` procesa un `ResourceModel` con `resource_type` `AWS::IAM::Role`, THE Matcher SHALL aplicar solo las reglas cuyo `resource_type` sea `AWS::IAM::Role`, sin aplicar reglas de `aws_iam_role`.
7. FOR ALL `Finding` objects producidos por el análisis CFN, el campo `rule_id` SHALL seguir el patrón `TMAC-CFN-{SERVICE}-{NNN}`, distinguiéndolos de los findings de Terraform (`TMAC-AWS-{SERVICE}-{NNN}`).

---

### Requisito 20: Reportes — Compatibilidad con Findings CFN

**User Story:** Como ingeniero de seguridad, quiero que los tres reporters existentes (HTML, Markdown, JSON/SARIF) generen reportes correctos con findings de CFN sin modificaciones, para no duplicar lógica de presentación.

#### Criterios de Aceptación

1. THE HTMLReporter SHALL generar reportes HTML válidos con findings de CFN sin modificaciones al código del reporter.
2. THE MarkdownReporter SHALL generar reportes Markdown válidos con findings de CFN sin modificaciones al código del reporter.
3. THE JSONReporter SHALL generar reportes SARIF 2.1.0 válidos con findings de CFN sin modificaciones al código del reporter.
4. WHEN el `HTMLReporter` renderiza un `Finding` con `rule_id` `TMAC-CFN-S3-001`, THE HTMLReporter SHALL mostrar el `rule_id`, `severity`, `stride`, `resource_type`, `resource_name`, `file_path`, `line_number`, `description` y `mitigation` correctamente.
5. WHEN el `JSONReporter` serializa un `Finding` de CFN, THE JSONReporter SHALL incluir el `rule_id` con prefijo `TMAC-CFN-` en el campo `ruleId` del resultado SARIF.
6. FOR ALL `ScanResult` objects producidos por el `CfnScanner`, los tres reporters SHALL generar reportes sin lanzar excepciones, independientemente del número de findings (incluyendo cero findings).
7. WHEN el `CfnScanner` retorna un `ScanResult` con `findings` vacía, THE HTMLReporter SHALL renderizar un estado de aprobación sin errores de template.


---

### Requisito 21: Pretty Printer y Propiedad Round-Trip del CloudFormationParser

**User Story:** Como mantenedor del proyecto, quiero que el `CloudFormationParser` tenga un pretty printer que serialice `ResourceModel` objects de vuelta a un formato estructurado, para poder verificar la propiedad round-trip del parser con Hypothesis.

#### Criterios de Aceptación

1. THE CloudFormationParser SHALL implementar un método `serialize(resources: List[ResourceModel]) -> dict` que produzca un diccionario con estructura `{"Resources": {resource.name: {"Type": resource.resource_type, "Properties": resource.attributes}}}` para cada `ResourceModel` de la lista.
2. THE CloudFormationParser SHALL implementar un método `serialize_to_yaml(resources: List[ResourceModel]) -> str` que serialice la lista de `ResourceModel` a un string YAML válido usando el formato de template CFN.
3. FOR ALL listas de `ResourceModel` producidas por el `CloudFormationParser` desde un template YAML válido sin Intrinsic Functions, serializar con `serialize_to_yaml` y parsear nuevamente SHALL producir una lista de `ResourceModel` con los mismos `resource_type`, `name` y `attributes` (propiedad round-trip del parser).
4. FOR ALL listas de `ResourceModel` producidas por el `CloudFormationParser` desde un template JSON válido sin Intrinsic Functions, serializar con `serialize` y parsear el diccionario resultante SHALL producir una lista de `ResourceModel` equivalente (propiedad round-trip JSON).
5. WHEN la lista de `ResourceModel` contiene `RefSentinel` en los `attributes`, THE `serialize` method SHALL preservar los `RefSentinel` como valores en el diccionario de salida sin intentar resolverlos.

---

### Requisito 22: Suite de Tests para v1.2.0

**User Story:** Como mantenedor del proyecto, quiero una suite de tests completa para las nuevas capacidades de v1.2.0, para garantizar la corrección del parser CFN, las reglas y el pipeline de análisis.

#### Criterios de Aceptación

1. THE Test_Suite SHALL incluir fixtures de templates CFN en `tests/fixtures/cfn/` que cubran: template YAML válido con múltiples recursos, template JSON válido, template con Intrinsic Functions (`!Ref`, `!Sub`, `!GetAtt`), template con comentarios `tmac:ignore`, template vacío (sin `Resources`), template con YAML inválido, y template con JSON inválido.
2. THE Test_Suite SHALL incluir fixtures de templates CFN seguros e inseguros para cada uno de los 11 servicios cubiertos (S3, IAM, SG, VPC, EC2, RDS, DDB, KMS, Lambda, CloudTrail, API Gateway) en `tests/fixtures/cfn/services/`.
3. THE Test_Suite SHALL incluir tests unitarios para el `CloudFormationParser` en `tests/unit/test_cfn_parser.py` que verifiquen: parseo YAML, parseo JSON, extracción de `LogicalId`, extracción de `Properties`, manejo de Intrinsic Functions, manejo de errores, y el mecanismo `tmac:ignore`.
4. THE Test_Suite SHALL incluir tests unitarios para las reglas CFN en `tests/unit/test_cfn_rules.py` que verifiquen que cada regla se dispara con el recurso inseguro correspondiente y no se dispara con el recurso seguro correspondiente.
5. THE Test_Suite SHALL incluir tests de integración en `tests/integration/test_cfn_cli.py` que invoquen `tmac cfn` con `CliRunner` y verifiquen exit codes, contenido del reporte y número de findings.
6. THE Test_Suite SHALL incluir tests de integración en `tests/integration/test_cfn_scanner.py` que invoquen `CfnScanner.run_scan()` directamente con directorios de fixtures y verifiquen el `ScanResult` completo.
7. WHEN se ejecuta `pytest --cov=tmac`, THE Test_Suite SHALL mantener cobertura ≥ 90% en `src/tmac/` incluyendo los nuevos módulos de v1.2.0.
8. THE Test_Suite SHALL incluir un test de no-regresión en `tests/integration/test_regression.py` que verifique que `tmac scan` produce los mismos resultados antes y después de añadir los módulos de v1.2.0.
9. THE Test_Suite SHALL incluir tests de no-regresión que verifiquen que `tmac plan` produce los mismos resultados antes y después de añadir los módulos de v1.2.0.
10. THE Test_Suite SHALL incluir property-based tests con Hypothesis en `tests/property/test_cfn_parser_properties.py` para las propiedades de corrección definidas en el Requisito 23.

---

### Requisito 23: Property-Based Tests con Hypothesis

**User Story:** Como mantenedor del proyecto, quiero property-based tests con Hypothesis para el `CloudFormationParser` y el pipeline CFN, para detectar casos extremos que los tests unitarios no cubren.

#### Criterios de Aceptación

1. THE Property_Tests SHALL verificar la propiedad de **determinismo**: para cualquier template CFN YAML válido generado por Hypothesis, parsear el archivo dos veces SHALL producir listas de `ResourceModel` idénticas.
2. THE Property_Tests SHALL verificar la propiedad de **round-trip YAML**: para cualquier lista de `ResourceModel` con `resource_type` en formato `AWS::*` y `attributes` sin `RefSentinel`, serializar con `serialize_to_yaml` y parsear nuevamente SHALL producir una lista equivalente.
3. THE Property_Tests SHALL verificar la propiedad de **round-trip JSON**: para cualquier lista de `ResourceModel` con `resource_type` en formato `AWS::*` y `attributes` sin `RefSentinel`, serializar con `serialize` y parsear el diccionario resultante SHALL producir una lista equivalente.
4. THE Property_Tests SHALL verificar la propiedad de **no-crash con Intrinsic Functions**: para cualquier template CFN con valores `!Ref`, `!Sub` o `!GetAtt` en cualquier posición de `Properties`, el `CloudFormationParser` SHALL retornar una lista de `ResourceModel` sin lanzar excepciones.
5. THE Property_Tests SHALL verificar la propiedad de **invariante de conteo**: para cualquier template CFN válido con N recursos en la sección `Resources`, el `CloudFormationParser` SHALL retornar exactamente N `ResourceModel` objects.
6. THE Property_Tests SHALL verificar la propiedad de **equivalencia YAML/JSON**: para cualquier template CFN semánticamente equivalente en YAML y JSON (sin Intrinsic Functions), el `CloudFormationParser` SHALL producir listas de `ResourceModel` con los mismos `resource_type`, `name` y `attributes`.
7. THE Property_Tests SHALL verificar la propiedad de **idempotencia del ignore_map**: para cualquier template CFN, llamar a `get_ignore_map()` dos veces SHALL retornar el mismo mapa.
8. THE Property_Tests SHALL verificar la propiedad de **consistencia de findings**: para cualquier `ScanResult` producido por el `CfnScanner`, la suma de `statistics.critical + statistics.high + statistics.medium + statistics.low + statistics.info` SHALL ser igual a `statistics.total_findings`.
9. THE Property_Tests SHALL verificar la propiedad de **monotonía de severidad**: para cualquier `ScanResult` producido con `min_severity="high"`, todos los findings SHALL tener severidad `High` o `Critical`.
10. THE Property_Tests SHALL verificar la propiedad de **serialización de Finding**: para cualquier `Finding` producido por el análisis CFN, serializar con `model_dump()` y reconstruir con `Finding(**data)` SHALL producir un objeto equivalente.


---

### Requisito 24: Sincronización de Cobertura de Servicios Terraform vs CFN

**User Story:** Como ingeniero de seguridad, quiero que la cobertura de servicios AWS en las reglas CFN sea equivalente a la de Terraform, para tener paridad de detección entre los dos frameworks IaC.

#### Criterios de Aceptación

1. THE cfn/threats.yaml SHALL cubrir los mismos 11 servicios AWS que `aws/threats.yaml`: S3, IAM, Security Groups, VPC, EC2, RDS, DynamoDB, KMS, Lambda, CloudTrail y API Gateway.
2. FOR ALL servicios cubiertos en `aws/threats.yaml`, el `cfn/threats.yaml` SHALL incluir al menos una regla equivalente para el tipo de recurso CFN correspondiente.
3. THE cfn/threats.yaml SHALL incluir una tabla de mapeo en su sección `metadata` que relacione cada `resource_type` CFN con su equivalente Terraform (ej. `AWS::S3::Bucket` ↔ `aws_s3_bucket`).
4. WHEN una regla Terraform no tiene equivalente directo en CFN por diferencias estructurales del framework (ej. `aws_iam_access_key` no existe en CFN), THE cfn/threats.yaml SHALL documentar la ausencia con un comentario explicativo en el archivo YAML.
5. THE cfn/threats.yaml SHALL incluir reglas adicionales para amenazas específicas de CloudFormation que no tienen equivalente en Terraform (ej. `AWS::CloudFormation::Stack` con `TemplateURL` apuntando a S3 público).

---

### Requisito 25: Documentación Actualizada

**User Story:** Como usuario de TMAC, quiero que el README y el CHANGELOG reflejen las nuevas capacidades de v1.2.0, para poder usar el subcomando `tmac cfn` correctamente y entender las limitaciones del soporte CFN.

#### Criterios de Aceptación

1. THE README SHALL documentar el subcomando `tmac cfn` con su sintaxis completa, todos los flags disponibles y al menos dos ejemplos de uso (análisis básico y análisis con filtro de severidad).
2. THE README SHALL incluir una sección que explique el formato de templates CFN soportado (YAML y JSON) con ejemplos de templates válidos.
3. THE README SHALL documentar la limitación de resolución parcial de Intrinsic Functions (`!Ref`, `!Sub`, `!GetAtt`) y su impacto en el análisis.
4. THE README SHALL incluir un ejemplo de integración en GitHub Actions que use `tmac cfn` para analizar templates CFN en un repositorio.
5. THE README SHALL incluir una tabla de mapeo de tipos de recursos CFN a tipos de recursos Terraform para los 11 servicios cubiertos.
6. THE README SHALL documentar el mecanismo `tmac:ignore` para templates CFN con ejemplos de uso en YAML.
7. THE CHANGELOG SHALL incluir una entrada para `v1.2.0 "Ixtla"` con las secciones `Added` y `Changed` que describan todas las nuevas capacidades, incluyendo el número de reglas CFN añadidas por servicio.
8. THE README SHALL incluir una sección de limitaciones conocidas que documente: la resolución parcial de Intrinsic Functions, la ausencia de correlación multi-recurso (workaround de VPC-001), y los tipos de recursos CFN no soportados en v1.2.0.


---

## Propiedades de Corrección (para Property-Based Testing con Hypothesis)

Las siguientes propiedades formales capturan los invariantes del sistema que deben mantenerse
para cualquier entrada válida. Estas propiedades son la base de los tests en `tests/property/`.

### P1 — Determinismo del Parser (Invariante)

```
∀ template CFN válido T:
  CloudFormationParser().parse(T) == CloudFormationParser().parse(T)
```

El parser es una función pura: la misma entrada siempre produce la misma salida.
Aplica tanto a templates YAML como JSON.

### P2 — Round-Trip YAML (Round-Trip Property)

```
∀ lista de ResourceModel R sin RefSentinel:
  parse(serialize_to_yaml(R)) ≡ R
  (donde ≡ significa equivalencia en resource_type, name y attributes)
```

Serializar y volver a parsear produce una lista equivalente. Esta propiedad es esencial
para verificar que el pretty printer no pierde información.

### P3 — Round-Trip JSON (Round-Trip Property)

```
∀ lista de ResourceModel R sin RefSentinel:
  parse_dict(serialize(R)) ≡ R
```

Equivalente a P2 pero para el formato JSON.

### P4 — Invariante de Conteo (Invariant)

```
∀ template CFN válido T con N recursos en Resources:
  len(CloudFormationParser().parse(T)) == N
```

El parser produce exactamente un `ResourceModel` por recurso en la sección `Resources`.
No se pierden ni se duplican recursos.

### P5 — No-Crash con Intrinsic Functions (Error Condition)

```
∀ template CFN T con Intrinsic Functions en cualquier posición:
  CloudFormationParser().parse(T) no lanza excepción
  ∧ len(result) == número de recursos en T.Resources
```

El parser nunca falla por la presencia de `!Ref`, `!Sub` o `!GetAtt`, independientemente
de su posición o anidamiento.

### P6 — Equivalencia YAML/JSON (Metamorphic Property)

```
∀ template CFN T semánticamente equivalente en YAML y JSON (sin Intrinsic Functions):
  parse(T_yaml).resource_types == parse(T_json).resource_types
  ∧ parse(T_yaml).names == parse(T_json).names
  ∧ parse(T_yaml).attributes == parse(T_json).attributes
```

El formato de entrada no afecta el resultado del parseo para templates equivalentes.

### P7 — Consistencia de Estadísticas (Invariant)

```
∀ ScanResult R producido por CfnScanner:
  R.statistics.critical + R.statistics.high + R.statistics.medium
  + R.statistics.low + R.statistics.info == R.statistics.total_findings
  ∧ len(R.findings) == R.statistics.total_findings
```

Las estadísticas del `ScanResult` son siempre consistentes con la lista de findings.

### P8 — Monotonía de Filtro de Severidad (Metamorphic Property)

```
∀ directorio D, ∀ severidades s1 ≤ s2 (en orden Critical > High > Medium > Low > Info):
  len(CfnScanner().run_scan(D, min_severity=s2).findings)
  ≤ len(CfnScanner().run_scan(D, min_severity=s1).findings)
```

Aumentar el umbral de severidad mínima nunca incrementa el número de findings.

### P9 — Idempotencia del ignore_map (Idempotence)

```
∀ template CFN T:
  CloudFormationParser().get_ignore_map(T) == CloudFormationParser().get_ignore_map(T)
```

El `ignore_map` es determinista: llamarlo dos veces produce el mismo resultado.

### P10 — Round-Trip de Serialización de Finding (Round-Trip Property)

```
∀ Finding f producido por análisis CFN:
  Finding(**f.model_dump()) == f
```

Los `Finding` objects son completamente serializables y reconstruibles sin pérdida de información.
Esta propiedad garantiza la integridad de los datos en los reportes JSON/SARIF.

### P11 — Supresión Correcta por ignore_map (Metamorphic Property)

```
∀ template CFN T, ∀ recurso R en T con tmac:ignore[RULE-ID]:
  RULE-ID ∉ {f.rule_id for f in CfnScanner().run_scan(T).findings
             where f.resource_name == R.LogicalId}
```

Un recurso con `tmac:ignore[RULE-ID]` nunca aparece en los findings con ese `rule_id`.

### P12 — Separación de Reglas por Framework (Invariant)

```
∀ ScanResult R producido por CfnScanner:
  ∀ f ∈ R.findings: f.rule_id.startswith("TMAC-CFN-")

∀ ScanResult R producido por Scanner (Terraform):
  ∀ f ∈ R.findings: f.rule_id.startswith("TMAC-AWS-")
```

Los findings de CFN siempre tienen IDs con prefijo `TMAC-CFN-` y los de Terraform con
`TMAC-AWS-`. No hay mezcla de prefijos entre los dos pipelines.

