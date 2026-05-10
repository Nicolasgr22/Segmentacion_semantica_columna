FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 1. Torch CPU-only (capa pesada que rara vez cambia)
RUN pip install --no-cache-dir torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# 2. Dependencias de PyPI
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Checkpoints del modelo.
#    Se copia model-pkg/ DENTRO de /app/ porque la app lee los .pt/.pth
#    desde rutas relativas tipo "model-pkg/medsam/...".
#    NOTA: el wheel model_medsam-*.whl NO se instala (solo lo necesitaría
#    el adapter legacy MedSAMAdapter, que no está en uso).
COPY model-pkg/ ./model-pkg/

# 4. Código de la aplicación
COPY app/ ./app/
COPY openapi/ ./openapi/

EXPOSE 8000

# Permite override del puerto via env (Railway-style / EC2 user-data).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
