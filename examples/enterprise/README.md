# Example: multi-AZ and multi-region enterprise architecture

Reproduces a complete enterprise web architecture on AWS, with high
availability (2 AZs), warm standby in a second region, a DevOps pipeline,
data analytics, and security services. It serves to thoroughly test the
dependency graph, filtering, grouping, and threat scanning.

## Components

| File | Layer | Main resources |
| :--- | :--- | :--- |
| `providers.tf` | Base | Providers Region A (us-east-1) and B (us-west-2) |
| `vpc.tf` | Network | VPC, IGW, public/app/db subnets across 2 AZs, NAT, route tables, flow logs |
| `security_groups.tf` | Network | SGs for ALB, app, db, endpoints |
| `alb_waf.tf` | Edge | ALB, target group, HTTPS listener, WAFv2 |
| `compute.tf` | Compute | Launch template, Auto Scaling Group, Elastic Beanstalk |
| `database.tf` | Data | Aurora MySQL Serverless v2 (primary + standby), RDS Proxy |
| `cognito.tf` | Auth | Cognito user pool, client, domain |
| `devops.tf` | CI/CD | CodeCommit, ECR, CodeBuild, CodeDeploy, CodePipeline |
| `vpc_endpoints.tf` | Network | Endpoints for ECR, KMS, Secrets Manager, S3 |
| `analytics.tf` | Data | Kinesis Firehose, S3 data lake, lifecycle to Glacier, QuickSight |
| `pinpoint.tf` | Messaging | Pinpoint app + event stream |
| `security_services.tf` | Security | KMS, Secrets Manager, ACM |
| `route53.tf` | DNS | Zone, primary/secondary records (failover), S3 site |
| `iam.tf` | IAM | Roles for app, DevOps, Firehose, RDS Proxy, flow logs |
| `monitoring.tf` | Observability | CloudTrail, CloudWatch logs/alarms, AWS Config |
| `region_b.tf` | DR | VPC, Aurora, and Beanstalk warm standby in Region B |

## Try the tool

```bash
# Full diagram (all resources)
tmac diagram --dir examples/enterprise --format mermaid --output enterprise.mmd

# Clean diagram, grouped by component, as PNG
tmac diagram --dir examples/enterprise --simplify --group --format png --output enterprise.png

# Diagram + metadata document for threat modeling
tmac diagram --dir examples/enterprise --metadata --metadata-format json

# Threat scan with embedded diagram
tmac scan --dir examples/enterprise --report html --output enterprise-report.html --diagram
```

## Expected security findings (intentional)

- `aws_s3_bucket.public_reports`: ACL `public-read`.
- `aws_s3_bucket.data_lake`: without SSE encryption.
- `aws_security_group.app`: SSH (22) open to `0.0.0.0/0`.
- `aws_iam_role_policy.app` and `.codepipeline`: `Resource: "*"`.
- `aws_rds_cluster.standby` (Region B): `storage_encrypted = false`.
- Cleartext credentials in `aws_rds_cluster` and `aws_secretsmanager_secret_version`.
