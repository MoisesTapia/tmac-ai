# Negative fixture: TMAC-AWS-IAM-002 — IAM group policy attachment (managed policy)
resource "aws_iam_group_policy_attachment" "managed_policy" {
  group      = "developers"
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
