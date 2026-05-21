# VertebraAI — Servicio de Inferencia

[![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-pytest%20≥80%25-4CAF50?logo=pytest&logoColor=white)](tests/)
[![AWS Cognito](https://img.shields.io/badge/Auth-AWS%20Cognito-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/cognito/)
[![License](https://img.shields.io/badge/License-Académica%20Uniandes-004B87)](https://uniandes.edu.co/)

> **Aviso clínico:** Esta herramienta es un apoyo diagnóstico exclusivamente. Toda decisión clínica debe ser revisada por un radiólogo o especialista cualificado.

Microservicio de segmentación automática de columna vertebral en radiografías, desarrollado como parte del proyecto de grado de la **Maestría en Inteligencia Artificial (MaIA)** — Universidad de los Andes, 2026.

Expone dos modelos de segmentación detrás de una API REST en FastAPI con arquitectura hexagonal (Ports & Adapters). El **pipeline ganador** (`VertebraPrompt-Net + BoxRefiner + MedSAM`, notebook 06) se carga como modelo por defecto. Detecta y segmenta hasta **17 vértebras** (T1-T12, L1-L5) en radiografías AP en formato PNG o JPEG.

---

## Tabla de contenidos

- [Descripción del servicio](#descripción-del-servicio)
  - [Pipeline de inferencia](#pipeline-de-inferencia)
  - [Modelos disponibles](#modelos-disponibles)
  - [Arquitectura interna](#arquitectura-interna)
- [Dependencias](#dependencias)
- [Entorno de ejecución](#entorno-de-ejecución)
- [Pasos de despliegue](#pasos-de-despliegue)
  - [Local (sin Docker)](#local-sin-docker)
  - [Docker](#docker)
  - [Producción (AWS ECR + EC2)](#producción-aws-ecr--ec2)
- [Variables de entorno](#variables-de-entorno)
- [Credenciales de ejemplo](#credenciales-de-ejemplo)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Autenticación](#autenticación)
  - [Analizar una radiografía](#analizar-una-radiografía)
  - [Otros endpoints](#otros-endpoints)
  - [Pruebas](#pruebas)
- [Contribución](#contribución)
- [Licencia](#licencia)

---

## Descripción del servicio

Microservicio FastAPI que expone los modelos de segmentación entrenados durante la investigación como una API REST lista para producción. Implementa arquitectura hexagonal (Ports & Adapters): la lógica de negocio no depende de los modelos concretos ni del framework HTTP, lo que permite cambiar de modelo o de base de datos sin tocar los casos de uso.

### Pipeline de inferencia

```
Imagen PNG o JPEG (≥ 32×32 px, cualquier tamaño)
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Adapter seleccionado (según parámetro `model`)      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Preprocesamiento propio del adapter           │  │
│  │  (resize 1024×1024 + norm percentil para       │  │
│  │  medsam; ventana deslizante 128×128 para        │  │
│  │  unetpp-patches)                               │  │
│  ├────────────────────────────────────────────────┤  │
│  │  Inferencia del modelo                         │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
       │
       ▼
[ Composición multi-clase + métricas + máscara coloreada ]
```

### Modelos disponibles

| Valor `model` | Descripción | Métricas |
|---------------|-------------|----------|
| `medsam` _(por defecto)_ | VertebraPrompt-Net + BoxRefiner + MedSAM ViT-B fine-tuned (pipeline ganador, notebook 06) | `GET /api/vertebraai/models/medsam` |
| `unetpp-patches` | UNet++ encoder EfficientNet-B7, ventana deslizante 128×128 | `GET /api/vertebraai/models/unetpp-patches` |

### Arquitectura interna

```
services/
├── app/
│   ├── api/v1/
│   │   ├── routers/                      # Endpoints FastAPI
│   │   │   ├── vertebrae.py              # POST /api/vertebraai/xrays
│   │   │   ├── health.py                 # GET  /api/vertebraai/health
│   │   │   ├── export.py                 # GET  /api/vertebraai/xrays/{id}/exports/{format}
│   │   │   ├── models.py                 # GET  /api/vertebraai/models[/{id}]
│   │   │   └── auth.py                   # POST /api/vertebraai/auth/login
│   │   └── schemas/
│   │       ├── requests.py               # Enums ModelName, ExportFormat
│   │       ├── responses.py              # Schemas Pydantic + analysis_to_response()
│   │       └── model_schemas.py          # Schemas de Model Cards
│   ├── core/
│   │   ├── domain/
│   │   │   ├── entities/                 # Vertebra, VertebraAnalysis, ModelCard, AuthUser
│   │   │   └── ports/                    # ABCs: ModelPort, StoragePort, AuthPort
│   │   └── use_cases/                    # AnalyzeImageUseCase, ExportResultUseCase
│   ├── infrastructure/
│   │   └── adapters/
│   │       ├── model/                    # VertebraPromptBoxRefiner, UnetPlusPlus, legacy
│   │       ├── registry/                 # InMemoryModelRegistry (Model Cards)
│   │       ├── storage/                  # InMemoryStorageAdapter (LRU max=100)
│   │       └── auth/                     # CognitoAuthAdapter
│   ├── config.py                         # Settings con pydantic-settings
│   ├── dependencies.py                   # Inyección de dependencias (lru_cache)
│   ├── main.py                           # FastAPI app + lifespan + CORS + rate limiting
│   └── rate_limit.py                     # SlowAPI limiter
├── openapi/vertebraAI.yml                # Especificación OpenAPI 3.0.3
├── docs/ARCHITECTURE.md                  # Documentación técnica detallada
├── tests/                                # Pruebas unitarias
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Dependencias

| Grupo | Paquetes |
|-------|----------|
| **API & Serving** | `fastapi>=0.111.0`, `uvicorn>=0.30.0`, `python-multipart>=0.0.9`, `slowapi>=0.1.9` |
| **Validación & Config** | `pydantic>=2.7.0`, `pydantic-settings>=2.3.0` |
| **Deep Learning** | `torch>=2.1.0`, `torchvision>=0.16.0`, `transformers>=4.40.0`, `segment-anything>=1.0`, `segmentation-models-pytorch>=0.3.3`, `cloudpickle>=3.0.0` |
| **Procesamiento de imagen** | `Pillow>=10.3.0`, `opencv-python-headless>=4.9.0.80`, `numpy>=1.26.0`, `albumentations>=1.4.0` |
| **Autenticación** | `boto3>=1.34.0`, `python-jose[cryptography]>=3.3.0`, `email-validator>=2.1.0` |
| **Testing** | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `httpx>=0.27.0` |
| **Paquete local** | `model-pkg/model_medsam-0.1.0-py3-none-any.whl` (instalar aparte, ver más abajo) |

---

## Entorno de ejecución

| Componente | Versión mínima |
|------------|----------------|
| Python | 3.14+ |
| [uv](https://github.com/astral-sh/uv) | última estable |
| Docker | 24+ (producción) |
| RAM | ~4 GB (modo CPU) |
| VRAM | 6 GB+ (GPU, opcional) |

Los checkpoints (~2 GB) no están en el repositorio. Descargarlos antes de arrancar el servicio (ver [Credenciales de ejemplo](#credenciales-de-ejemplo)).

---

## Pasos de despliegue

### Local (sin Docker)

```bash
# 1. Desde la raíz del monorepo, crear el entorno virtual
uv venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# 2. Entrar al directorio del servicio
cd services

# 3. Instalar PyTorch CPU-only (cambiar URL para CUDA)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Instalar dependencias
uv pip install -r requirements.txt

# 5. Instalar el paquete local MedSAM
uv pip install model-pkg/model_medsam-0.1.0-py3-none-any.whl

# 6. Configurar variables de entorno
cp .env.example .env
# Editar .env si los checkpoints están en otra ruta

# 7. Arrancar con recarga automática
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El servicio estará disponible en `http://localhost:8000`. La documentación interactiva requiere `DEBUG=true`:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Docker

```bash
cd services

# Construir imagen
docker build -t vertebraai .

# Ejecutar con checkpoints montados
docker run -p 8000:8000 \
  -v /ruta/local/model-pkg:/app/model-pkg:ro \
  -e MODEL_DEVICE=cpu \
  -e AUTH_ENABLED=false \
  vertebraai
```

El primer arranque puede tardar 60–120 segundos mientras se cargan los dos adapters en memoria.

### Producción (AWS ECR + EC2)

El despliegue en producción se gestiona desde Terraform en la raíz del monorepo. El script `scripts/deploy_ecr.sh` construye la imagen y la sube al ECR:

```bash
# Desde services/
bash scripts/deploy_ecr.sh
```

Para el despliegue completo en AWS, ver [`../terraform/`](../terraform/) y la sección **AWS (Terraform)** del [README raíz](../README.md).

---

## Variables de entorno

Todas las variables se leen desde el archivo `.env` ubicado en `services/` o directamente del entorno del proceso (variables de entorno del sistema o del contenedor Docker). La configuración es gestionada por [`app/config.py`](app/config.py) usando `pydantic-settings`, que valida tipos y aplica los valores por defecto automáticamente.

> **Cualquier parámetro definido en `app/config.py` puede sobreescribirse sin tocar el código**, simplemente declarándolo como variable de entorno o en `.env`. El orden de prioridad es:
>
> ```
> 1. Variable de entorno del sistema  (export UNETPP_SIGMA=30.0)
> 2. Archivo .env                     (UNETPP_SIGMA=30.0)
> 3. Valor default en config.py       (unetpp_sigma: float = 50.0)
> ```
>
> Solo es necesario declarar las variables que difieren del default. El resto se aplica automáticamente.

```bash
# Punto de partida para configuración local
cp services/.env.example services/.env
```

### Servidor

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `DEBUG` | Activa Swagger UI (`/api/docs`), ReDoc (`/api/redoc`) y modo debug de FastAPI. **No activar en producción.** | `false` |
| `HOST` | Dirección de escucha del servidor | `0.0.0.0` |
| `PORT` | Puerto del servidor | `8000` |

### Modelo e inferencia

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MODEL_DEVICE` | Dispositivo de inferencia: `cpu`, `cuda` o `mps` | `cpu` |
| `MODEL_INPUT_SIZE` | Resolución interna de entrada al modelo (píxeles) | `512` |
| `MAX_UPLOAD_MB` | Tamaño máximo de imagen aceptada en MB | `50` |
| `INFERENCE_TIMEOUT_S` | Timeout de inferencia en segundos | `60` |

### Checkpoints de los modelos

Rutas relativas al directorio `services/`. Si los modelos se montan en otra ubicación (p. ej. volumen Docker), ajustar estas variables.

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MEDSAM_PROMPT_NET_CHECKPOINT` | Checkpoint de VertebraPrompt-Net | `model-pkg/medsam/vertebraprompt_net_auxiliar_best.pt` |
| `MEDSAM_BOX_REFINER_CHECKPOINT` | Checkpoint de BoxRefiner | `model-pkg/medsam/box_refiner_best.pt` |
| `MEDSAM_SAM_CHECKPOINT` | Checkpoint base SAM ViT-B | `model-pkg/medsam/medsam_vit_b.pth` |
| `MEDSAM_FINETUNED_CHECKPOINT` | Checkpoint MedSAM fine-tuned (decoder + encoder parcial) | `model-pkg/medsam/medsam_decoder_encoder_parcial_entrenado_vertebraprompt_aux.pt` |
| `UNETPP_PATCHES_CHECKPOINT` | Checkpoint UNet++ con ventana deslizante | `model-pkg/unet++_patches/unet++_patches.pth` |

### Hiperparámetros MedSAM pipeline (configurables sin recompilar)

Los valores siguientes corresponden a los **hiperparámetros del pipeline ganador** (notebook 06). Solo es necesario declararlos en `.env` si se quiere experimentar con valores distintos.

#### Arquitectura VertebraPrompt-Net y decodificación

| Variable | Descripción | Default |
|----------|-------------|---------|
| `MEDSAM_PROMPT_NET_INPUT` | Resolución de entrada de VertebraPrompt-Net (píxeles) | `512` |
| `MEDSAM_IMG_SIZE` | Resolución de la grilla MedSAM y el letterbox | `1024` |
| `MEDSAM_BASE_CHANNELS` | Canales base de la U-Net multi-tarea | `32` |
| `MEDSAM_N_CLASSES` | Clases predichas (T1..T12 + L1..L5) | `17` |
| `MEDSAM_TOP_PEAKS` | Máximo de picos extraídos del heatmap | `90` |
| `MEDSAM_MIN_PEAK_DIST` | Distancia mínima entre picos (supresión no máxima) | `8` |
| `MEDSAM_THR_REL_PEAKS` | Umbral relativo al máximo del heatmap para aceptar un pico | `0.12` |
| `MEDSAM_N_BOXES_PATH` | Pasos de la programación dinámica (= n_classes) | `17` |
| `MEDSAM_MAX_CANDIDATES` | Candidatos máximos enviados a la DP | `120` |
| `MEDSAM_MAX_GAP_REL_DY` | Multiplicador del gap esperado en la DP | `2.40` |
| `MEDSAM_Y_MIN_ANATOMIC_MARGIN` | Margen superior para exclusión de cráneo (fracción de la imagen) | `0.06` |
| `MEDSAM_SKULL_SCORE_FACTOR` | Penalización de score en zona de cráneo | `0.12` |

#### Construcción de cajas

| Variable | Descripción | Default |
|----------|-------------|---------|
| `MEDSAM_BOX_EXPAND_W` | Factor de expansión horizontal de la caja final | `1.12` |
| `MEDSAM_BOX_EXPAND_H` | Factor de expansión vertical de la caja final | `1.12` |
| `MEDSAM_WH_PRED_BLEND` | Peso de la predicción del wh-map en la mezcla | `0.65` |
| `MEDSAM_WH_TEMPLATE_BLEND` | Peso de la plantilla mediana en la mezcla | `0.35` |
| `MEDSAM_WH_CLIP_W` | Límites `[min, max]` para recorte de w_rel (lista JSON) | `[0.03, 0.28]` |
| `MEDSAM_WH_CLIP_H` | Límites `[min, max]` para recorte de h_rel (lista JSON) | `[0.025, 0.18]` |

#### BoxRefiner

| Variable | Descripción | Default |
|----------|-------------|---------|
| `MEDSAM_BOX_REFINER_SIZE` | Resolución del crop de entrada al refinador (píxeles) | `192` |
| `MEDSAM_BOX_REFINER_BLEND` | Factor de mezcla al aplicar los deltas del refinador | `0.80` |
| `MEDSAM_BOX_REFINER_MAX_ABS_DXY` | Saturación tanh para desplazamientos dx, dy | `0.45` |
| `MEDSAM_BOX_REFINER_MAX_ABS_LOG_SCALE` | Saturación tanh para escala logarítmica dw, dh | `0.45` |
| `MEDSAM_BOX_REFINER_CONTEXT_FRAC` | Fracción de contexto extra en el crop de refinamiento | `0.85` |
| `MEDSAM_N_SERVICE_CLASSES` | Clases totales del contrato del servicio (bg + C1..C7 + T1..T12 + L1..L5) | `23` |

**Ejemplo:** ajustar agresividad del BoxRefiner:
```bash
MEDSAM_BOX_REFINER_BLEND=0.50
MEDSAM_BOX_REFINER_CONTEXT_FRAC=1.0
```

---

### Hiperparámetros UNet++ (configurables sin recompilar)

Los valores siguientes corresponden a los **hiperparámetros ganadores** del barrido documentado en `notebooks/unet++/Unet++_patches.ipynb` (celdas 30–32, Dice test 0.4711). Solo es necesario declararlos en `.env` o como variable de entorno si se quiere experimentar con valores distintos; de lo contrario se aplican los defaults de `config.py`.

| Variable | Descripción | Default (ganador) |
|----------|-------------|-------------------|
| `UNETPP_ENCODER_NAME` | Encoder backbone de la arquitectura UNet++ | `efficientnet-b7` |
| `UNETPP_IN_CHANNELS` | Canales de entrada (3 = RGB) | `3` |
| `UNETPP_NUM_MODEL_CLASSES` | Clases que emite el modelo (bg + T1..T12 + L1..L5) | `18` |
| `UNETPP_PATCH_SIZE` | Resolución a la que se redimensiona cada parche antes de inferencia | `128` |
| `UNETPP_MEAN` | Media de normalización ImageNet (lista JSON) | `[0.485, 0.456, 0.406]` |
| `UNETPP_STD` | Desviación estándar de normalización ImageNet (lista JSON) | `[0.229, 0.224, 0.225]` |
| `UNETPP_CLAHE_CLIP` | `clipLimit` del preprocesado CLAHE | `2.0` |
| `UNETPP_CLAHE_TILE` | `tileGridSize` del preprocesado CLAHE (lista JSON `[h, w]`) | `[8, 8]` |
| `UNETPP_PATCH_AREA` | Fracción del área total de la imagen que define el tamaño de la ventana deslizante | `0.5` |
| `UNETPP_SIGMA` | Sigma de la ventana gaussiana de fusión de parches | `50.0` |
| `UNETPP_STRIDE_RATIO` | Divisor del tamaño de parche para calcular el stride (`stride = patch / ratio`) | `4` |
| `UNETPP_N_SERVICE_CLASSES` | Clases totales del contrato del servicio (C1-C7 + T1-T12 + L1-L5 + bg) | `23` |
| `UNETPP_FIRST_VERTEBRA_ID` | ID de servicio de T1 (primera vértebra que predice el modelo) | `6` |
| `UNETPP_LAST_VERTEBRA_ID` | ID de servicio de L5 (última vértebra que predice el modelo) | `22` |

**Ejemplo:** experimentar con ventana más pequeña y mayor stride:
```bash
# .env o export
UNETPP_PATCH_AREA=0.3
UNETPP_STRIDE_RATIO=6
UNETPP_SIGMA=30.0
```

### Seguridad y acceso

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `CORS_ORIGINS` | Orígenes HTTP permitidos (lista JSON). Usar dominios específicos en producción. | `["*"]` |
| `RATE_LIMIT_DEFAULT` | Límite de tasa global para todos los endpoints | `120/minute` |
| `RATE_LIMIT_ANALYZE` | Límite de tasa estricto para `POST /xrays` (inferencia consume CPU/RAM por ~30 s) | `5/minute` |
| `AUTH_ENABLED` | Activa validación de tokens Cognito. Poner `false` para desarrollo local sin Cognito. | `true` |

### Autenticación (AWS Cognito)

Solo necesarias cuando `AUTH_ENABLED=true`. Los valores corresponden al User Pool del proyecto.

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `COGNITO_USER_POOL_ID` | ID del User Pool de AWS Cognito | `us-east-1_M9mJH2Qim` |
| `COGNITO_CLIENT_ID` | Client ID de la aplicación web en Cognito | `5am1u0928s7p69vor1rbpt4qg7` |
| `COGNITO_REGION` | Región AWS donde está el User Pool | `us-east-1` |

---

## Credenciales de ejemplo

### Checkpoints de los modelos (AWS S3)

Los pesos entrenados están en un bucket S3 privado con credenciales de solo lectura.

| Campo | Valor |
|-------|-------|
| Bucket | `s3://maia-proyecto-final-models` |
| Ruta | `s3://maia-proyecto-final-models/models/` |
| Región | `us-east-1` |
| AWS Access Key ID | `AKIAZQ3DPKVWU4CKQKNG` |
| AWS Secret Access Key | *(solicitar por canal seguro — ver nota abajo)* |

```bash
# Configurar perfil de solo lectura
aws configure --profile vertebraai-models
# AWS Access Key ID:     AKIAZQ3DPKVWU4CKQKNG
# AWS Secret Access Key: <solicitar por canal seguro>
# Default region:        us-east-1

# Descargar todos los checkpoints
aws s3 cp s3://maia-proyecto-final-models/models/ ./model-pkg/ --recursive --profile vertebraai-models

# Verificar contenido
aws s3 ls s3://maia-proyecto-final-models/models/ --recursive --profile vertebraai-models
```

> Las credenciales tienen permisos de **solo lectura** sobre este bucket. No pueden escribir ni eliminar archivos.
>
> Si necesitas el `AWS Secret Access Key`, escríbenos a [af.rinconr1@uniandes.edu.co](mailto:af.rinconr1@uniandes.edu.co).

### Usuario de prueba (AWS Cognito)

Para probar los endpoints protegidos sin necesidad de crear una cuenta propia:

| Campo | Valor |
|-------|-------|
| Usuario | `maia_groupo5` |
| Contraseña | *(solicitar por canal seguro)* |
| User Pool | `us-east-1_M9mJH2Qim` |
| Región | `us-east-1` |

> En desarrollo local se puede evitar la autenticación Cognito configurando `AUTH_ENABLED=false` en `.env`.

---

## Ejemplos de uso

### Autenticación

```bash
# Obtener token JWT
curl -X POST http://localhost:8000/api/vertebraai/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "maia_groupo5", "password": "<contraseña>"}' \
  | jq '{token: .token, user: .user}'

# Guardar el token para usarlo en requests siguientes
TOKEN=$(curl -s -X POST http://localhost:8000/api/vertebraai/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "maia_groupo5", "password": "<contraseña>"}' \
  | jq -r '.token')
```

### Analizar una radiografía

```bash
# Con el pipeline ganador (medsam por defecto)
curl -X POST http://localhost:8000/api/vertebraai/xrays \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@radiografia.png;type=image/png" \
  -F "model=medsam" \
  | jq '{study_id, detected: .metrics.detected_count, dice: .metrics.model_metrics.dice}'

# Con UNet++ patches
curl -X POST http://localhost:8000/api/vertebraai/xrays \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@radiografia.png;type=image/png" \
  -F "model=unetpp-patches" \
  | jq '{study_id, detected: .metrics.detected_count}'
```

**Salida:** JSON con `study_id`, máscara coloreada en base64, métricas y lista de 22 vértebras (C3-C7 + T1-T12 + L1-L5).

### Otros endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/vertebraai/auth/login` | — | Obtener token JWT |
| `GET` | `/api/vertebraai/auth/me` | 🔒 | Datos del usuario autenticado |
| `POST` | `/api/vertebraai/xrays` | 🔒 | Analizar radiografía |
| `GET` | `/api/vertebraai/health` | — | Estado del servicio y modelo |
| `GET` | `/api/vertebraai/models` | — | Catálogo de modelos con métricas |
| `GET` | `/api/vertebraai/models/{model_id}` | — | Detalle de un Model Card |
| `GET` | `/api/vertebraai/xrays/{id}/exports/{format}` | 🔒 | Exportar resultado |

**Formatos de exportación** (`format`): `png` · `mask` · `overlay` · `report`

```bash
# Estado del servicio
curl http://localhost:8000/api/vertebraai/health | jq .

# Catálogo de modelos
curl http://localhost:8000/api/vertebraai/models | jq '.[] | {id, name}'

# Exportar máscara de segmentación
STUDY_ID="<id-del-estudio>"
curl -o mask.png \
  "http://localhost:8000/api/vertebraai/xrays/$STUDY_ID/exports/mask"

# Exportar reporte JSON completo
curl "http://localhost:8000/api/vertebraai/xrays/$STUDY_ID/exports/report" \
  | jq .metrics
```

Especificación completa: [`openapi/vertebraAI.yml`](openapi/vertebraAI.yml)

> La documentación interactiva (Swagger / ReDoc) está disponible solo con `DEBUG=true`:
> - Swagger UI: `http://localhost:8000/api/docs`
> - ReDoc: `http://localhost:8000/api/redoc`

### Pruebas

Las pruebas se ejecutan **sin GPU ni checkpoints reales** — todos los puertos externos están mockeados con `unittest.mock`.

```bash
# Todas las pruebas
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ -v --cov=app --cov-report=term-missing

# Solo unitarias
pytest tests/unit/ -v
```

Cobertura objetivo: ≥ 80 %

| Archivo | Cobertura |
|---------|-----------|
| `tests/unit/test_analyze_image_use_case.py` | Use case de análisis |
| `tests/unit/test_vertebrae_router.py` | Router principal |
| `tests/unit/test_vertebraprompt_adapter.py` | Adapter VertebraPromptBoxRefiner (pipeline ganador) |
| `tests/unit/test_unetpp_patches_adapter.py` | Adapter UNet++ con patches |
| `tests/unit/test_segformer_adapter.py` | Adapter Segformer (legacy) |

---

## Contribución

1. Crear rama: `git checkout -b feature/nombre-feature`
2. Ejecutar pruebas antes de commit: `pytest tests/ -v`
3. Formatear código: `black app/ tests/` y `isort app/ tests/`
4. Abrir Pull Request con descripción del cambio

---

## Licencia

Proyecto académico — Universidad de los Andes, MaIA 2026. Uso restringido a fines educativos e investigativos.
