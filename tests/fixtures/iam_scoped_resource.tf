# Negative fixture: TMAC-AWS-IAM-001 — IAM policy with scoped resource ARN
resource "aws_iam_policy" "scoped_policy" {
  name = "scoped-policy"

  policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "arn:aws:s3:::my-bucket/*"
      }
    ]
  }
}
