# Rule Catalog — TMAC v1.6.0

TMAC includes **1,075 rules** covering **269 AWS resource types** across **178 services**, organized by service. Each rule follows the format `TMAC-AWS-{SERVICE}-{NNN}`.

## Summary by severity

| Severity | Rules |
| :--- | :--- |
| 🔴 Critical | 81 |
| 🟠 High | 268 |
| 🟡 Medium | 278 |
| 🟢 Low | 145 |
| 🔵 Info | 303 |
| **Total** | **1,075** |

## Rules by service

| Service | Rules | Resource types |
| :--- | :--- | :--- |
| AURORA | 9 | `aws_rds_cluster` |
| IAM | 9 | `aws_iam_access_key`, `aws_iam_policy`, `aws_iam_role`, `aws_iam_user`, `aws_iam_user_login_profile`, `aws_iam_user_policy` |
| VPC | 9 | `aws_default_security_group`, `aws_vpc` |
| ACM | 8 | `aws_acm_certificate` |
| ASG | 8 | `aws_autoscaling_group` |
| CB | 8 | `aws_codebuild_project` |
| CC | 8 | `aws_codecommit_repository` |
| CDA | 8 | `aws_codedeploy_app` |
| CDG | 8 | `aws_codedeploy_deployment_group` |
| CFGR | 8 | `aws_config_configuration_recorder` |
| COGCLIENT | 8 | `aws_cognito_user_pool_client` |
| COGDOM | 8 | `aws_cognito_user_pool_domain` |
| COGNITO | 8 | `aws_cognito_user_pool` |
| CP | 8 | `aws_codepipeline` |
| CWALARM | 8 | `aws_cloudwatch_metric_alarm` |
| DBSG | 8 | `aws_db_subnet_group` |
| DPT | 8 | `aws_db_proxy_target` |
| DPTG | 8 | `aws_db_proxy_default_target_group` |
| EB | 8 | `aws_elastic_beanstalk_environment` |
| EBAPP | 8 | `aws_elastic_beanstalk_application` |
| ECR | 8 | `aws_ecr_repository` |
| EIP | 8 | `aws_eip` |
| FL | 8 | `aws_flow_log` |
| IAMRP | 8 | `aws_iam_role_policy` |
| IGW | 8 | `aws_internet_gateway` |
| IIP | 8 | `aws_iam_instance_profile` |
| KMSAL | 8 | `aws_kms_alias` |
| LT | 8 | `aws_launch_template` |
| NAT | 8 | `aws_nat_gateway` |
| PINPOINT | 8 | `aws_pinpoint_app` |
| PINSTREAM | 8 | `aws_pinpoint_event_stream` |
| QS | 8 | `aws_quicksight_data_source` |
| R53R | 8 | `aws_route53_record` |
| R53Z | 8 | `aws_route53_zone` |
| RDSCI | 8 | `aws_rds_cluster_instance` |
| RT | 8 | `aws_route_table` |
| RTA | 8 | `aws_route_table_association` |
| S3 | 8 | `aws_s3_bucket` |
| S3LC | 8 | `aws_s3_bucket_lifecycle_configuration` |
| S3SSE | 8 | `aws_s3_bucket_server_side_encryption_configuration` |
| S3WEB | 8 | `aws_s3_bucket_website_configuration` |
| SG | 8 | `aws_security_group` |
| SMVER | 8 | `aws_secretsmanager_secret_version` |
| SUBNET | 8 | `aws_subnet` |
| TG | 8 | `aws_lb_target_group` |
| VPCE | 8 | `aws_vpc_endpoint` |
| WAFASSOC | 8 | `aws_wafv2_web_acl_association` |
| CT | 7 | `aws_cloudtrail` |
| CWLG | 7 | `aws_cloudwatch_log_group` |
| DBPROXY | 7 | `aws_db_proxy` |
| KDF | 7 | `aws_kinesis_firehose_delivery_stream` |
| LB | 7 | `aws_lb` |
| LBL | 7 | `aws_lb_listener` |
| WAFACL | 7 | `aws_wafv2_web_acl` |
| IAMROLE | 6 | `aws_iam_role` |
| SMSEC | 6 | `aws_secretsmanager_secret` |
| KMSKEY | 5 | `aws_kms_key` |
| RDS | 5 | `aws_db_instance` |
| APIGW | 3 | `aws_api_gateway_method`, `aws_api_gateway_stage` |
| DDB | 3 | `aws_dynamodb_table` |
| EC2 | 3 | `aws_ebs_volume`, `aws_instance` |
| EKS | 3 | `aws_eks_cluster` |
| FARGATE | 3 | `aws_ecs_task_definition` |
| KMS | 3 | `aws_kms_key` |
| LMD | 3 | `aws_lambda_function`, `aws_lambda_function_url` |
| OS | 3 | `aws_opensearch_domain` |
| RS | 3 | `aws_redshift_cluster` |
| ALB | 2 | `aws_lb`, `aws_lb_listener` |
| CF | 2 | `aws_cloudfront_distribution` |
| FSX | 2 | `aws_fsx_lustre_file_system`, `aws_fsx_windows_file_system` |
| MSK | 2 | `aws_msk_cluster` |
| SM | 2 | `aws_secretsmanager_secret` |
| SNS | 2 | `aws_sns_topic`, `aws_sns_topic_policy` |
| SQS | 2 | `aws_sqs_queue`, `aws_sqs_queue_policy` |
| WAF | 2 | `aws_wafv2_web_acl`, `aws_wafv2_web_acl_logging_configuration` |
| AMP | 1 | `aws_amplify_branch` |
| APPR | 1 | `aws_apprunner_service` |
| APPSYNC | 1 | `aws_appsync_graphql_api` |
| BCH | 1 | `aws_batch_compute_environment` |
| BKP | 1 | `aws_backup_vault` |
| CFG | 1 | `aws_config_configuration_recorder` |
| CFN | 1 | `aws_cloudformation_stack` |
| CW | 1 | `aws_cloudtrail` |
| CWL | 1 | `aws_cloudwatch_log_group` |
| DF | 1 | `aws_devicefarm_project` |
| DOCDB | 1 | `aws_docdb_cluster` |
| ECS | 1 | `aws_ecs_cluster` |
| EFS | 1 | `aws_efs_file_system` |
| ELASTI | 1 | `aws_elasticache_replication_group` |
| FIREHOSE | 1 | `aws_kinesis_firehose_delivery_stream` |
| IB | 1 | `aws_imagebuilder_distribution_configuration` |
| KDS | 1 | `aws_kinesis_stream` |
| KEYS | 1 | `aws_keyspaces_keyspace` |
| LOC | 1 | `aws_location_tracker` |
| MEMDB | 1 | `aws_memorydb_cluster` |
| NEPTUNE | 1 | `aws_neptune_cluster` |
| ORG | 1 | `aws_organizations_organization` |
| RDSPROXY | 1 | `aws_db_proxy` |
| SES | 1 | `aws_ses_receipt_rule` |
| SGW | 1 | `aws_storagegateway_smb_file_share` |
| SSM | 1 | `aws_ssm_parameter` |
| TIME | 1 | `aws_timestreamwrite_database` |

---

## Rule detail

### ACM

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-ACM-001` | Certificate with email validation | Medium | Spoofing |
| `TMAC-AWS-ACM-002` | Certificate with broad wildcard | Low | Spoofing |
| `TMAC-AWS-ACM-003` | Certificate without log transparency | Low | Repudiation |
| `TMAC-AWS-ACM-004` | Imported certificate (not managed by ACM) | Medium | Information Disclosure |
| `TMAC-AWS-ACM-005` | Certificate without declared SANs | Info | Spoofing |
| `TMAC-AWS-ACM-006` | Certificate without tags | Info | Repudiation |
| `TMAC-AWS-ACM-007` | Certificate with weak key algorithm | Low | Information Disclosure |
| `TMAC-AWS-ACM-008` | Certificate without safe recreation | Low | Denial of Service |

### ALB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-ALB-001` | Application Load Balancer without Access Logs | Medium | Repudiation |
| `TMAC-AWS-ALB-002` | ALB Listener without HTTP→HTTPS Redirection | High | Information Disclosure |

### AMP

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-AMP-001` | Public AWS Amplify Branch (Exposed Environment) | Low | Information Disclosure |

### APIGW

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-APIGW-001` | API Gateway Method without Authorization | Critical | Spoofing |
| `TMAC-AWS-APIGW-002` | API Gateway Stage without Access Logging | Medium | Repudiation |
| `TMAC-AWS-APIGW-003` | API Gateway Stage without X-Ray Tracing | Low | Repudiation |

### APPR

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-APPR-001` | App Runner Service Publicly Exposed (No VPC Ingress) | High | Spoofing |

### APPSYNC

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-APPSYNC-001` | AppSync GraphQL API without Logging (Field-Level Logs) | Medium | Repudiation |

### ASG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-ASG-001` | Auto Scaling Group Limited to a Single Zone (SPOF) | High | Denial of Service |
| `TMAC-AWS-ASG-002` | ASG in a single subnet/AZ | Medium | Denial of Service |
| `TMAC-AWS-ASG-003` | ASG without ELB health check | Low | Denial of Service |
| `TMAC-AWS-ASG-004` | ASG with zero minimum capacity | Low | Denial of Service |
| `TMAC-AWS-ASG-005` | ASG without instance scale-in protection | Info | Denial of Service |
| `TMAC-AWS-ASG-006` | ASG without a safe termination policy | Info | Denial of Service |
| `TMAC-AWS-ASG-007` | ASG without propagated tags | Info | Repudiation |
| `TMAC-AWS-ASG-008` | ASG without instance warm-up | Info | Denial of Service |

### AURORA

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-AURORA-001` | Amazon Aurora Cluster without Encryption | High | Information Disclosure |
| `TMAC-AWS-AURORA-002` | Aurora Cluster with Encryption Explicitly Disabled | High | Information Disclosure |
| `TMAC-AWS-AURORA-003` | Aurora Cluster with Master Password in Cleartext | Critical | Information Disclosure |
| `TMAC-AWS-AURORA-004` | Aurora Cluster publicly accessible via instances | High | Information Disclosure |
| `TMAC-AWS-AURORA-005` | Aurora Cluster without sufficient backup retention | Medium | Denial of Service |
| `TMAC-AWS-AURORA-006` | Aurora Cluster without log export | Low | Repudiation |
| `TMAC-AWS-AURORA-007` | Aurora Cluster without Deletion Protection | Medium | Denial of Service |
| `TMAC-AWS-AURORA-008` | Aurora Cluster with final snapshot skipped | Low | Denial of Service |
| `TMAC-AWS-AURORA-009` | Aurora Cluster without IAM authentication | Low | Spoofing |

### BCH

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-BCH-001` | AWS Batch Compute with Public IP Assignment | Medium | Information Disclosure |

### BKP

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-BKP-001` | AWS Backup Vault without Encryption (KMS) | Medium | Information Disclosure |

### CB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CB-001` | CodeBuild in Privileged Mode | Medium | Elevation of Privilege |
| `TMAC-AWS-CB-002` | CodeBuild without artifact encryption | High | Information Disclosure |
| `TMAC-AWS-CB-003` | CodeBuild with sensitive variables in cleartext | Medium | Information Disclosure |
| `TMAC-AWS-CB-004` | CodeBuild without KMS artifact encryption | Low | Information Disclosure |
| `TMAC-AWS-CB-005` | CodeBuild with logging disabled | Low | Repudiation |
| `TMAC-AWS-CB-006` | CodeBuild with source lacking credential verification | Info | Spoofing |
| `TMAC-AWS-CB-007` | CodeBuild without VPC (access to private resources) | Info | Information Disclosure |
| `TMAC-AWS-CB-008` | CodeBuild without tags | Info | Repudiation |

### CC

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CC-001` | CodeCommit without a declared KMS key | Low | Information Disclosure |
| `TMAC-AWS-CC-002` | CodeCommit without description | Info | Repudiation |
| `TMAC-AWS-CC-003` | CodeCommit without tags | Info | Repudiation |
| `TMAC-AWS-CC-004` | CodeCommit with generic name | Info | Repudiation |
| `TMAC-AWS-CC-005` | CodeCommit without project tag | Info | Repudiation |
| `TMAC-AWS-CC-006` | CodeCommit without environment tag | Info | Repudiation |
| `TMAC-AWS-CC-007` | CodeCommit without data classification | Info | Information Disclosure |
| `TMAC-AWS-CC-008` | CodeCommit without a declared owner | Info | Repudiation |

### CDA

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CDA-001` | CodeDeploy App without a declared platform | Info | Tampering |
| `TMAC-AWS-CDA-002` | CodeDeploy App without tags | Info | Repudiation |
| `TMAC-AWS-CDA-003` | CodeDeploy App with generic name | Info | Repudiation |
| `TMAC-AWS-CDA-004` | CodeDeploy App without project tag | Info | Repudiation |
| `TMAC-AWS-CDA-005` | CodeDeploy App without environment tag | Info | Repudiation |
| `TMAC-AWS-CDA-006` | CodeDeploy App without owner | Info | Repudiation |
| `TMAC-AWS-CDA-007` | CodeDeploy App on Server platform (EC2) without control | Info | Tampering |
| `TMAC-AWS-CDA-008` | CodeDeploy App without data classification | Info | Information Disclosure |

### CDG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CDG-001` | Deployment Group without automatic rollback | Medium | Denial of Service |
| `TMAC-AWS-CDG-002` | Deployment Group without alarms | Low | Repudiation |
| `TMAC-AWS-CDG-003` | Deployment Group without a service role | Medium | Elevation of Privilege |
| `TMAC-AWS-CDG-004` | Deployment Group without a blue/green strategy | Low | Denial of Service |
| `TMAC-AWS-CDG-005` | Deployment Group with all-at-once deployment | Medium | Denial of Service |
| `TMAC-AWS-CDG-006` | Deployment Group without a notification trigger | Info | Repudiation |
| `TMAC-AWS-CDG-007` | Deployment Group without tags | Info | Repudiation |
| `TMAC-AWS-CDG-008` | Deployment Group without halt on alarm failure | Low | Denial of Service |

### CF

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CF-001` | CloudFront Distribution without Associated WAF | High | Tampering |
| `TMAC-AWS-CF-002` | CloudFront Distribution with Cache Policy Allowing HTTP | High | Information Disclosure |

### CFG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CFG-001` | AWS Config Recorder Disabled | Medium | Repudiation |

### CFGR

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CFGR-001` | Config Recorder without all resources | Medium | Repudiation |
| `TMAC-AWS-CFGR-002` | Config Recorder without global resources | Low | Repudiation |
| `TMAC-AWS-CFGR-003` | Config Recorder without a declared role | Medium | Elevation of Privilege |
| `TMAC-AWS-CFGR-004` | Config Recorder with reduced recording frequency | Low | Repudiation |
| `TMAC-AWS-CFGR-005` | Config Recorder with resource exclusions | Low | Repudiation |
| `TMAC-AWS-CFGR-006` | Config Recorder with generic name | Info | Repudiation |
| `TMAC-AWS-CFGR-007` | Config Recorder without a declared recording strategy | Medium | Repudiation |
| `TMAC-AWS-CFGR-008` | Config Recorder with unaudited override strategy | Info | Repudiation |

### CFN

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CFN-001` | CloudFormation Stack without Termination Protection | Low | Tampering |

### COGCLIENT

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-COGCLIENT-001` | Cognito Client with implicit flow enabled | Medium | Spoofing |
| `TMAC-AWS-COGCLIENT-002` | Cognito Client with no generated secret | Low | Spoofing |
| `TMAC-AWS-COGCLIENT-003` | Cognito Client with non-HTTPS callbacks | Medium | Spoofing |
| `TMAC-AWS-COGCLIENT-004` | Cognito Client with high token validity | Low | Elevation of Privilege |
| `TMAC-AWS-COGCLIENT-005` | Cognito Client with ADMIN_NO_SRP flows | Medium | Spoofing |
| `TMAC-AWS-COGCLIENT-006` | Cognito Client without enumeration prevention | Low | Information Disclosure |
| `TMAC-AWS-COGCLIENT-007` | Cognito Client with broad scopes | Medium | Elevation of Privilege |
| `TMAC-AWS-COGCLIENT-008` | Cognito Client with uncontrolled providers | Info | Spoofing |

### COGDOM

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-COGDOM-001` | Cognito Domain without its own certificate | Info | Spoofing |
| `TMAC-AWS-COGDOM-002` | Cognito Domain with generic prefix | Info | Repudiation |
| `TMAC-AWS-COGDOM-003` | Cognito Domain without user pool association | Medium | Spoofing |
| `TMAC-AWS-COGDOM-004` | Custom Cognito Domain without managed validation | Info | Spoofing |
| `TMAC-AWS-COGDOM-005` | Cognito Domain with name too short | Info | Spoofing |
| `TMAC-AWS-COGDOM-006` | Cognito Domain without organization branding | Info | Repudiation |
| `TMAC-AWS-COGDOM-007` | Managed Cognito Domain in production | Info | Spoofing |
| `TMAC-AWS-COGDOM-008` | Cognito Domain without a TLS version policy | Info | Information Disclosure |

### COGNITO

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-COGNITO-001` | Cognito User Pool without Mandatory MFA | High | Spoofing |
| `TMAC-AWS-COGNITO-002` | Cognito User Pool without a Strong Password Policy | Medium | Spoofing |
| `TMAC-AWS-COGNITO-003` | Cognito User Pool without Risk Event Logging | Medium | Repudiation |
| `TMAC-AWS-COGNITO-004` | Cognito User Pool without MFA | High | Spoofing |
| `TMAC-AWS-COGNITO-005` | Cognito without advanced security protection | Low | Spoofing |
| `TMAC-AWS-COGNITO-006` | Cognito without secure account recovery | Low | Spoofing |
| `TMAC-AWS-COGNITO-007` | Cognito with open self-registration | Medium | Spoofing |
| `TMAC-AWS-COGNITO-008` | Cognito without tags | Info | Repudiation |

### CP

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CP-001` | CodePipeline without CMK artifact encryption | Medium | Information Disclosure |
| `TMAC-AWS-CP-002` | CodePipeline without a declared store | Medium | Tampering |
| `TMAC-AWS-CP-003` | CodePipeline without a declared role | Medium | Elevation of Privilege |
| `TMAC-AWS-CP-004` | CodePipeline without tags | Info | Repudiation |
| `TMAC-AWS-CP-005` | CodePipeline with a non-S3 store type | Info | Tampering |
| `TMAC-AWS-CP-006` | CodePipeline without a manual approval stage | Low | Tampering |
| `TMAC-AWS-CP-007` | CodePipeline without protected variables | Info | Information Disclosure |
| `TMAC-AWS-CP-008` | CodePipeline with pipeline type V1 | Info | Tampering |

### CT

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CT-001` | CloudTrail not multi-region | Medium | Repudiation |
| `TMAC-AWS-CT-002` | CloudTrail without integrity validation | Medium | Tampering |
| `TMAC-AWS-CT-003` | CloudTrail without KMS encryption | Medium | Information Disclosure |
| `TMAC-AWS-CT-004` | CloudTrail without global service events | Low | Repudiation |
| `TMAC-AWS-CT-005` | CloudTrail without CloudWatch Logs integration | Low | Repudiation |
| `TMAC-AWS-CT-006` | CloudTrail without data events | Low | Repudiation |
| `TMAC-AWS-CT-007` | CloudTrail without tags | Info | Repudiation |

### CW

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CW-001` | CloudTrail without Management Event Logging | Medium | Repudiation |

### CWALARM

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CWALARM-001` | Alarm without actions | Low | Repudiation |
| `TMAC-AWS-CWALARM-002` | Alarm without an action on OK state | Info | Repudiation |
| `TMAC-AWS-CWALARM-003` | Alarm without missing-data handling | Info | Repudiation |
| `TMAC-AWS-CWALARM-004` | Alarm without a notification action on insufficient data | Info | Repudiation |
| `TMAC-AWS-CWALARM-005` | Alarm with a long evaluation period | Info | Denial of Service |
| `TMAC-AWS-CWALARM-006` | Alarm without tags | Info | Repudiation |
| `TMAC-AWS-CWALARM-007` | Alarm with a single evaluation period | Info | Denial of Service |
| `TMAC-AWS-CWALARM-008` | Alarm without description | Info | Repudiation |

### CWL

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CWL-001` | CloudWatch Log Group without Encryption | Medium | Information Disclosure |

### CWLG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-CWLG-001` | Log Group without KMS encryption | Medium | Information Disclosure |
| `TMAC-AWS-CWLG-002` | Log Group without retention (infinite) | Low | Information Disclosure |
| `TMAC-AWS-CWLG-003` | Log Group with excessive retention | Info | Information Disclosure |
| `TMAC-AWS-CWLG-004` | Log Group without tags | Info | Repudiation |
| `TMAC-AWS-CWLG-005` | Log Group with generic name | Info | Repudiation |
| `TMAC-AWS-CWLG-006` | Log Group with short retention for auditing | Low | Repudiation |
| `TMAC-AWS-CWLG-007` | Log Group without data classification | Info | Information Disclosure |

### DBPROXY

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-DBPROXY-002` | RDS Proxy without IAM authentication | Medium | Spoofing |
| `TMAC-AWS-DBPROXY-003` | RDS Proxy without security groups | Medium | Information Disclosure |
| `TMAC-AWS-DBPROXY-004` | RDS Proxy with SQL logging disabled | Info | Repudiation |
| `TMAC-AWS-DBPROXY-005` | RDS Proxy with a high idle timeout | Info | Denial of Service |
| `TMAC-AWS-DBPROXY-006` | RDS Proxy without a declared secret | Medium | Information Disclosure |
| `TMAC-AWS-DBPROXY-007` | RDS Proxy without multi-AZ subnets | Low | Denial of Service |
| `TMAC-AWS-DBPROXY-008` | RDS Proxy without tags | Info | Repudiation |

### DBSG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-DBSG-001` | DB Subnet Group without declared subnets | Medium | Denial of Service |
| `TMAC-AWS-DBSG-002` | DB Subnet Group without tags | Info | Repudiation |
| `TMAC-AWS-DBSG-003` | DB Subnet Group without description | Info | Repudiation |
| `TMAC-AWS-DBSG-004` | DB Subnet Group with generic name | Info | Repudiation |
| `TMAC-AWS-DBSG-005` | DB Subnet Group potentially in public subnets | High | Information Disclosure |
| `TMAC-AWS-DBSG-006` | DB Subnet Group without declared AZ redundancy | Low | Denial of Service |
| `TMAC-AWS-DBSG-007` | DB Subnet Group without project convention | Info | Repudiation |
| `TMAC-AWS-DBSG-008` | DB Subnet Group without data classification | Info | Information Disclosure |

### DDB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-DDB-001` | DynamoDB Table without Point-In-Time Recovery (PITR) | High | Tampering |
| `TMAC-AWS-DDB-002` | DynamoDB Table without CMK for Encryption (Server-Side Encryption) | Medium | Information Disclosure |
| `TMAC-AWS-DDB-003` | DynamoDB Table without Deletion Protection | Medium | Tampering |

### DF

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-DF-001` | Device Farm Project outside the Private Environment (VPC) | Low | Information Disclosure |

### DOCDB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-DOCDB-001` | Amazon DocumentDB Cluster without Encryption | High | Information Disclosure |

### DPT

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-DPT-001` | RDS Proxy Target without a declared proxy | Medium | Denial of Service |
| `TMAC-AWS-DPT-002` | RDS Proxy Target without a target group | Low | Denial of Service |
| `TMAC-AWS-DPT-003` | RDS Proxy Target without a destination | Medium | Denial of Service |
| `TMAC-AWS-DPT-004` | RDS Proxy Target pointing to a single instance | Info | Denial of Service |
| `TMAC-AWS-DPT-005` | RDS Proxy Target with a static identifier | Info | Repudiation |
| `TMAC-AWS-DPT-006` | RDS Proxy Target without a default group | Info | Repudiation |
| `TMAC-AWS-DPT-007` | RDS Proxy Target on a cluster without verified encryption | Info | Information Disclosure |
| `TMAC-AWS-DPT-008` | RDS Proxy Target without a declared endpoint | Info | Repudiation |

### DPTG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-DPTG-001` | RDS Proxy Target Group without connection pooling | Low | Denial of Service |
| `TMAC-AWS-DPTG-002` | RDS Proxy Target Group with high maximum connections | Info | Denial of Service |
| `TMAC-AWS-DPTG-003` | RDS Proxy Target Group without a declared proxy | Medium | Denial of Service |
| `TMAC-AWS-DPTG-004` | RDS Proxy Target Group with a high borrow timeout | Info | Denial of Service |
| `TMAC-AWS-DPTG-005` | RDS Proxy Target Group without controlled session pinning | Info | Information Disclosure |
| `TMAC-AWS-DPTG-006` | RDS Proxy Target Group with an unaudited init query | Info | Tampering |
| `TMAC-AWS-DPTG-007` | RDS Proxy Target Group with an undeclared idle timeout | Info | Denial of Service |
| `TMAC-AWS-DPTG-008` | RDS Proxy Target Group without a default group name | Info | Repudiation |

### EB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-EB-001` | Elastic Beanstalk without Managed Updates | Medium | Tampering |
| `TMAC-AWS-EB-002` | Elastic Beanstalk without Log/Streaming Configuration | Low | Repudiation |
| `TMAC-AWS-EB-003` | Beanstalk without a declared VPC | Low | Information Disclosure |
| `TMAC-AWS-EB-004` | Beanstalk without a declared tier | Info | Repudiation |
| `TMAC-AWS-EB-005` | Beanstalk without tags | Info | Repudiation |
| `TMAC-AWS-EB-006` | Beanstalk with a potentially outdated stack solution | Low | Tampering |
| `TMAC-AWS-EB-007` | Beanstalk without a descriptive environment name | Info | Repudiation |
| `TMAC-AWS-EB-008` | Beanstalk without a pinned application version | Info | Tampering |

### EBAPP

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-EBAPP-001` | Beanstalk Application without description | Info | Repudiation |
| `TMAC-AWS-EBAPP-002` | Beanstalk Application without version retention | Low | Denial of Service |
| `TMAC-AWS-EBAPP-003` | Beanstalk Application without a lifecycle role | Info | Elevation of Privilege |
| `TMAC-AWS-EBAPP-004` | Beanstalk Application without tags | Info | Repudiation |
| `TMAC-AWS-EBAPP-005` | Beanstalk Application with generic name | Info | Repudiation |
| `TMAC-AWS-EBAPP-006` | Beanstalk Application without maximum version retention | Info | Denial of Service |
| `TMAC-AWS-EBAPP-007` | Beanstalk Application without project tag | Info | Repudiation |
| `TMAC-AWS-EBAPP-008` | Beanstalk Application without a declared environment | Info | Repudiation |

### EC2

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-EC2-001` | EC2 Instance with IMDSv1 Enabled | Critical | Spoofing |
| `TMAC-AWS-EC2-002` | Unencrypted EBS Volume (EC2) | High | Information Disclosure |
| `TMAC-AWS-EC2-003` | EC2 Instance with Directly Assigned Public IP | High | Tampering |

### ECR

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-ECR-001` | ECR Repository without Automatic Vulnerability Scanning | High | Tampering |
| `TMAC-AWS-ECR-002` | ECR Repository with Mutable Image Tags | Medium | Tampering |
| `TMAC-AWS-ECR-003` | ECR without scan on push | Medium | Tampering |
| `TMAC-AWS-ECR-004` | ECR with mutable tags | Medium | Tampering |
| `TMAC-AWS-ECR-005` | ECR without KMS encryption | Low | Information Disclosure |
| `TMAC-AWS-ECR-006` | ECR without a lifecycle policy | Info | Denial of Service |
| `TMAC-AWS-ECR-007` | ECR without tags | Info | Repudiation |
| `TMAC-AWS-ECR-008` | ECR with force_delete enabled | Low | Denial of Service |

### ECS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-ECS-001` | ECS Cluster without Container Insights | Low | Repudiation |

### EFS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-EFS-001` | Amazon EFS without Encryption at Rest Enabled | High | Information Disclosure |

### EIP

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-EIP-001` | EIP outside the VPC domain | Low | Information Disclosure |
| `TMAC-AWS-EIP-002` | EIP without tags | Info | Repudiation |
| `TMAC-AWS-EIP-003` | EIP without a Name tag | Info | Repudiation |
| `TMAC-AWS-EIP-004` | EIP associated directly with an instance | Low | Information Disclosure |
| `TMAC-AWS-EIP-005` | EIP without environment tag | Info | Repudiation |
| `TMAC-AWS-EIP-006` | EIP without project tag | Info | Repudiation |
| `TMAC-AWS-EIP-007` | EIP with a custom border group | Info | Information Disclosure |
| `TMAC-AWS-EIP-008` | EIP without an owner tag | Info | Repudiation |

### EKS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-EKS-001` | EKS Cluster with Endpoint Open to the Public | Critical | Spoofing |
| `TMAC-AWS-EKS-002` | EKS Cluster without Secrets Encryption (KMS) | High | Information Disclosure |
| `TMAC-AWS-EKS-003` | EKS Cluster without Component Logging (Control Plane) | Medium | Repudiation |

### ELASTI

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-ELASTI-001` | ElastiCache (Redis) without Encryption at Rest and in Transit | Medium | Information Disclosure |

### FARGATE

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-FARGATE-001` | Fargate Task Definition without Logging Configured | Medium | Repudiation |
| `TMAC-AWS-FARGATE-002` | Fargate Task Definition with a Privileged Container | Critical | Elevation of Privilege |
| `TMAC-AWS-FARGATE-003` | Fargate Task Definition without Read-Only Root Filesystem | Medium | Tampering |

### FIREHOSE

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-FIREHOSE-002` | Kinesis Firehose with Unencrypted Buffer to S3 | Low | Information Disclosure |

### FL

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-FL-001` | Flow Log that does not capture all traffic | Low | Repudiation |
| `TMAC-AWS-FL-002` | Flow Log without a destination | Medium | Repudiation |
| `TMAC-AWS-FL-003` | Flow Log without an IAM role | Low | Repudiation |
| `TMAC-AWS-FL-004` | Flow Log with a long aggregation interval | Info | Repudiation |
| `TMAC-AWS-FL-005` | Flow Log without a custom format | Info | Repudiation |
| `TMAC-AWS-FL-006` | Flow Log to S3 without declared encryption | Info | Information Disclosure |
| `TMAC-AWS-FL-007` | Flow Log without tags | Info | Repudiation |
| `TMAC-AWS-FL-008` | Flow Log for an ENI/subnet instead of the full VPC | Info | Repudiation |

### FSX

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-FSX-001` | Amazon FSx (Windows) without Managed Encryption | Medium | Information Disclosure |
| `TMAC-AWS-FSX-002` | Amazon FSx (Lustre) without Managed Encryption | Medium | Information Disclosure |

### IAM

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-IAM-001` | Use of Wildcards (*) in IAM Policies | High | Elevation of Privilege |
| `TMAC-AWS-IAM-002` | IAM User with an Inline Policy | Medium | Spoofing |
| `TMAC-AWS-IAM-003` | Full Administrative Permissions (Action: *) | Critical | Elevation of Privilege |
| `TMAC-AWS-IAM-004` | IAM Role assumable by any entity (AssumeRole * | Critical | Spoofing |
| `TMAC-AWS-IAM-005` | Permanent User Access Keys | High | Information Disclosure |
| `TMAC-AWS-IAM-006` | IAM Role vulnerable to Confused Deputy (No ExternalId) | High | Spoofing |
| `TMAC-AWS-IAM-007` | Unrestricted iam:PassRole Permissions | Critical | Elevation of Privilege |
| `TMAC-AWS-IAM-008` | Creation of Direct IAM Users (Identity Anti-Pattern) | Medium | Spoofing |
| `TMAC-AWS-IAM-009` | IAM User Login Profile without Password Reset | High | Spoofing |

### IAMROLE

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-IAMROLE-001` | IAM Role trusting a wildcard Principal | Critical | Elevation of Privilege |
| `TMAC-AWS-IAMROLE-002` | IAM Role with cross-account trust without ExternalId | High | Elevation of Privilege |
| `TMAC-AWS-IAMROLE-003` | IAM Role without a permissions boundary | Low | Elevation of Privilege |
| `TMAC-AWS-IAMROLE-004` | IAM Role with an extended maximum session | Info | Elevation of Privilege |
| `TMAC-AWS-IAMROLE-005` | IAM Role with broad AWS managed policies | Critical | Elevation of Privilege |
| `TMAC-AWS-IAMROLE-006` | IAM Role without tags | Info | Repudiation |

### IAMRP

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-IAMRP-001` | Inline policy with wildcard Action and Resource | Critical | Elevation of Privilege |
| `TMAC-AWS-IAMRP-002` | Inline policy with wildcard Resource | High | Elevation of Privilege |
| `TMAC-AWS-IAMRP-003` | Inline policy with IAM privileges | High | Elevation of Privilege |
| `TMAC-AWS-IAMRP-004` | Inline policy with full data access | High | Information Disclosure |
| `TMAC-AWS-IAMRP-005` | Inline policy without conditions | Low | Elevation of Privilege |
| `TMAC-AWS-IAMRP-006` | Inline policy with NotAction | Medium | Elevation of Privilege |
| `TMAC-AWS-IAMRP-007` | Inline policy with partial wildcard in actions | Medium | Elevation of Privilege |
| `TMAC-AWS-IAMRP-008` | Inline policy allowing broad sts:AssumeRole | Medium | Elevation of Privilege |

### IB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-IB-001` | EC2 Image Builder without an AMI Encryption Key | Medium | Information Disclosure |

### IGW

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-IGW-001` | Internet Gateway without a declared VPC | Low | Denial of Service |
| `TMAC-AWS-IGW-002` | Internet Gateway without tags | Info | Repudiation |
| `TMAC-AWS-IGW-003` | Internet Gateway without a Name tag | Info | Repudiation |
| `TMAC-AWS-IGW-004` | Internet Gateway without environment tag | Info | Repudiation |
| `TMAC-AWS-IGW-005` | Internet Gateway without project tag | Info | Repudiation |
| `TMAC-AWS-IGW-006` | Internet Gateway without an owner tag | Info | Repudiation |
| `TMAC-AWS-IGW-007` | Internet Gateway in a VPC marked as private | Medium | Information Disclosure |
| `TMAC-AWS-IGW-008` | Internet Gateway without exposure classification | Info | Information Disclosure |

### IIP

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-IIP-001` | Instance Profile without a role | Medium | Elevation of Privilege |
| `TMAC-AWS-IIP-002` | Instance Profile without tags | Info | Repudiation |
| `TMAC-AWS-IIP-003` | Instance Profile with generic name | Info | Repudiation |
| `TMAC-AWS-IIP-004` | Instance Profile with a non-standard path | Info | Repudiation |
| `TMAC-AWS-IIP-005` | Instance Profile without project tag | Info | Repudiation |
| `TMAC-AWS-IIP-006` | Instance Profile without environment tag | Info | Repudiation |
| `TMAC-AWS-IIP-007` | Instance Profile with dynamic name_prefix | Info | Repudiation |
| `TMAC-AWS-IIP-008` | Instance Profile without an owner tag | Info | Repudiation |

### KDF

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-KDF-001` | Kinesis Data Firehose without Server-Side Encryption | Medium | Information Disclosure |
| `TMAC-AWS-KDF-002` | Firehose without CloudWatch logging | Low | Repudiation |
| `TMAC-AWS-KDF-003` | Firehose without backup of failed records | Info | Denial of Service |
| `TMAC-AWS-KDF-004` | Firehose with a long-duration buffer | Info | Repudiation |
| `TMAC-AWS-KDF-005` | Firehose with an uncontrolled HTTP destination | Medium | Information Disclosure |
| `TMAC-AWS-KDF-006` | Firehose without tags | Info | Repudiation |
| `TMAC-AWS-KDF-007` | Firehose without validated data transformation | Info | Tampering |

### KDS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-KDS-001` | Kinesis Data Streams Stream without Encryption (KMS) | Medium | Information Disclosure |

### KEYS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-KEYS-001` | Amazon Keyspaces (Cassandra) without Encryption | Low | Information Disclosure |

### KMS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-KMS-001` | KMS Key without Automatic Rotation Enabled | Medium | Information Disclosure |
| `TMAC-AWS-KMS-002` | KMS Key in Pending Deletion State (Deletion) | Medium | Denial of Service |
| `TMAC-AWS-KMS-003` | KMS Policy Open to the Public | Critical | Information Disclosure |

### KMSAL

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-KMSAL-001` | KMS Alias without a target key | Medium | Denial of Service |
| `TMAC-AWS-KMSAL-002` | KMS Alias with a reserved AWS prefix | Low | Tampering |
| `TMAC-AWS-KMSAL-003` | KMS Alias with generic name | Info | Repudiation |
| `TMAC-AWS-KMSAL-004` | KMS Alias without a project namespace | Info | Repudiation |
| `TMAC-AWS-KMSAL-005` | KMS Alias potentially shared across environments | Info | Information Disclosure |
| `TMAC-AWS-KMSAL-006` | KMS Alias without the alias/ prefix | Low | Tampering |
| `TMAC-AWS-KMSAL-007` | KMS Alias with unaudited dynamic name_prefix | Info | Repudiation |
| `TMAC-AWS-KMSAL-008` | KMS Alias without a declared use | Info | Repudiation |

### KMSKEY

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-KMSKEY-001` | KMS Key without a declared policy | Medium | Elevation of Privilege |
| `TMAC-AWS-KMSKEY-002` | KMS Key with a wildcard policy | High | Elevation of Privilege |
| `TMAC-AWS-KMSKEY-003` | KMS Key with a short deletion window | Low | Denial of Service |
| `TMAC-AWS-KMSKEY-004` | KMS Key multi-region | Info | Information Disclosure |
| `TMAC-AWS-KMSKEY-005` | KMS Key without tags | Info | Repudiation |

### LB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-LB-003` | Load Balancer Exposed to the Internet | Low | Spoofing |
| `TMAC-AWS-LB-004` | Load Balancer without deletion protection | Low | Denial of Service |
| `TMAC-AWS-LB-005` | ALB without dropping invalid headers | Medium | Tampering |
| `TMAC-AWS-LB-006` | ALB without desync mitigation mode | Low | Tampering |
| `TMAC-AWS-LB-007` | Load Balancer without tags | Info | Repudiation |
| `TMAC-AWS-LB-008` | Network Load Balancer without cross-zone balancing | Low | Denial of Service |
| `TMAC-AWS-LB-009` | Load Balancer without an exposure classification tag | Info | Information Disclosure |

### LBL

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-LBL-001` | Listener with an outdated TLS policy | High | Information Disclosure |
| `TMAC-AWS-LBL-002` | HTTP Listener without encryption | Medium | Information Disclosure |
| `TMAC-AWS-LBL-003` | Listener without a declared certificate | High | Spoofing |
| `TMAC-AWS-LBL-004` | Listener on a non-standard port for TLS | Low | Information Disclosure |
| `TMAC-AWS-LBL-005` | Listener with an insecure fixed-response default action | Info | Tampering |
| `TMAC-AWS-LBL-006` | Listener without ALPN for TLS | Info | Information Disclosure |
| `TMAC-AWS-LBL-007` | Listener without a TLS 1.3 policy | Low | Information Disclosure |

### LMD

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-LMD-001` | Public Lambda URL without Authentication | Critical | Spoofing |
| `TMAC-AWS-LMD-002` | Lambda without Tracing Configuration (X-Ray) | Low | Repudiation |
| `TMAC-AWS-LMD-003` | Lambda without a Concurrency Limit (Financial DoS) | Medium | Denial of Service |

### LOC

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-LOC-001` | Amazon Location Tracker without Managed Encryption (KMS) | Medium | Information Disclosure |

### LT

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-LT-001` | Launch Template without mandatory IMDSv2 | High | Elevation of Privilege |
| `TMAC-AWS-LT-002` | Launch Template with an unencrypted EBS volume | High | Information Disclosure |
| `TMAC-AWS-LT-003` | Launch Template with automatic public IP | Medium | Information Disclosure |
| `TMAC-AWS-LT-004` | Launch Template without a limited IMDS endpoint | Low | Elevation of Privilege |
| `TMAC-AWS-LT-005` | Launch Template without detailed monitoring | Info | Repudiation |
| `TMAC-AWS-LT-006` | Launch Template with unencrypted user_data | Low | Information Disclosure |
| `TMAC-AWS-LT-007` | Launch Template without security groups | Medium | Information Disclosure |
| `TMAC-AWS-LT-008` | Launch Template without an instance profile | Info | Elevation of Privilege |

### MEMDB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-MEMDB-001` | Amazon MemoryDB without Encryption | Medium | Information Disclosure |

### MSK

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-MSK-001` | MSK Cluster (Kafka) without Encryption in Transit | High | Information Disclosure |
| `TMAC-AWS-MSK-002` | MSK Cluster without Client Authentication (mTLS/SASL) | High | Spoofing |

### NAT

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-NAT-001` | Public NAT Gateway | Info | Information Disclosure |
| `TMAC-AWS-NAT-002` | NAT Gateway without a declared EIP | Low | Denial of Service |
| `TMAC-AWS-NAT-003` | NAT Gateway without a declared subnet | Medium | Denial of Service |
| `TMAC-AWS-NAT-004` | NAT Gateway without tags | Info | Repudiation |
| `TMAC-AWS-NAT-005` | NAT Gateway without a Name tag | Info | Repudiation |
| `TMAC-AWS-NAT-006` | NAT Gateway without environment tag | Info | Repudiation |
| `TMAC-AWS-NAT-007` | NAT Gateway without a declared private IP | Info | Denial of Service |
| `TMAC-AWS-NAT-008` | NAT Gateway without project tag | Info | Repudiation |

### NEPTUNE

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-NEPTUNE-001` | Amazon Neptune Cluster without Encryption | High | Information Disclosure |

### ORG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-ORG-001` | AWS Organizations without SCPs Enabled | High | Elevation of Privilege |

### OS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-OS-001` | OpenSearch Domain without Encryption at Rest | High | Information Disclosure |
| `TMAC-AWS-OS-002` | OpenSearch Domain with Public Access (No VPC) | Critical | Information Disclosure |
| `TMAC-AWS-OS-003` | OpenSearch Domain without Encryption in Transit (TLS) | High | Information Disclosure |

### PINPOINT

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-PINPOINT-001` | Pinpoint App without sending limits | Low | Denial of Service |
| `TMAC-AWS-PINPOINT-002` | Pinpoint App without tags | Info | Repudiation |
| `TMAC-AWS-PINPOINT-003` | Pinpoint App without a daily limit | Info | Denial of Service |
| `TMAC-AWS-PINPOINT-004` | Pinpoint App without a maximum rate per second | Info | Denial of Service |
| `TMAC-AWS-PINPOINT-005` | Pinpoint App with generic name | Info | Repudiation |
| `TMAC-AWS-PINPOINT-006` | Pinpoint App without project tag | Info | Repudiation |
| `TMAC-AWS-PINPOINT-007` | Pinpoint App without environment tag | Info | Repudiation |
| `TMAC-AWS-PINPOINT-008` | Pinpoint App with an unbounded maximum campaign duration | Info | Denial of Service |

### PINSTREAM

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-PINSTREAM-001` | Pinpoint Event Stream without a declared role | Medium | Elevation of Privilege |
| `TMAC-AWS-PINSTREAM-002` | Pinpoint Event Stream without a destination | Medium | Repudiation |
| `TMAC-AWS-PINSTREAM-003` | Pinpoint Event Stream without an associated app | Low | Repudiation |
| `TMAC-AWS-PINSTREAM-004` | Pinpoint Event Stream to an unencrypted destination | Info | Information Disclosure |
| `TMAC-AWS-PINSTREAM-005` | Pinpoint Event Stream with a cross-account role | Info | Elevation of Privilege |
| `TMAC-AWS-PINSTREAM-006` | Pinpoint Event Stream without a dedicated Kinesis destination | Info | Repudiation |
| `TMAC-AWS-PINSTREAM-007` | Pinpoint Event Stream without event segregation | Info | Information Disclosure |
| `TMAC-AWS-PINSTREAM-008` | Pinpoint Event Stream without retention validation | Info | Repudiation |

### QS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-QS-001` | QuickSight Data Source without declared permissions | Medium | Elevation of Privilege |
| `TMAC-AWS-QS-002` | QuickSight Data Source without SSL properties | Low | Information Disclosure |
| `TMAC-AWS-QS-003` | QuickSight Data Source with SSL disabled | High | Information Disclosure |
| `TMAC-AWS-QS-004` | QuickSight Data Source without a VPC connection | Info | Information Disclosure |
| `TMAC-AWS-QS-005` | QuickSight Data Source without tags | Info | Repudiation |
| `TMAC-AWS-QS-006` | QuickSight Data Source with embedded credentials | Medium | Information Disclosure |
| `TMAC-AWS-QS-007` | QuickSight Data Source over public S3 | Info | Information Disclosure |
| `TMAC-AWS-QS-008` | QuickSight Data Source without secret_arn | Low | Information Disclosure |

### R53R

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-R53R-001` | Route53 Record with a very high TTL | Info | Denial of Service |
| `TMAC-AWS-R53R-002` | Route53 Record without a health check on failover | Medium | Denial of Service |
| `TMAC-AWS-R53R-003` | Route53 Record pointing to a fixed public IP | Info | Spoofing |
| `TMAC-AWS-R53R-004` | Route53 Record without an alias evaluating health | Low | Denial of Service |
| `TMAC-AWS-R53R-005` | Route53 TXT Record with a permissive SPF | Medium | Spoofing |
| `TMAC-AWS-R53R-006` | Route53 Record without a declared routing policy | Info | Denial of Service |
| `TMAC-AWS-R53R-007` | Route53 CNAME Record at the apex | Info | Spoofing |
| `TMAC-AWS-R53R-008` | Route53 Record with an undeclared TTL | Info | Denial of Service |

### R53Z

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-R53Z-001` | Route53 Zone without query logging | Low | Repudiation |
| `TMAC-AWS-R53Z-002` | Private Route53 Zone without a declared VPC | Info | Information Disclosure |
| `TMAC-AWS-R53Z-003` | Route53 Zone without tags | Info | Repudiation |
| `TMAC-AWS-R53Z-004` | Route53 Zone without a descriptive comment | Info | Repudiation |
| `TMAC-AWS-R53Z-005` | Route53 Zone with force_destroy | Low | Denial of Service |
| `TMAC-AWS-R53Z-006` | Route53 Zone without documented DNSSEC | Low | Spoofing |
| `TMAC-AWS-R53Z-007` | Route53 Zone with a non-FQDN name | Info | Spoofing |
| `TMAC-AWS-R53Z-008` | Route53 Zone without an owner | Info | Repudiation |

### RDS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-RDS-001` | RDS Database without Encryption | Medium | Information Disclosure |
| `TMAC-AWS-RDS-002` | RDS Instance with Public Access | High | Information Disclosure |
| `TMAC-AWS-RDS-003` | RDS Database without Multi-AZ Enabled | High | Denial of Service |
| `TMAC-AWS-RDS-004` | RDS Instance without Deletion Protection | Medium | Tampering |
| `TMAC-AWS-RDS-005` | RDS without IAM Authentication Enabled | Medium | Spoofing |

### RDSCI

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-RDSCI-001` | Cluster instance publicly accessible | Critical | Information Disclosure |
| `TMAC-AWS-RDSCI-002` | Cluster instance without Performance Insights | Info | Repudiation |
| `TMAC-AWS-RDSCI-003` | Cluster instance without encrypted Performance Insights | Low | Information Disclosure |
| `TMAC-AWS-RDSCI-004` | Cluster instance without enhanced monitoring | Info | Repudiation |
| `TMAC-AWS-RDSCI-005` | Cluster instance without auto minor upgrade | Low | Tampering |
| `TMAC-AWS-RDSCI-006` | Cluster instance without a maintenance window | Info | Denial of Service |
| `TMAC-AWS-RDSCI-007` | Cluster instance without a declared certificate CA | Info | Spoofing |
| `TMAC-AWS-RDSCI-008` | Cluster instance without tags | Info | Repudiation |

### RDSPROXY

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-RDSPROXY-001` | RDS Proxy without Required TLS | Medium | Information Disclosure |

### RS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-RS-001` | Redshift Cluster without Encryption at Rest | High | Information Disclosure |
| `TMAC-AWS-RS-002` | Redshift Cluster with Public Access | Critical | Information Disclosure |
| `TMAC-AWS-RS-003` | Redshift Cluster without Audit Logging | Medium | Repudiation |

### RT

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-RT-001` | Route Table with a default route to IGW | Info | Information Disclosure |
| `TMAC-AWS-RT-002` | Route Table without a declared VPC | Low | Denial of Service |
| `TMAC-AWS-RT-003` | Route Table with a broad 0.0.0.0/0 route | Info | Information Disclosure |
| `TMAC-AWS-RT-004` | Route Table without tags | Info | Repudiation |
| `TMAC-AWS-RT-005` | Route Table without a Name tag | Info | Repudiation |
| `TMAC-AWS-RT-006` | Route Table with an unaudited peering route | Low | Information Disclosure |
| `TMAC-AWS-RT-007` | Route Table with a route to an instance (NAT instance) | Low | Denial of Service |
| `TMAC-AWS-RT-008` | Route Table without environment tag | Info | Repudiation |

### RTA

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-RTA-001` | Table association without a route table | Medium | Denial of Service |
| `TMAC-AWS-RTA-002` | Association without a subnet or gateway | Medium | Denial of Service |
| `TMAC-AWS-RTA-003` | Gateway association without edge auditing | Info | Information Disclosure |
| `TMAC-AWS-RTA-004` | Subnet association to a public table without control | Info | Information Disclosure |
| `TMAC-AWS-RTA-005` | Association without a naming convention | Info | Repudiation |
| `TMAC-AWS-RTA-006` | Association with a static subnet | Info | Repudiation |
| `TMAC-AWS-RTA-007` | Gateway association with a static ID | Info | Repudiation |
| `TMAC-AWS-RTA-008` | Potentially public association on a data subnet | Low | Information Disclosure |

### S3

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-S3-001` | S3 Bucket with Public Access (ACL) | Critical | Information Disclosure |
| `TMAC-AWS-S3-002` | S3 Bucket without Server-Side Encryption | High | Information Disclosure |
| `TMAC-AWS-S3-003` | S3 Bucket without Access Logging | Medium | Repudiation |
| `TMAC-AWS-S3-004` | S3 Bucket with Force Destroy Enabled | High | Denial of Service |
| `TMAC-AWS-S3-005` | S3 Bucket without Object Lock (Ransomware Protection) | High | Tampering |
| `TMAC-AWS-S3-006` | S3 Bucket Configured as a Static Website | Medium | Information Disclosure |
| `TMAC-AWS-S3-007` | S3 Bucket without controlled force_destroy | Low | Denial of Service |
| `TMAC-AWS-S3-008` | S3 Bucket without tags | Info | Repudiation |

### S3LC

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-S3LC-001` | Lifecycle without expiration of non-current versions | Low | Information Disclosure |
| `TMAC-AWS-S3LC-002` | Lifecycle without cleanup of incomplete multipart uploads | Info | Denial of Service |
| `TMAC-AWS-S3LC-003` | Lifecycle without transition to cold storage | Info | Denial of Service |
| `TMAC-AWS-S3LC-004` | Lifecycle with disabled rules | Low | Information Disclosure |
| `TMAC-AWS-S3LC-005` | Lifecycle without a declared bucket | Medium | Repudiation |
| `TMAC-AWS-S3LC-006` | Lifecycle without object expiration | Info | Information Disclosure |
| `TMAC-AWS-S3LC-007` | Lifecycle without a defined filter | Info | Tampering |
| `TMAC-AWS-S3LC-008` | Lifecycle without transition to Glacier for archiving | Info | Information Disclosure |

### S3SSE

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-S3SSE-001` | SSE with AES256 algorithm instead of KMS | Low | Information Disclosure |
| `TMAC-AWS-S3SSE-002` | SSE without a declared KMS key | Low | Information Disclosure |
| `TMAC-AWS-S3SSE-003` | SSE without a bucket key (KMS cost/exposure) | Info | Information Disclosure |
| `TMAC-AWS-S3SSE-004` | SSE without a declared bucket | Medium | Repudiation |
| `TMAC-AWS-S3SSE-005` | SSE without a declared rule | Medium | Information Disclosure |
| `TMAC-AWS-S3SSE-006` | SSE with an undeclared algorithm | Medium | Information Disclosure |
| `TMAC-AWS-S3SSE-007` | SSE with DSSE not considered for critical data | Info | Information Disclosure |
| `TMAC-AWS-S3SSE-008` | SSE with a key under the aws/s3 alias | Low | Information Disclosure |

### S3WEB

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-S3WEB-001` | S3 Website hosting enabled | Medium | Information Disclosure |
| `TMAC-AWS-S3WEB-002` | S3 Website with an error document that leaks info | Info | Information Disclosure |
| `TMAC-AWS-S3WEB-003` | S3 Website with redirection to a non-HTTPS host | Medium | Information Disclosure |
| `TMAC-AWS-S3WEB-004` | S3 Website with unaudited routing rules | Info | Tampering |
| `TMAC-AWS-S3WEB-005` | S3 Website without a declared bucket | Medium | Repudiation |
| `TMAC-AWS-S3WEB-006` | S3 Website with error-document routing to itself | Info | Information Disclosure |
| `TMAC-AWS-S3WEB-007` | S3 Website exposed without CloudFront | Low | Spoofing |
| `TMAC-AWS-S3WEB-008` | S3 Website with a redirect that preserves an insecure protocol | Low | Information Disclosure |

### SES

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SES-001` | SES Receipt Rule without enforcing TLS (Insecure Transit) | High | Information Disclosure |

### SG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SG-001` | SSH Port (22) Open to the World | High | Tampering |
| `TMAC-AWS-SG-002` | RDP Port (3389) Open to the World | Critical | Tampering |
| `TMAC-AWS-SG-003` | Security Group with Unrestricted Outbound Traffic (Egress) | Medium | Information Disclosure |
| `TMAC-AWS-SG-004` | Security Group with fully open egress | Low | Information Disclosure |
| `TMAC-AWS-SG-005` | Security Group with an exposed database | Critical | Information Disclosure |
| `TMAC-AWS-SG-006` | Security Group with all ports open | Critical | Tampering |
| `TMAC-AWS-SG-007` | Security Group without rule descriptions | Info | Repudiation |
| `TMAC-AWS-SG-008` | Security Group without tags | Info | Repudiation |

### SGW

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SGW-001` | AWS Storage Gateway (SMB Share) without KMSEncrypted | Medium | Information Disclosure |

### SM

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SM-001` | Secrets Manager Secret without Automatic Rotation | High | Information Disclosure |
| `TMAC-AWS-SM-002` | Secrets Manager Secret without a KMS CMK | Medium | Information Disclosure |

### SMSEC

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SMSEC-001` | Secret without automatic rotation | Medium | Information Disclosure |
| `TMAC-AWS-SMSEC-002` | Secret without recovery (recovery window 0) | Low | Denial of Service |
| `TMAC-AWS-SMSEC-003` | Secret with a wildcard resource policy | High | Information Disclosure |
| `TMAC-AWS-SMSEC-004` | Secret without tags | Info | Repudiation |
| `TMAC-AWS-SMSEC-005` | Secret with a name that reveals its content | Low | Information Disclosure |
| `TMAC-AWS-SMSEC-006` | Secret without an adequate rotation frequency | Low | Information Disclosure |

### SMVER

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SMVER-001` | Secret version with a password in cleartext | High | Information Disclosure |
| `TMAC-AWS-SMVER-002` | Secret version with an embedded private key | Critical | Information Disclosure |
| `TMAC-AWS-SMVER-003` | Secret version with an embedded token/API key | High | Information Disclosure |
| `TMAC-AWS-SMVER-004` | Secret version with a binary without structure | Low | Information Disclosure |
| `TMAC-AWS-SMVER-005` | Secret version without a version stage | Info | Repudiation |
| `TMAC-AWS-SMVER-006` | Secret version with a full connection string | High | Information Disclosure |
| `TMAC-AWS-SMVER-007` | Secret version with an embedded AWS access key | Critical | Information Disclosure |
| `TMAC-AWS-SMVER-008` | Secret version without structured JSON | Info | Repudiation |

### SNS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SNS-001` | SNS Topic without Encryption (KMS) | Medium | Information Disclosure |
| `TMAC-AWS-SNS-002` | SNS Policy Open to the Public | Critical | Elevation of Privilege |

### SQS

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SQS-001` | SQS Queue without Encryption (Server-Side Encryption KMS) | Medium | Information Disclosure |
| `TMAC-AWS-SQS-002` | SQS Policy Open to the Public | Critical | Spoofing |

### SSM

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SSM-001` | SSM Parameter without Encryption (Not a SecureString) | High | Information Disclosure |

### SUBNET

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-SUBNET-001` | Subnet with automatic public IP | Medium | Information Disclosure |
| `TMAC-AWS-SUBNET-002` | Subnet with automatic public IPv6 | Medium | Information Disclosure |
| `TMAC-AWS-SUBNET-003` | Subnet without a Name tag | Info | Repudiation |
| `TMAC-AWS-SUBNET-004` | Subnet without tags | Info | Repudiation |
| `TMAC-AWS-SUBNET-005` | Subnet without an explicit AZ | Low | Denial of Service |
| `TMAC-AWS-SUBNET-006` | Subnet with a broad CIDR | Info | Information Disclosure |
| `TMAC-AWS-SUBNET-007` | Subnet without customer-owned balancing | Info | Information Disclosure |
| `TMAC-AWS-SUBNET-008` | Subnet with DNS64 enabled | Info | Information Disclosure |

### TG

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-TG-001` | Target Group without a health check | Medium | Denial of Service |
| `TMAC-AWS-TG-002` | Target Group with an HTTP health check | Low | Information Disclosure |
| `TMAC-AWS-TG-003` | Target Group without TLS protocol | Medium | Information Disclosure |
| `TMAC-AWS-TG-004` | Target Group without controlled stickiness | Info | Information Disclosure |
| `TMAC-AWS-TG-005` | Target Group without deregistration delay | Info | Denial of Service |
| `TMAC-AWS-TG-006` | Target Group with target_type IP without VPC | Info | Information Disclosure |
| `TMAC-AWS-TG-007` | Target Group without tags | Info | Repudiation |
| `TMAC-AWS-TG-008` | Target Group with a lax health threshold | Info | Denial of Service |

### TIME

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-TIME-001` | Amazon Timestream Database without a CMK | Medium | Information Disclosure |

### VPC

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-VPC-001` | Amazon VPC without Flow Logs Enabled | Medium | Repudiation |
| `TMAC-AWS-VPC-002` | Default Security Group without Restrictions | High | Tampering |
| `TMAC-AWS-VPC-003` | VPC without DNS hostnames | Low | Repudiation |
| `TMAC-AWS-VPC-004` | VPC without DNS support | Low | Denial of Service |
| `TMAC-AWS-VPC-005` | VPC with undeclared dedicated tenancy | Info | Information Disclosure |
| `TMAC-AWS-VPC-006` | VPC with a CIDR that is too broad | Low | Information Disclosure |
| `TMAC-AWS-VPC-007` | VPC without governance tags | Info | Repudiation |
| `TMAC-AWS-VPC-008` | VPC without an identifiable name | Info | Repudiation |
| `TMAC-AWS-VPC-009` | VPC with undeclared data classification | Info | Information Disclosure |

### VPCE

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-VPCE-001` | VPC Endpoint without private DNS | Low | Spoofing |
| `TMAC-AWS-VPCE-002` | VPC Endpoint without a restrictive policy | Medium | Elevation of Privilege |
| `TMAC-AWS-VPCE-003` | VPC Endpoint with a wildcard policy | Medium | Elevation of Privilege |
| `TMAC-AWS-VPCE-004` | VPC Endpoint without security groups | Medium | Information Disclosure |
| `TMAC-AWS-VPCE-005` | VPC Gateway Endpoint without route tables | Low | Denial of Service |
| `TMAC-AWS-VPCE-006` | VPC Endpoint without tags | Info | Repudiation |
| `TMAC-AWS-VPCE-007` | VPC Endpoint without declared auto-accept | Info | Tampering |
| `TMAC-AWS-VPCE-008` | VPC Endpoint in a single subnet | Low | Denial of Service |

### WAF

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-WAF-001` | WAFv2 Web ACL without a Rate Limiting Rule | High | Denial of Service |
| `TMAC-AWS-WAF-002` | WAFv2 Web ACL without Logging Enabled | Medium | Repudiation |

### WAFACL

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-WAFACL-001` | WAF with a default allow action | Medium | Tampering |
| `TMAC-AWS-WAFACL-002` | WAF without common managed rules | High | Tampering |
| `TMAC-AWS-WAFACL-003` | WAF without CloudWatch metrics | Low | Repudiation |
| `TMAC-AWS-WAFACL-004` | WAF without request sampling | Low | Repudiation |
| `TMAC-AWS-WAFACL-005` | WAF CLOUDFRONT scope used regionally | Info | Tampering |
| `TMAC-AWS-WAFACL-006` | WAF without tags | Info | Repudiation |
| `TMAC-AWS-WAFACL-007` | WAF without a rate limiting rule | Medium | Denial of Service |

### WAFASSOC

| ID | Name | Severity | STRIDE |
| :--- | :--- | :--- | :--- |
| `TMAC-AWS-WAFASSOC-001` | WAF association without a declared resource | Medium | Tampering |
| `TMAC-AWS-WAFASSOC-002` | WAF association without a Web ACL | Medium | Tampering |
| `TMAC-AWS-WAFASSOC-003` | WAF association with a static ARN | Info | Repudiation |
| `TMAC-AWS-WAFASSOC-004` | WAF association to a resource by static ARN | Info | Repudiation |
| `TMAC-AWS-WAFASSOC-005` | WAF association to an unsupported resource | Low | Tampering |
| `TMAC-AWS-WAFASSOC-006` | WAF association to an internal load balancer | Info | Tampering |
| `TMAC-AWS-WAFASSOC-007` | WAF association to an API Gateway without a stage | Info | Tampering |
| `TMAC-AWS-WAFASSOC-008` | WAF association without coverage verification | Info | Tampering |
