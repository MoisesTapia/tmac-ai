# Mapping of AWS Services to the STRIDE Framework (TMAC)

The following table describes how the TMAC tool classifies and analyzes the different AWS services under the **Threat Modeling per Element** (STRIDE) methodology.

Each resource in the architecture is mapped to a base element (Process, Data Store, Data Flow, External Entity) and then cross-referenced with the threats that apply to it.

---

## ✅ Rules Implemented in TMAC v1.0.0 "Ixtla"

The following rules are **currently implemented** in `src/tmac/rules/aws/threats.yaml` and are evaluated by the TMAC engine on every scan.

## Service and Threat Mapping Table

| AWS Service | Architecture Element | Applicable STRIDE Categories | TMAC Rules Evaluated |
|---|---|---|---|
| **Amazon S3** | Data Store | **I**nfo Disclosure, **T**ampering, **D**oS | `TMAC-AWS-S3-001` (Public ACL), `TMAC-AWS-S3-002` (No SSE), `TMAC-AWS-S3-003` (No logging), `TMAC-AWS-S3-004` (Force destroy), `TMAC-AWS-S3-005` (No Object Lock), `TMAC-AWS-S3-006` (Static website) |
| **AWS IAM (Users/Roles/Policies)** | External Entity / Trust Boundary | **S**poofing, **E**levation of Privilege | `TMAC-AWS-IAM-001` (Wildcard Resource), `TMAC-AWS-IAM-002` (Inline policy), `TMAC-AWS-IAM-003` (Action: *), `TMAC-AWS-IAM-004` (AssumeRole *), `TMAC-AWS-IAM-005` (Permanent access keys), `TMAC-AWS-IAM-006` (Confused Deputy), `TMAC-AWS-IAM-007` (Unrestricted PassRole), `TMAC-AWS-IAM-008` (Direct IAM Users), `TMAC-AWS-IAM-009` (No password reset) |
| **Amazon VPC & Security Groups** | Data Flow | **I**nfo Disclosure, **T**ampering, **R**epudiation | `TMAC-AWS-SG-001` (SSH open), `TMAC-AWS-SG-002` (RDP open), `TMAC-AWS-SG-003` (Unrestricted egress), `TMAC-AWS-VPC-001` (No Flow Logs — see note), `TMAC-AWS-VPC-002` (Default SG without restrictions) |
| **Amazon EC2 & EBS** | Process | **E**levation of Privilege, **S**poofing, **I**nfo Disclosure | `TMAC-AWS-EC2-001` (IMDSv1 enabled), `TMAC-AWS-EC2-002` (Unencrypted EBS), `TMAC-AWS-EC2-003` (Direct public IP) |
| **Amazon RDS** | Data Store | **I**nfo Disclosure, **D**oS, **T**ampering, **S**poofing | `TMAC-AWS-RDS-001` (No encryption), `TMAC-AWS-RDS-002` (Public access), `TMAC-AWS-RDS-003` (No Multi-AZ), `TMAC-AWS-RDS-004` (No deletion protection), `TMAC-AWS-RDS-005` (No IAM authentication) |
| **Amazon DynamoDB** | Data Store | **I**nfo Disclosure, **T**ampering, **D**oS | `TMAC-AWS-DDB-001` (No PITR), `TMAC-AWS-DDB-002` (No CMK/SSE), `TMAC-AWS-DDB-003` (No deletion protection) |
| **AWS CloudTrail & AWS Config** | Security Control (Audit) | **R**epudiation | `TMAC-AWS-CW-001` (CloudTrail without management logging) |
| **AWS Lambda & Serverless** | Process | **S**poofing, **R**epudiation, **D**oS | `TMAC-AWS-LMD-001` (Public URL without auth), `TMAC-AWS-LMD-002` (No X-Ray), `TMAC-AWS-LMD-003` (No concurrency limit) |
| **Amazon API Gateway** | Data Flow / Boundary | **S**poofing, **R**epudiation | `TMAC-AWS-APIGW-001` (Method without authorization), `TMAC-AWS-APIGW-002` (No access logging), `TMAC-AWS-APIGW-003` (No X-Ray) |
| **AWS KMS** | Security Control | **I**nfo Disclosure, **D**oS, **S**poofing | `TMAC-AWS-KMS-001` (No automatic rotation), `TMAC-AWS-KMS-002` (Key in pending deletion), `TMAC-AWS-KMS-003` (Policy open to the public) |
| **Amazon SQS & Amazon SNS** | Data Flow | **I**nfo Disclosure, **S**poofing, **E**oP | `TMAC-AWS-SQS-001` (SQS without SSE-KMS), `TMAC-AWS-SQS-002` (Public SQS policy), `TMAC-AWS-SNS-001` (SNS without KMS), `TMAC-AWS-SNS-002` (Public SNS policy) |
| **Amazon SES** | Data Flow | **I**nfo Disclosure | `TMAC-AWS-SES-001` (No enforced TLS on receipt) |
| **Storage (Backup, EFS, FSx)** | Data Store | **I**nfo Disclosure, **T**ampering | `TMAC-AWS-BKP-001` (Backup vault without KMS), `TMAC-AWS-EFS-001` (EFS without encryption), `TMAC-AWS-FSX-001` (FSx Windows without CMK), `TMAC-AWS-FSX-002` (FSx Lustre without CMK) |
| **AWS Auto Scaling** | Process | **D**enial of Service | `TMAC-AWS-ASG-001` (ASG in a single AZ — SPOF) |
| **Amazon CloudWatch Logs** | Data Store (Audit) | **I**nformation Disclosure | `TMAC-AWS-CWL-001` (Log group without KMS) |
| **AWS Systems Manager (SSM)** | Data Store (Secrets) | **I**nformation Disclosure | `TMAC-AWS-SSM-001` (Parameter as String instead of SecureString) |
| **AWS Organizations** | External Entity | **E**levation of Privilege | `TMAC-AWS-ORG-001` (No SCPs enabled) |
| **AWS CloudFormation** | Process (Deployment) | **T**ampering, **D**enial of Service | `TMAC-AWS-CFN-001` (Stack without termination protection) |
| **Amazon ECR** | Data Store (Images) | **T**ampering | `TMAC-AWS-ECR-001` (No scan-on-push), `TMAC-AWS-ECR-002` (Mutable tags) |
| **Amazon EKS & ECS** | Process (Orchestrator) | **R**epudiation, **S**poofing | `TMAC-AWS-EKS-001` (Public endpoint), `TMAC-AWS-EKS-002` (No KMS secrets encryption), `TMAC-AWS-EKS-003` (No control plane logging), `TMAC-AWS-ECS-001` (No Container Insights) |
| **AWS WAFv2** | Data Flow (Edge) | **D**enial of Service, **R**epudiation | `TMAC-AWS-WAF-001` (No rate limiting rules), `TMAC-AWS-WAF-002` (No logging enabled) |
| **Application Load Balancer (ALB)** | Data Flow | **R**epudiation, **I**nfo Disclosure | `TMAC-AWS-ALB-001` (No access logs), `TMAC-AWS-ALB-002` (HTTP listener without redirect to HTTPS) |
| **Amazon CloudFront** | Data Flow (CDN/Edge) | **T**ampering, **I**nfo Disclosure | `TMAC-AWS-CF-001` (No associated WAF), `TMAC-AWS-CF-002` (Viewer protocol allow-all) |
| **Amazon Cognito** | External Entity (IdP) | **S**poofing, **R**epudiation | `TMAC-AWS-COGNITO-001` (No mandatory MFA), `TMAC-AWS-COGNITO-002` (No password policy), `TMAC-AWS-COGNITO-003` (No Advanced Security Mode) |
| **AWS Secrets Manager** | Data Store (Secrets) | **I**nfo Disclosure | `TMAC-AWS-SM-001` (No automatic rotation), `TMAC-AWS-SM-002` (No KMS CMK) |
| **Amazon Redshift** | Data Store (DW) | **I**nfo Disclosure, **R**epudiation | `TMAC-AWS-RS-001` (No encryption), `TMAC-AWS-RS-002` (Public access), `TMAC-AWS-RS-003` (No audit logging) |
| **Amazon OpenSearch Service** | Data Store (Search) | **I**nfo Disclosure | `TMAC-AWS-OS-001` (No encryption at rest), `TMAC-AWS-OS-002` (No VPC), `TMAC-AWS-OS-003` (No enforced TLS) |
| **Amazon Kinesis Data Streams** | Data Flow (Streaming) | **I**nfo Disclosure | `TMAC-AWS-KDS-001` (No KMS encryption) |
| **Amazon MSK (Kafka)** | Data Flow (Streaming) | **I**nfo Disclosure, **S**poofing | `TMAC-AWS-MSK-001` (No TLS in transit), `TMAC-AWS-MSK-002` (No mTLS/SASL authentication) |
| **AWS Fargate (ECS Task Definitions)** | Process (Container) | **R**epudiation, **E**levation of Privilege, **T**ampering | `TMAC-AWS-FARGATE-001` (No logging), `TMAC-AWS-FARGATE-002` (Privileged container), `TMAC-AWS-FARGATE-003` (No read-only rootfs) |

---

## 🚧 Services Planned for Future Versions

The following AWS services appear in the threat mapping but **do not yet have implemented rules**. They are planned for later versions.

| AWS Service | STRIDE Categories | Identified Threats | Planned Version |
|---|---|---|---|
| **AWS Glue** | **R**epudiation, **I**nfo Disclosure | Jobs without CloudWatch logging, connections without SSL | v1.3.0 |
| **Amazon Athena** | **R**epudiation | Workgroup without query logging | v1.3.0 |
| **AWS Step Functions** | **R**epudiation | State machine without logging enabled | v1.3.0 |
| **Amazon EventBridge** | **T**ampering, **S**poofing | Event bus with a policy open to the public | v1.3.0 |
| **AWS Transfer Family** | **I**nfo Disclosure, **S**poofing | SFTP server without IAM authentication | v1.3.0 |
| **Amazon MQ** | **I**nfo Disclosure | Broker without encryption at rest | v1.3.0 |

---

## ⚠️ Technical Note: Limitation of `TMAC-AWS-VPC-001`

### Description of the Workaround

The `TMAC-AWS-VPC-001` rule ("Amazon VPC without Flow Logs Enabled") has a **known technical limitation** stemming from the architecture of the TMAC v1.0.0 static analysis engine.

**Root cause:** VPC Flow Logs in Terraform are configured as a separate resource (`aws_flow_log`), not as an inline attribute of the `aws_vpc` resource. The TMAC v1.0.0 engine evaluates each resource independently and does not correlate distinct resources within the same blueprint.

**Current detection mechanism (workaround):** Instead of checking for the existence of an associated `aws_flow_log` resource, the rule checks for the **absence of the `FlowLogs = "enabled"` tag** on the `aws_vpc` resource:

```yaml
check:
  attribute: "tags.FlowLogs"
  condition: "not_exists"
  values: []
```

**Implications:**

| Scenario | TMAC-AWS-VPC-001 Behavior |
|---|---|
| VPC without `aws_flow_log` and without `FlowLogs` tag | ✅ Detected correctly (true positive) |
| VPC with `aws_flow_log` declared but without `FlowLogs` tag | ⚠️ False positive — TMAC reports a finding even though Flow Logs are active |
| VPC without `aws_flow_log` but with `FlowLogs = "enabled"` tag | ⚠️ False negative — TMAC does not report a finding even though Flow Logs are not active |
| VPC with `aws_flow_log` and with `FlowLogs = "enabled"` tag | ✅ Not detected (true negative) |

**Recommended mitigation for users:** If you have already declared an `aws_flow_log` resource in your blueprint, add the `FlowLogs = "enabled"` tag to your `aws_vpc` resource to avoid the false positive:

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

**Roadmap:** Cross-resource correlation (`aws_vpc` ↔ `aws_flow_log`) is planned for TMAC v1.2.0 through a multi-resource analysis engine that will be able to verify the existence of related resources within the same blueprint.

---

## 🎯 TMAC's Approach to the STRIDE Framework

*   **Spoofing (Identity Impersonation):** Addressed by ensuring integration with **IAM** (strict authentication on DBs and APIs), preventing `Principal: *` or "NONE" access on Lambdas and Gateways, enforcing **MFA on Cognito**, mTLS/SASL authentication on MSK, and blocking Lambda URLs without authorization.
*   **Tampering (Data Manipulation):** Heavily penalizes data stores (S3, RDS, DynamoDB, CFN) that lack Versioning, Point-In-Time-Recovery, or anti-deletion locks. Includes protection of Fargate containers (read-only rootfs, no privileged) and CloudFront without WAF.
*   **Repudiation:** Covered by requiring the relevant Audit Logs to be enabled per service: VPC Flow Logs, APIGW Access Logs, AWS X-Ray, CloudTrail, Config, **ALB Access Logs**, **WAFv2 Logging**, **Redshift Audit Logging**, **Cognito Advanced Security**, and Fargate container logging.
*   **Information Disclosure (Data Leakage):** A critical and predominant category. Safeguarded by verifying the mandatory general implementation of **CMK (KMS)** keys, requiring continuous TLS (ALB, MSK, OpenSearch, Kinesis), blocking public access on **Redshift** and **OpenSearch**, and protecting secrets with **Secrets Manager** with automatic rotation.
*   **Denial of Service:** Controlled by mitigating architectural failures (Multi-AZ on RDS, multi-AZ Auto Scaling), concurrency limits on Lambdas, and adding **WAFv2 with rate limiting** as an edge protection layer for CloudFront and ALB.
*   **Elevation of Privilege:** Mapped by detecting blind cross-account trust (open Trust Policies), blocking network vulnerabilities (IMDSv1 on EC2), requiring organizational SCP control (Organizations), and preventing **privileged Fargate containers** that allow escaping container isolation.
