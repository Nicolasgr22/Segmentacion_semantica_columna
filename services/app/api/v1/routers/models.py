from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.model_schemas import (
    ModelCardResponse,
    ModelsListResponse,
    model_card_to_response,
)
from app.core.domain.ports.model_registry_port import ModelRegistryPort
from app.dependencies import get_model_registry_port

router = APIRouter(tags=["models"])


@router.get(
    "/models",
    response_model=ModelsListResponse,
    summary="Listar modelos disponibles y sus métricas de experimento",
    description=(
        "Retorna el catálogo de modelos publicados por el servicio junto con las "
        "métricas obtenidas durante la evaluación experimental (Dice/IoU estricto y "
        "flexible) y la trazabilidad de checkpoints y notebooks."
    ),
)
async def list_models(
    registry: ModelRegistryPort = Depends(get_model_registry_port),
) -> ModelsListResponse:
    cards = await registry.list_models()
    items = [model_card_to_response(c) for c in cards]
    return ModelsListResponse(count=len(items), items=items)


@router.get(
    "/models/{model_id}",
    response_model=ModelCardResponse,
    summary="Detalle de un modelo por id",
    responses={404: {"description": "Modelo no encontrado"}},
)
async def get_model(
    model_id: str,
    registry: ModelRegistryPort = Depends(get_model_registry_port),
) -> ModelCardResponse:
    card = await registry.get_model(model_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Modelo '{model_id}' no encontrado")
    return model_card_to_response(card)
