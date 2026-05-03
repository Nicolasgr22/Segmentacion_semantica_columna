from abc import ABC, abstractmethod
from typing import Optional

from ..entities.analysis import VertebraAnalysis


class StoragePort(ABC):
    @abstractmethod
    async def save(self, analysis: VertebraAnalysis) -> str:
        """Persiste el análisis y retorna el study_id."""
        ...

    @abstractmethod
    async def get(self, study_id: str) -> Optional[VertebraAnalysis]: ...

    @abstractmethod
    async def exists(self, study_id: str) -> bool: ...

    @abstractmethod
    async def delete(self, study_id: str) -> bool: ...
