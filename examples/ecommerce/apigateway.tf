# =====================================================================
# API Gateway — punto de entrada del usuario, rutea a 3 microservicios
# =====================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "ecommerce-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# --- Integración + ruta: Product ---
resource "aws_apigatewayv2_integration" "product" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.product.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "product" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /product"
  target    = "integrations/${aws_apigatewayv2_integration.product.id}"
}

# --- Integración + ruta: Basket ---
resource "aws_apigatewayv2_integration" "basket" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.basket.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "basket" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /basket"
  target    = "integrations/${aws_apigatewayv2_integration.basket.id}"
}

# --- Integración + ruta: Order ---
resource "aws_apigatewayv2_integration" "order" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.order.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "order" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /order"
  target    = "integrations/${aws_apigatewayv2_integration.order.id}"
}

# Permisos para que API Gateway invoque cada Lambda
resource "aws_lambda_permission" "product" {
  statement_id  = "AllowAPIGatewayProduct"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.product.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "basket" {
  statement_id  = "AllowAPIGatewayBasket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.basket.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "order" {
  statement_id  = "AllowAPIGatewayOrder"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
