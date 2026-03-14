# Negative fixture: TMAC-AWS-S3-003 — S3 bucket with access logging enabled
resource "aws_s3_bucket" "logged_bucket" {
  bucket = "my-logged-bucket"

  logging {
    target_bucket = "my-log-bucket"
    target_prefix = "s3-access-logs/"
  }
}
