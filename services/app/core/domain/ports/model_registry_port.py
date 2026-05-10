from abc import ABC, abstractmethod
from typing import Optional

from ..entities.model_card import ModelCard


class ModelRegistryPort(ABC):
    @abstractmethod
    async def list_models(self) -> list[ModelCard]: ...

    @abstractmethod
    async def get_model(self, model_id: str) -> Optional[ModelCard]: ...
