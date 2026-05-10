# ── CloudFront delante del frontend (S3) y del backend (EC2) ────────────────
# Una sola distribución con dos origins:
#   - S3 website endpoint para los estáticos del frontend (default behavior).
#   - EC2 Spot para `/api/*` (backend FastAPI).
# CloudFront termina TLS al borde y habla HTTP plano a ambos origins. Esto
# resuelve el mixed-content del browser y elimina CORS (todo same-origin).
#
# Cuando el spot rota y la IP cambia, `terraform apply` actualiza el origin
# del backend automáticamente. Caveat: la propagación de un cambio de origin
# en CloudFront tarda ~5 min.

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${var.project_name} frontend + api"
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

  origin {
    # CloudFront rechaza IPs como domain_name; usamos el FQDN público que
    # AWS asigna automáticamente a la EC2 (ec2-X-X-X-X.compute-1.amazonaws.com).
    # Cambia junto con la IP cuando el spot rota → terraform actualiza el origin.
    domain_name = aws_instance.svc.public_dns
    origin_id   = "ec2-backend"

    custom_origin_config {
      http_port                = var.host_port
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 5
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

  # config.js: TTL corto. Útil aunque ahora BACKEND_URL sea relativo, por si
  # se vuelve a inyectar algo dependiente del runtime más adelante.
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

  # /api/* → backend EC2. Usa managed policies en vez del legacy
  # `forwarded_values`, porque éste último NO soporta `headers = ["*"]` (silently
  # no forwardea headers como Content-Type del multipart, rompiendo POST con
  # archivos). Las managed policies de AWS son la forma soportada de "forward
  # todo y no cachear".
  #   - CachingDisabled (4135ea2d-6df8-44a3-9df3-4b5a84be39ad)
  #   - AllViewerExceptHostHeader (b689b0a8-53d0-40ab-baf2-68738e2966ac):
  #     forwardea TODOS los headers/query/cookies del viewer EXCEPTO Host
  #     (Host se rewrite al del origin → FastAPI lo ve como el FQDN EC2).
  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "ec2-backend"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    compress                 = true
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
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
