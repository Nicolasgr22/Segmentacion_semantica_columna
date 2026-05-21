# VertebraAI — Segmentación Semántica de Columna Vertebral

[![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MLflow](https://img.shields.io/badge/MLflow-Databricks-0194E2?logo=mlflow&logoColor=white)](https://dbc-250dea69-0463.cloud.databricks.com)
[![AWS S3](https://img.shields.io/badge/AWS-S3%20Static%20Hosting-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/s3/)
[![Terraform](https://img.shields.io/badge/Terraform-1.5%2B-7B42BC?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-pytest%20≥80%25-4CAF50?logo=pytest&logoColor=white)](services/tests/)
[![License](https://img.shields.io/badge/License-Académica%20Uniandes-004B87)](https://uniandes.edu.co/)
[![MaIA](https://img.shields.io/badge/MaIA-Proyecto%20de%20Grado%202026-004B87)](https://uniandes.edu.co/)

> **Aviso clínico:** Esta herramienta es un apoyo diagnóstico exclusivamente. Toda decisión clínica debe ser revisada por un radiólogo o especialista cualificado.

Proyecto de grado de la **Maestría en Inteligencia Artificial (MaIA)** — Universidad de los Andes, 2026.

Sistema de segmentación semántica de columna vertebral en radiografías que detecta y segmenta **17 vértebras** (T1–T12, L1–L5) sobre el dataset MaIA Scoliosis. Se evaluaron tres familias de modelos — **U-Net / U-Net++**, **U-Net++ con patches** y el pipeline **VertebraPrompt-Net + BoxRefiner + MedSAM** —, siendo este último la estrategia ganadora con Dice estricto de 0.553 y Dice flexible de 0.768.

---

## Tabla de contenidos

- [Descripción del proyecto](#descripción-del-proyecto)
  - [Frontend](#frontend)
  - [Modelos y experimentos](#modelos-y-experimentos)
- [Dependencias](#dependencias)
- [Entorno de ejecución](#entorno-de-ejecución)
- [Pasos de despliegue](#pasos-de-despliegue)
  - [Backend (local)](#backend-local)
  - [Backend (Docker)](#backend-docker)
  - [Frontend (local)](#frontend-local)
  - [AWS (Terraform)](#aws-terraform)
- [Credenciales de ejemplo](#credenciales-de-ejemplo)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Pruebas](#pruebas)
- [Contribución](#contribución)
- [Licencia](#licencia)

---

## Descripción del proyecto

> [!IMPORTANT]
> **Carpetas obligatorias para la entrega del proyecto:**
>
> | Carpeta | Ubicación | Contenido esperado |
> |---------|----------|--------------------|
> | `Notebooks/` | [`notebooks/`](notebooks/) — en este repositorio | Cuadernos con análisis, entrenamiento y pruebas |
> | `Modelos/` | `s3://maia-proyecto-final-models/models/` — **no se encuentra en el repositorio git por restricciones de tamaño** | Archivo(s) del modelo final guardado (`.pt`) |
> | `Datos/` | [`notebooks/medsam_pipeline/results_summary/`](notebooks/medsam_pipeline/results_summary/) — en este repositorio | Muestras o estructura de los datos usados |
>
> Para descargar los modelos: `aws s3 cp s3://maia-proyecto-final-models/models/ ./models/ --recursive --profile vertebraai-models`
> (credenciales de solo lectura disponibles en la sección [Credenciales de ejemplo](#credenciales-de-ejemplo))

Este es un repositorio **monorepo** que agrupa los tres componentes del proyecto bajo un mismo control de versiones: la investigación experimental (notebooks), el servicio de inferencia (backend), la interfaz de usuario (frontend) y la infraestructura (terraform). Cada componente tiene su propio ciclo de vida, dependencias y documentación, pero comparten el mismo dataset, los mismos checkpoints de referencia y la misma nomenclatura de métricas.

| Componente | Carpeta | Tecnología | Propósito |
|------------|---------|------------|-----------|
| Investigación | `notebooks/` | Jupyter + PyTorch | Exploración, entrenamiento y evaluación de modelos |
| Frontend | `frontend/` | React (SPA) | Interfaz web para radiólogos |
| Backend | `services/` | FastAPI + Docker | API REST de inferencia en producción |
| model-pkg | `services/model-pkg` |  | Modelos usados por los servicios |
| Infraestructura | `terraform/` | Terraform + AWS | Despliegue reproducible en la nube |

```
Segmentacion_semantica_columna/
├── deprecated/                             # Código abandonado, conservado por trazabilidad
│   └── package-src/
│       └── medsam/                         # Empaquetamiento el pipeline MedSAM como .whl
│           ├── dist/                       # Artefactos generados (model_medsam-0.1.0.whl)
│           ├── model/                      # Redes, pipeline, entrenamiento y predicción
│           ├── tests/                      # Pruebas unitarias del paquete
│           └── setup.py
├── frontend/                               # Interfaz React (SPA)
│   ├── app.jsx
│   ├── styles.css
│   └── index.html
├── notebooks/                              # Jupyter notebooks de investigación
│   ├── medsam_pipeline/                    # Pipeline MedSAM completo
│   │   ├── checkpoints/                    # Instrucciones para pesos externos
│   │   ├── notebooks/                      # Notebooks 01–07
│   │   └── results_summary/                # Métricas y comparativo de modelos
│   ├── unet/                               # Experimentos U-Net
│   ├── unet++/                             # Experimentos U-Net++
│   ├── 01-recoleccion-preparacion-datos.ipynb
│   └── prueba inicial multiclase preliminar SAM.ipynb
├── services/                               # Microservicio de inferencia (FastAPI)
│   ├── app/
│   │   ├── api/v1/routers/                 # Endpoints REST
│   │   ├── core/
│   │   │   ├── domain/                     # Entidades y puertos (ABCs)
│   │   │   └── use_cases/                  # Lógica de negocio
│   │   └── infrastructure/adapters/        # MedSAM + almacenamiento
│   ├── docs/ARCHITECTURE.md                # Documentación técnica detallada
│   ├── openapi/vertebraAI.yml              # Especificación OpenAPI 3.0.3
│   ├── tests/                              # Pruebas unitarias (sin GPU)
│   ├── Dockerfile
│   ├── README.md                           # Guía del servicio
│   └── requirements.txt
├── terraform/                              # Infraestructura como código (AWS)
│   ├── iam.tf                              # Usuarios y roles IAM
│   ├── outputs.tf
│   ├── s3_frontend.tf                      # Hosting estático del frontend
│   └── s3_state.tf                         # Backend remoto de Terraform
└── .gitignore
```

### Frontend

Interfaz React de página única desplegada en **AWS S3 Static Website Hosting**.

- Subida de radiografías en formato PNG
- Visualización de máscara de segmentación superpuesta
- Panel de ajuste de opacidad y visualización por vértebra
- Comparación simultánea de múltiples modelos

> Para instrucciones de desarrollo local, estructura de componentes y despliegue del frontend, ver:
> - [`frontend/README.md`](frontend/README.md) — guía completa del frontend

### Modelos y experimentos

El entrenamiento y la experimentación se gestionan con **MLflow** sobre **Databricks Community Edition**.

| Parámetro | Valor |
|-----------|-------|
| `DATABRICKS_HOST` | `https://dbc-250dea69-0463.cloud.databricks.com` |
| `MLFLOW_EXPERIMENT_NAME` | `/Users/anferiro@gmail.com/columna-vertebral-medsam` |
| Pipeline final | `VertebraPrompt-Net + BoxRefiner + MedSAM ViT-B` |
| Dataset | MaIA Scoliosis — radiografías AP y lateral |

#### Notebooks de investigación

| Notebook | Descripción |
|----------|-------------|
| [`01-recoleccion-preparacion-datos.ipynb`](notebooks/01-recoleccion-preparacion-datos.ipynb) | Recolección, exploración y preparación del dataset |
| [`prueba inicial multiclase preliminar SAM.ipynb`](notebooks/prueba%20inicial%20multiclase%20preliminar%20SAM.ipynb) | Prueba de concepto inicial con SAM multiclase |
| [`unet/`](notebooks/unet/) | Experimentos con U-Net base y variantes robustas |
| [`unet++/`](notebooks/unet++/) | Experimentos con U-Net++ y enfoque por patches |
| [`medsam_pipeline/notebooks/`](notebooks/medsam_pipeline/notebooks/) | Pipeline completo MedSAM: baseline → NN-SAM → estrategia ganadora |

La evolución del proyecto sigue esta trayectoria:

```
Preparación de datos
  → Baseline binario
  → U-Net / U-Net++ multiclase
  → Detección automática de cajas (CenterNetLite)
  → NN-SAM + MedSAM como base robusta
  → VertebraPrompt + BoxRefiner  ← estrategia ganadora
```

Los pesos `.pt` no se versionan por tamaño. Ver [`notebooks/medsam_pipeline/checkpoints/README.md`](notebooks/medsam_pipeline/checkpoints/) para la correspondencia entre notebooks y checkpoints.

---

## Dependencias
### Declaradas (desde el manifest)

- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*

**Grupo de dependencias:**
- **Web API & Serving:** `fastapi`, `uvicorn`, `python-multipart` — handle HTTP requests and image uploads for the segmentation service.
- **Deep Learning:** `torch`, `torchvision`, `transformers` — load and execute PyTorch segmentation models.
- **Image Processing & Augmentation:** `opencv-python-headless`, `Pillow`, `albumentations`, `numpy` — preprocess, augment, and manipulate radiograph images.
- **Data Validation & Configuration:** `pydantic`, `pydantic-settings` — enforce API contracts and manage runtime settings.
- **Testing:** `pytest`, `pytest-asyncio`, `httpx`, `pytest-cov` — run async tests, exercise HTTP endpoints, and measure coverage.
- **Static File Serving (Dev):** `serve` — npm dev dependency for local static asset serving.

---

## Entorno de ejecución

| Componente | Versión mínima |
|------------|----------------|
| Python | 3.14+ |
| [uv](https://github.com/astral-sh/uv) | última estable |
| Node.js / npx | 18+ |
| Docker | 24+ (para producción) |
| [AWS CLI](https://aws.amazon.com/cli/) | 2+ (solo despliegue en AWS) |
| RAM | ~4 GB (CPU) |
| VRAM | 6 GB+ (GPU opcional) |

Los checkpoints del modelo (~2 GB) no se incluyen en el repositorio ya que por el tamaño no se pueden subir a github. Descárgarlos desde Drive antes de arrancar:
[https://drive.google.com/drive/folders/1kf8aPQV06_A_4ROW5TwkgXL0XxcgF5KU](https://drive.google.com/drive/folders/1kf8aPQV06_A_4ROW5TwkgXL0XxcgF5KU)

>[!IMPORTANT] Los modelos fueron entrenados en colab y sus archivos pasados en la carpeta de servicios. Se recrearon algunos pipelines para generar el empaquetamiento desde alli, sin embargo se abandono la idea por el tiempo de procesamiento y la cantidad de trabajo asociado, sin embargo se puede ver el trabajo realizado con las primeras versiones del modelo en la carpeta deprecated/package-src

---

## Pasos de despliegue

### Backend (local)

1. Crear y activar entorno virtual
```bash
uv venv .venv                      # Si no existe el ambiente virtual de python
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows
```

2. Entrar al directorio del servicio
```bash
cd services
```

3. Instalar PyTorch CPU-only (cambiar URL para CUDA)
```bash
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

4. Instalar dependencias
```bash
uv pip install -r requirements.txt
```

5. Configurar variables de entorno (rutas a checkpoints)
```bash
cp .env.example .env
```

6. Arrancar
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Backend (Docker)

```bash
cd services
docker build -t vertebraai .
docker run -p 8000:8000 \
  -v /ruta/local/model-pkg:/app/model-pkg:ro \
  -e MODEL_DEVICE=cpu \
  vertebraai
```

### Frontend (local)

```bash
cd frontend
npx http-server -p 5500 --cors
```

Abrir http://localhost:5500/ en el navegador. Requiere el backend corriendo en `localhost:8000`.

> Abrir el archivo directamente como `file://` no funciona porque el navegador bloquea las peticiones fetch a localhost por política de origen cruzado.

### AWS (Terraform)

La infraestructura completa se provisiona con Terraform sobre **AWS us-east-1**. Un solo `terraform apply` levanta todos los recursos y sube el frontend y el backend.

#### Recursos creados

| Recurso | Nombre | Descripción |
|---------|--------|-------------|
| S3 Bucket (frontend) | `anferiro-maia-proyecto-final-frontend` | Hosting estático del frontend |
| S3 Bucket (state) | `anferiro-maia-proyecto-final-state` | Backend remoto del estado de Terraform |
| CloudFront | distribución única | HTTPS, caché, enruta `/api/*` al EC2 y `/*` al S3 |
| EC2 Spot | `t3.large` (8 GB RAM / 2 vCPU) | Corre el contenedor FastAPI + MedSAM |
| ECR | `vertebraai` | Registro Docker privado de la imagen del servicio |
| IAM User | `maia-proyecto-user` | Usuario de despliegue |
| IAM Role | `maia-proyecto-grado` | Role con permisos del proyecto |

> **Spot instance:** sin EIP fija — si AWS reclama el spot, un nuevo `terraform apply` levanta otra instancia y CloudFront apunta a la nueva IP automáticamente.

#### Pre-requisitos

```bash
aws configure        # AWS CLI con credenciales del usuario IAM
terraform -version   # >= 1.5
docker info          # para build y push de la imagen al ECR
```

#### Paso 1 — Primera vez: crear el bucket de estado

```bash
cd terraform

cp terraform.tfvars.example terraform.tfvars   # revisar variables si es necesario

terraform init
terraform apply -target=aws_s3_bucket.tfstate
```

Descomentar el bloque `backend "s3"` en `providers.tf` y migrar el estado local a S3:

```bash
terraform init -migrate-state
```

#### Paso 2 — Despliegue completo

```bash
terraform plan
terraform apply
```

El apply ejecuta en orden:
1. Crea S3, ECR, Security Groups y distribución CloudFront
2. Construye la imagen Docker y la sube al ECR
3. Lanza la instancia EC2 Spot que arranca el contenedor vía `user_data`
4. Genera `frontend/config.js` con `window.BACKEND_URL = ""` (ruta relativa vía CloudFront)
5. Sincroniza `frontend/` al bucket S3 e invalida la caché de CloudFront

#### Outputs útiles

```bash
terraform output frontend_cloudfront_url   # URL HTTPS del frontend
terraform output service_health_check      # curl para verificar el backend
terraform output ecr_repository_url        # registry para push manual de imagen
terraform output service_public_ip         # IP directa del EC2 (debug)
```

#### Re-desplegar tras cambios

```bash
# Solo el frontend (cambios en frontend/)
terraform apply -target=null_resource.deploy_frontend

# Solo el backend (cambios en services/)
terraform apply -target=null_resource.deploy_image

# Forzar re-build de imagen aunque el hash no cambie (ej: modelos nuevos)
terraform taint null_resource.deploy_image && terraform apply
```

> **`config.js`** es generado automáticamente por Terraform — no editar a mano ni commitear. Está en `.gitignore`.

---

## Credenciales de ejemplo

Los checkpoints de **MedSAM ViT-B** y **UNet++ EfficientNet-B7** usados en producción están disponibles en un bucket S3 privado.

| Campo | Valor |
|-------|-------|
| Bucket | `s3://maia-proyecto-final-models` |
| Ruta modelos | `s3://maia-proyecto-final-models/models/` |
| Región | `us-east-1` |
| AWS Access Key ID | `AKIAZQ3DPKVWU4CKQKNG` |
| AWS Secret Access Key | *(ver nota abajo — se comparte por canal seguro)* |

```bash
# Configurar credenciales de solo lectura
aws configure --profile vertebraai-models
# AWS Access Key ID: AKIAZQ3DPKVWU4CKQKNG
# AWS Secret Access Key: <solicitar por canal seguro>
# Default region: us-east-1

# Descargar todos los modelos
aws s3 cp s3://maia-proyecto-final-models/models/ ./models/ --recursive --profile vertebraai-models

# Verificar contenido
aws s3 ls s3://maia-proyecto-final-models/models/ --recursive --profile vertebraai-models
```

> Las credenciales tienen permisos de **solo lectura** sobre este bucket. No pueden escribir ni eliminar archivos.

> **Secret Key:** no se publica en este repositorio. Si necesitas el `AWS Secret Access Key` para descargar los modelos, escríbenos a [af.rinconr1@uniandes.edu.co](mailto:af.rinconr1@uniandes.edu.co) y te lo enviamos por correo.

---

## Ejemplos de uso

### Analizar una radiografía

```bash
curl -X POST http://localhost:8000/api/vertebraai/xrays \
  -F "file=@radiografia.png;type=image/png" \
  -F "model=medsam" \
  | jq '{study_id, detected: .metrics.detected_count, dice: .metrics.model_metrics.dice}'
```

### Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/vertebraai/xrays` | Analizar radiografía PNG |
| `GET` | `/api/vertebraai/health` | Estado del servicio y modelo |
| `GET` | `/api/vertebraai/models` | Catálogo de modelos con métricas |
| `GET` | `/api/vertebraai/xrays/{id}/exports/{format}` | Exportar resultado (`png`, `mask`, `overlay`, `report`) |
| `GET` | `/api/docs` | Swagger UI interactivo |

Especificación completa: [`services/openapi/vertebraAI.yml`](services/openapi/vertebraAI.yml)

> Para ejemplos de respuesta, variables de entorno, arquitectura interna y guía de desarrollo del backend, ver la documentación detallada:
> - [`services/README.md`](services/README.md) — guía completa del servicio
> - [`services/docs/ARCHITECTURE.md`](services/docs/ARCHITECTURE.md) — diseño de capas, puertos y adaptadores

### Pruebas

Las pruebas se ejecutan **sin GPU ni checkpoints reales** — todos los puertos externos están mockeados.

```bash
cd services

# Todas las pruebas
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ -v --cov=app --cov-report=term-missing

# Solo unitarias
pytest tests/unit/ -v
```

Cobertura objetivo: ≥ 80 %

---

## Contribución

1. Crear rama: `git checkout -b feature/nombre-feature`
2. Ejecutar pruebas antes de commit: `pytest tests/ -v`
3. Formatear código: `black app/ tests/` y `isort app/ tests/`
4. Abrir Pull Request con descripción del cambio y referencia al notebook o issue relacionado

---

## Licencia

Proyecto académico — Universidad de los Andes, MaIA 2026. Uso restringido a fines educativos e investigativos.
