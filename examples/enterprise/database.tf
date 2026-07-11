# =====================================================================
# Aurora MySQL Serverless v2 — Primary + Standby + RDS Proxy
# =====================================================================

resource "aws_db_subnet_group" "aurora" {
  name       = "${var.project}-aurora-subnets"
  subnet_ids = [aws_subnet.private_db_a.id, aws_subnet.private_db_b.id]
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier     = "${var.project}-aurora"
  engine                 = "aurora-mysql"
  engine_mode            = "provisioned"
  engine_version         = "8.0.mysql_aurora.3.04.0"
  database_name          = "appdb"
  master_username        = "admin"
  master_password        = "ChangeMe123!" # (inseguro) debería venir de Secrets Manager
  db_subnet_group_name   = aws_db_subnet_group.aurora.name
  vpc_security_group_ids = [aws_security_group.db.id]
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.main.arn
  skip_final_snapshot    = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 4.0
  }
}

# Instancia primaria (AZ1)
resource "aws_rds_cluster_instance" "primary" {
  identifier         = "${var.project}-aurora-primary"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version
}

# Instancia standby (AZ2)
resource "aws_rds_cluster_instance" "standby" {
  identifier          = "${var.project}-aurora-standby"
  cluster_identifier  = aws_rds_cluster.aurora.id
  instance_class      = "db.serverless"
  engine              = aws_rds_cluster.aurora.engine
  engine_version      = aws_rds_cluster.aurora.engine_version
  publicly_accessible = false
}

# RDS Proxy — pool de conexiones entre la app y Aurora
resource "aws_db_proxy" "main" {
  name                   = "${var.project}-rds-proxy"
  engine_family          = "MYSQL"
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_security_group_ids = [aws_security_group.db.id]
  vpc_subnet_ids         = [aws_subnet.private_db_a.id, aws_subnet.private_db_b.id]

  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "REQUIRED"
    secret_arn  = aws_secretsmanager_secret.db.arn
  }
}

resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name
}

resource "aws_db_proxy_target" "aurora" {
  db_proxy_name         = aws_db_proxy.main.name
  target_group_name     = aws_db_proxy_default_target_group.main.name
  db_cluster_identifier = aws_rds_cluster.aurora.id
}
