# Negative fixture: TMAC-AWS-RDS-002 — RDS instance not publicly accessible
resource "aws_db_instance" "private_db" {
  identifier          = "private-db"
  engine              = "mysql"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  username            = "admin"
  password            = "password123"
  publicly_accessible = false
}
