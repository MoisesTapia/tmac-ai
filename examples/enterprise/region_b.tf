# =====================================================================
# Región B (Warm Standby) — us-west-2
# VPC mínima + Aurora MySQL + Elastic Beanstalk para failover
# =====================================================================

resource "aws_vpc" "standby" {
  provider             = aws.standby
  cidr_block           = "10.1.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project}-standby-vpc" }
}

resource "aws_subnet" "standby_db_a" {
  provider          = aws.standby
  vpc_id            = aws_vpc.standby.id
  cidr_block        = "10.1.21.0/24"
  availability_zone = "us-west-2a"
}

resource "aws_subnet" "standby_db_b" {
  provider          = aws.standby
  vpc_id            = aws_vpc.standby.id
  cidr_block        = "10.1.22.0/24"
  availability_zone = "us-west-2b"
}

resource "aws_security_group" "standby_db" {
  provider = aws.standby
  name     = "${var.project}-standby-db-sg"
  vpc_id   = aws_vpc.standby.id

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["10.1.0.0/16"]
  }
}

resource "aws_db_subnet_group" "standby" {
  provider   = aws.standby
  name       = "${var.project}-standby-subnets"
  subnet_ids = [aws_subnet.standby_db_a.id, aws_subnet.standby_db_b.id]
}

# (intencional) Aurora standby SIN encriptación en reposo → hallazgo RDS
resource "aws_rds_cluster" "standby" {
  provider               = aws.standby
  cluster_identifier     = "${var.project}-aurora-standby-region"
  engine                 = "aurora-mysql"
  engine_version         = "8.0.mysql_aurora.3.04.0"
  database_name          = "appdb"
  master_username        = "admin"
  master_password        = "ChangeMe123!"
  db_subnet_group_name   = aws_db_subnet_group.standby.name
  vpc_security_group_ids = [aws_security_group.standby_db.id]
  storage_encrypted      = false
  skip_final_snapshot    = true
}

resource "aws_rds_cluster_instance" "standby_region" {
  provider           = aws.standby
  identifier         = "${var.project}-aurora-standby-region-1"
  cluster_identifier = aws_rds_cluster.standby.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.standby.engine
  engine_version     = aws_rds_cluster.standby.engine_version
}

resource "aws_elastic_beanstalk_application" "standby" {
  provider    = aws.standby
  name        = "${var.project}-eb-standby"
  description = "Aplicación de warm standby en la Región B"
}

resource "aws_elastic_beanstalk_environment" "standby" {
  provider            = aws.standby
  name                = "${var.project}-eb-standby-env"
  application         = aws_elastic_beanstalk_application.standby.name
  solution_stack_name = "64bit Amazon Linux 2 v3.7.1 running Docker"

  setting {
    namespace = "aws:ec2:vpc"
    name      = "VPCId"
    value     = aws_vpc.standby.id
  }
}
