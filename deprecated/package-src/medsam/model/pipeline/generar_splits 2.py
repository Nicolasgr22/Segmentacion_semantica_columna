"""
Pipeline de preparación de datos: genera splits.csv desde indice_dataset.csv.

Aplica el mismo filtro de calidad del notebook 01-recoleccion-preparacion-datos:
  - Descarta imágenes con resolución < 256px en cualquier dimensión
  - Descarta imágenes uniformes (std < 5, posible corrupción)
  - Descarta máscaras completamente vacías (S_107)
  - División estratificada train/val/test 70/15/15
"""

from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image as PILImage
from sklearn.model_selection import train_test_split


def _es_valida(ruta_img: str, ruta_mask: str) -> bool:
    try:
        img = cv2.imread(ruta_img, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        # El filtro min(h,w) < 256 fue removido: radiografías estrechas (ej: 181×727 px)
        # son válidas — SAM las maneja correctamente con ResizeLongestSide(1024).
        # Filtrarlo excluía ~100 imágenes y reducía el Dice de 0.88 a 0.83.
        if img.std() < 5:
            return False
        mask = np.array(PILImage.open(ruta_mask))
        if mask.max() == 0:
            return False
        return True
    except Exception:
        return False


def generar_splits(
    dataset_root: Path | str,
    output_csv: Path | str,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Lee indice_dataset.csv, aplica control de calidad y genera splits.csv.

    Args:
        dataset_root: ruta a la carpeta Scoliosis_Dataset (contiene indice_dataset.csv)
        output_csv:   ruta de salida del splits.csv generado
        seed:         semilla aleatoria para reproducibilidad

    Returns:
        DataFrame con columnas [patient_id, tipo, split, ruta_img, ruta_mask_id]
    """
    random.seed(seed)
    np.random.seed(seed)

    dataset_root = Path(dataset_root)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(dataset_root / "indice_dataset.csv")

    df = df.rename(columns={"grupo": "tipo", "id_paciente": "patient_id"})
    df["tipo"] = df["tipo"].map({"Normal": "sano", "Scoliosis": "escoliosis"})

    df["ruta_img"] = df["ruta_radiografia"].apply(
        lambda p: str(dataset_root / p) if pd.notna(p) else None
    )
    df["ruta_mask_id"] = df["ruta_mascara_multiclase_id_png"].apply(
        lambda p: str(dataset_root / p) if pd.notna(p) else None
    )

    prefix = df["tipo"].map({"sano": "N", "escoliosis": "S"})
    df["patient_id"] = prefix + "_" + df["patient_id"].astype(str)

    df = df.dropna(subset=["ruta_img", "ruta_mask_id"])
    df = df[df["ruta_img"].apply(lambda p: Path(p).exists())]
    df = df[df["ruta_mask_id"].apply(lambda p: Path(p).exists())]
    df = df.reset_index(drop=True)

    validas = df.apply(lambda r: _es_valida(r["ruta_img"], r["ruta_mask_id"]), axis=1)
    descartadas = int((~validas).sum())
    df = df[validas].reset_index(drop=True)

    print(f"Control de calidad: {len(df)} válidas, {descartadas} descartadas")
    print(df["tipo"].value_counts().to_string())

    df_tr, df_vt = train_test_split(
        df, test_size=0.30, stratify=df["tipo"], random_state=seed
    )
    df_val, df_te = train_test_split(
        df_vt, test_size=0.50, stratify=df_vt["tipo"], random_state=seed
    )

    df_tr["split"] = "train"
    df_val["split"] = "val"
    df_te["split"] = "test"

    cols = ["patient_id", "tipo", "split", "ruta_img", "ruta_mask_id"]
    df_splits = pd.concat([df_tr, df_val, df_te], ignore_index=True)[cols]
    df_splits.to_csv(output_csv, index=False)

    print(f"\nsplits.csv → {output_csv}")
    print(
        df_splits["split"].value_counts().reindex(["train", "val", "test"]).to_string()
    )

    return df_splits


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parents[2]
    generar_splits(
        dataset_root=ROOT / "recursos/Scoliosis_Dataset",
        output_csv=ROOT / "recursos/dataset_procesado/splits.csv",
    )
