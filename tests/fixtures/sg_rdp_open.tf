# Positive fixture: TMAC-AWS-SG-002 — Security group with RDP open to the world
resource "aws_security_group" "rdp_open" {
  name        = "rdp-open-sg"
  description = "Security group with RDP open to the world"

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
