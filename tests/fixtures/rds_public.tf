# Positive fixture: TMAC-AWS-RDS-002 — RDS instance publicly accessible
resource "aws_db_instance" "public_db" {
  identifier          = "public-db"
  engine              = "mysql"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  username            = "admin"
  password            = "password123"
  publicly_accessible = true
}
