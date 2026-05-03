from __future__ import annotations

from collections import OrderedDict
from typing import Optional

from app.core.domain.entities.analysis import VertebraAnalysis
from app.core.domain.ports.storage_port import StoragePort


class InMemoryStorageAdapter(StoragePort):
    def __init__(self, max_entries: int = 100) -> None:
        self._store: OrderedDict[str, VertebraAnalysis] = OrderedDict()
        self._max_entries = max_entries

    async def save(self, analysis: VertebraAnalysis) -> str:
        if len(self._store) >= self._max_entries:
            self._store.popitem(last=False)
        self._store[analysis.study_id] = analysis
        return analysis.study_id

    async def get(self, study_id: str) -> Optional[VertebraAnalysis]:
        return self._store.get(study_id)

    async def exists(self, study_id: str) -> bool:
        return study_id in self._store

    async def delete(self, study_id: str) -> bool:
        if study_id in self._store:
            del self._store[study_id]
            return True
        return False
