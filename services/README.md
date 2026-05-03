# VertebraAI — Servicio de Segmentación de Columna Vertebral

Microservicio de análisis automático de radiografías de columna vertebral desarrollado como parte del proyecto de grado de la **Maestría en Inteligencia Artificial (MaIA)** de la Universidad de los Andes.

Utiliza el modelo **SegFormer-B2** (`nvidia/mit-b2`) fine-tuneado sobre el dataset MaIA Scoliosis para segmentar 22 vértebras (C3–C7, T1–T12, L1–L5) en radiografías AP y laterales en formato PNG.

> **Aviso clínico:** Esta herramienta es un apoyo diagnóstico exclusivamente. Toda decisión clínica debe ser revisada por un radiólogo o especialista cualificado.

---

## Arquitectura

VertebraAI implementa **arquitectura hexagonal (puertos y adaptadores)** que desacopla la lógica de negocio de los frameworks y dependencias externas.

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│                    multipart/form-data PNG                       │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼───────────────────────────────────────┐
│              ADAPTADORES DE ENTRADA (api/v1/routers/)            │
│        vertebrae.py     health.py     export.py                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Schemas Pydantic
┌──────────────────────────▼───────────────────────────────────────┐
│                    CASOS DE USO (core/use_cases/)                │
│         AnalyzeImageUseCase       ExportResultUseCase            │
│                   │                        │                     │
│          ┌────────▼────────┐   ┌───────────▼────────┐           │
│          │   ModelPort     │   │   StoragePort      │ ← PUERTOS  │
│          └────────┬────────┘   └───────────┬────────┘           │
└───────────────────┼────────────────────────┼────────────────────┘
                    │                        │
┌───────────────────▼────────────────────────▼────────────────────┐
│              ADAPTADORES DE SALIDA (infrastructure/)             │
│    SegFormerAdapter (HuggingFace)    InMemoryStorageAdapter      │
└──────────────────────────────────────────────────────────────────┘
```

### Capas

| Capa | Ruta | Responsabilidad |
|------|------|-----------------|
| Dominio | `app/core/domain/` | Entidades, puertos (ABCs), lógica pura |
| Casos de uso | `app/core/use_cases/` | Orquestación del flujo de negocio |
| Adaptadores entrada | `app/api/v1/` | Routers FastAPI, schemas Pydantic |
| Adaptadores salida | `app/infrastructure/` | SegFormer, almacenamiento en memoria |

---

## Prerrequisitos

- Python 3.11+
- ~4 GB RAM (inferencia CPU) o GPU con 6 GB+ VRAM para CUDA
- Conexión a internet para descargar el checkpoint de HuggingFace (primera ejecución)
- (Opcional) Checkpoint fine-tuneado local en `MODEL_LOCAL_PATH`

---

## Instalación

```bash
# 1. Clonar el repositorio y entrar al directorio del servicio
git clone <repo-url>
cd columna/services

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# 3. Instalar PyTorch CPU-only (más liviano; cambiar URL para GPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración
```

---

## Variables de entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MODEL_CHECKPOINT` | Checkpoint de HuggingFace Hub | `nvidia/mit-b2` |
| `MODEL_LOCAL_PATH` | Ruta a checkpoint fine-tuneado local (vacío = usar Hub) | `` |
| `MODEL_DEVICE` | Dispositivo de inferencia: `cpu`, `cuda`, `mps` | `cpu` |
| `MAX_UPLOAD_MB` | Tamaño máximo de imagen aceptada (MB) | `50` |
| `INFERENCE_TIMEOUT_S` | Timeout de inferencia (segundos) | `60` |
| `CORS_ORIGINS` | Orígenes permitidos (JSON array) | `["http://localhost:3000","http://localhost:5500"]` |
| `DEBUG` | Modo debug de FastAPI | `false` |
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

# Ejecutar con checkpoint local montado
docker run -p 8000:8000 \
  -v /ruta/al/modelo:/opt/models \
  -e MODEL_LOCAL_PATH=/opt/models/segformer-b2-finetuned \
  -e MODEL_DEVICE=cpu \
  vertebraai
```

Al arrancar, el servicio carga el modelo en memoria. El primer inicio puede tardar 30–60 segundos dependiendo de la conexión y el hardware.

---

## Endpoints

### `POST /api/vertebraai/xrays`

Crea un nuevo análisis de radiografía de columna vertebral. Retorna `201 Created`.

```bash
curl -X POST http://localhost:8000/api/vertebraai/xrays \
  -F "file=@radiografia.png;type=image/png" \
  | jq '{study_id, detected: .metrics.detected_count, confidence: .metrics.confidence}'
```

**Entrada:** `multipart/form-data` con campo `file` (PNG, mínimo 512×512 px)

**Salida:** JSON con `study_id`, máscara en base64, métricas y lista de 22 vértebras.

---

### `GET /api/vertebraai/health`

Estado del servicio y del modelo.

```bash
curl http://localhost:8000/api/vertebraai/health | jq .
# {"status": "ok", "model_version": "nvidia/mit-b2", "model_loaded": true, "uptime_s": 120.3}
```

---

### `GET /api/vertebraai/xrays/{analysis_id}/exports/{format}`

Exporta el resultado de un análisis previo.

| Formato | Descripción | Content-Type |
|---------|-------------|--------------|
| `png` | Imagen original redimensionada | `image/png` |
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

Con el servicio corriendo:

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json

El archivo `openapi/vertebraAI.yml` contiene la especificación completa OpenAPI 3.0.3.

---

## Pruebas

```bash
# Ejecutar todas las pruebas
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ -v --cov=app --cov-report=term-missing

# Solo pruebas unitarias
pytest tests/unit/ -v

# Prueba específica
pytest tests/unit/test_analyze_image_use_case.py -v
```

Las pruebas están diseñadas para ejecutarse **sin GPU ni modelo descargado**: todos los adapters externos son mockeados con `unittest.mock`.

Cobertura objetivo: ≥ 80%

---

## Estructura del proyecto

```
services/
├── app/
│   ├── api/v1/
│   │   ├── routers/          # Endpoints FastAPI
│   │   │   ├── vertebrae.py  # POST /api/vertebrae/analyze
│   │   │   ├── health.py     # GET  /api/health
│   │   │   └── export.py     # GET  /api/export/{study_id}/{format}
│   │   └── schemas/
│   │       ├── requests.py   # Enum ExportFormat
│   │       └── responses.py  # Schemas Pydantic + mapper analysis_to_response()
│   ├── core/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   ├── vertebra.py   # Vertebra, VertebralRegion, ID2LABEL, build_vertebrae_from_mask()
│   │   │   │   └── analysis.py   # VertebraAnalysis, AnalysisMetrics, VertebralMask
│   │   │   └── ports/
│   │   │       ├── model_port.py    # ABC ModelPort, ModelOutput
│   │   │       └── storage_port.py  # ABC StoragePort
│   │   └── use_cases/
│   │       ├── analyze_image.py  # AnalyzeImageUseCase (orquesta el flujo completo)
│   │       └── export_result.py  # ExportResultUseCase
│   ├── infrastructure/
│   │   └── adapters/
│   │       ├── model/
│   │       │   └── segformer_adapter.py  # SegFormerAdapter (HuggingFace)
│   │       └── storage/
│   │           └── in_memory_adapter.py  # InMemoryStorageAdapter (OrderedDict LRU)
│   ├── config.py       # Settings con pydantic-settings
│   ├── dependencies.py # Inyección de dependencias (lru_cache singletons)
│   └── main.py         # FastAPI app + lifespan + CORS
├── tests/
│   ├── conftest.py     # Fixtures compartidas (mocks, imágenes dummy)
│   └── unit/
│       ├── test_analyze_image_use_case.py  # 8 casos
│       ├── test_vertebrae_router.py        # 7 casos
│       └── test_segformer_adapter.py       # 5 casos
├── openapi/
│   └── vertebraAI.yml  # Especificación OpenAPI 3.0.3 completa
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## Decisiones de diseño

**CLAHE en el caso de uso, no en el adapter**
El preprocesamiento CLAHE es parte de la lógica de negocio (definida durante el entrenamiento en `augment.py`). Vivirlo en el use case permite testarlo sin el modelo real y garantiza que cualquier cambio de arquitectura de modelo no lo afecte.

**`run_in_executor` en el adapter**
PyTorch en CPU bloquea ~3 segundos durante la inferencia. Sin `run_in_executor`, el event loop de uvicorn no puede responder otros requests (`/health`, `/export`) durante ese tiempo.

**`@lru_cache` en las dependencias**
Garantiza que el modelo (~500 MB en memoria) se cargue una sola vez al arrancar, independientemente de cuántos requests simultáneos lleguen.

**`InMemoryStorageAdapter` con límite de 100 entradas**
Para MVP sin base de datos. El límite previene memory leaks. Migrar a Redis o S3 solo requiere implementar un nuevo adapter que cumpla `StoragePort`.

---

## Contribución

1. Crear rama: `git checkout -b feature/nombre-feature`
2. Ejecutar pruebas antes de commit: `pytest tests/ -v`
3. Formatear código: `black app/ tests/` y `isort app/ tests/`
4. Abrir Pull Request con descripción del cambio

---

## Licencia

Proyecto académico — Universidad de los Andes, MaIA 2026.
