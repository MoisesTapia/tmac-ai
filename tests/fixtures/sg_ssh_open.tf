# Positive fixture: TMAC-AWS-SG-001 — Security group with SSH open to the world
resource "aws_security_group" "ssh_open" {
  name        = "ssh-open-sg"
  description = "Security group with SSH open to the world"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
