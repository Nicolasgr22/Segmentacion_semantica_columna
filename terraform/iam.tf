# Referencia al usuario y role existentes creados en Proyecto_maia/terraform

data "aws_iam_user" "maia_user" {
  user_name = var.iam_user_name
}

data "aws_iam_role" "maia_role" {
  name = var.iam_role_name
}

# ── Permisos adicionales sobre el bucket de estado ───────────────────────────

resource "aws_iam_role_policy" "maia_role_tfstate" {
  name = "maia-tfstate-policy"
  role = data.aws_iam_role.maia_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TfstateBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
        ]
        Resource = aws_s3_bucket.tfstate.arn
      },
      {
        Sid    = "TfstateObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = "${aws_s3_bucket.tfstate.arn}/*"
      }
    ]
  })
}

# ── Permisos adicionales sobre el bucket del frontend ───────────────────────

resource "aws_iam_role_policy" "maia_role_frontend" {
  name = "maia-frontend-deploy-policy"
  role = data.aws_iam_role.maia_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "FrontendBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
        ]
        Resource = aws_s3_bucket.frontend.arn
      },
      {
        Sid    = "FrontendObjectDeploy"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:PutObjectAcl",
        ]
        Resource = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}
