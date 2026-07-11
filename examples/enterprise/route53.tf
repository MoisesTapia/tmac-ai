# =====================================================================
# Route53 — DNS, registro principal hacia el ALB y failover a Región B
# =====================================================================

resource "aws_route53_zone" "main" {
  name = var.domain_name
}

# Registro primario — apunta al ALB de la Región A
resource "aws_route53_record" "primary" {
  zone_id        = aws_route53_zone.main.zone_id
  name           = var.domain_name
  type           = "A"
  set_identifier = "primary"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }

  failover_routing_policy {
    type = "PRIMARY"
  }
}

# Registro secundario — failover hacia el sitio estático de la Región B
resource "aws_route53_record" "secondary" {
  zone_id        = aws_route53_zone.main.zone_id
  name           = var.domain_name
  type           = "A"
  set_identifier = "secondary"

  alias {
    name                   = aws_s3_bucket.failover_site.website_endpoint
    zone_id                = "Z2FDTNDATAQYW2"
    evaluate_target_health = false
  }

  failover_routing_policy {
    type = "SECONDARY"
  }
}

# Sitio estático de failover (S3 website)
resource "aws_s3_bucket" "failover_site" {
  bucket = "${var.project}-failover-site"
}

resource "aws_s3_bucket_website_configuration" "failover_site" {
  bucket = aws_s3_bucket.failover_site.id

  index_document {
    suffix = "index.html"
  }
}
