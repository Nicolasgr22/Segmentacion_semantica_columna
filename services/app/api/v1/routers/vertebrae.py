import asyncio
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.api.v1.schemas.requests import ModelName
from app.api.v1.schemas.responses import AnalyzeResponse, ErrorResponse, analysis_to_response
from app.config import settings
from app.core.domain.ports.model_port import ModelPort
from app.core.domain.ports.storage_port import StoragePort
from app.core.use_cases.analyze_image import AnalyzeImageUseCase, InvalidImageError
from app.dependencies import get_model_dispatch, get_storage_adapter
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/xrays", tags=["xrays"])


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Imagen inválida o modelo no disponible"},
        413: {"model": ErrorResponse, "description": "Imagen demasiado grande"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
        504: {"model": ErrorResponse, "description": "Timeout en inferencia"},
    },
    summary="Crear análisis de radiografía de columna vertebral",
    description=(
        "Recibe una imagen (PNG o JPEG) de radiografía de columna, aplica letterbox a "
        "1024×1024 (preservando aspect ratio) y normalización por percentiles 1/99.5; "
        "retorna la segmentación de vértebras T1–L5 con métricas de confianza por región."
    ),
)
@limiter.limit(settings.rate_limit_analyze)
async def create_analysis(
    request: Request,
    file: UploadFile = File(..., description="Imagen PNG o JPEG"),
    model: ModelName = Form(
        default=ModelName.MEDSAM,
        description="Modelo de segmentación a utilizar",
    ),
    model_registry: dict[ModelName, ModelPort] = Depends(get_model_dispatch),
    storage: StoragePort = Depends(get_storage_adapter),
) -> AnalyzeResponse:
    accepted_types = ("image/png", "image/jpeg", "image/jpg", "application/octet-stream")
    if file.content_type not in accepted_types:
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan imágenes en formato PNG o JPEG",
        )

    model_port = model_registry.get(model)
    if model_port is None:
        raise HTTPException(
            status_code=400,
            detail=f"Modelo '{model}' no está disponible actualmente",
        )

    image_bytes = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"La imagen supera el límite de {settings.max_upload_mb} MB",
        )

    use_case = AnalyzeImageUseCase(model=model_port, storage=storage)

    try:
        analysis = await asyncio.wait_for(
            use_case.execute(image_bytes, file.filename or "unknown.png"),
            timeout=settings.inference_timeout_s,
        )
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout: la inferencia superó {settings.inference_timeout_s}s",
        )
    except Exception:
        logger.exception("Error inesperado en análisis de vértebras")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    return analysis_to_response(analysis)
