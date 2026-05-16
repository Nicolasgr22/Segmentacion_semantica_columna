#!/bin/bash
# Bootstrap del nodo Spot que corre el servicio VertebraAI.
# - Instala Docker
# - Login en ECR + pull de la imagen
# - Corre el contenedor en :80 con restart=always
#
# image_hash: ${image_hash}
# (cambiar este hash fuerza la recreación de la EC2 vía user_data_replace_on_change)
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
  # Hardening del contenedor:
  # - --read-only + tmpfs : root fs inmutable; solo /tmp escribible (en RAM, 256M).
  # - --cap-drop=ALL      : sin capabilities de Linux. La app no necesita ninguna.
  # - --security-opt no-new-privileges : evita escalada via setuid.
  # - --pids-limit        : limita fork bombs.
  # - --memory / --cpus   : t3.large tiene 8G/2vCPU; dejamos ~1GB de margen al host.
  # - --user 1000:1000    : redundancia (Dockerfile ya hace USER vertebra).
  docker run -d \
    --name vertebra-svc \
    --restart=always \
    --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,size=256m \
    --cap-drop=ALL \
    --security-opt no-new-privileges \
    --pids-limit 256 \
    --memory=7000m \
    --memory-swap=7000m \
    --cpus=1.8 \
    --user 1000:1000 \
    -p ${host_port}:8000 \
    -e PORT=8000 \
    -e CORS_ORIGINS='${cors_origins_json}' \
    "${ecr_image}:latest"
else
  echo "Imagen aún no publicada en ECR. Subila con scripts/deploy_ecr.sh y reinicia la instancia." >&2
fi
