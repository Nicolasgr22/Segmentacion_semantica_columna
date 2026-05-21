# ── Bucket S3 para distribución de modelos ML ────────────────────────────────
# Almacena los checkpoints de MedSAM ViT-B y UNet++ EfficientNet-B7 que
# usa el endpoint /xrays. Acceso de solo lectura via IAM user models-reader.
#
# Estructura esperada:
#   models/medsam/   → archivos .pt / .pth de MedSAM
#   models/unetpp/   → checkpoint de UNet++ EfficientNet-B7

resource "aws_s3_bucket" "models" {
  bucket        = "${var.project_name}-models"
  force_destroy = false

  tags = {
    Project = var.project_name
    Purpose = "ml-model-distribution"
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
