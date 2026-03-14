# Positive fixture: TMAC-AWS-CW-001 — CloudTrail with logging disabled
resource "aws_cloudtrail" "disabled_trail" {
  name                          = "disabled-trail"
  s3_bucket_name                = "my-trail-bucket"
  enable_logging                = false
  include_global_service_events = true
  is_multi_region_trail         = true
}
