from __future__ import annotations

import io
import json

import numpy as np
from PIL import Image

from ..domain.ports.storage_port import StoragePort


class StudyNotFoundError(KeyError):
    pass


class ExportResultUseCase:
    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage

    async def execute(self, study_id: str, format: str) -> tuple[bytes, str]:
        analysis = await self._storage.get(study_id)
        if analysis is None:
            raise StudyNotFoundError(study_id)

        if format == "mask":
            return analysis.mask.data, "image/png"

        if format == "png":
            if analysis.original_image_bytes:
                return analysis.original_image_bytes, "image/png"
            return analysis.mask.data, "image/png"

        if format == "overlay":
            return self._build_overlay(analysis), "image/png"

        if format == "report":
            return self._build_report(analysis), "application/json"

        raise ValueError(f"Formato desconocido: {format}")

    def _build_overlay(self, analysis) -> bytes:
        if not analysis.original_image_bytes:
            return analysis.mask.data

        orig = Image.open(io.BytesIO(analysis.original_image_bytes)).convert("RGB")
        mask_img = Image.open(io.BytesIO(analysis.mask.data)).convert("RGB")

        if orig.size != mask_img.size:
            mask_img = mask_img.resize(orig.size, Image.NEAREST)

        mask_arr = np.array(mask_img)
        orig_arr = np.array(orig)
        is_background = (mask_arr == 0).all(axis=2)

        overlay = orig_arr.copy().astype(float)
        overlay[~is_background] = (
            orig_arr[~is_background] * 0.5 + mask_arr[~is_background] * 0.5
        )

        result = Image.fromarray(overlay.astype(np.uint8))
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    def _build_report(self, analysis) -> bytes:
        report = {
            "study_id": analysis.study_id,
            "timestamp": analysis.timestamp.isoformat(),
            "original_filename": analysis.original_filename,
            "metrics": {
                "detected_count": analysis.metrics.detected_count,
                "global_confidence": analysis.metrics.global_confidence,
                "by_region": {
                    region: {
                        "detected_count": rm.detected_count,
                        "expected_count": rm.expected_count,
                        "mean_confidence": rm.mean_confidence,
                        "mean_dice": rm.mean_dice,
                    }
                    for region, rm in analysis.metrics.by_region.items()
                },
                "model_metrics": {
                    "dice": analysis.metrics.model_metrics.dice,
                    "iou": analysis.metrics.model_metrics.iou,
                    "latency_ms": analysis.metrics.model_metrics.latency_ms,
                    "model_version": analysis.metrics.model_metrics.model_version,
                },
            },
            "vertebrae": [
                {
                    "id": v.label,
                    "label": v.label,
                    "region": v.region.value,
                    "detected": v.detected,
                    "confidence": v.confidence,
                    "pixel_count": v.pixel_count,
                    "bounding_box": (
                        {"x_min": v.bounding_box[0], "y_min": v.bounding_box[1],
                         "x_max": v.bounding_box[2], "y_max": v.bounding_box[3]}
                        if v.bounding_box else None
                    ),
                    "centroid": (
                        {"x": v.centroid[0], "y": v.centroid[1]}
                        if v.centroid else None
                    ),
                }
                for v in analysis.vertebrae
            ],
            "processing": {
                "steps": analysis.processing_steps,
                "total_time_ms": analysis.total_time_ms,
            },
        }
        return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
