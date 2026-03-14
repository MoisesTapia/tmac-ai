# Positive fixture: TMAC-AWS-RDS-001 — RDS instance without storage encryption
resource "aws_db_instance" "unencrypted_db" {
  identifier        = "unencrypted-db"
  engine            = "mysql"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  username          = "admin"
  password          = "password123"
  storage_encrypted = false
}
