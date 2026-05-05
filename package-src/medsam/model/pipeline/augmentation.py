"""
Pipelines de data augmentation con albumentations.

Las transformaciones se aplican simétricamente a imagen y máscara.
Diseñadas para radiografías de columna vertebral: se evitan flips
verticales (invertirían la anatomía) y transformaciones que destruyan
la estructura espinal (shear extremo, perspectiva agresiva).
"""

from __future__ import annotations

import albumentations as A


def build_train_transform(p_flip: float = 0.5) -> A.Compose:
    """
    Augmentations para entrenamiento.

    Conserva:
      - HorizontalFlip   → simula variación de postura L/R
      - ShiftScaleRotate → inclinaciones leves del paciente (±15°)
      - BrightnessContrast → diferencias entre equipos RX
      - GaussianBlur     → artefactos de adquisición leves
      - ElasticTransform → deformaciones anatómicas leves
    """
    return A.Compose(
        [
            A.HorizontalFlip(p=p_flip),
            A.ShiftScaleRotate(
                shift_limit=0.05,
                scale_limit=0.1,
                rotate_limit=15,
                border_mode=0,
                p=0.5,
            ),
            A.RandomBrightnessContrast(
                brightness_limit=0.15,
                contrast_limit=0.15,
                p=0.5,
            ),
            A.GaussianBlur(blur_limit=(3, 5), p=0.3),
            A.ElasticTransform(
                alpha=1,
                sigma=50,
                p=0.3,
            ),
        ],
        additional_targets={"mask": "mask"},
    )


def build_val_transform() -> A.Compose:
    """Sin augmentation para validación y test."""
    return A.Compose([], additional_targets={"mask": "mask"})
