# tmac:ignore
resource "aws_s3_bucket" "global_ignored" {
  bucket = "global-ignored-bucket"
  acl    = "public-read"
}

# tmac:ignore[TMAC-AWS-S3-001]
resource "aws_s3_bucket" "rule_ignored" {
  bucket = "rule-ignored-bucket"
  acl    = "public-read"
}

resource "aws_s3_bucket" "inline_ignored" { # tmac:ignore
  bucket = "inline-ignored-bucket"
  acl    = "public-read"
}

resource "aws_s3_bucket" "not_ignored" {
  bucket = "not-ignored-bucket"
  acl    = "public-read"
}

# tmac:ignore[TMAC-AWS-SG-001]
# tmac:ignore[TMAC-AWS-SG-002]
resource "aws_security_group" "multi_rule_ignored" {
  name = "multi-rule-ignored-sg"
}
