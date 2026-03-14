# Positive fixture: TMAC-AWS-IAM-002 — IAM user with inline policy
resource "aws_iam_user_policy" "inline_policy" {
  name = "inline-policy"
  user = "my-user"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "arn:aws:s3:::my-bucket/*"
      }
    ]
  })
}
