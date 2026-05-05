"""
Preprocesamiento de imágenes y máscaras para MedSAM.

Pipeline estándar (notebook 01-recoleccion y 04-medsam):
  imagen  → escala de grises → CLAHE → letterbox 1024×1024 → float32 [0,1]
  máscara → PIL uint16       → letterbox NEAREST             → uint8 binario
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


# ─── Lectura ────────────────────────────────────────────────────────────────


def load_rgb_image(path: Path | str) -> np.ndarray:
    img_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise FileNotFoundError(f"No se pudo leer imagen: {path}")
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def load_mask_binary(path: Path | str) -> np.ndarray:
    """Lee máscara binaria JPG. Devuelve array uint8 con 0/1."""
    m = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if m is None:
        raise FileNotFoundError(f"No se pudo leer máscara: {path}")
    if m.ndim == 3:
        m = cv2.cvtColor(m, cv2.COLOR_BGR2GRAY)
    return (m > 0).astype(np.uint8)


# ─── Preprocesamiento ────────────────────────────────────────────────────────


def preproc_img(path: Path | str, size: tuple[int, int] = (1024, 1024)) -> np.ndarray:
    """
    Pipeline completo de imagen:
      1. Lectura en escala de grises
      2. CLAHE (contraste local)
      3. Letterbox resize (mantiene aspect ratio, padding negro)
      4. Normalización float32 [0, 1]
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer: {path}")

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)

    return _letterbox_gray(img, size)


def preproc_mask(path: Path | str, size: tuple[int, int] = (1024, 1024)) -> np.ndarray:
    """
    Redimensiona máscara uint16 con interpolación NEAREST.
    PIL es obligatorio para uint16; cv2 truncaría a uint8.
    """
    mask = np.array(Image.open(str(path)))
    return _letterbox_mask(mask, size)


def _letterbox_gray(img: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    th, tw = size
    h, w = img.shape
    s = min(tw / w, th / h)
    nw, nh = int(w * s), int(h * s)
    img_r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    canvas = np.zeros((th, tw), np.uint8)
    yo, xo = (th - nh) // 2, (tw - nw) // 2
    canvas[yo : yo + nh, xo : xo + nw] = img_r
    return canvas.astype(np.float32) / 255.0


def _letterbox_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    th, tw = size
    h, w = mask.shape
    s = min(tw / w, th / h)
    nw, nh = int(w * s), int(h * s)
    m_r = np.array(Image.fromarray(mask).resize((nw, nh), Image.NEAREST))
    canvas = np.zeros((th, tw), mask.dtype)
    yo, xo = (th - nh) // 2, (tw - nw) // 2
    canvas[yo : yo + nh, xo : xo + nw] = m_r
    return canvas


# ─── Bounding box ────────────────────────────────────────────────────────────


def bbox_from_mask(mask: np.ndarray, pad: int = 10) -> np.ndarray:
    """
    Devuelve [x1, y1, x2, y2] desde una máscara binaria 2D.
    Cubre todos los píxeles > 0.
    """
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        h, w = mask.shape
        return np.array([0, 0, w - 1, h - 1], dtype=np.float32)

    x1 = max(0, xs.min() - pad)
    y1 = max(0, ys.min() - pad)
    x2 = min(mask.shape[1] - 1, xs.max() + pad)
    y2 = min(mask.shape[0] - 1, ys.max() + pad)
    return np.array([x1, y1, x2, y2], dtype=np.float32)


# ─── Post-procesamiento ──────────────────────────────────────────────────────


def postprocess_mask(mask: np.ndarray) -> np.ndarray:
    """
    Limpieza morfológica + componente conectada más grande.
    Elimina ruido y fragmentos espúreos en la predicción binaria.
    """
    mask = mask.astype(np.uint8)
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if num_labels > 1:
        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = (labels == largest).astype(np.uint8)
    return mask
