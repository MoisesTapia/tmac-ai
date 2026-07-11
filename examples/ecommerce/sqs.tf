# =====================================================================
# SQS — cola que desacopla EventBridge del Ordering Microservice
# =====================================================================

# Cola principal del Ordering — SIN encriptación SSE (hallazgo esperado)
resource "aws_sqs_queue" "order_queue" {
  name                       = "order-queue"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 86400

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.order_dlq.arn
    maxReceiveCount     = 5
  })
}

# Dead-letter queue
resource "aws_sqs_queue" "order_dlq" {
  name = "order-dlq"
}

# Policy que permite a EventBridge enviar mensajes a la cola
resource "aws_sqs_queue_policy" "order_queue" {
  queue_url = aws_sqs_queue.order_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.order_queue.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.checkout.arn }
      }
    }]
  })
}
