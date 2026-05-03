from functools import lru_cache

from fastapi import Depends

from app.config import settings
from app.core.domain.ports.model_port import ModelPort
from app.core.domain.ports.storage_port import StoragePort
from app.core.use_cases.analyze_image import AnalyzeImageUseCase
from app.core.use_cases.export_result import ExportResultUseCase
from app.infrastructure.adapters.model.segformer_adapter import SegFormerAdapter
from app.infrastructure.adapters.storage.in_memory_adapter import InMemoryStorageAdapter


@lru_cache(maxsize=1)
def get_model_adapter() -> SegFormerAdapter:
    adapter = SegFormerAdapter(
        device=settings.model_device,
        n_classes=settings.n_classes,
    )
    adapter.load_model(
        checkpoint_path=settings.model_checkpoint,
        local_path=settings.model_local_path,
    )
    return adapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> InMemoryStorageAdapter:
    return InMemoryStorageAdapter(max_entries=100)


def get_model_port(model: SegFormerAdapter = Depends(get_model_adapter)) -> ModelPort:
    return model


def get_analyze_use_case(
    model: ModelPort = Depends(get_model_adapter),
    storage: StoragePort = Depends(get_storage_adapter),
) -> AnalyzeImageUseCase:
    return AnalyzeImageUseCase(model=model, storage=storage)


def get_export_use_case(
    storage: StoragePort = Depends(get_storage_adapter),
) -> ExportResultUseCase:
    return ExportResultUseCase(storage=storage)
