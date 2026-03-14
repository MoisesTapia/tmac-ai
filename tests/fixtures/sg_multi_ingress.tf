# Fixture: Security group with multiple ingress blocks — tests Evaluator list iteration
# One ingress block is safe (port 443), another triggers TMAC-AWS-SG-001 (SSH open)
resource "aws_security_group" "multi_ingress" {
  name        = "multi-ingress-sg"
  description = "Security group with multiple ingress rules"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
