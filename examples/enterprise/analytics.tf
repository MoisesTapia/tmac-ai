# =====================================================================
# Analítica — Kinesis Firehose → S3 (data lake) → Glacier + QuickSight
# =====================================================================

# Data lake — (intencional) bucket SIN encriptación SSE → hallazgo TMAC-AWS-S3-002
resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project}-data-lake"
}

# (intencional) ACL pública → hallazgo TMAC-AWS-S3-001
resource "aws_s3_bucket" "public_reports" {
  bucket = "${var.project}-public-reports"
  acl    = "public-read"
}

# Ciclo de vida: archivar objetos inactivos a Glacier tras 6 meses
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "archive-to-glacier"
    status = "Enabled"

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }
}

# Kinesis Data Firehose — ingesta de datos de uso hacia el data lake
resource "aws_kinesis_firehose_delivery_stream" "usage" {
  name        = "${var.project}-usage-stream"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose.arn
    bucket_arn = aws_s3_bucket.data_lake.arn

    buffering_size     = 5
    buffering_interval = 300
  }
}

# QuickSight — fuente de datos sobre el data lake
resource "aws_quicksight_data_source" "data_lake" {
  data_source_id = "${var.project}-datalake"
  name           = "${var.project} Data Lake"
  aws_account_id = "123456789012"
  type           = "S3"

  parameters {
    s3 {
      manifest_file_location {
        bucket = aws_s3_bucket.data_lake.bucket
        key    = "manifests/usage.json"
      }
    }
  }
}
