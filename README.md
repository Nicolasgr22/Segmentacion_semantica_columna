# VertebraAI — Segmentación Semántica de Columna Vertebral

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-SegFormer--B2-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/nvidia/mit-b2)
[![MLflow](https://img.shields.io/badge/MLflow-Databricks-0194E2?logo=mlflow&logoColor=white)](https://dbc-250dea69-0463.cloud.databricks.com)
[![AWS S3](https://img.shields.io/badge/AWS-S3%20Static%20Hosting-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/s3/)
[![Terraform](https://img.shields.io/badge/Terraform-1.5%2B-7B42BC?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Académica%20Uniandes-004B87)](https://uniandes.edu.co/)
[![MaIA](https://img.shields.io/badge/MaIA-Proyecto%20de%20Grado%202026-004B87)](https://uniandes.edu.co/)

> **Aviso clínico:** Esta herramienta es un apoyo diagnóstico exclusivamente. Toda decisión clínica debe ser revisada por un radiólogo o especialista cualificado.

Proyecto de grado de la **Maestría en Inteligencia Artificial (MaIA)** — Universidad de los Andes, 2026.

Sistema completo de segmentación semántica de columna vertebral en radiografías, que detecta y segmenta **22 vértebras** (C3–C7, T1–T12, L1–L5) usando el modelo **SegFormer-B2** fine-tuneado sobre el dataset MaIA Scoliosis.

---

## Tabla de contenidos

- [Arquitectura general](#arquitectura-general)
- [Experimento en Databricks / MLflow](#experimento-en-databricks--mlflow)
- [Notebooks](#notebooks)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Inicio rápido](#inicio-rápido)
- [Frontend](#frontend)
- [Infraestructura (Terraform + AWS)](#infraestructura-terraform--aws)
- [Contribución](#contribución)

---

## Arquitectura general

```
┌─────────────────────────────────────────────────────────────┐
│              USUARIO / RADIÓLOGO                            │
└────────────────────────┬────────────────────────────────────┘
                         │  PNG radiografía
┌────────────────────────▼────────────────────────────────────┐
│           FRONTEND — React (S3 Static Hosting)              │
│       anferiro-maia-proyecto-final-frontend.s3-website      │
└────────────────────────┬────────────────────────────────────┘
                         │  multipart/form-data
┌────────────────────────▼────────────────────────────────────┐
│         BACKEND — FastAPI + SegFormer-B2 (Docker)           │
│   POST /api/vertebraai/xrays   GET /api/vertebraai/health   │
│         Arquitectura Hexagonal (Puertos y Adaptadores)      │
└────────────────────────┬────────────────────────────────────┘
                         │  entrenamiento / experimentos
┌────────────────────────▼────────────────────────────────────┐
│         DATABRICKS — MLflow Experiment Tracking             │
│   Host:  https://dbc-250dea69-0463.cloud.databricks.com     │
│   Exp:   /Users/anferiro@gmail.com/columna-vertebral-medsam │
└─────────────────────────────────────────────────────────────┘
```

---

## Experimento en Databricks / MLflow

El entrenamiento y la experimentación del modelo se gestionan con **MLflow** sobre **Databricks Community Edition**.

| Parámetro | Valor |
|-----------|-------|
| `DATABRICKS_HOST` | `https://dbc-250dea69-0463.cloud.databricks.com` |
| `MLFLOW_EXPERIMENT_NAME` | `/Users/anferiro@gmail.com/columna-vertebral-medsam` |
| Modelo base | `nvidia/mit-b2` (SegFormer-B2) |
| Dataset | MaIA Scoliosis — radiografías AP y lateral |
| Clases | 22 vértebras (C3–C7, T1–T12, L1–L5) + fondo |

### Configurar el entorno para MLflow

```bash
export DATABRICKS_HOST=https://dbc-250dea69-0463.cloud.databricks.com
export DATABRICKS_TOKEN=<tu-token-personal-de-acceso>
export MLFLOW_EXPERIMENT_NAME=/Users/anferiro@gmail.com/columna-vertebral-medsam
```

```python
import mlflow

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Users/anferiro@gmail.com/columna-vertebral-medsam")

with mlflow.start_run():
    mlflow.log_param("model", "nvidia/mit-b2")
    mlflow.log_param("num_classes", 23)
    mlflow.log_metric("val_miou", 0.82)
```

---

## Notebooks

Los notebooks están en la carpeta [`notebooks/`](notebooks/) y documentan las fases de investigación y desarrollo:

| Notebook | Descripción |
|----------|-------------|
| [`01-recoleccion-preparacion-datos.ipynb`](notebooks/01-recoleccion-preparacion-datos.ipynb) | Recolección, exploración y preparación del dataset MaIA Scoliosis |
| [`prueba inicial multiclase preliminar SAM.ipynb`](notebooks/prueba%20inicial%20multiclase%20preliminar%20SAM.ipynb) | Prueba de concepto inicial con SAM (Segment Anything Model) multiclase |

> Los notebooks están diseñados para ejecutarse en Databricks o localmente con las dependencias del entorno de entrenamiento.

---

## Estructura del repositorio

```
Segmentacion_semantica_columna/
├── notebooks/                         # Jupyter notebooks de experimentación
│   ├── 01-recoleccion-preparacion-datos.ipynb
│   └── prueba inicial multiclase preliminar SAM.ipynb
├── services/                          # Microservicio de inferencia (FastAPI)
│   ├── app/
│   │   ├── api/v1/routers/            # Endpoints REST
│   │   ├── core/
│   │   │   ├── domain/                # Entidades y puertos (ABCs)
│   │   │   └── use_cases/             # Lógica de negocio
│   │   └── infrastructure/adapters/   # SegFormer + almacenamiento
│   ├── openapi/vertebraAI.yml         # Especificación OpenAPI 3.0.3
│   ├── tests/                         # Pruebas unitarias (sin GPU)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md                      # Documentación detallada del servicio
├── frontend/                          # Interfaz React (SPA)
│   ├── VertebraAI.html
│   ├── app.jsx
│   ├── styles.css
│   ├── tweaks-panel.jsx
│   └── vertebra-assets.jsx
├── terraform/                         # Infraestructura como código (AWS)
│   ├── providers.tf
│   ├── variables.tf
│   ├── s3_frontend.tf                 # Hosting estático del frontend
│   ├── s3_state.tf                    # Backend remoto de Terraform
│   ├── iam.tf                         # Usuarios y roles IAM
│   └── outputs.tf
└── .gitignore
```

---

## Inicio rápido

### Prerrequisitos

- Python 3.11+
- Docker (recomendado para producción)
- ~4 GB RAM (CPU) o GPU con 6 GB+ VRAM

### Servicio de inferencia (local)

```bash
# 1. Entrar al directorio del servicio
cd services

# 2. Crear entorno virtual
python -m venv .venv && source .venv/bin/activate

# 3. Instalar dependencias
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env

# 5. Arrancar
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Con Docker

```bash
cd services
docker build -t vertebraai .
docker run -p 8000:8000 vertebraai
```

### Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/vertebraai/xrays` | Analizar radiografía PNG |
| `GET` | `/api/vertebraai/health` | Estado del servicio |
| `GET` | `/api/vertebraai/xrays/{id}/exports/{format}` | Exportar resultado (`png`, `mask`, `overlay`, `report`) |
| `GET` | `/api/docs` | Swagger UI interactivo |

```bash
# Ejemplo de análisis
curl -X POST http://localhost:8000/api/vertebraai/xrays \
  -F "file=@radiografia.png;type=image/png" | jq .metrics
```

---

## Frontend

Interfaz React de página única desplegada en **AWS S3 Static Website Hosting**.

- Subida de radiografías en formato PNG
- Visualización de máscara de segmentación superpuesta
- Panel de ajustes por vértebra

Para desarrollo local abrir directamente `frontend/VertebraAI.html` en un navegador con el servicio corriendo en `localhost:8000`.

---

## Infraestructura (Terraform + AWS)

La infraestructura se gestiona con Terraform sobre **AWS us-east-1**.

| Recurso | Nombre | Descripción |
|---------|--------|-------------|
| S3 Bucket (frontend) | `anferiro-maia-proyecto-final-frontend` | Hosting estático del frontend |
| S3 Bucket (state) | `anferiro-maia-proyecto-final-state` | Backend remoto de Terraform |
| IAM User | `maia-proyecto-user` | Usuario de despliegue |
| IAM Role | `maia-proyecto-grado` | Role con permisos del proyecto |

```bash
cd terraform

# Primera vez: crear bucket de estado
terraform init
terraform apply -target=aws_s3_bucket.tfstate

# Despliegue completo
terraform plan
terraform apply
```

> Después del primer apply, descomentar el bloque `backend "s3"` en `providers.tf` y ejecutar `terraform init -migrate-state`.

---

## Pruebas

```bash
cd services

# Todas las pruebas (sin GPU ni modelo descargado)
pytest tests/ -v

# Con cobertura
pytest tests/ -v --cov=app --cov-report=term-missing
```

Cobertura objetivo: ≥ 80%

---

## Contribución

1. Crear rama: `git checkout -b feature/nombre-feature`
2. Ejecutar pruebas: `pytest tests/ -v`
3. Formatear: `black app/ tests/` y `isort app/ tests/`
4. Abrir Pull Request con descripción del cambio

---

## Licencia

Proyecto académico — Universidad de los Andes, MaIA 2026. Uso restringido a fines educativos e investigativos.
