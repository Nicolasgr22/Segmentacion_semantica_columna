"""Adapter del modelo Experimento B (Progressive U-Net binaria estilo paper).

Carga el checkpoint guardado vía ``mlflow.pytorch.log_model`` en el notebook
``notebooks/unet/SegmentacionSemanticaImagenes_UNet_Exp_BPaper_MLFlow.ipynb``
(sección 9, Experimento B) y lo expone al servicio bajo el contrato
``ModelPort``. El modelo es **binario** (vértebra vs fondo); para encajar en la
máscara multi-clase 0..22 del contrato se hace un *band-split* vertical
top-to-bottom del foreground, etiquetando 17 bandas como T1..L5 (IDs 6..22).

Pipeline de inferencia:

  1. RGB uint8 → grayscale (cv2.COLOR_RGB2GRAY), idéntico al Dataset del notebook.
  2. Resize a (W=512, H=256) con INTER_AREA.
  3. Normalización /255.0 → tensor (1, 1, 256, 512) float32.
  4. forward → logits (1, 1, 256, 512); sigmoid → ``prob_fg`` en [0, 1].
  5. Resize ``prob_fg`` a (H_orig, W_orig) con INTER_LINEAR; threshold 0.5 →
     máscara binaria.
  6. Band-split del foreground en 17 bandas T1..L5 (IDs 6..22).
  7. Construcción de ``probabilities (23, H, W)``: canal 0 = 1 - prob_fg,
     canales 1..5 (cervicales) = 0, canales 6..22 = prob_fg restringido a su
     banda vertical.

Notas sobre el checkpoint:

  El archivo ``model.pth`` fue guardado con ``mlflow.pytorch.log_model(...)`` en
  el Colab del notebook, es decir el módulo completo serializado vía pickle
  (no ``state_dict``). Para que el unpickle encuentre las clases (que
  originalmente residían en ``__main__`` del Colab), exponemos
  ``PaperConvBlock`` y ``ProgressiveUNetBinaryPaperLike`` en ``__main__`` antes
  de hacer ``torch.load``. Como fallback, también soportamos un ``.pth`` en
  formato ``state_dict`` por si en el futuro se re-exporta el modelo de forma
  más portable.
"""

from __future__ import annotations

import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.core.domain.ports.model_port import ModelOutput, ModelPort

_executor = ThreadPoolExecutor(max_workers=2)


# ---------------------------------------------------------------------------
# Constantes (alineadas con EXPERIMENT_B_CONFIG del notebook)
# ---------------------------------------------------------------------------
INPUT_W = 512          # ancho objetivo (cv2.resize toma (W, H))
INPUT_H = 256          # alto objetivo
THRESHOLD = 0.5        # threshold sobre sigmoid(logits)
BASE_CHANNELS = 32
DROPOUT = 0.25
IN_CHANNELS = 1
OUT_CHANNELS = 1

# Remap binario → contrato 23 clases del servicio.
NUM_BANDS = 17                                          # T1..L5
FIRST_VERTEBRA_ID = 6                                   # T1 según VERTEBRA_LABELS_MAP
LAST_VERTEBRA_ID = FIRST_VERTEBRA_ID + NUM_BANDS - 1    # 22 (L5)
N_SERVICE_CLASSES = 23


# ---------------------------------------------------------------------------
# Arquitectura (port directo del notebook, sección 9.4 — celdas 197514..197650)
# ---------------------------------------------------------------------------
class PaperConvBlock(nn.Module):
    """Conv 3x3 → InstanceNorm → ReLU → Dropout2d, dos veces."""

    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.25):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout2d(dropout),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout2d(dropout),
        )

    def forward(self, x):
        return self.block(x)


class ProgressiveUNetBinaryPaperLike(nn.Module):
    """U-Net 4-encoder con deep-supervision (3 side outputs) tipo paper."""

    def __init__(
        self,
        in_channels: int = IN_CHANNELS,
        out_channels: int = OUT_CHANNELS,
        base_channels: int = BASE_CHANNELS,
        dropout: float = DROPOUT,
    ) -> None:
        super().__init__()

        c1 = base_channels
        c2 = base_channels * 2
        c3 = base_channels * 4
        c4 = base_channels * 8
        c5 = base_channels * 16

        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        self.enc1 = PaperConvBlock(in_channels, c1, dropout=dropout)
        self.enc2 = PaperConvBlock(c1, c2, dropout=dropout)
        self.enc3 = PaperConvBlock(c2, c3, dropout=dropout)
        self.enc4 = PaperConvBlock(c3, c4, dropout=dropout)
        self.bottleneck = PaperConvBlock(c4, c5, dropout=dropout)

        self.up4 = nn.ConvTranspose2d(c5, c4, kernel_size=2, stride=2)
        self.dec4 = PaperConvBlock(c4 + c4, c4, dropout=dropout)
        self.up3 = nn.ConvTranspose2d(c4, c3, kernel_size=2, stride=2)
        self.dec3 = PaperConvBlock(c3 + c3, c3, dropout=dropout)
        self.up2 = nn.ConvTranspose2d(c3, c2, kernel_size=2, stride=2)
        self.dec2 = PaperConvBlock(c2 + c2, c2, dropout=dropout)
        self.up1 = nn.ConvTranspose2d(c2, c1, kernel_size=2, stride=2)
        self.dec1 = PaperConvBlock(c1 + c1, c1, dropout=dropout)

        # Side outputs (deep supervision): x/8, x/4, x/2
        self.side4 = nn.Conv2d(c4, out_channels, kernel_size=1)
        self.side3 = nn.Conv2d(c3, out_channels, kernel_size=1)
        self.side2 = nn.Conv2d(c2, out_channels, kernel_size=1)

        self.final_conv = nn.Conv2d(c1, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        input_size = x.shape[-2:]

        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))

        d4 = self.up4(b)
        d4 = torch.cat([d4, e4], dim=1)
        d4 = self.dec4(d4)
        side4 = self.side4(d4)

        d3 = self.up3(d4)
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)
        side4_up = F.interpolate(side4, size=d3.shape[-2:], mode="bilinear", align_corners=False)
        side3 = self.side3(d3) + side4_up

        d2 = self.up2(d3)
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)
        side3_up = F.interpolate(side3, size=d2.shape[-2:], mode="bilinear", align_corners=False)
        side2 = self.side2(d2) + side3_up

        d1 = self.up1(d2)
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)
        side2_up = F.interpolate(side2, size=d1.shape[-2:], mode="bilinear", align_corners=False)

        logits = self.final_conv(d1) + side2_up
        if logits.shape[-2:] != input_size:
            logits = F.interpolate(logits, size=input_size, mode="bilinear", align_corners=False)
        return logits


# ---------------------------------------------------------------------------
# Carga de checkpoint (módulo pickle de mlflow ó state_dict)
# ---------------------------------------------------------------------------
def _register_classes_for_pickle() -> None:
    # `mlflow.pytorch.log_model` pickleó la clase con `__module__ == "__main__"`
    # (definida en el Colab). Sin este puente, el unpickle revienta con
    # AttributeError porque no encuentra las clases en `__main__`.
    main_mod = sys.modules.get("__main__")
    if main_mod is None:
        return
    if not hasattr(main_mod, "PaperConvBlock"):
        main_mod.PaperConvBlock = PaperConvBlock
    if not hasattr(main_mod, "ProgressiveUNetBinaryPaperLike"):
        main_mod.ProgressiveUNetBinaryPaperLike = ProgressiveUNetBinaryPaperLike


def _load_checkpoint(path: Path, device: torch.device) -> ProgressiveUNetBinaryPaperLike:
    # El pickle del notebook fue guardado con torch 2.10+cu128. Hacer forward
    # sobre el módulo deserializado directamente puede segfaultear con torch
    # 2.11 CPU. Por eso, sea cual sea el formato, extraemos solo el
    # state_dict y reconstruimos una instancia limpia con la clase local.
    _register_classes_for_pickle()
    try:
        obj = torch.load(str(path), map_location=device, weights_only=False)
    except TypeError:
        # torch < 2.0: no soporta weights_only.
        obj = torch.load(str(path), map_location=device)

    if isinstance(obj, nn.Module):
        state = obj.state_dict()
    elif isinstance(obj, dict):
        state = obj
        for key in ("model", "model_state_dict", "state_dict"):
            inner = state.get(key)
            if isinstance(inner, dict):
                state = inner
                break
    else:
        raise RuntimeError(
            f"Formato inesperado de checkpoint en {path}: {type(obj).__name__}"
        )

    model = ProgressiveUNetBinaryPaperLike(
        in_channels=IN_CHANNELS,
        out_channels=OUT_CHANNELS,
        base_channels=BASE_CHANNELS,
        dropout=DROPOUT,
    ).to(device)
    model.load_state_dict(state, strict=True)
    return model


# ---------------------------------------------------------------------------
# Adapter principal
# ---------------------------------------------------------------------------
class ProgressiveUNetBinaryAdapter(ModelPort):
    """Adapter del Experimento B sobre el contrato del servicio."""

    def __init__(self, device: str = "cpu") -> None:
        self._device = torch.device(device)
        self._model: Optional[ProgressiveUNetBinaryPaperLike] = None
        self._loaded = False
        self._model_version = "not-loaded"

    def load_model(self, checkpoint: str) -> None:
        path = Path(checkpoint)
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint no encontrado: {path}")
        model = _load_checkpoint(path, self._device)
        model.eval()
        self._model = model
        self._loaded = True
        self._model_version = f"progressive-unet-binary@{path.stem}"

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_version(self) -> str:
        return self._model_version

    async def predict(self, image: np.ndarray) -> ModelOutput:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_predict, image)

    @torch.no_grad()
    def _sync_predict(self, image: np.ndarray) -> ModelOutput:
        if not self._loaded or self._model is None:
            raise RuntimeError("Modelo no cargado")
        t0 = time.perf_counter()

        # Aceptar (H,W,3) RGB uint8 o (H,W) gris. RGBA → descartar alpha.
        if image.ndim == 3 and image.shape[2] == 4:
            image = image[:, :, :3]
        H_orig, W_orig = image.shape[:2]

        if image.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        if gray.dtype != np.uint8:
            gray = np.clip(gray, 0, 255).astype(np.uint8)

        gray_small = cv2.resize(gray, (INPUT_W, INPUT_H), interpolation=cv2.INTER_AREA)

        x = gray_small.astype(np.float32) / 255.0
        x = torch.from_numpy(x).unsqueeze(0).unsqueeze(0).to(self._device)

        logits = self._model(x)
        prob_fg_small = torch.sigmoid(logits)[0, 0].cpu().numpy()  # (256, 512)

        prob_fg = cv2.resize(prob_fg_small, (W_orig, H_orig), interpolation=cv2.INTER_LINEAR)
        prob_fg = np.clip(prob_fg, 0.0, 1.0).astype(np.float32)
        binary_mask = (prob_fg > THRESHOLD).astype(np.uint8)

        mask, proba = _band_split_to_service_mask(binary_mask, prob_fg)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ModelOutput(
            mask=mask,
            probabilities=proba,
            latency_ms=latency_ms,
            model_version=self._model_version,
        )


def _band_split_to_service_mask(
    binary_mask: np.ndarray,
    prob_fg: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Remapea (binary_mask, prob_fg) al contrato (mask uint8 0..22, proba (23,H,W) f32).

    Divide el foreground en ``NUM_BANDS`` bandas horizontales uniformes dentro
    de su bounding box vertical y las etiqueta T1..L5 (IDs 6..22). Los canales
    cervicales 1..5 quedan en cero porque el modelo no los discrimina.
    """
    H, W = binary_mask.shape
    mask = np.zeros((H, W), dtype=np.uint8)
    proba = np.zeros((N_SERVICE_CLASSES, H, W), dtype=np.float32)

    proba[0] = (1.0 - prob_fg).astype(np.float32)

    fg_rows = np.where(binary_mask.any(axis=1))[0]
    if fg_rows.size == 0:
        return mask, proba

    y_min = int(fg_rows[0])
    y_max = int(fg_rows[-1])
    span = max(y_max - y_min + 1, 1)

    rows = np.arange(H)
    relative = (rows - y_min).astype(np.float32) / span
    band_per_row = np.clip(
        np.floor(relative * NUM_BANDS).astype(np.int32),
        0,
        NUM_BANDS - 1,
    )

    fg_bool = binary_mask.astype(bool)
    for band_idx in range(NUM_BANDS):
        rows_in_band = np.where(band_per_row == band_idx)[0]
        if rows_in_band.size == 0:
            continue
        row_selector = np.zeros(H, dtype=bool)
        row_selector[rows_in_band] = True
        band_pixels = fg_bool & row_selector[:, None]
        if not band_pixels.any():
            continue
        class_id = FIRST_VERTEBRA_ID + band_idx
        mask[band_pixels] = class_id
        proba[class_id][band_pixels] = prob_fg[band_pixels]

    return mask, proba
