# Fixture Terraform file for TMAC integration tests
# This file intentionally contains a minimal S3 bucket resource
# to ensure the workspace is recognized as a Terraform workspace.

resource "aws_s3_bucket" "example" {
  bucket = "my-test-bucket"
  acl    = "public-read"

  tags = {
    Name        = "Test Bucket"
    Environment = "Test"
  }
}
