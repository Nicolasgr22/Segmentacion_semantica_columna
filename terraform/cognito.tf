# ── Cognito User Pool ────────────────────────────────────────────────────────
#
# Pool existente: us-east-1_xdT7n8901 (vertebraai-users)
# Creado manualmente via CLI. Para importar al state de Terraform:
#   terraform import aws_cognito_user_pool.vertebraai us-east-1_xdT7n8901
#   terraform import aws_cognito_user_pool_client.vertebraai_web us-east-1_xdT7n8901/33an9jq8fegpjp2v1iafcpc7av

resource "aws_cognito_user_pool" "vertebraai" {
  name = "vertebraai-users"

  # alias_attributes permite login con username (ej: maia_groupo5) O email.
  # Diferente a username_attributes donde el email ES el username.
  alias_attributes         = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_uppercase = true
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  tags = {
    Project   = var.project_name
    Component = "auth"
    ManagedBy = "terraform"
  }
}

# ── Cognito App Client (SPA — sin client secret) ─────────────────────────────

resource "aws_cognito_user_pool_client" "vertebraai_web" {
  name         = "vertebraai-web"
  user_pool_id = aws_cognito_user_pool.vertebraai.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

# ── Usuario administrador inicial ────────────────────────────────────────────
# Usuario creado: maia_groupo5 / anferiro@gmail.com (CONFIRMED, contraseña permanente)
# Para importar: terraform import aws_cognito_user.admin us-east-1_xdT7n8901/maia_groupo5

resource "aws_cognito_user" "admin" {
  user_pool_id = aws_cognito_user_pool.vertebraai.id
  username     = var.cognito_admin_username

  attributes = {
    email          = var.cognito_admin_email
    email_verified = "true"
  }

  message_action = "SUPPRESS"
}
