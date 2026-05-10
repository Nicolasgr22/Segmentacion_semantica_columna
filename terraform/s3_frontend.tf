locals {
  frontend_dir = "${path.module}/../frontend"
}

# ── config.js generado por terraform: inyecta BACKEND_URL al frontend ───────
# Como el frontend y el backend se sirven detrás del MISMO CloudFront
# (frontend = default behavior, backend = /api/*), BACKEND_URL queda vacío
# para que `${BACKEND_URL}/api/...` resuelva a una ruta relativa same-origin.
# Esto elimina mixed-content y CORS, y hace que el cambio de IP del spot sea
# transparente para el browser (CloudFront actualiza el origin vía terraform).
resource "local_file" "frontend_config" {
  filename = "${local.frontend_dir}/config.js"
  content  = <<-EOT
    // Auto-generado por terraform. NO editar a mano.
    // Backend se sirve detrás del mismo CloudFront en /api/* → ruta relativa.
    window.BACKEND_URL = "";
  EOT
}

# ── Bucket público para el frontend ─────────────────────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket = var.frontend_bucket_name

  tags = {
    Project   = var.project_name
    Component = "frontend"
    ManagedBy = "terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

resource "aws_s3_bucket_policy" "frontend_public_read" {
  bucket = aws_s3_bucket.frontend.id

  # Depende del bloque de acceso público para evitar error de orden
  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })
}

# ── Sync del contenido de /frontend al bucket ────────────────────────────────

resource "null_resource" "deploy_frontend" {
  triggers = {
    # Hash de los archivos estáticos del frontend, EXCLUYENDO config.js que es
    # generado por terraform durante el apply (incluirlo causa "fileset returned
    # an inconsistent result" porque el archivo no existe en plan time pero sí
    # en apply time).
    sources_static = sha256(join("", [
      for f in sort(fileset(local.frontend_dir, "**"))
      : filemd5("${local.frontend_dir}/${f}")
      if f != "config.js"
    ]))
    # Cambios en config.js (IP del backend, puerto, etc.) se detectan via el
    # md5 que terraform calcula del local_file. Cubre el caso del spot reclamado.
    config_hash     = local_file.frontend_config.content_md5
    distribution_id = aws_cloudfront_distribution.frontend.id
  }

  provisioner "local-exec" {
    command = "aws s3 sync ${local.frontend_dir}/ s3://${aws_s3_bucket.frontend.bucket} --delete && aws cloudfront create-invalidation --distribution-id ${aws_cloudfront_distribution.frontend.id} --paths '/*'"
  }

  depends_on = [
    aws_s3_bucket.frontend,
    aws_s3_bucket_policy.frontend_public_read,
    aws_s3_bucket_website_configuration.frontend,
    local_file.frontend_config,
    aws_cloudfront_distribution.frontend,
  ]
}
