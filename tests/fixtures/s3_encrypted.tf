# Negative fixture: TMAC-AWS-S3-002 — S3 bucket with server-side encryption configured inline
resource "aws_s3_bucket" "encrypted_bucket" {
  bucket = "my-encrypted-bucket"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}
