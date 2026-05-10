output "tfstate_bucket" {
  description = "Bucket S3 del estado remoto de Terraform"
  value       = aws_s3_bucket.tfstate.bucket
}

output "frontend_bucket" {
  description = "Bucket S3 del frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_website_url" {
  description = "URL pública del frontend (S3 static website, origin de CloudFront)"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "frontend_cloudfront_url" {
  description = "URL HTTPS del frontend servida por CloudFront"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_cloudfront_distribution_id" {
  description = "ID de la distribución CloudFront (para invalidaciones manuales)"
  value       = aws_cloudfront_distribution.frontend.id
}

output "iam_user_arn" {
  description = "ARN del usuario IAM que asume el role"
  value       = data.aws_iam_user.maia_user.arn
}

output "iam_role_arn" {
  description = "ARN del role con permisos del proyecto"
  value       = data.aws_iam_role.maia_role.arn
}

# ── Servicio EC2 Spot ────────────────────────────────────────────────────────

output "ecr_repository_url" {
  description = "URL del repositorio ECR donde publicar la imagen del servicio"
  value       = aws_ecr_repository.svc.repository_url
}

output "ecr_registry" {
  description = "Registry ECR (para `docker login`)"
  value       = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}

output "service_instance_id" {
  description = "ID de la instancia Spot que corre el servicio"
  value       = aws_instance.svc.id
}

output "service_public_ip" {
  description = "IP pública de la instancia Spot. Cambia si el spot se reclama."
  value       = aws_instance.svc.public_ip
}

output "backend_url_direct" {
  description = "URL HTTP directa al backend (sin CloudFront). Útil para debug/curl."
  value       = "http://${aws_instance.svc.public_ip}${var.host_port == 80 ? "" : ":${var.host_port}"}"
}

output "backend_url_cloudfront" {
  description = "URL HTTPS del backend servida por CloudFront (la que usa el frontend)"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}/api"
}

output "service_health_check" {
  description = "Curl para verificar que el servicio está arriba (vía CloudFront)"
  value       = "curl https://${aws_cloudfront_distribution.frontend.domain_name}/api/vertebraai/health"
}
