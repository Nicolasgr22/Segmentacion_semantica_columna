from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.core.domain.entities.analysis import VertebraAnalysis


class BoundingBoxResponse(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class CentroidResponse(BaseModel):
    x: float
    y: float


class VertebraResponse(BaseModel):
    id: str
    label: str
    region: str
    detected: bool
    confidence: float
    pixel_count: int
    bounding_box: Optional[BoundingBoxResponse] = None
    centroid: Optional[CentroidResponse] = None


class RegionMetricsResponse(BaseModel):
    detected_count: int
    expected_count: int
    mean_confidence: float
    mean_dice: float


class ModelMetricsResponse(BaseModel):
    dice: float
    iou: float
    latency_ms: float
    model_version: str


class AnalysisMetricsResponse(BaseModel):
    detected_count: int
    confidence: float
    by_region: dict[str, RegionMetricsResponse]
    model_metrics: ModelMetricsResponse


class MaskResponse(BaseModel):
    data: str
    format: str
    dimensions: dict[str, int]


class ProcessingResponse(BaseModel):
    steps: list[str]
    total_time_ms: float


class AnalyzeResponse(BaseModel):
    study_id: str
    timestamp: str
    mask: MaskResponse
    metrics: AnalysisMetricsResponse
    vertebrae: list[VertebraResponse]
    processing: ProcessingResponse


class HealthResponse(BaseModel):
    status: str
    model_version: str
    model_loaded: bool
    uptime_s: float


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str


def analysis_to_response(analysis: VertebraAnalysis) -> AnalyzeResponse:
    vertebrae_resp = []
    for v in analysis.vertebrae:
        bbox = None
        if v.bounding_box:
            bbox = BoundingBoxResponse(
                x_min=v.bounding_box[0],
                y_min=v.bounding_box[1],
                x_max=v.bounding_box[2],
                y_max=v.bounding_box[3],
            )
        centroid = None
        if v.centroid:
            centroid = CentroidResponse(x=v.centroid[0], y=v.centroid[1])

        vertebrae_resp.append(VertebraResponse(
            id=v.label,
            label=v.label,
            region=v.region.value,
            detected=v.detected,
            confidence=v.confidence,
            pixel_count=v.pixel_count,
            bounding_box=bbox,
            centroid=centroid,
        ))

    by_region_resp = {
        region: RegionMetricsResponse(
            detected_count=rm.detected_count,
            expected_count=rm.expected_count,
            mean_confidence=rm.mean_confidence,
            mean_dice=rm.mean_dice,
        )
        for region, rm in analysis.metrics.by_region.items()
    }

    return AnalyzeResponse(
        study_id=analysis.study_id,
        timestamp=analysis.timestamp.isoformat(),
        mask=MaskResponse(
            data=analysis.mask.to_base64(),
            format=analysis.mask.format,
            dimensions={"width": analysis.mask.width, "height": analysis.mask.height},
        ),
        metrics=AnalysisMetricsResponse(
            detected_count=analysis.metrics.detected_count,
            confidence=analysis.metrics.global_confidence,
            by_region=by_region_resp,
            model_metrics=ModelMetricsResponse(
                dice=analysis.metrics.model_metrics.dice,
                iou=analysis.metrics.model_metrics.iou,
                latency_ms=analysis.metrics.model_metrics.latency_ms,
                model_version=analysis.metrics.model_metrics.model_version,
            ),
        ),
        vertebrae=vertebrae_resp,
        processing=ProcessingResponse(
            steps=analysis.processing_steps,
            total_time_ms=analysis.total_time_ms,
        ),
    )
