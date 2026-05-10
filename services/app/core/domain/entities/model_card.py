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
