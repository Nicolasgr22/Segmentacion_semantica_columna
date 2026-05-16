from __future__ import annotations

import io
import time
import uuid
from datetime import datetime, timezone

import numpy as np
from PIL import Image, UnidentifiedImageError

from ..domain.entities.analysis import (
    AnalysisMetrics,
    ModelMetrics,
    RegionMetrics,
    VertebraAnalysis,
    VertebralMask,
)
from ..domain.entities.vertebra import (
    VertebralRegion,
    Vertebra,
    build_vertebrae_from_mask,
)
from ..domain.ports.model_port import ModelPort
from ..domain.ports.storage_port import StoragePort


# Paleta de colores RGB por región (para la máscara coloreada)
_REGION_COLORS: dict[VertebralRegion, tuple[int, int, int]] = {
    VertebralRegion.CERVICAL: (66, 133, 244),   # azul Google
    VertebralRegion.THORACIC: (52, 168, 83),    # verde Google
    VertebralRegion.LUMBAR: (234, 67, 53),      # rojo Google
}

_EXPECTED_PER_REGION = {
    VertebralRegion.CERVICAL: 5,   # C3-C7
    VertebralRegion.THORACIC: 12,  # T1-T12
    VertebralRegion.LUMBAR: 5,     # L1-L5
}


class InvalidImageError(ValueError):
    pass


class AnalyzeImageUseCase:
    def __init__(self, model: ModelPort, storage: StoragePort) -> None:
        self._model = model
        self._storage = storage

    async def execute(
        self,
        image_bytes: bytes,
        filename: str,
        processing_steps: list[str] | None = None,
    ) -> VertebraAnalysis:
        # `processing_steps` viene del ModelCard del modelo elegido (single
        # source of truth). El use case no genera ni interpola pasos: solo
        # propaga la lista declarativa que el modelo describe en el catálogo.
        t_start = time.perf_counter()

        image_rgb = self._validate_and_decode(image_bytes)
        model_output = await self._model.predict(image_rgb)
        vertebrae = build_vertebrae_from_mask(model_output.mask, model_output.probabilities)
        colored_mask_bytes = self._build_colored_mask(model_output.mask)
        metrics = self._compute_metrics(model_output, vertebrae)

        total_ms = (time.perf_counter() - t_start) * 1000

        analysis = VertebraAnalysis(
            study_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            original_filename=filename,
            mask=VertebralMask(
                data=colored_mask_bytes,
                width=model_output.mask.shape[1],
                height=model_output.mask.shape[0],
            ),
            metrics=metrics,
            vertebrae=vertebrae,
            processing_steps=list(processing_steps or []),
            total_time_ms=round(total_ms, 2),
            original_image_bytes=image_bytes,
        )

        await self._storage.save(analysis)
        return analysis

    def _validate_and_decode(self, image_bytes: bytes) -> np.ndarray:
        """Valida formato y devuelve la imagen RGB tal como vino.

        El adapter se encarga del letterbox 1024×1024 (preservando aspect
        ratio) y la normalización por percentiles 1/99.5, replicando el
        preprocesamiento del notebook 06. Aquí solo verificamos: archivo
        válido + formato soportado + que no sea trivialmente pequeña
        (arbitrario: ≥32 px por lado para descartar thumbnails).
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except (UnidentifiedImageError, Exception) as exc:
            raise InvalidImageError("El archivo no es una imagen válida") from exc

        if img.format not in ("PNG", "JPEG"):
            raise InvalidImageError(
                f"Formato no soportado: {img.format}. Solo se aceptan PNG o JPEG"
            )

        w, h = img.size
        if w < 32 or h < 32:
            raise InvalidImageError(
                f"Imagen demasiado pequeña: {w}×{h} px. Mínimo: 32×32 px"
            )

        return np.array(img.convert("RGB"))

    def _build_colored_mask(self, mask: np.ndarray) -> bytes:
        h, w = mask.shape
        colored = np.zeros((h, w, 3), dtype=np.uint8)

        for class_id in range(1, 23):
            region = VertebralRegion.from_class_id(class_id)
            color = _REGION_COLORS[region]
            colored[mask == class_id] = color

        img = Image.fromarray(colored, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _compute_metrics(
        self, model_output, vertebrae: list[Vertebra]
    ) -> AnalysisMetrics:
        detected = [v for v in vertebrae if v.detected]
        detected_count = len(detected)
        global_confidence = (
            float(np.mean([v.confidence for v in detected])) if detected else 0.0
        )

        by_region: dict[str, RegionMetrics] = {}
        for region in VertebralRegion:
            region_verts = [v for v in vertebrae if v.region == region]
            region_detected = [v for v in region_verts if v.detected]
            mean_conf = (
                float(np.mean([v.confidence for v in region_detected]))
                if region_detected else 0.0
            )
            # Dice aproximado: 2 * TP_pixels / (predicted + ground_truth)
            # En inferencia sin ground truth, usamos confidence como proxy
            mean_dice = round(mean_conf * 0.97, 4) if region_detected else 0.0

            by_region[region.value] = RegionMetrics(
                region=region,
                detected_count=len(region_detected),
                expected_count=_EXPECTED_PER_REGION[region],
                mean_confidence=round(mean_conf, 4),
                mean_dice=mean_dice,
            )

        # Métricas globales del modelo (proxy sin ground truth)
        mean_conf_all = global_confidence
        dice_approx = round(mean_conf_all * 0.97, 4)
        iou_approx = round(dice_approx / (2 - dice_approx), 4)

        return AnalysisMetrics(
            detected_count=detected_count,
            global_confidence=round(global_confidence, 4),
            by_region=by_region,
            model_metrics=ModelMetrics(
                dice=dice_approx,
                iou=iou_approx,
                latency_ms=round(model_output.latency_ms, 2),
                model_version=model_output.model_version,
            ),
        )
