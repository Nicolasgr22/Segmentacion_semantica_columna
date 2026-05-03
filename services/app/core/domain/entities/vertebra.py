from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np


ID2LABEL: dict[int, str] = {
    0: "background",
    1: "C7", 2: "C6", 3: "C5", 4: "C4", 5: "C3",
    6: "T1", 7: "T2", 8: "T3", 9: "T4", 10: "T5", 11: "T6",
    12: "T7", 13: "T8", 14: "T9", 15: "T10", 16: "T11", 17: "T12",
    18: "L1", 19: "L2", 20: "L3", 21: "L4", 22: "L5",
}

LABEL2ID: dict[str, int] = {v: k for k, v in ID2LABEL.items()}


class VertebralRegion(str, Enum):
    CERVICAL = "cervical"
    THORACIC = "thoracic"
    LUMBAR = "lumbar"

    @staticmethod
    def from_class_id(class_id: int) -> "VertebralRegion":
        if 1 <= class_id <= 5:
            return VertebralRegion.CERVICAL
        if 6 <= class_id <= 17:
            return VertebralRegion.THORACIC
        if 18 <= class_id <= 22:
            return VertebralRegion.LUMBAR
        raise ValueError(f"class_id {class_id} no corresponde a ninguna región vertebral")


@dataclass
class Vertebra:
    class_id: int
    label: str
    region: VertebralRegion
    detected: bool
    confidence: float
    pixel_count: int
    bounding_box: Optional[tuple[int, int, int, int]]
    centroid: Optional[tuple[float, float]]


def build_vertebrae_from_mask(
    mask: np.ndarray,
    probabilities: np.ndarray,
) -> list[Vertebra]:
    """Construye la lista de 22 vértebras a partir de la máscara y probabilidades.

    Args:
        mask: uint8 array (H, W) con valores 0-22.
        probabilities: float32 array (N_CLASSES, H, W) con probabilidades softmax.

    Returns:
        Lista de exactamente 22 Vertebra (detected=False si no aparece en la máscara).
    """
    vertebrae: list[Vertebra] = []

    for class_id in range(1, 23):
        label = ID2LABEL[class_id]
        region = VertebralRegion.from_class_id(class_id)
        pixel_mask = mask == class_id
        pixel_count = int(pixel_mask.sum())

        if pixel_count == 0:
            vertebrae.append(Vertebra(
                class_id=class_id,
                label=label,
                region=region,
                detected=False,
                confidence=0.0,
                pixel_count=0,
                bounding_box=None,
                centroid=None,
            ))
            continue

        # Confianza media sobre píxeles de esta clase
        confidence = float(probabilities[class_id][pixel_mask].mean())

        # Bounding box
        rows, cols = np.where(pixel_mask)
        y_min, y_max = int(rows.min()), int(rows.max())
        x_min, x_max = int(cols.min()), int(cols.max())

        # Centroide
        cx = float(cols.mean())
        cy = float(rows.mean())

        vertebrae.append(Vertebra(
            class_id=class_id,
            label=label,
            region=region,
            detected=True,
            confidence=round(confidence, 4),
            pixel_count=pixel_count,
            bounding_box=(x_min, y_min, x_max, y_max),
            centroid=(round(cx, 2), round(cy, 2)),
        ))

    return vertebrae
