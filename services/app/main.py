import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.routers import auth, export, health, models, vertebrae
from app.config import settings
from app.dependencies import get_model_adapter
from app.rate_limit import limiter

# Cap absoluto al tamaño de imagen que Pillow va a decodificar. Por default Pillow
# solo emite warning >89M px; sin límite habilita "decompression bombs".
# 50 MP = 7000×7000 ≈ cubre cualquier radiografía clínica realista (~3000×4000).
Image.MAX_IMAGE_PIXELS = 50_000_000

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
    # Docs interactivas (Swagger/ReDoc/OpenAPI) deshabilitadas en producción
    # para evitar enumeración de endpoints. Se exponen solo si DEBUG=True.
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # `allow_credentials=True` con `allow_origins=["*"]` rompe CORS:
    # el spec exige una origin específica cuando hay credenciales. La API
    # no usa cookies ni auth — todo va por multipart sin credentials —
    # así que lo dejamos en False y mantenemos el wildcard utilizable.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vertebrae.router, prefix="/api/vertebraai")
app.include_router(health.router, prefix="/api/vertebraai")
app.include_router(export.router, prefix="/api/vertebraai")
app.include_router(models.router, prefix="/api/vertebraai")
app.include_router(auth.router, prefix="/api/vertebraai")
