# Negative fixture: TMAC-AWS-CW-001 — CloudTrail with logging enabled
resource "aws_cloudtrail" "enabled_trail" {
  name                          = "enabled-trail"
  s3_bucket_name                = "my-trail-bucket"
  enable_logging                = true
  include_global_service_events = true
  is_multi_region_trail         = true
}
