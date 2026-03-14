# Positive fixture: TMAC-AWS-S3-003 — S3 bucket without access logging
resource "aws_s3_bucket" "no_logging_bucket" {
  bucket = "my-no-logging-bucket"
}
