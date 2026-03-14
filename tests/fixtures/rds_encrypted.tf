# Negative fixture: TMAC-AWS-RDS-001 — RDS instance with storage encryption enabled
resource "aws_db_instance" "encrypted_db" {
  identifier        = "encrypted-db"
  engine            = "mysql"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  username          = "admin"
  password          = "password123"
  storage_encrypted = true
}
