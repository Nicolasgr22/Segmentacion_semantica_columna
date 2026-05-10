#!/usr/bin/env bash
#
# Build + push de la imagen del servicio VertebraAI a ECR.
#
# Requisitos previos:
#   - Terraform aplicado (ECR creado): `cd terraform && terraform apply`
#   - AWS CLI configurada con credenciales del proyecto
#   - Docker corriendo localmente
#   - Modelos en services/model-pkg/ (.pth + .pt)
#
# Uso:
#   ./services/scripts/deploy_ecr.sh           # build + push :latest
#   ./services/scripts/deploy_ecr.sh v1.2.0    # build + push :v1.2.0 (y :latest)
#
# Después del primer push hay que reiniciar el contenedor en la EC2:
#   aws ssm start-session --target $(terraform -chdir=terraform output -raw service_instance_id)
#   sudo docker pull <ecr_repo>:latest && sudo docker rm -f vertebra-svc && <re-run>
#   (o más simple: terraform taint aws_instance.svc && terraform apply)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$(cd "$SERVICE_DIR/../terraform" && pwd)"

TAG="${1:-latest}"

echo "▸ Leyendo outputs de terraform..."
ECR_REGISTRY=$(terraform -chdir="$TERRAFORM_DIR" output -raw ecr_registry)
ECR_REPO=$(terraform -chdir="$TERRAFORM_DIR" output -raw ecr_repository_url)
AWS_REGION=$(terraform -chdir="$TERRAFORM_DIR" output -raw -json 2>/dev/null \
  | grep -o '"aws_region":[^,]*' || echo '')

# Si no hay output de region (no lo expusimos), lo deducimos del registry
if [ -z "${AWS_REGION:-}" ]; then
  AWS_REGION=$(echo "$ECR_REGISTRY" | sed -E 's/.*\.dkr\.ecr\.([^.]+)\.amazonaws\.com/\1/')
fi

echo "  ECR registry : $ECR_REGISTRY"
echo "  ECR repo     : $ECR_REPO"
echo "  Region       : $AWS_REGION"
echo "  Tag          : $TAG"
echo ""

echo "▸ Verificando que existen los modelos..."
for f in \
  "$SERVICE_DIR/model-pkg/sam_vit_b_01ec64.pth" \
  "$SERVICE_DIR/model-pkg/medsam/vertebraprompt_net_auxiliar_best.pt" \
  "$SERVICE_DIR/model-pkg/medsam/box_refiner_best.pt" \
  "$SERVICE_DIR/model-pkg/medsam/medsam_decoder_encoder_parcial_entrenado_vertebraprompt_aux.pt"
do
  if [ ! -f "$f" ]; then
    echo "  ✘ Falta: $f" >&2
    exit 1
  fi
done
echo "  ✔ Modelos presentes"
echo ""

echo "▸ Login en ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"
echo ""

echo "▸ Building imagen (linux/amd64 — la EC2 es x86_64)..."
docker buildx build \
  --platform linux/amd64 \
  -t "$ECR_REPO:$TAG" \
  -t "$ECR_REPO:latest" \
  --push \
  "$SERVICE_DIR"
echo ""

echo "✔ Imagen publicada: $ECR_REPO:$TAG"
echo ""
echo "Para reiniciar el contenedor en la EC2 con la nueva imagen:"
echo "  aws ssm start-session --target \$(terraform -chdir=$TERRAFORM_DIR output -raw service_instance_id)"
echo "  sudo docker pull $ECR_REPO:latest"
echo "  sudo docker rm -f vertebra-svc && sudo docker run -d --name vertebra-svc --restart=always -p 80:8000 -e PORT=8000 $ECR_REPO:latest"
echo ""
echo "O re-crear la instancia (más simple, ~3min):"
echo "  terraform -chdir=$TERRAFORM_DIR taint aws_instance.svc"
echo "  terraform -chdir=$TERRAFORM_DIR apply"
