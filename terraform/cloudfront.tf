# ── CloudFront delante del bucket de frontend ───────────────────────────────
# Origin = S3 website endpoint (custom origin HTTP). Mantiene el fallback a
# index.html del website hosting para el routing del SPA.
#
# Mixed content: el frontend se sirve por HTTPS pero el backend EC2 sigue en
# HTTP. Las llamadas del browser al backend romperán hasta que el backend
# tenga TLS (otro CloudFront, ALB+ACM, o dominio + cert).

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${var.project_name} frontend"
  price_class         = "PriceClass_100"

  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend.website_endpoint
    origin_id   = "s3-website-frontend"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "s3-website-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # config.js cambia cuando la IP del spot rota → TTL corto para que la
  # invalidación post-sync se note rápido aunque alguien cachee.
  ordered_cache_behavior {
    path_pattern           = "/config.js"
    target_origin_id       = "s3-website-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 60
    max_ttl     = 300
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Project   = var.project_name
    Component = "frontend"
    ManagedBy = "terraform"
  }
}
