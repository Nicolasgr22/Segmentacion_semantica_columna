# VertebraAI — Servicio de Segmentación de Columna Vertebral

[![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

Microservicio de análisis automático de radiografías de columna vertebral desarrollado como parte del proyecto de grado de la **Maestría en Inteligencia Artificial (MaIA)** de la Universidad de los Andes.

Expone tres modelos de segmentación detrás de una API REST en FastAPI con arquitectura hexagonal (Ports & Adapters). El **pipeline ganador** (`VertebraPrompt-Net + BoxRefiner + MedSAM`, notebook 06) se carga como modelo por defecto (`medsam`). Segmenta hasta **22 vértebras** (C3-C7, T1-T12, L1-L5) en radiografías AP en formato PNG o JPEG.

> **Aviso clínico:** Esta herramienta es un apoyo diagnóstico exclusivamente. Toda decisión clínica debe ser revisada por un radiólogo o especialista cualificado.

---

## Pipeline de inferencia

```
Imagen PNG o JPEG (≥32×32 px, cualquier tamaño)
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Adapter seleccionado (según parámetro `model`)      │
│  ┌────────────────────────────────────────────────┐  │
│  │ Preprocesamiento propio del adapter            │  │
│  │ (p.ej. resize 1024×1024 + norm percentil       │  │
│  │  para medsam; ventana deslizante para          │  │
│  │  unetpp-patches)                               │  │
│  ├────────────────────────────────────────────────┤  │
│  │ Inferencia del modelo                          │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
       │
       ▼
[ Composición multi-clase + métricas + máscara coloreada ]
```

Resultados objetivo del modelo ganador (test, según `notebooks/medsam_pipeline/results_summary/`):
- Dice estricto: **0.5530** | Dice flexible: **0.7678**

---

## Pre-requisitos

- Python 3.14.1
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes/venv)

## Instalación

```bash
# 1. Clonar y entrar al servicio
cd services

# 2. Crear y activar entorno virtual
uv venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# 3. Instalar PyTorch CPU-only (cambiar URL para CUDA)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Instalar dependencias
uv pip install -r requirements.txt

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con las rutas de los checkpoints
```

---

## Variables de entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MODEL_DEVICE` | Dispositivo de inferencia: `cpu`, `cuda`, `mps` | `cpu` |
| `MODEL_INPUT_SIZE` | Resolución de entrada interna | `512` |
| `MEDSAM_PROMPT_NET_CHECKPOINT` | Checkpoint de VertebraPrompt-Net | `model-pkg/medsam/vertebraprompt_net_auxiliar_best.pt` |
| `MEDSAM_BOX_REFINER_CHECKPOINT` | Checkpoint de BoxRefiner | `model-pkg/medsam/box_refiner_best.pt` |
| `MEDSAM_SAM_CHECKPOINT` | Checkpoint base SAM ViT-B | `model-pkg/medsam/medsam_vit_b.pth` |
| `MEDSAM_FINETUNED_CHECKPOINT` | Checkpoint MedSAM fine-tuned (decoder + encoder parcial) | `model-pkg/medsam/medsam_decoder_encoder_parcial_entrenado_vertebraprompt_aux.pt` |
| `UNETPP_PATCHES_CHECKPOINT` | Checkpoint del modelo UNet++ con ventana deslizante | `model-pkg/unet++_patches/unet++_patches.pth` |
| `MAX_UPLOAD_MB` | Tamaño máximo de imagen aceptada (MB) | `50` |
| `INFERENCE_TIMEOUT_S` | Timeout de inferencia (segundos) | `60` |
| `CORS_ORIGINS` | Orígenes permitidos (lista JSON) | `["*"]` |
| `RATE_LIMIT_DEFAULT` | Límite de tasa para endpoints generales | `120/minute` |
| `RATE_LIMIT_ANALYZE` | Límite de tasa para el endpoint de análisis | `5/minute` |
| `DEBUG` | Activa Swagger UI / ReDoc y modo debug de FastAPI | `false` |
| `PORT` | Puerto del servidor | `8000` |

---

## Ejecución

### Desarrollo (con recarga automática)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Producción con Docker

```bash
# Construir imagen
docker build -t vertebraai .

# Ejecutar con checkpoints montados
docker run -p 8000:8000 \
  -v /path/to/model-pkg:/app/model-pkg:ro \
  -e MEDSAM_PROMPT_NET_CHECKPOINT=model-pkg/medsam/vertebraprompt_net_auxiliar_best.pt \
  -e MEDSAM_BOX_REFINER_CHECKPOINT=model-pkg/medsam/box_refiner_best.pt \
  -e MEDSAM_SAM_CHECKPOINT=model-pkg/medsam/medsam_vit_b.pth \
  -e MEDSAM_FINETUNED_CHECKPOINT=model-pkg/medsam/medsam_decoder_encoder_parcial_entrenado_vertebraprompt_aux.pt \
  -e UNETPP_PATCHES_CHECKPOINT=model-pkg/unet++_patches/unet++_patches.pth \
  -e MODEL_DEVICE=cpu \
  vertebraai
```

Al arrancar, el servicio carga los **dos adapters activos** en memoria. El primer arranque puede tardar 60–120 segundos dependiendo del hardware.

---

## Endpoints

Todos bajo el prefix `/api/vertebraai`. Los endpoints marcados con 🔒 requieren `Authorization: Bearer <token>`.

### `POST /api/vertebraai/auth/login`

Autentica al usuario contra AWS Cognito. Devuelve el IdToken JWT.

```bash
curl -X POST http://localhost:8000/api/vertebraai/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "maia_groupo5", "password": "tu-contraseña"}' \
  | jq '{token: .token, user: .user}'
```

**Entrada:** JSON `{ username, password }` — acepta nombre de usuario o email alias de Cognito.  
**Salida:** `{ token, user: { email, name, sub }, token_type }` — usar `token` como Bearer en peticiones siguientes.

---

### `GET /api/vertebraai/auth/me` 🔒

Devuelve los datos del usuario autenticado.

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/vertebraai/auth/me
```

---

### `POST /api/vertebraai/xrays` 🔒

Crea un nuevo análisis de radiografía. Retorna `201 Created`.

```bash
curl -X POST http://localhost:8000/api/vertebraai/xrays \
  -H "Authorization: Bearer <token>" \
  -F "file=@radiografia.png;type=image/png" \
  -F "model=medsam" \
  | jq '{study_id, detected: .metrics.detected_count, confidence: .metrics.global_confidence}'
```

**Entrada:** `multipart/form-data`
- `file`: PNG o JPEG, mínimo 32×32 px (cualquier tamaño es aceptado; cada adapter aplica su propio preprocesamiento internamente)
- `model` (opcional): nombre del modelo a utilizar. Valores disponibles:

| Valor | Modelo | Notas |
|-------|--------|-------|
| `medsam` _(por defecto)_ | VertebraPrompt-Net + BoxRefiner + MedSAM ViT-B fine-tuned | Pipeline ganador notebook 06 |
| `unetpp-patches` | UNet++ encoder efficientnet-b7, ventana deslizante 128×128 | Dice test 0.4711 |

**Salida:** JSON con `study_id`, máscara coloreada en base64, métricas y lista de 22 vértebras (C3-C7 + T1-T12 + L1-L5).

---

### `GET /api/vertebraai/health`

Estado del servicio y del modelo cargado.

```bash
curl http://localhost:8000/api/vertebraai/health | jq .
# {
#   "status": "ok",
#   "model_version": "vertebraprompt+boxrefiner+medsam-vit-b",
#   "model_loaded": true,
#   "uptime_s": 120.3
# }
```

---

### `GET /api/vertebraai/models`

Catálogo de modelos publicados con sus métricas de experimento (Model Cards).

```bash
curl http://localhost:8000/api/vertebraai/models | jq '.[] | {id, name, dice}'
```

### `GET /api/vertebraai/models/{model_id}`

Detalle de un Model Card específico.

---

### `GET /api/vertebraai/xrays/{xray_id}/exports/{format}`

Exporta el resultado de un análisis previo.

| Formato | Descripción | Content-Type |
|---------|-------------|--------------|
| `png` | Imagen original | `image/png` |
| `mask` | Máscara de segmentación coloreada | `image/png` |
| `overlay` | Original + máscara superpuesta | `image/png` |
| `report` | Reporte JSON completo | `application/json` |

```bash
# Exportar máscara
curl -o mask.png \
  "http://localhost:8000/api/vertebraai/xrays/550e8400-e29b-41d4-a716-446655440000/exports/mask"

# Exportar reporte completo
curl "http://localhost:8000/api/vertebraai/xrays/550e8400-e29b-41d4-a716-446655440000/exports/report" \
  | jq .metrics
```

---

## Documentación interactiva

La documentación interactiva solo está disponible cuando el servicio se ejecuta con `DEBUG=true`:

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json

El archivo `openapi/vertebraAI.yml` contiene la especificación OpenAPI 3.0.3 completa.

---

## Pruebas

```bash
# Ejecutar todas las pruebas
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ -v --cov=app --cov-report=term-missing

# Solo unitarias
pytest tests/unit/ -v

# Test específico
pytest tests/unit/test_analyze_image_use_case.py -v
```

Las pruebas se ejecutan **sin GPU ni checkpoints reales**: todos los puertos externos están mockeados con `unittest.mock` (ver `tests/conftest.py`).

Archivos de prueba disponibles:

| Archivo | Descripción |
|---------|-------------|
| `tests/unit/test_analyze_image_use_case.py` | Use case de análisis |
| `tests/unit/test_vertebrae_router.py` | Router principal |
| `tests/unit/test_vertebraprompt_adapter.py` | Adapter VertebraPromptBoxRefiner (ganador) |
| `tests/unit/test_unetpp_patches_adapter.py` | Adapter UNet++ con patches |
| `tests/unit/test_segformer_adapter.py` | Adapter Segformer (legacy, no usado en producción) |

---

## Estructura del proyecto

```
services/
├── app/
│   ├── api/v1/
│   │   ├── routers/                      # Endpoints FastAPI
│   │   │   ├── vertebrae.py              # POST /api/vertebraai/xrays
│   │   │   ├── health.py                 # GET  /api/vertebraai/health
│   │   │   ├── export.py                 # GET  /api/vertebraai/xrays/{id}/exports/{format}
│   │   │   └── models.py                 # GET  /api/vertebraai/models[/{id}]
│   │   └── schemas/
│   │       ├── requests.py               # Enums ModelName, ExportFormat
│   │       ├── responses.py              # Schemas Pydantic + analysis_to_response()
│   │       └── model_schemas.py          # Schemas de Model Cards
│   ├── core/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   ├── vertebra.py           # Vertebra, VertebralRegion, build_vertebrae_from_mask
│   │   │   │   ├── analysis.py           # VertebraAnalysis, AnalysisMetrics, VertebralMask
│   │   │   │   └── model_card.py         # ModelCard
│   │   │   └── ports/
│   │   │       ├── model_port.py         # ABC ModelPort, ModelOutput
│   │   │       ├── model_registry_port.py
│   │   │       └── storage_port.py       # ABC StoragePort
│   │   └── use_cases/
│   │       ├── analyze_image.py          # Orquesta validación → predict → postprocesar
│   │       └── export_result.py          # Lectura desde storage + serialización por formato
│   ├── infrastructure/
│   │   └── adapters/
│   │       ├── model/
│   │       │   ├── vertebraprompt_boxrefiner_adapter.py   # ★ activo: pipeline ganador (medsam)
│   │       │   ├── unetpp_patches_adapter.py              # activo: unetpp-patches
│   │       │   ├── medsam_adapter.py                      # legacy (no usado)
│   │       │   └── segformer_adapter.py                   # legacy (no usado)
│   │       ├── registry/
│   │       │   └── in_memory_model_registry.py            # Catálogo de Model Cards
│   │       └── storage/
│   │           └── in_memory_adapter.py                   # OrderedDict LRU (max=100)
│   ├── config.py                         # Settings con pydantic-settings
│   ├── dependencies.py                   # Inyección de dependencias (lru_cache + dispatch dict)
│   ├── main.py                           # FastAPI app + lifespan + CORS + rate limiting
│   └── rate_limit.py                     # SlowAPI limiter (120/min global, 5/min analyze)
├── scripts/
│   └── generate_template_bbox.py
├── tests/
│   ├── conftest.py                       # Fixtures compartidas
│   └── unit/
│       ├── test_analyze_image_use_case.py
│       ├── test_segformer_adapter.py
│       ├── test_unetpp_patches_adapter.py
│       ├── test_vertebrae_router.py
│       └── test_vertebraprompt_adapter.py
├── openapi/
│   └── vertebraAI.yml                    # Especificación OpenAPI 3.0.3
├── docs/
│   └── ARCHITECTURE.md                   # Documentación técnica de arquitectura
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## Decisiones de diseño

**Arquitectura hexagonal (Ports & Adapters)**
El use case `AnalyzeImageUseCase` solo conoce el contrato `ModelPort` (interface). Los adapters concretos se inyectan en `dependencies.py`. Esto permite cambiar de modelo sin tocar el use case y testear sin cargar el modelo real.

**Dispatch pattern para multi-modelo**
El endpoint `POST /xrays` acepta un parámetro `model` (form). En `dependencies.py`, la función `get_model_dispatch()` retorna un `dict[ModelName, ModelPort]` que mapea cada nombre a su adapter. Para añadir un modelo nuevo: registrar el enum, cargar el adapter, mapearlo en el dict. El router queda cerrado a modificación.

**Preprocesamiento dentro del adapter (no en el use case)**
El use case solo valida el formato (PNG o JPEG) y la resolución mínima (32×32 px), y entrega la imagen RGB cruda al adapter. Cada adapter aplica el preprocesamiento exacto que su modelo requiere, evitando divergencias entre el entrenamiento y la inferencia en producción.

**Rate limiting con SlowAPI**
El endpoint de análisis está limitado a 5 requests/minuto por IP para evitar saturación durante la inferencia. Los endpoints de consulta tienen un límite por defecto de 120 requests/minuto. La configuración se controla con `RATE_LIMIT_DEFAULT` y `RATE_LIMIT_ANALYZE`.

**`run_in_executor` en los adapters**
PyTorch en CPU bloquea varios segundos durante la inferencia. Sin `run_in_executor`, el event loop de uvicorn no puede responder otros requests (`/health`, `/export`) durante ese tiempo.

**`@lru_cache` en las dependencias**
Garantiza que los tres adapters activos se carguen una sola vez al primer request, independientemente de cuántos requests simultáneos lleguen.

**`InMemoryStorageAdapter` con límite de 100 entradas**
Para MVP sin base de datos. El límite previene memory leaks. Migrar a Redis o S3 solo requiere implementar un nuevo adapter que cumpla `StoragePort`.

---

## Contribución

1. Crear rama: `git checkout -b feature/nombre-feature`
2. Ejecutar pruebas antes de commit: `pytest tests/ -v`
3. Formatear código (si aplica): `black app/ tests/` y `isort app/ tests/`
4. Abrir Pull Request con descripción del cambio

---

## Licencia

Proyecto académico — Universidad de los Andes, MaIA 2026.
