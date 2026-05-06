"""
Dataset y DataLoaders para fine-tuning de MedSAM.

SpineMedSAMDataset sigue el contrato del notebook 04-medsam:
  - Cada muestra devuelve imagen SAM-preprocesada, máscara binaria,
    bounding box transformado e información de tamaño original.
  - SAM trabaja muestra a muestra (no batch real); collate_fn devuelve lista.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from .augmentation import build_train_transform, build_val_transform
from .preprocessing import bbox_from_mask, load_mask_binary, load_rgb_image


class SpineMedSAMDataset(Dataset):
    def __init__(
        self,
        df: pd.DataFrame,
        sam_model,
        box_pad: int = 10,
        augment: bool = False,
    ) -> None:
        from segment_anything.utils.transforms import ResizeLongestSide

        self.df = df.reset_index(drop=True).copy()
        self.box_pad = box_pad
        self.transform = ResizeLongestSide(sam_model.image_encoder.img_size)
        self.aug = build_train_transform() if augment else build_val_transform()

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> dict:
        row = self.df.iloc[idx]
        image = load_rgb_image(Path(row["ruta_img"]))
        mask = load_mask_binary(Path(row["ruta_mask_id"]))
        original_size = image.shape[:2]

        if len(self.aug.transforms) > 0:
            augmented = self.aug(image=image, mask=mask)
            image, mask = augmented["image"], augmented["mask"]

        box = bbox_from_mask(mask, pad=self.box_pad)
        image_resized = self.transform.apply_image(image)
        resized_size = image_resized.shape[:2]

        image_torch = (
            torch.as_tensor(image_resized).permute(2, 0, 1).contiguous().float()
        )
        box_resized = self.transform.apply_boxes(box[None, :], original_size)[0]

        mask_resized = cv2.resize(
            mask.astype(np.uint8),
            (resized_size[1], resized_size[0]),
            interpolation=cv2.INTER_NEAREST,
        )

        return {
            "image": image_torch,
            "mask": torch.tensor(mask_resized[None, :, :]).float(),
            "box": torch.tensor(box_resized).float(),
            "original_size": torch.tensor(original_size),
            "resized_size": torch.tensor(resized_size),
            "id": row["patient_id"],
            "image_path": str(row["ruta_img"]),
            "mask_path": str(row["ruta_mask_id"]),
        }


def _collate_fn(batch: list) -> list:
    # SAM no soporta batch real; devolvemos lista de muestras
    return batch


def make_dataloaders(
    splits_csv: Path | str,
    sam_model,
    batch_size: int = 2,
    num_workers: int = 0,
    box_pad: int = 10,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    """
    Lee splits.csv y construye DataLoaders para train, val y test.

    Returns:
        (train_loader, val_loader, test_loader)
    """
    df = pd.read_csv(splits_csv)

    df_train = df[df["split"] == "train"].copy()
    df_val = df[df["split"] == "val"].copy()
    df_test = df[df["split"] == "test"].copy()

    # Augmentation desactivada: con ~103 imágenes de train las transformaciones
    # geométricas agresivas (flip, rotate, elastic) generan anatomía irreal
    # y reducen el Dice ~3% respecto al notebook original (0.85 vs 0.88)
    train_ds = SpineMedSAMDataset(df_train, sam_model, box_pad=box_pad, augment=False)
    val_ds = SpineMedSAMDataset(df_val, sam_model, box_pad=box_pad, augment=False)
    test_ds = SpineMedSAMDataset(df_test, sam_model, box_pad=box_pad, augment=False)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        collate_fn=_collate_fn,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        collate_fn=_collate_fn,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        collate_fn=_collate_fn,
    )
    return train_loader, val_loader, test_loader
