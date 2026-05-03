from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class ModelOutput:
    mask: np.ndarray        # uint8 (H, W), valores 0-22
    probabilities: np.ndarray  # float32 (N_CLASSES, H, W)
    latency_ms: float
    model_version: str


class ModelPort(ABC):
    @abstractmethod
    async def predict(self, image: np.ndarray) -> ModelOutput:
        """Recibe imagen RGB uint8 (H, W, 3) ya preprocesada. Retorna ModelOutput."""
        ...

    @abstractmethod
    def is_loaded(self) -> bool: ...

    @abstractmethod
    def get_model_version(self) -> str: ...
