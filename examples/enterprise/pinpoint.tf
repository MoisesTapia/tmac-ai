# =====================================================================
# Amazon Pinpoint — push notifications a clientes
# =====================================================================

resource "aws_pinpoint_app" "main" {
  name = "${var.project}-pinpoint"

  limits {
    daily               = 100000
    maximum_duration    = 600
    messages_per_second = 50
    total               = 100000
  }
}

# Stream de eventos de Pinpoint hacia Kinesis Firehose
resource "aws_pinpoint_event_stream" "main" {
  application_id         = aws_pinpoint_app.main.application_id
  destination_stream_arn = aws_kinesis_firehose_delivery_stream.usage.arn
  role_arn               = aws_iam_role.firehose.arn
}
