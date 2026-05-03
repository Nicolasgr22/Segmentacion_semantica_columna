locals {
  frontend_dir = "${path.module}/../../frontend"
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
  error_document { key    = "index.html" }
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
    sources = sha256(join("", [
      for f in sort(fileset(local.frontend_dir, "**"))
      : filemd5("${local.frontend_dir}/${f}")
    ]))
  }

  provisioner "local-exec" {
    command = "aws s3 sync ${local.frontend_dir}/ s3://${aws_s3_bucket.frontend.bucket} --delete"
  }

  depends_on = [
    aws_s3_bucket.frontend,
    aws_s3_bucket_policy.frontend_public_read,
    aws_s3_bucket_website_configuration.frontend,
  ]
}
