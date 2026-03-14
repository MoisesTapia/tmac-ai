# Negative fixture: TMAC-AWS-SG-001 — Security group with SSH restricted to corporate IP
resource "aws_security_group" "ssh_restricted" {
  name        = "ssh-restricted-sg"
  description = "Security group with SSH restricted to corporate network"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
}
