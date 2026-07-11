# =====================================================================
# DynamoDB tables — una por microservicio
# =====================================================================

# Product Microservice — tabla segura (encriptada)
resource "aws_dynamodb_table" "product" {
  name         = "product"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

# Basket Microservice — tabla SIN encriptación en reposo (hallazgo esperado)
resource "aws_dynamodb_table" "basket" {
  name         = "basket"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userName"

  attribute {
    name = "userName"
    type = "S"
  }
}

# Ordering Microservice — tabla SIN encriptación ni PITR (hallazgo esperado)
resource "aws_dynamodb_table" "order" {
  name         = "order"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userName"
  range_key    = "orderDate"

  attribute {
    name = "userName"
    type = "S"
  }

  attribute {
    name = "orderDate"
    type = "S"
  }
}
