# Positive fixture: TMAC-AWS-S3-002 — S3 bucket without server-side encryption
resource "aws_s3_bucket" "unencrypted_bucket" {
  bucket = "my-unencrypted-bucket"
}
