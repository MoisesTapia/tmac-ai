# Positive fixture: TMAC-AWS-IAM-001 — IAM policy with wildcard resource
resource "aws_iam_policy" "wildcard_policy" {
  name = "wildcard-policy"

  policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "*"
      }
    ]
  }
}
