# Negative fixture: TMAC-AWS-SG-002 — Security group with RDP restricted to VPN
resource "aws_security_group" "rdp_restricted" {
  name        = "rdp-restricted-sg"
  description = "Security group with RDP restricted to corporate VPN"

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
}
