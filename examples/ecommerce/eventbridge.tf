# =====================================================================
# EventBridge — bus de eventos "checkout" + reglas → SQS del Ordering
# =====================================================================

resource "aws_cloudwatch_event_bus" "checkout" {
  name = "checkout-event-bus"
}

# Regla que captura el Checkout Event y lo enruta a la SQS queue del Ordering
resource "aws_cloudwatch_event_rule" "checkout" {
  name           = "checkout-rule"
  event_bus_name = aws_cloudwatch_event_bus.checkout.name

  event_pattern = jsonencode({
    source      = ["com.ecommerce.basket"]
    detail-type = ["CheckoutBasket"]
  })
}

resource "aws_cloudwatch_event_target" "checkout_to_sqs" {
  rule           = aws_cloudwatch_event_rule.checkout.name
  event_bus_name = aws_cloudwatch_event_bus.checkout.name
  target_id      = "OrderingQueue"
  arn            = aws_sqs_queue.order_queue.arn
}

# Permite que el Basket Lambda publique eventos en el bus
resource "aws_iam_role_policy" "basket_eventbridge" {
  name = "basket-eventbridge-policy"
  role = aws_iam_role.basket_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "events:PutEvents"
      Resource = aws_cloudwatch_event_bus.checkout.arn
    }]
  })
}
