# ──────────────────────────────────────────────────────────────────────────────
#  EC2 Spot que corre el servicio FastAPI (VertebraPrompt + BoxRefiner + MedSAM).
#
#  Diseño: una sola instancia Spot one-time con IP pública auto-asignada.
#  - Sin EIP (más barato; si AWS reclama el spot, `terraform apply` levanta
#    otra instancia con IP nueva y el frontend se re-sincroniza).
#  - Sin ALB ni NLB (HTTP plano por la IP pública en el puerto var.host_port).
#  - Sin EKS (control plane $73/mes innecesario para un único servicio).
# ──────────────────────────────────────────────────────────────────────────────

# 1. AMI Amazon Linux 2023 más reciente
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 2. VPC + subred default (evita crear networking propio)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# 3. ECR repo para la imagen del servicio
resource "aws_ecr_repository" "svc" {
  name                 = "${var.project_name}-svc"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Project   = var.project_name
    Component = "services"
    ManagedBy = "terraform"
  }
}

# Lifecycle: conservar solo las últimas 3 imágenes para no inflar el costo de
# storage en ECR (~$0.10/GB-mes). Cada imagen pesa ~3 GB con los modelos.
resource "aws_ecr_lifecycle_policy" "svc" {
  repository = aws_ecr_repository.svc.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar solo las últimas 3 imágenes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}

# 4. IAM: instance profile que permite a la EC2 hacer pull desde ECR
resource "aws_iam_role" "svc_instance" {
  name = "${var.project_name}-svc-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# Permisos: solo lo justo para `aws ecr get-login-password` y pull.
resource "aws_iam_role_policy" "svc_ecr_pull" {
  name = "${var.project_name}-svc-ecr-pull"
  role = aws_iam_role.svc_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
        ]
        Resource = aws_ecr_repository.svc.arn
      },
    ]
  })
}

# Permite SSM Session Manager (debug remoto sin abrir SSH público)
resource "aws_iam_role_policy_attachment" "svc_ssm" {
  role       = aws_iam_role.svc_instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "svc" {
  name = "${var.project_name}-svc-instance-profile"
  role = aws_iam_role.svc_instance.name
}

# 5. Security group: solo expone el puerto del servicio al mundo
resource "aws_security_group" "svc" {
  name        = "${var.project_name}-svc-sg"
  description = "VertebraAI service: HTTP en var.host_port"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP del servicio FastAPI"
    from_port   = var.host_port
    to_port     = var.host_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Salida total (pull ECR, dnf update, etc.)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# 6. EC2 Spot one-time
resource "aws_instance" "svc" {
  ami           = data.aws_ami.al2023.id
  instance_type = var.instance_type

  instance_market_options {
    market_type = "spot"
    spot_options {
      spot_instance_type             = "one-time"
      instance_interruption_behavior = "terminate"
    }
  }

  iam_instance_profile        = aws_iam_instance_profile.svc.name
  vpc_security_group_ids      = [aws_security_group.svc.id]
  subnet_id                   = data.aws_subnets.default.ids[0]
  associate_public_ip_address = true

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    ecr_registry      = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
    ecr_image         = aws_ecr_repository.svc.repository_url
    host_port         = var.host_port
    cors_origins_json = jsonencode(var.cors_origins)
  }))

  # Disco: 30 GB es suficiente para imagen ~3GB + capas + logs.
  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 obligatorio
    http_put_response_hop_limit = 2
  }

  tags = {
    Name      = "${var.project_name}-svc-spot"
    Project   = var.project_name
    Component = "services"
    ManagedBy = "terraform"
  }

  # Si cambia la AMI o el user-data, se recrea la instancia (esperado).
  lifecycle {
    create_before_destroy = false
  }
}
