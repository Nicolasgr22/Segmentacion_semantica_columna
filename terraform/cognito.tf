# ── Cognito User Pool ────────────────────────────────────────────────────────

resource "aws_cognito_user_pool" "vertebraai" {
  name = "vertebraai-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_uppercase = true
    require_lowercase = true
    require_numbers   = true
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

resource "aws_cognito_user" "admin" {
  user_pool_id = aws_cognito_user_pool.vertebraai.id
  username     = var.cognito_admin_email

  temporary_password = var.cognito_admin_temp_password

  attributes = {
    email          = var.cognito_admin_email
    email_verified = "true"
  }

  # Suprimir el email de bienvenida: el admin ya conoce sus credenciales
  message_action = "SUPPRESS"
}
