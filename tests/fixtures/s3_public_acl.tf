# Positive fixture: TMAC-AWS-S3-001 — S3 bucket with public ACL
resource "aws_s3_bucket" "public_bucket" {
  bucket = "my-public-bucket"
  acl    = "public-read"
}
