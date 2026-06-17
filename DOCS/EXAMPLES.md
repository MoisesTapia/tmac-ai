# Examples

The `examples/` directory contains ready-to-use Terraform architectures for
trying out TMAC.

| Example | Description |
| :--- | :--- |
| `examples/demo/` | Minimal architecture used to generate the sample reports and diagrams. |
| `examples/ecommerce/` | Serverless microservices: API Gateway → Lambda → DynamoDB, EventBridge, and SQS. |
| `examples/enterprise/` | Multi-AZ and multi-region enterprise architecture: VPC, ALB+WAF, Auto Scaling, Aurora Serverless, RDS Proxy, Cognito, DevOps, VPC endpoints, Kinesis/S3/Glacier, Pinpoint, Route53 failover, CloudTrail, and warm standby. |

## Try it

```bash
# Scan the enterprise example and embed the architecture diagram in the report
tmac scan --dir examples/enterprise --report html --output report.html --diagram

# Generate the clean, grouped architecture diagram as a PNG image
tmac diagram --dir examples/enterprise --simplify --group --format png --output arch.png
```

```bash
# Scan the serverless e-commerce example
tmac scan --dir examples/ecommerce --report md --output report.md
```

See the `README.md` inside each example directory for architecture details.
