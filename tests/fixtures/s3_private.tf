# Negative fixture: TMAC-AWS-S3-001 — S3 bucket with private ACL
resource "aws_s3_bucket" "private_bucket" {
  bucket = "my-private-bucket"
  acl    = "private"
}
