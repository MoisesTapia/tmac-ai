# =====================================================================
# KMS, Secrets Manager, ACM
# =====================================================================

resource "aws_kms_key" "main" {
  description             = "${var.project} CMK para cifrado en reposo"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project}"
  target_key_id = aws_kms_key.main.key_id
}

resource "aws_secretsmanager_secret" "db" {
  name       = "${var.project}/db-credentials"
  kms_key_id = aws_kms_key.main.arn
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = "admin"
    password = "ChangeMe123!"
    host     = aws_rds_cluster.aurora.endpoint
  })
}

resource "aws_acm_certificate" "main" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}
