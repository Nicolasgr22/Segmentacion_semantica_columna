import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import export, health, vertebrae
from app.config import settings
from app.dependencies import get_model_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Cargando modelo SegFormer-B2...")
    try:
        get_model_adapter()
        logger.info("Modelo cargado correctamente.")
    except Exception:
        logger.exception("Error al cargar el modelo. El servicio arrancará en modo degradado.")
    yield
    logger.info("Servicio detenido.")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Servicio de segmentación automática de columna vertebral en radiografías. "
        "Utiliza SegFormer-B2 (nvidia/mit-b2) fine-tuneado sobre el dataset MaIA Scoliosis "
        "para detectar y segmentar 22 vértebras (C3-C7, T1-T12, L1-L5). "
        "\n\n**Nota clínica:** Esta herramienta es un apoyo diagnóstico. "
        "Toda decisión clínica debe ser revisada por un especialista."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vertebrae.router, prefix="/api/vertebraai")
app.include_router(health.router, prefix="/api/vertebraai")
app.include_router(export.router, prefix="/api/vertebraai")
