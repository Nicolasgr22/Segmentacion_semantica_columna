FROM python:3.11-slim

WORKDIR /app

# Paquetes runtime + curl para healthcheck. --no-install-recommends recorta
# superficie de ataque y tamaño.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 curl \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Usuario no-root (UID/GID fijos para reproducibilidad). Si hay RCE en Pillow
# o torch al decodificar input del usuario, el atacante NO queda como root.
RUN groupadd -r -g 1000 vertebra \
    && useradd -r -u 1000 -g vertebra -m -d /home/vertebra -s /sbin/nologin vertebra

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

# 5. Permisos: el usuario vertebra solo necesita LECTURA. Sin permisos de
#    escritura sobre el código ni los modelos -> incluso con RCE el atacante
#    no puede modificar binarios ni esconder backdoors persistentes.
RUN chown -R root:vertebra /app && chmod -R o-rwx,g-w /app

USER vertebra

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/vertebraai/health" || exit 1

# Permite override del puerto via env (Railway-style / EC2 user-data).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
