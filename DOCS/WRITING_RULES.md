# Writing Rules

TMAC rules are declarative YAML documents validated with Pydantic. They live in
`src/tmac/rules/aws/` and are loaded automatically from every `threats*.yaml` file.
You can also supply your own rules at runtime with `--rules-dir ./my-rules`.

## Rule structure (`threats.yaml`)

Rule IDs follow the format `TMAC-{CLOUD}-{SERVICE}-{NNN}`:

```yaml
version: "1.0"
rules:
  - id: TMAC-AWS-S3-001
    name: "S3 Bucket with Public Access (ACL)"
    resource_type: "aws_s3_bucket"
    check:
      attribute: "acl"
      condition: "in"
      values: ["public-read", "public-read-write"]
    severity: "Critical"
    stride: "Information Disclosure"
    description: "Description of the threat."
    mitigation: "Mitigation steps."
    references:
      - "https://docs.aws.amazon.com/..."
    tags: ["s3", "public-access"]
```

| Field | Required | Description |
| :--- | :--- | :--- |
| `id` | Yes | Unique rule identifier (`TMAC-{CLOUD}-{SERVICE}-{NNN}`). |
| `name` | Yes | Short, descriptive title. |
| `resource_type` | Yes | Terraform resource type the rule applies to. |
| `check` | Yes | Condition that triggers the finding (see below). |
| `severity` | Yes | `Critical`, `High`, `Medium`, `Low`, or `Info`. |
| `stride` | Yes | STRIDE category of the threat. |
| `description` | Yes | Explanation of the risk. |
| `mitigation` | Yes | How to remediate the finding. |
| `references` | No | Links to supporting documentation. |
| `tags` | No | Free-form labels for filtering and grouping. |

## Condition operators

| Operator | Description |
| :--- | :--- |
| `equals` | The attribute equals the value. |
| `not_equals` | The attribute does not equal the value. |
| `in` | The attribute is in the list of values. |
| `not_in` | The attribute is not in the list of values. |
| `contains` | The attribute contains the value (string or list). |
| `not_contains` | The attribute does not contain the value. |
| `regex` | The attribute matches the regular expression. |
| `not_regex` | The attribute is present and does not match the regular expression. |
| `exists` | The attribute exists in the resource. |
| `not_exists` | The attribute does not exist in the resource. |

## Rule file organization

Rules are loaded automatically from every `threats*.yaml` file in `src/tmac/rules/aws/`:

| File | Content |
| :--- | :--- |
| `threats.yaml` | Base catalog by service (S3, IAM, SG, RDS, EC2, Lambda, etc.). |
| `threats_extended.yaml` | Extended coverage up to ≥8 rules per resource type. |
| `security_attrs.yaml` | Curated layer of security-relevant attributes per resource (used by `tmac diagram --metadata`). |

To add your own rules without modifying the built-in catalog, point TMAC at an
external directory:

```bash
tmac scan --dir ./infra --rules-dir ./my-rules
```

See the [complete rule catalog](RULES.md) for the full breakdown by service.
