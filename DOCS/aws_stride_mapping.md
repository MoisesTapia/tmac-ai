# Mapeo de Servicios AWS al Framework STRIDE (TMAC)

La siguiente tabla describe cómo la herramienta TMAC clasifica y analiza los diferentes servicios de AWS bajo la metodología de **Threat Modeling por Elemento** (STRIDE). 

Cada recurso de la arquitectura es asimilado a un elemento base (Proceso, Almacenamiento, Flujo de Datos, Entidad Externa) y luego cruzado con las amenazas que le corresponden.

---

## ✅ Reglas Implementadas en TMAC v1.0.0 "Ixtla"

Las siguientes reglas están **actualmente implementadas** en `src/tmac/rules/aws/threats.yaml` y son evaluadas por el motor de TMAC en cada escaneo.

## Tabla de Mapeo de Servicios y Amenazas

| Servicio AWS | Elemento de Arquitectura | Categorías STRIDE Aplicables | Reglas TMAC Evaluadas |
|---|---|---|---|
| **Amazon S3** | Data Store | **I**nfo Disclosure, **T**ampering, **D**oS | `TMAC-AWS-S3-001` (ACL pública), `TMAC-AWS-S3-002` (Sin SSE), `TMAC-AWS-S3-003` (Sin logging), `TMAC-AWS-S3-004` (Force destroy), `TMAC-AWS-S3-005` (Sin Object Lock), `TMAC-AWS-S3-006` (Sitio web estático) |
| **AWS IAM (Users/Roles/Policies)** | External Entity / Trust Boundary | **S**poofing, **E**levation of Privilege | `TMAC-AWS-IAM-001` (Wildcard Resource), `TMAC-AWS-IAM-002` (Política inline), `TMAC-AWS-IAM-003` (Action: *), `TMAC-AWS-IAM-004` (AssumeRole *), `TMAC-AWS-IAM-005` (Access keys permanentes), `TMAC-AWS-IAM-006` (Confused Deputy), `TMAC-AWS-IAM-007` (PassRole irrestricto), `TMAC-AWS-IAM-008` (IAM Users directos), `TMAC-AWS-IAM-009` (Sin password reset) |
| **Amazon VPC & Security Groups** | Data Flow | **I**nfo Disclosure, **T**ampering, **R**epudiation | `TMAC-AWS-SG-001` (SSH abierto), `TMAC-AWS-SG-002` (RDP abierto), `TMAC-AWS-SG-003` (Egress irrestricto), `TMAC-AWS-VPC-001` (Sin Flow Logs — ver nota), `TMAC-AWS-VPC-002` (Default SG sin restricciones) |
| **Amazon EC2 & EBS** | Process | **E**levation of Privilege, **S**poofing, **I**nfo Disclosure | `TMAC-AWS-EC2-001` (IMDSv1 habilitado), `TMAC-AWS-EC2-002` (EBS sin cifrar), `TMAC-AWS-EC2-003` (IP pública directa) |
| **Amazon RDS** | Data Store | **I**nfo Disclosure, **D**oS, **T**ampering, **S**poofing | `TMAC-AWS-RDS-001` (Sin encriptación), `TMAC-AWS-RDS-002` (Acceso público), `TMAC-AWS-RDS-003` (Sin Multi-AZ), `TMAC-AWS-RDS-004` (Sin deletion protection), `TMAC-AWS-RDS-005` (Sin autenticación IAM) |
| **Amazon DynamoDB** | Data Store | **I**nfo Disclosure, **T**ampering, **D**oS | `TMAC-AWS-DDB-001` (Sin PITR), `TMAC-AWS-DDB-002` (Sin CMK/SSE), `TMAC-AWS-DDB-003` (Sin deletion protection) |
| **AWS CloudTrail & AWS Config** | Security Control (Audit) | **R**epudiation | `TMAC-AWS-CW-001` (CloudTrail sin logging de gestión) |
| **AWS Lambda & Serverless** | Process | **S**poofing, **R**epudiation, **D**oS | `TMAC-AWS-LMD-001` (URL pública sin auth), `TMAC-AWS-LMD-002` (Sin X-Ray), `TMAC-AWS-LMD-003` (Sin límite de concurrencia) |
| **Amazon API Gateway** | Data Flow / Boundary | **S**poofing, **R**epudiation | `TMAC-AWS-APIGW-001` (Método sin autorización), `TMAC-AWS-APIGW-002` (Sin access logging), `TMAC-AWS-APIGW-003` (Sin X-Ray) |
| **AWS KMS** | Security Control | **I**nfo Disclosure, **D**oS, **S**poofing | `TMAC-AWS-KMS-001` (Sin rotación automática), `TMAC-AWS-KMS-002` (Clave en pending deletion), `TMAC-AWS-KMS-003` (Política abierta al público) |
| **Amazon SQS & Amazon SNS** | Data Flow | **I**nfo Disclosure, **S**poofing, **E**oP | `TMAC-AWS-SQS-001` (SQS sin SSE-KMS), `TMAC-AWS-SQS-002` (Política SQS pública), `TMAC-AWS-SNS-001` (SNS sin KMS), `TMAC-AWS-SNS-002` (Política SNS pública) |
| **Amazon SES** | Data Flow | **I**nfo Disclosure | `TMAC-AWS-SES-001` (Sin TLS forzado en recepción) |
| **Almacenamiento (Backup, EFS, FSx)** | Data Store | **I**nfo Disclosure, **T**ampering | `TMAC-AWS-BKP-001` (Backup vault sin KMS), `TMAC-AWS-EFS-001` (EFS sin cifrado), `TMAC-AWS-FSX-001` (FSx Windows sin CMK), `TMAC-AWS-FSX-002` (FSx Lustre sin CMK) |
| **AWS Auto Scaling** | Process | **D**enial of Service | `TMAC-AWS-ASG-001` (ASG en una sola AZ — SPOF) |
| **Amazon CloudWatch Logs** | Data Store (Audit) | **I**nformation Disclosure | `TMAC-AWS-CWL-001` (Log group sin KMS) |
| **AWS Systems Manager (SSM)** | Data Store (Secrets) | **I**nformation Disclosure | `TMAC-AWS-SSM-001` (Parámetro como String en lugar de SecureString) |
| **AWS Organizations** | External Entity | **E**levation of Privilege | `TMAC-AWS-ORG-001` (Sin SCPs habilitadas) |
| **AWS CloudFormation** | Process (Deployment) | **T**ampering, **D**enial of Service | `TMAC-AWS-CFN-001` (Stack sin termination protection) |
| **Amazon ECR** | Data Store (Images) | **T**ampering | `TMAC-AWS-ECR-001` (Sin scan-on-push), `TMAC-AWS-ECR-002` (Etiquetas mutables) |
| **Amazon EKS & ECS** | Process (Orchestrator) | **R**epudiation, **S**poofing | `TMAC-AWS-EKS-001` (Endpoint público), `TMAC-AWS-EKS-002` (Sin cifrado de secretos KMS), `TMAC-AWS-EKS-003` (Sin logging de control plane), `TMAC-AWS-ECS-001` (Sin Container Insights) |

---

## 🚧 Servicios Planificados para Versiones Futuras

Los siguientes servicios AWS aparecen en el mapeo de amenazas pero **no tienen reglas implementadas** en TMAC v1.0.0 "Ixtla". Están planificados para versiones posteriores.

| Servicio AWS | Categorías STRIDE | Amenazas Identificadas | Versión Planificada |
|---|---|---|---|
| **AWS Fargate** | **R**epudiation | Clústeres sin Container Insights (invisibilidad de trazas) | v1.1.0 |
| **AWS Elastic Beanstalk** | **T**ampering, **I**nfo Disclosure | Entornos sin Managed Updates | v1.1.0 |
| **AWS Batch** | **I**nformation Disclosure | Entornos sin subredes estrictas (IPs públicas) | v1.1.0 |
| **AWS App Runner** | **S**poofing, **I**nfo Disclosure | Sin Ingress VPC Configuration | v1.1.0 |
| **Amazon EC2 Image Builder** | **I**nformation Disclosure | AMIs sin CMK de KMS (`kms_key_id`) | v1.1.0 |
| **Amazon Aurora / Neptune / DocumentDB** | **I**nformation Disclosure | Sin `storage_encrypted` | v1.1.0 |
| **Amazon ElastiCache & MemoryDB** | **I**nformation Disclosure | Sin TLS en tránsito (`tls_enabled`) | v1.1.0 |
| **AWS AppSync** | **R**epudiation | Sin Field Level Logs en GraphQL | v1.2.0 |
| **AWS Amplify** | **I**nformation Disclosure | Ramas pre-productivas sin Basic Auth | v1.2.0 |
| **Amazon Location Tracker** | **I**nformation Disclosure | Repositorios de ubicación sin KMS | v1.2.0 |
| **Amazon Device Farm** | **I**nformation Disclosure | Sin configuración VPC estricta | v1.2.0 |

---

## ⚠️ Nota Técnica: Limitación de `TMAC-AWS-VPC-001`

### Descripción del Workaround

La regla `TMAC-AWS-VPC-001` ("Amazon VPC sin Flow Logs Habilitados") presenta una **limitación técnica conocida** derivada de la arquitectura del motor de análisis estático de TMAC v1.0.0.

**Problema raíz:** Los VPC Flow Logs en Terraform se configuran como un recurso separado (`aws_flow_log`), no como un atributo inline del recurso `aws_vpc`. El motor de TMAC v1.0.0 evalúa cada recurso de forma independiente y no realiza correlación entre recursos distintos en el mismo blueprint.

**Mecanismo de detección actual (workaround):** En lugar de verificar la existencia de un recurso `aws_flow_log` asociado, la regla verifica la **ausencia del tag `FlowLogs = "enabled"`** en el recurso `aws_vpc`:

```yaml
check:
  attribute: "tags.FlowLogs"
  condition: "not_exists"
  values: []
```

**Implicaciones:**

| Escenario | Comportamiento de TMAC-AWS-VPC-001 |
|---|---|
| VPC sin `aws_flow_log` y sin tag `FlowLogs` | ✅ Detectado correctamente (verdadero positivo) |
| VPC con `aws_flow_log` declarado pero sin tag `FlowLogs` | ⚠️ Falso positivo — TMAC reporta hallazgo aunque Flow Logs estén activos |
| VPC sin `aws_flow_log` pero con tag `FlowLogs = "enabled"` | ⚠️ Falso negativo — TMAC no reporta hallazgo aunque Flow Logs no estén activos |
| VPC con `aws_flow_log` y con tag `FlowLogs = "enabled"` | ✅ No detectado (verdadero negativo) |

**Mitigación recomendada para usuarios:** Si ya declaraste un recurso `aws_flow_log` en tu blueprint, añade el tag `FlowLogs = "enabled"` a tu recurso `aws_vpc` para evitar el falso positivo:

```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = {
    FlowLogs = "enabled"
  }
}

resource "aws_flow_log" "main" {
  vpc_id          = aws_vpc.main.id
  traffic_type    = "ALL"
  iam_role_arn    = aws_iam_role.flow_log.arn
  log_destination = aws_cloudwatch_log_group.flow_log.arn
}
```

**Roadmap:** La correlación entre recursos (`aws_vpc` ↔ `aws_flow_log`) está planificada para TMAC v1.2.0 mediante un motor de análisis multi-recurso que permitirá verificar la existencia de recursos relacionados en el mismo blueprint.

---

## 🎯 Abordaje de TMAC frente al Framework STRIDE

*   **Spoofing (Suplantación de Identidad):** Abordado garantizando la integración con **IAM** (Autenticación estricta en DBs y APIs) y previniendo `Principal: *` o accesos "NONE" en Lambdas y Gateways.
*   **Tampering (Manipulación de Datos):** Penaliza fuertemente a las bases de datos (S3, RDS, DynamoDB, CFN) que no presentan mecánicas de Versionado, Point-In-Time-Recovery o candados Anti-Borrado.
*   **Repudiation (Repudio):** Cubierto obligando a activar los Logs de Auditoría pertinentes por servicio: VPC Flow Logs, APIGW Access Logs, AWS X-Ray, CloudTrail y Recording en Config.
*   **Information Disclosure (Fuga de Información):** Categoría crítica y predominante. Salvaguardada verificando la obligatoria implementación general de llaves **CMK (KMS)**, requiriendo TLS continuo y bloqueando SGs con puerto saliente 0.0.0.0/0.
*   **Denial of Service (Denegación de Servicio):** Controlado mitigando fallas de arquitectura, como Multi-AZ en RDS y Auto Scaling, o límites de concurrencia en Funciones Serverless para prevenir DoS Financiero.
*   **Elevation of Privilege (Elevación de Privilegios):** Mapeado detectando confianza ciega inter-cuenta (Trust Policies abiertas), bloqueando vulnerabilidades de red (IMDSv1 en EC2) y exigiendo control organizacional SCP (Organizations).
