variable "aws_region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
  default     = "673857242697"
}

variable "state_bucket_name" {
  description = "Bucket S3 para el estado remoto de Terraform"
  type        = string
  default     = "anferiro-maia-proyecto-final-state"
}

variable "frontend_bucket_name" {
  description = "Bucket S3 para el hosting estático del frontend"
  type        = string
  default     = "anferiro-maia-proyecto-final-frontend"
}

variable "iam_user_name" {
  description = "Usuario IAM existente que asume el role del proyecto"
  type        = string
  default     = "maia-proyecto-user"
}

variable "iam_role_name" {
  description = "Role IAM existente con permisos del proyecto"
  type        = string
  default     = "maia-proyecto-grado"
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "maia-proyecto-final"
}

# ── Servicio EC2 Spot ────────────────────────────────────────────────────────

variable "instance_type" {
  description = "Tipo de EC2 para el servicio. t3.medium = 4GB / 2vCPU (mínimo viable para SAM ViT-B en CPU). t3.large si el primer arranque OOM."
  type        = string
  default     = "t3.medium"
}

variable "host_port" {
  description = "Puerto público en la instancia (mapeado al 8000 del contenedor)"
  type        = number
  default     = 80
}

variable "cors_origins" {
  description = "Orígenes permitidos por CORS en el backend. Incluye S3 website y localhost."
  type        = list(string)
  default     = ["*"]
}
