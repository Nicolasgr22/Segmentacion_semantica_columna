from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from app.api.v1.schemas.requests import ModelName
from app.config import settings
from app.core.domain.entities.user import AuthUser
from app.core.domain.ports.auth_port import AuthPort
from app.core.domain.ports.model_port import ModelPort
from app.core.domain.ports.model_registry_port import ModelRegistryPort
from app.core.domain.ports.storage_port import StoragePort
from app.core.use_cases.analyze_image import AnalyzeImageUseCase
from app.core.use_cases.auth_use_case import (
    InvalidCredentialsError,
    TokenValidationError,
    ValidateTokenUseCase,
)
from app.core.use_cases.export_result import ExportResultUseCase
from app.infrastructure.adapters.auth.cognito_auth_adapter import CognitoAuthAdapter
from app.infrastructure.adapters.model.progressive_unet_adapter import (
    ProgressiveUNetBinaryAdapter,
)
from app.infrastructure.adapters.model.unetpp_patches_adapter import (
    UnetPlusPlusPatchesAdapter,
)
from app.infrastructure.adapters.model.vertebraprompt_boxrefiner_adapter import (
    VertebraPromptBoxRefinerAdapter,
)
from app.infrastructure.adapters.registry.in_memory_model_registry import (
    InMemoryModelRegistry,
)
from app.infrastructure.adapters.storage.in_memory_adapter import InMemoryStorageAdapter


@lru_cache(maxsize=1)
def get_model_adapter() -> VertebraPromptBoxRefinerAdapter:
    adapter = VertebraPromptBoxRefinerAdapter(device=settings.model_device)
    adapter.load_model(
        prompt_net_checkpoint=settings.medsam_prompt_net_checkpoint,
        box_refiner_checkpoint=settings.medsam_box_refiner_checkpoint,
        sam_base_checkpoint=settings.medsam_sam_checkpoint,
        medsam_finetuned_checkpoint=settings.medsam_finetuned_checkpoint,
    )
    return adapter


@lru_cache(maxsize=1)
def get_progressive_unet_adapter() -> ProgressiveUNetBinaryAdapter:
    adapter = ProgressiveUNetBinaryAdapter(device=settings.model_device)
    adapter.load_model(checkpoint=settings.progressive_unet_checkpoint)
    return adapter


@lru_cache(maxsize=1)
def get_unetpp_patches_adapter() -> UnetPlusPlusPatchesAdapter:
    adapter = UnetPlusPlusPatchesAdapter(device=settings.model_device)
    adapter.load_model(checkpoint=settings.unetpp_patches_checkpoint)
    return adapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> InMemoryStorageAdapter:
    return InMemoryStorageAdapter(max_entries=100)


@lru_cache(maxsize=1)
def get_model_registry() -> InMemoryModelRegistry:
    return InMemoryModelRegistry()


def get_model_port(model: VertebraPromptBoxRefinerAdapter = Depends(get_model_adapter)) -> ModelPort:
    return model


def get_model_registry_port(
    registry: InMemoryModelRegistry = Depends(get_model_registry),
) -> ModelRegistryPort:
    return registry


def get_model_dispatch(
    medsam: ModelPort = Depends(get_model_adapter),
    progressive_unet: ModelPort = Depends(get_progressive_unet_adapter),
    unetpp_patches: ModelPort = Depends(get_unetpp_patches_adapter),
) -> dict[ModelName, ModelPort]:
    """Mapea cada ModelName al adapter cargado.

    El nombre `medsam` se conserva como alias público del pipeline ganador
    (VertebraPrompt + BoxRefiner + MedSAM). Para añadir un nuevo modelo:
      1. Registrar su ModelCard en InMemoryModelRegistry.
      2. Cargar su adapter aquí y mapearlo en este dict.
    """
    return {
        ModelName.MEDSAM: medsam,
        ModelName.PROGRESSIVE_UNET_BINARY: progressive_unet,
        ModelName.UNETPP_PATCHES: unetpp_patches,
    }


def get_analyze_use_case(
    model: ModelPort = Depends(get_model_adapter),
    storage: StoragePort = Depends(get_storage_adapter),
) -> AnalyzeImageUseCase:
    return AnalyzeImageUseCase(model=model, storage=storage)


def get_export_use_case(
    storage: StoragePort = Depends(get_storage_adapter),
) -> ExportResultUseCase:
    return ExportResultUseCase(storage=storage)


@lru_cache(maxsize=1)
def get_auth_adapter() -> CognitoAuthAdapter:
    return CognitoAuthAdapter()


def get_auth_port(adapter: CognitoAuthAdapter = Depends(get_auth_adapter)) -> AuthPort:
    return adapter


_DUMMY_USER = AuthUser(email="dev@local", name="dev", sub="local-dev")


async def get_current_user(
    request: Request,
    auth_port: AuthPort = Depends(get_auth_port),
) -> AuthUser:
    """Extrae y valida el Bearer token del header Authorization.

    Si auth_enabled=False (desarrollo local sin Cognito), devuelve un usuario
    ficticio para que los endpoints protegidos funcionen sin credenciales.
    """
    if not settings.auth_enabled:
        return _DUMMY_USER

    auth_header: str = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Se requiere autenticación Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.removeprefix("Bearer ").strip()
    use_case = ValidateTokenUseCase(auth=auth_port)
    try:
        return await use_case.execute(token)
    except (TokenValidationError, InvalidCredentialsError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
