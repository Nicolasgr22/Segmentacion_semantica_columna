from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ExperimentMetric:
    name: str
    value: float
    description: str


@dataclass(frozen=True)
class ModelCard:
    id: str
    display_name: str
    description: str
    architecture: str
    task: str
    classes: list[str]
    checkpoints: list[str]
    metrics: list[ExperimentMetric]
    dataset: str
    notebook: str
    status: str = "active"
    extra: dict[str, str] = field(default_factory=dict)
    # Pasos del pipeline del modelo. Source of truth: cada modelo declara los
    # suyos en el registry; /models los expone, /xrays los retorna en el
    # campo `processing.steps` del análisis, y el frontend los muestra en la
    # animación durante la inferencia.
    processing_steps: list[str] = field(default_factory=list)
