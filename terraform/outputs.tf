output "tfstate_bucket" {
  description = "Bucket S3 del estado remoto de Terraform"
  value       = aws_s3_bucket.tfstate.bucket
}

output "frontend_bucket" {
  description = "Bucket S3 del frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_website_url" {
  description = "URL pública del frontend (S3 static website)"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "iam_user_arn" {
  description = "ARN del usuario IAM que asume el role"
  value       = data.aws_iam_user.maia_user.arn
}

output "iam_role_arn" {
  description = "ARN del role con permisos del proyecto"
  value       = data.aws_iam_role.maia_role.arn
}
