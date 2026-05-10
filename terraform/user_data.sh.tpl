#!/bin/bash
# Bootstrap del nodo Spot que corre el servicio VertebraAI.
# - Instala Docker
# - Login en ECR + pull de la imagen
# - Corre el contenedor en :80 con restart=always
set -euxo pipefail

LOG=/var/log/vertebra-bootstrap.log
exec > >(tee -a "$LOG") 2>&1

# 1. Paquetes base (Amazon Linux 2023 ya trae aws-cli v2)
dnf update -y
dnf install -y docker
systemctl enable --now docker

# 2. Region desde IMDSv2
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region)

# 3. Login en ECR
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ecr_registry}"

# 4. Pull + run del servicio. Si la imagen aún no existe (primer apply
#    antes del primer push), salimos sin error y un 'docker pull && docker run'
#    posterior al push lo arranca (vía SSM o re-launching la instancia).
if docker pull "${ecr_image}:latest"; then
  docker rm -f vertebra-svc 2>/dev/null || true
  docker run -d \
    --name vertebra-svc \
    --restart=always \
    -p ${host_port}:8000 \
    -e PORT=8000 \
    -e CORS_ORIGINS='${cors_origins_json}' \
    "${ecr_image}:latest"
else
  echo "Imagen aún no publicada en ECR. Subila con scripts/deploy_ecr.sh y reinicia la instancia." >&2
fi
