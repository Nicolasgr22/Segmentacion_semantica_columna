import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import export, health, models, vertebrae
from app.config import settings
from app.dependencies import get_model_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Cargando pipeline VertebraPrompt + BoxRefiner + MedSAM...")
    try:
        get_model_adapter()
        logger.info("Pipeline cargado correctamente.")
    except Exception:
        logger.exception("Error al cargar el modelo. El servicio arrancará en modo degradado.")
    yield
    logger.info("Servicio detenido.")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Servicio de segmentación automática de columna vertebral en radiografías. "
        "Pipeline ganador: VertebraPrompt-Net (propuestas de cajas con identidad "
        "anatómica T1–L5) → BoxRefiner (ajuste local) → MedSAM ViT-B fine-tuned "
        "(decoder + último bloque del encoder ajustados). "
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
app.include_router(models.router, prefix="/api/vertebraai")
