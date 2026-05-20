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

# ── Cognito Auth ─────────────────────────────────────────────────────────────

variable "cognito_admin_username" {
  description = "Nombre de usuario del administrador inicial en Cognito"
  type        = string
  default     = "maia_grupo5"
}

variable "cognito_admin_email" {
  description = "Email del administrador inicial (para recuperación de contraseña)"
  type        = string
  default     = "anferiro@gmail.com"
}

# ── Servicio EC2 Spot ────────────────────────────────────────────────────────

variable "instance_type" {
  description = "Tipo de EC2 para el servicio. t3.large = 8GB / 2vCPU — necesario al cargar 3 adapters en RAM (medsam + progressive-unet + unet++ efficientnet-b7). t3.medium causaba OOM al inicio."
  type        = string
  default     = "t3.large"
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
