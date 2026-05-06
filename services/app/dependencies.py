from functools import lru_cache

from fastapi import Depends

from app.api.v1.schemas.requests import ModelName
from app.config import settings
from app.core.domain.ports.model_port import ModelPort
from app.core.domain.ports.storage_port import StoragePort
from app.core.use_cases.analyze_image import AnalyzeImageUseCase
from app.core.use_cases.export_result import ExportResultUseCase
from app.infrastructure.adapters.model.medsam_adapter import MedSAMAdapter
from app.infrastructure.adapters.storage.in_memory_adapter import InMemoryStorageAdapter


@lru_cache(maxsize=1)
def get_model_adapter() -> MedSAMAdapter:
    adapter = MedSAMAdapter(device=settings.model_device)
    adapter.load_model(
        sam_checkpoint=settings.medsam_sam_checkpoint,
        finetuned_checkpoint=settings.medsam_finetuned_checkpoint,
    )
    return adapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> InMemoryStorageAdapter:
    return InMemoryStorageAdapter(max_entries=100)


def get_model_port(model: MedSAMAdapter = Depends(get_model_adapter)) -> ModelPort:
    return model


def get_model_registry(
    medsam: ModelPort = Depends(get_model_adapter),
) -> dict[ModelName, ModelPort]:
    """Mapea cada ModelName al adapter cargado con su checkpoint de config.

    Para activar un nuevo modelo:
      1. Añadir sus settings en config.py
      2. Instanciar y cargar el adapter aquí
      3. Agregarlo al dict
    """
    registry: dict[ModelName, ModelPort] = {
        ModelName.MEDSAM: medsam,
    }

    # SegFormer-B2 — activar cuando se requiera segmentación multi-clase (23 clases)
    # from app.infrastructure.adapters.model.segformer_adapter import SegFormerAdapter
    # segformer = SegFormerAdapter(device=settings.model_device, n_classes=23)
    # segformer.load_model(checkpoint_path="nvidia/mit-b2", local_path="")
    # registry[ModelName.SEGFORMER_B2] = segformer

    return registry


def get_analyze_use_case(
    model: ModelPort = Depends(get_model_adapter),
    storage: StoragePort = Depends(get_storage_adapter),
) -> AnalyzeImageUseCase:
    return AnalyzeImageUseCase(model=model, storage=storage)


def get_export_use_case(
    storage: StoragePort = Depends(get_storage_adapter),
) -> ExportResultUseCase:
    return ExportResultUseCase(storage=storage)
