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
      },
      # CloudFront sólo soporta Resource="*" en la mayoría de acciones de
      # gestión de distribuciones; las invalidaciones también van al "*".
      {
        Sid    = "CloudFrontFrontendDistribution"
        Effect = "Allow"
        Action = [
          "cloudfront:CreateDistribution",
          "cloudfront:UpdateDistribution",
          "cloudfront:DeleteDistribution",
          "cloudfront:GetDistribution",
          "cloudfront:GetDistributionConfig",
          "cloudfront:ListDistributions",
          "cloudfront:TagResource",
          "cloudfront:UntagResource",
          "cloudfront:ListTagsForResource",
          "cloudfront:CreateInvalidation",
          "cloudfront:GetInvalidation",
          "cloudfront:ListInvalidations",
        ]
        Resource = "*"
      }
    ]
  })
}

# ── Permisos para administrar el stack del servicio (EC2 + ECR + IAM) ───────
# El role del proyecto necesita estos permisos para que `terraform apply`
# pueda crear/actualizar el ECR repo, la EC2 Spot, el security group y el
# instance profile que asume la EC2.

resource "aws_iam_role_policy" "maia_role_services_stack" {
  name = "maia-services-stack-policy"
  role = data.aws_iam_role.maia_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ec2:Describe*, RunInstances, CreateSecurityGroup y la familia spot solo
      # soportan Resource="*" en IAM. Lo scopeamos por condición a la región del
      # proyecto y a tags del proyecto, así si el role se filtra el blast radius
      # queda limitado a recursos taggeados/region propia.
      {
        Sid    = "EC2DescribeReadOnly"
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ec2:GetConsoleOutput",
        ]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:RequestedRegion" = var.aws_region }
        }
      },
      {
        Sid    = "EC2WriteScopedToProject"
        Effect = "Allow"
        Action = [
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:CreateSecurityGroup",
          "ec2:DeleteSecurityGroup",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:AuthorizeSecurityGroupEgress",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupEgress",
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:ModifyInstanceAttribute",
          "ec2:RequestSpotInstances",
          "ec2:CancelSpotInstanceRequests",
        ]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:RequestedRegion" = var.aws_region }
        }
      },
      # ECR sí soporta ARN-level. Limitamos a repos del proyecto.
      {
        Sid      = "ECRGetAuthGlobal"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRManageProjectRepo"
        Effect = "Allow"
        Action = [
          "ecr:CreateRepository",
          "ecr:DeleteRepository",
          "ecr:DescribeRepositories",
          "ecr:ListTagsForResource",
          "ecr:TagResource",
          "ecr:UntagResource",
          "ecr:PutLifecyclePolicy",
          "ecr:GetLifecyclePolicy",
          "ecr:DeleteLifecyclePolicy",
          "ecr:PutImageScanningConfiguration",
          "ecr:PutImageTagMutability",
          "ecr:SetRepositoryPolicy",
          "ecr:GetRepositoryPolicy",
          "ecr:DeleteRepositoryPolicy",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:BatchDeleteImage",
          "ecr:ListImages",
          "ecr:DescribeImages",
        ]
        Resource = "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.project_name}-*"
      },
      {
        Sid    = "IAMServiceRoleManage"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PassRole",
          "iam:PutRolePolicy",
          "iam:GetRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListRolePolicies",
          "iam:CreateInstanceProfile",
          "iam:DeleteInstanceProfile",
          "iam:GetInstanceProfile",
          "iam:AddRoleToInstanceProfile",
          "iam:RemoveRoleFromInstanceProfile",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:ListInstanceProfilesForRole",
        ]
        Resource = [
          "arn:aws:iam::${var.aws_account_id}:role/${var.project_name}-svc-*",
          "arn:aws:iam::${var.aws_account_id}:instance-profile/${var.project_name}-svc-*",
        ]
      },
    ]
  })
}
