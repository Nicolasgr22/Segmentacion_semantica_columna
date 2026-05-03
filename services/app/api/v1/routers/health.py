import time

from fastapi import APIRouter, Depends

from app.api.v1.schemas.responses import HealthResponse
from app.core.domain.ports.model_port import ModelPort
from app.dependencies import get_model_port

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Estado del servicio y del modelo",
)
async def health_check(model: ModelPort = Depends(get_model_port)) -> HealthResponse:
    return HealthResponse(
        status="ok" if model.is_loaded() else "degraded",
        model_version=model.get_model_version(),
        model_loaded=model.is_loaded(),
        uptime_s=round(time.time() - _start_time, 2),
    )
