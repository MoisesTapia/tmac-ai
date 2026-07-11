# 🛡️ TMAC Security Report

**Generated on:** 2026-06-17T08:50:34.224612Z  
**Scanned Directory:** `examples/demo`  
**Execution Time:** 0.15s

## 📊 Summary

| Metric | Count |
|--------|-------|
| 📦 Total Resources | **6** |
| 🚫 Total Findings | **16** |
| 🔴 **Critical** | 0 |
| 🟠 **High** | 2 |
| 🟡 **Medium** | 3 |

---

## 🔍 Findings



### [🟡 Medium] Amazon VPC without Flow Logs Enabled

- **Rule ID:** `TMAC-AWS-VPC-001`
- **Resource:** `aws_vpc.main`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
An AWS VPC is being defined without network-level traceability (Flow Logs). By not capturing information about the IP traffic entering and leaving the network interfaces, there is no visibility into network scans, anomalous traffic or intrusions (Repudiation). IMPLEMENTATION NOTE: This rule uses a tag-based workaround because the TMAC v1.0.0 engine does not correlate distinct resources. If you already declared an aws_flow_log resource associated with this VPC, add the 'FlowLogs = "enabled"' tag to suppress this finding. See DOCS/aws_stride_mapping.md for full documentation of the limitation.


**Mitigation:**
```terraform
Create an 'aws_flow_log' resource associated with this VPC and add the 'FlowLogs = "enabled"' tag to indicate to TMAC that Flow Logs are active:
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
---

### [🔵 Info] VPC without governance tags

- **Rule ID:** `TMAC-AWS-VPC-007`
- **Resource:** `aws_vpc.main`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The VPC does not define tags, hindering cost attribution, ownership and auditing.

**Mitigation:**
```terraform
Add ownership, environment and cost-center tags.
```
---

### [🔵 Info] VPC without an identifiable name

- **Rule ID:** `TMAC-AWS-VPC-008`
- **Resource:** `aws_vpc.main`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The VPC has no Name tag, complicating operational identification.

**Mitigation:**
```terraform
Add tags = { Name = "..." }.
```
---

### [🔵 Info] VPC with undeclared data classification

- **Rule ID:** `TMAC-AWS-VPC-009`
- **Resource:** `aws_vpc.main`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Information Disclosure

**Description:**
The VPC does not declare data classification in tags, hindering applying controls by sensitivity.

**Mitigation:**
```terraform
Add tags.DataClassification (e.g. public/internal/confidential).
```
---

### [🔵 Info] Subnet without a Name tag

- **Rule ID:** `TMAC-AWS-SUBNET-003`
- **Resource:** `aws_subnet.web`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The subnet has no Name tag, hindering its identification.

**Mitigation:**
```terraform
Add tags = { Name = "..." }.
```
---

### [🔵 Info] Subnet without tags

- **Rule ID:** `TMAC-AWS-SUBNET-004`
- **Resource:** `aws_subnet.web`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The subnet does not define governance tags.

**Mitigation:**
```terraform
Add environment and ownership tags.
```
---

### [🟢 Low] Subnet without an explicit AZ

- **Rule ID:** `TMAC-AWS-SUBNET-005`
- **Resource:** `aws_subnet.web`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Denial of Service

**Description:**
The subnet does not pin an explicit AZ; non-deterministic deployments can break high availability.

**Mitigation:**
```terraform
Define availability_zone explicitly and distribute across multiple AZs.
```
---

### [🟠 High] SSH Port (22) Open to the World

- **Rule ID:** `TMAC-AWS-SG-001`
- **Resource:** `aws_security_group.web_sg`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Tampering

**Description:**
The SSH port (22) is globally exposed (0.0.0.0/0), enabling brute-force attacks, exploitation of SSH service vulnerabilities, and unauthorized access to instances.


**Mitigation:**
```terraform
Restrict SSH access to known corporate IPs only, or use AWS Systems Manager Session Manager as an alternative with no open ports:
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Corporate network only
  }

```
---

### [🔵 Info] Security Group without rule descriptions

- **Rule ID:** `TMAC-AWS-SG-007`
- **Resource:** `aws_security_group.web_sg`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The ingress rules have no description, hindering audits and reviews.

**Mitigation:**
```terraform
Add a description to each ingress/egress rule.
```
---

### [🔵 Info] Security Group without tags

- **Rule ID:** `TMAC-AWS-SG-008`
- **Resource:** `aws_security_group.web_sg`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The security group does not define governance tags.

**Mitigation:**
```terraform
Add ownership and environment tags.
```
---

### [🟠 High] RDS Database without Multi-AZ Enabled

- **Rule ID:** `TMAC-AWS-RDS-003`
- **Resource:** `aws_db_instance.prod`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Denial of Service

**Description:**
The RDS instance does not have Multi-AZ deployment enabled. This means the database is a single point of failure (SPOF). In the event of an availability zone outage, the application will suffer a Denial of Service (DoS).


**Mitigation:**
```terraform
Configure 'multi_az = true' for production deployments to ensure high availability:
  resource "aws_db_instance" "example" {
    # ...
    multi_az = true
  }

```
---

### [🟡 Medium] RDS Instance without Deletion Protection

- **Rule ID:** `TMAC-AWS-RDS-004`
- **Resource:** `aws_db_instance.prod`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Tampering

**Description:**
Accidental deletion protection ('deletion_protection') is disabled or not explicitly configured. This allows the database to be deleted easily, which could cause irreversible data loss through negligence or malicious tampering.


**Mitigation:**
```terraform
Enable 'deletion_protection' on production databases to enforce safe deletion locks:
  resource "aws_db_instance" "example" {
    # ...
    deletion_protection = true
  }

```
---

### [🟡 Medium] RDS without IAM Authentication Enabled

- **Rule ID:** `TMAC-AWS-RDS-005`
- **Resource:** `aws_db_instance.prod`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Spoofing

**Description:**
The RDS instance relies entirely on embedded static passwords, with no integration with AWS IAM. This raises the risk of credential theft and Spoofing due to the lack of automated rotation and granular permissions.


**Mitigation:**
```terraform
Use IAM Database Authentication to map database users to temporary IAM roles:
  resource "aws_db_instance" "example" {
    # ...
    iam_database_authentication_enabled = true
  }

```
---

### [🟢 Low] Flow Log without an IAM role

- **Rule ID:** `TMAC-AWS-FL-003`
- **Resource:** `aws_flow_log.vpc_flow`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The flow log to CloudWatch does not specify iam_role_arn to publish the records.

**Mitigation:**
```terraform
Assign iam_role_arn with permissions to write to CloudWatch Logs.
```
---

### [🔵 Info] Flow Log without a custom format

- **Rule ID:** `TMAC-AWS-FL-005`
- **Resource:** `aws_flow_log.vpc_flow`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The flow log uses the default format; additional fields (pkt-srcaddr, flow-direction) improve analysis.

**Mitigation:**
```terraform
Define log_format with the fields relevant to your detection.
```
---

### [🔵 Info] Flow Log without tags

- **Rule ID:** `TMAC-AWS-FL-007`
- **Resource:** `aws_flow_log.vpc_flow`
- **File:** `examples/demo/main.tf`
- **STRIDE Category:** Repudiation

**Description:**
The flow log does not define governance tags.

**Mitigation:**
```terraform
Add ownership and environment tags.
```
---


