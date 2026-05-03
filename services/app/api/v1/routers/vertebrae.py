import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.v1.schemas.responses import AnalyzeResponse, ErrorResponse, analysis_to_response
from app.config import settings
from app.core.use_cases.analyze_image import AnalyzeImageUseCase, InvalidImageError
from app.dependencies import get_analyze_use_case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/xrays", tags=["xrays"])


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Imagen inválida"},
        413: {"model": ErrorResponse, "description": "Imagen demasiado grande"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
        504: {"model": ErrorResponse, "description": "Timeout en inferencia"},
    },
    summary="Crear análisis de radiografía de columna vertebral",
    description=(
        "Recibe una imagen PNG de radiografía de columna, aplica preprocesamiento "
        "(CLAHE + letterbox 512×512) y retorna la segmentación de vértebras con "
        "métricas de confianza por región."
    ),
)
async def create_analysis(
    file: UploadFile = File(..., description="Imagen PNG, resolución mínima 512×512 px"),
    use_case: AnalyzeImageUseCase = Depends(get_analyze_use_case),
) -> AnalyzeResponse:
    if file.content_type not in ("image/png", "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan imágenes en formato PNG",
        )

    image_bytes = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"La imagen supera el límite de {settings.max_upload_mb} MB",
        )

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
