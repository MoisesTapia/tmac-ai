# =====================================================================
# Observabilidad y gobernanza — CloudTrail, CloudWatch, Config
# =====================================================================

resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/${var.project}/vpc-flow-logs"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.main.arn
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/${var.project}/app"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.main.arn
}

# Bucket de logs de CloudTrail
resource "aws_s3_bucket" "cloudtrail" {
  bucket = "${var.project}-cloudtrail-logs"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
  }
}

# CloudTrail multi-región
resource "aws_cloudtrail" "main" {
  name                          = "${var.project}-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.main.arn
}

# AWS Config — grabador de configuración
resource "aws_config_configuration_recorder" "main" {
  name     = "${var.project}-config"
  role_arn = aws_iam_role.flow_logs.arn

  recording_group {
    all_supported = true
  }
}

# Alarma de CloudWatch sobre la CPU del Auto Scaling Group
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.project}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.app.name
  }
}
