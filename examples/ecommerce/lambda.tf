# =====================================================================
# Lambda — una función por microservicio
# =====================================================================

# Product Microservice
resource "aws_lambda_function" "product" {
  function_name = "product-service"
  role          = aws_iam_role.product_lambda.arn
  handler       = "product.handler"
  runtime       = "nodejs18.x"
  filename      = "product.zip"

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.product.name
    }
  }
}

# Basket Microservice — publica un Checkout Event al EventBridge bus
resource "aws_lambda_function" "basket" {
  function_name = "basket-service"
  role          = aws_iam_role.basket_lambda.arn
  handler       = "basket.handler"
  runtime       = "nodejs18.x"
  filename      = "basket.zip"

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.basket.name
      EVENT_BUS_NAME      = aws_cloudwatch_event_bus.checkout.name
    }
  }
}

# Ordering Microservice — consume mensajes desde la SQS queue
resource "aws_lambda_function" "order" {
  function_name = "order-service"
  role          = aws_iam_role.order_lambda.arn
  handler       = "order.handler"
  runtime       = "nodejs18.x"
  filename      = "order.zip"

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.order.name
    }
  }
}

# Mapeo de la SQS queue como fuente de eventos del Ordering Lambda
resource "aws_lambda_event_source_mapping" "order_sqs" {
  event_source_arn = aws_sqs_queue.order_queue.arn
  function_name    = aws_lambda_function.order.arn
  batch_size       = 10
}
