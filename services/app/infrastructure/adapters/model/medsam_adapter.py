from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from app.core.domain.ports.model_port import ModelOutput, ModelPort

_executor = ThreadPoolExecutor(max_workers=2)

# Clase de columna vertebral en la máscara binaria MedSAM
_SPINE_CLASS_ID = 1


class MedSAMAdapter(ModelPort):
    """Adapter para MedSAM fine-tuneado sobre el dataset MaIA Scoliosis.

    Produce máscaras binarias (0=fondo, 1=columna). El adapter las proyecta
    al formato ModelOutput de 2 clases para ser compatible con ModelPort.
    """

    def __init__(self, device: str = "cpu") -> None:
        self._device = device
        self._predictor = None
        self._loaded = False
        self._model_version = "not-loaded"

    def load_model(self, sam_checkpoint: str, finetuned_checkpoint: str) -> None:
        from model.predict import MedSAMPredictor  # requiere model_medsam instalado

        self._predictor = MedSAMPredictor.from_checkpoint(
            checkpoint_path=sam_checkpoint,
            finetuned_weights=finetuned_checkpoint,
            device=self._device,
        )
        self._loaded = True
        self._model_version = Path(finetuned_checkpoint).stem

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_version(self) -> str:
        return self._model_version

    async def predict(self, image: np.ndarray) -> ModelOutput:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_predict, image)

    def _sync_predict(self, image: np.ndarray) -> ModelOutput:
        t0 = time.perf_counter()

        proba = self._predictor.predict_proba(image)  # float32 (H, W), valores [0, 1]
        mask = (proba >= 0.5).astype(np.uint8) * _SPINE_CLASS_ID

        # Convierte a formato de 2 clases compatible con ModelPort
        h, w = mask.shape
        probabilities = np.zeros((2, h, w), dtype=np.float32)
        probabilities[0] = 1.0 - proba
        probabilities[1] = proba

        latency_ms = (time.perf_counter() - t0) * 1000
        return ModelOutput(
            mask=mask,
            probabilities=probabilities,
            latency_ms=round(latency_ms, 2),
            model_version=self._model_version,
        )
