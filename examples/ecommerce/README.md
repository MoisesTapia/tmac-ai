# Example: serverless e-commerce architecture

Reproduces the serverless microservices architecture (AWS CDK e-commerce style):

```
User → API Gateway ──┬─ /product → Lambda → DynamoDB (product)
                     ├─ /basket  → Lambda → DynamoDB (basket)  ── Checkout Event ─┐
                     └─ /order   → Lambda → DynamoDB (order)                      │
                                                                                  ▼
                                          SQS (order-queue) ◄── EventBridge Rule ◄── Event Bus
                                              │
                                              └─► Ordering Lambda (event source mapping)
```

## Files

| File | Resources |
| :--- | :--- |
| `apigateway.tf` | HTTP API, stages, integrations, routes, and Lambda permissions |
| `lambda.tf` | 3 Lambda functions + SQS→Ordering event source mapping |
| `dynamodb.tf` | 3 tables (product, basket, order) |
| `iam.tf` | Execution roles and policies per microservice |
| `eventbridge.tf` | Event bus, checkout rule, and target to SQS |
| `sqs.tf` | Ordering queue + DLQ + policy |

## Try the tool

Architecture diagram (Mermaid):
```bash
tmac diagram --dir examples/ecommerce --format mermaid --output arch.mmd
```

Diagram + configuration metadata document:
```bash
tmac diagram --dir examples/ecommerce --format mermaid --metadata
```

PNG image (requires Graphviz):
```bash
tmac diagram --dir examples/ecommerce --format png --output arch.png
```

Threat scan with embedded diagram:
```bash
tmac scan --dir examples/ecommerce --report html --output report.html --diagram
```

## Expected security findings (intentional)

- `aws_dynamodb_table.basket` and `.order`: without SSE encryption.
- `aws_iam_role_policy.basket_lambda`: policy with `Action: dynamodb:*` and `Resource: "*"`.
- `aws_sqs_queue.order_queue`: without SSE encryption (`kms_master_key_id`).
