from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .vertebra import Vertebra, VertebralRegion


@dataclass
class VertebralMask:
    data: bytes
    width: int
    height: int
    format: str = "PNG"

    def to_base64(self) -> str:
        return base64.b64encode(self.data).decode("utf-8")


@dataclass
class RegionMetrics:
    region: VertebralRegion
    detected_count: int
    expected_count: int
    mean_confidence: float
    mean_dice: float


@dataclass
class ModelMetrics:
    dice: float
    iou: float
    latency_ms: float
    model_version: str


@dataclass
class AnalysisMetrics:
    detected_count: int
    global_confidence: float
    by_region: dict[str, RegionMetrics]
    model_metrics: ModelMetrics


@dataclass
class VertebraAnalysis:
    study_id: str
    timestamp: datetime
    original_filename: str
    mask: VertebralMask
    metrics: AnalysisMetrics
    vertebrae: list[Vertebra]
    processing_steps: list[str]
    total_time_ms: float
    original_image_bytes: Optional[bytes] = field(default=None, repr=False)
