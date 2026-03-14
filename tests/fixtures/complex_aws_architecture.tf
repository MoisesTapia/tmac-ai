# AWS API Gateway
resource "aws_api_gateway_rest_api" "main_api" {
  name        = "main-crud-api"
  description = "Main API Gateway for CRUD operations"
}

resource "aws_api_gateway_resource" "items" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_rest_api.main_api.root_resource_id
  path_part   = "items"
}

resource "aws_api_gateway_method" "get_items" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.items.id
  http_method   = "GET"
  # Vulnerability: Spoofing (No authorization)
  authorization = "NONE"
}

resource "aws_api_gateway_deployment" "main_api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  depends_on  = [aws_api_gateway_method.get_items]
}

resource "aws_api_gateway_stage" "prod_stage" {
  deployment_id = aws_api_gateway_deployment.main_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  stage_name    = "prod"
  # Vulnerability: Repudiation (No access_log_settings, xray_tracing_enabled = false is implicit or missing)
}

# Networking (VPC & SG)
resource "aws_vpc" "main_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  # Vulnerability: Repudiation (No Flow Logs set/tagged)
}

resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main_vpc.id

  # Vulnerability: Tampering (Leaving default SG with an ingress rule rather than completely cleared)
  ingress {
    protocol  = -1
    self      = true
    from_port = 0
    to_port   = 0
  }
}

resource "aws_security_group" "app_sg" {
  name        = "app_security_group"
  description = "Application SG"
  vpc_id      = aws_vpc.main_vpc.id

  # Existing checks for SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Vulnerability: Egress to 0.0.0.0/0 (Info Disclosure/Exfiltration)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Lambdas (CRUD)
resource "aws_lambda_function" "create_lambda" {
  function_name = "create_item"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  # Vulnerability: Environment variables might contain plain text secrets
  environment {
    variables = {
      DB_PASSWORD = "supersecretpassword123" 
    }
  }
}

resource "aws_lambda_function" "read_lambda" {
  function_name = "read_item"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "nodejs18.x"
}

resource "aws_lambda_function" "update_lambda" {
  function_name = "update_item"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "nodejs18.x"
}

resource "aws_lambda_function" "delete_lambda" {
  function_name = "delete_item"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "nodejs18.x"
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  
  origin {
    domain_name = aws_s3_bucket.frontend_bucket.bucket_regional_domain_name
    origin_id   = "myS3Origin"
  }
  
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "myS3Origin"
    
    # Vulnerability: Allowing HTTP traffic instead of strictly HTTPS
    viewer_protocol_policy = "allow-all" 
  }
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

# AWS WAF
resource "aws_wafv2_web_acl" "example" {
  name        = "example-waf"
  description = "Example WAF"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  visibility_config {
    # Vulnerability: Not enabling CloudWatch metrics reduces visibility into attacks
    cloudwatch_metrics_enabled = false 
    metric_name                = "friendly-rule-metric-name"
    sampled_requests_enabled   = false 
  }
}

# RDS Instance
resource "aws_db_instance" "default" {
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "14.7"
  instance_class       = "db.t3.micro"
  username             = "admin"
  password             = "admin123"
  parameter_group_name = "default.postgres14"
  skip_final_snapshot  = true
  
  # Vulnerability: Database is publicly accessible
  publicly_accessible  = true  
  
  # Vulnerability: Storage is not encrypted
  storage_encrypted    = false 
  
  # Implicit Vulnerabilities tested by new RDS rules:
  # - multi_az not set (Denial of Service)
  # - deletion_protection not set (Tampering)
  # - iam_database_authentication_enabled not set (Spoofing)
}

# DynamoDB Table
resource "aws_dynamodb_table" "basic_dynamodb_table" {
  name           = "GameScores"
  billing_mode   = "PROVISIONED"
  read_capacity  = 20
  write_capacity = 20
  hash_key       = "UserId"
  range_key      = "GameTitle"

  attribute {
    name = "UserId"
    type = "S"
  }

  attribute {
    name = "GameTitle"
    type = "S"
  }

  # Vulnerability: Tampering (No point_in_time_recovery block)
  # Vulnerability: Information Disclosure (No server_side_encryption block)
  # Vulnerability: Tampering / DoS (No deletion_protection_enabled attribute)
}

# 3 S3 Buckets
resource "aws_s3_bucket" "frontend_bucket" {
  bucket = "my-frontend-app-bucket"
  
  # Vulnerability: ACL allows public read access
  acl    = "public-read" 
}

resource "aws_s3_bucket" "data_bucket" {
  bucket = "my-data-processing-bucket"
  # Implicit Vulnerability: Missing server-side encryption and public access block
}

resource "aws_s3_bucket" "logs_bucket" {
  bucket = "my-application-logs-bucket"
  acl    = "log-delivery-write"
}

# KMS Key
resource "aws_kms_key" "mykey" {
  description             = "Esta llave KMS es compartida"
  # Vulnerability: Info Disclosure (No tiene enable_key_rotation)
  # Vulnerability: DoS (La llave está apagada/is_enabled=false causando fallas)
  is_enabled              = false

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "kms:*",
      "Resource": "*"
    }
  ]
}
EOF
}

# Messaging & Email (SQS, SNS, SES)
resource "aws_sqs_queue" "my_queue" {
  name = "app-event-queue"
  # Vulnerability: Info Disclosure (No kms_master_key_id)
}

resource "aws_sqs_queue_policy" "my_queue_policy" {
  queue_url = aws_sqs_queue.my_queue.id
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.my_queue.arn}"
    }
  ]
}
EOF
}

resource "aws_sns_topic" "my_topic" {
  name = "app-alert-topic"
  # Vulnerability: Info Disclosure (No kms_master_key_id)
}

resource "aws_sns_topic_policy" "my_topic_policy" {
  arn = aws_sns_topic.my_topic.arn
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sns:Publish",
      "Resource": "${aws_sns_topic.my_topic.arn}"
    }
  ]
}
EOF
}

resource "aws_ses_receipt_rule_set" "main" {
  rule_set_name = "primary-rules"
}

resource "aws_ses_receipt_rule" "inbound_email" {
  name          = "inbound"
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  recipients    = ["admin@example.com"]
  enabled       = true
  scan_enabled  = true

  # Vulnerability: TLS Transit is merely optional, exposing email bodies (Info Disclosure)
  tls_policy = "Optional"
}

# Storage Auxiliary (EFS, FSx, AWS Backup, Storage Gateway)
resource "aws_efs_file_system" "my_efs" {
  creation_token = "my-efs"
  # Vulnerability: No encrypted = true block (Info Disclosure)
}

resource "aws_backup_vault" "my_vault" {
  name        = "example_backup_vault"
  # Vulnerability: No kms_key_arn block (Info Disclosure)
}

resource "aws_fsx_windows_file_system" "my_fsx" {
  active_directory_id = "d-1234567890"
  storage_capacity    = 300
  subnet_ids          = [aws_subnet.app.id]
  throughput_capacity = 8
  # Vulnerability: No kms_key_id block (Info Disclosure)
}

resource "aws_storagegateway_smb_file_share" "my_share" {
  authentication = "ActiveDirectory"
  gateway_arn    = "arn:aws:storagegateway:us-east-1:111122223333:gateway/sgw-12A3456B"
  location_arn   = aws_s3_bucket.data_bucket.arn
  role_arn       = "arn:aws:iam::111122223333:role/MyRole"
  # Vulnerability: No kms_encrypted block (Info Disclosure)
}

# Management & Governance
resource "aws_autoscaling_group" "my_asg" {
  name                 = "my-asg"
  max_size             = 2
  min_size             = 1
  # Vulnerability: No vpc_zone_identifier (DoS / SPOF)
}

resource "aws_cloudwatch_log_group" "my_log_group" {
  name = "/app/logs"
  # Vulnerability: No kms_key_id (Info Disclosure)
}

resource "aws_config_configuration_recorder" "my_recorder" {
  name     = "example"
  role_arn = "arn:aws:iam::111122223333:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig"
  recording_group {
    # Vulnerability: all_supported is false (Repudiation)
    all_supported = false
  }
}

resource "aws_ssm_parameter" "my_parameter" {
  name  = "/app/secret"
  # Vulnerability: Type is String instead of SecureString (Info Disclosure)
  type  = "String"
  value = "super-secret-token"
}

resource "aws_organizations_organization" "my_org" {
  # Vulnerability: Only CONSOLIDATED_BILLING enabled, no SCPs (Elevation of Privilege)
  feature_set = "CONSOLIDATED_BILLING"
}

# Front-End Web & Mobile
resource "aws_appsync_graphql_api" "my_api" {
  authentication_type = "API_KEY"
  name                = "appsync-api"
  # Vulnerability: No log_config (Repudiation)
}

resource "aws_amplify_app" "my_app" {
  name = "frontend-app"
}

resource "aws_amplify_branch" "staging_branch" {
  app_id      = aws_amplify_app.my_app.id
  branch_name = "staging"
  # Vulnerability: No enable_basic_auth for non-prod (Info Disclosure)
}

resource "aws_location_tracker" "my_tracker" {
  tracker_name = "vehicle-tracker"
  # Vulnerability: No kms_key_id (Information Disclosure)
}

resource "aws_devicefarm_project" "my_df_project" {
  name = "mobile-tests"
  # Vulnerability: No vpc_config (Information Disclosure)
}

# Specialized Databases (Aurora, DocDB, Neptune, ElastiCache, etc.)
resource "aws_rds_cluster" "my_aurora" {
  cluster_identifier      = "aurora-cluster"
  engine                  = "aurora-mysql"
  # Vulnerability: No storage_encrypted (Info Disclosure)
}

resource "aws_docdb_cluster" "my_docdb" {
  cluster_identifier      = "docdb-cluster"
  master_username         = "admin"
  master_password         = "password123"
  # Vulnerability: No storage_encrypted (Info Disclosure)
}

resource "aws_neptune_cluster" "my_neptune" {
  cluster_identifier                  = "neptune-cluster"
  # Vulnerability: No storage_encrypted (Info Disclosure)
}

resource "aws_elasticache_replication_group" "my_redis" {
  replication_group_id = "mem-cluster"
  description          = "Redis cluster"
  # Vulnerability: No at_rest_encryption_enabled (Info Disclosure)
}

resource "aws_memorydb_cluster" "my_memdb" {
  name       = "my-memorydb"
  node_type  = "db.r6g.large"
  # Vulnerability: No tls_enabled (Info Disclosure)
}

resource "aws_timestreamwrite_database" "my_timestream" {
  database_name = "iot_telemetry"
  # Vulnerability: No kms_key_id (Info Disclosure)
}

# Containers & Orchestration (ECR, ECS, EKS)
resource "aws_ecr_repository" "my_repo" {
  name                 = "microservice-repo"
  # Vulnerability: image_tag_mutability = "MUTABLE" by default (Tampering)
  image_tag_mutability = "MUTABLE"
  # Vulnerability: No image_scanning_configuration block (Tampering)
}

data "aws_iam_role" "eks_role" {
  name = "EKSClusterRole"
}

resource "aws_eks_cluster" "my_eks" {
  name     = "production-eks"
  role_arn = data.aws_iam_role.eks_role.arn

  vpc_config {
    subnet_ids = [aws_subnet.app.id]
    # Vulnerability: endpoint_public_access = true (Spoofing / DoS)
    endpoint_public_access = true
  }
  # Vulnerability: No encryption_config for secrets (Info Disclosure)
  # Vulnerability: No enabled_cluster_log_types for audit (Repudiation)
}

resource "aws_ecs_cluster" "my_ecs" {
  name = "backend-ecs-cluster"
  # Vulnerability: No containerInsights setting enabled (Repudiation)
}

# Advanced Compute (App Runner, Batch, Beanstalk, EC2 Image Builder)
resource "aws_apprunner_service" "my_apprunner" {
  service_name = "example-app"
  source_configuration {
    image_repository {
      image_identifier      = "public.ecr.aws/example/app:latest"
      image_repository_type = "ECR_PUBLIC"
    }
  }
  # Vulnerability: No network_configuration/ingress_configuration (Public App)
}

resource "aws_batch_compute_environment" "my_batch" {
  compute_environment_name = "example-env"
  type                     = "MANAGED"
  # Vulnerability: compute_resources/subnets block missing (Info disclosure / insecure network)
}

resource "aws_elastic_beanstalk_environment" "my_eb" {
  name                = "my-eb-env"
  application         = "my-app"
  solution_stack_name = "64bit Amazon Linux 2023 v4.0.0 running Python 3.11"
  # Vulnerability: No ManagedActionsEnabled setting (Tampering / Outdated OS)
}

resource "aws_imagebuilder_distribution_configuration" "my_ib" {
  name = "example-dist"
  distribution {
    region = "us-east-1"
    # Vulnerability: ami_distribution_configuration lacking kms_key_id (Info Disclosure)
  }
}
