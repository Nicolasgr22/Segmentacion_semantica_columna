"""Adapter del modelo Unet++ (encoder efficientnet-b7) entrenado por parches.

Reproduce el protocolo de inferencia de
``notebooks/unet++/Unet++_patches.ipynb`` (celdas 28 y 36), que ejecuta una
ventana deslizante sobre la imagen completa, infiere por parches de 128×128 y
fusiona las probabilidades con una ventana Gaussiana. Los hiperparámetros
ganadores reportados en el notebook son:

  ``patch_area=0.5`` · ``sigma=50.0`` · ``stride_ratio=4`` → Dice test 0.4711.

El modelo del notebook emite 18 clases:
  ``[bg, T1..T12, L1..L5]`` (índices 0..17).

El servicio expone 23 clases con cervicales C7..C3 (1..5) que este modelo no
identifica. El adapter remapea cada clase del modelo a su id de servicio:

  ``0 → 0`` (background) y ``k → k + 5`` para 1..17 (T1..L5 → 6..22).

Los canales cervicales del tensor ``probabilities`` quedan en cero porque el
modelo no los predice.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.config import settings
from app.core.domain.ports.model_port import ModelOutput, ModelPort

_executor = ThreadPoolExecutor(max_workers=2)


def _model_to_service_class_id(model_class: int) -> int:
    """Remapea el id del modelo al id del servicio.

    Offset = first_vertebra_id - 1 (T1 arranca en id 6 del contrato).
    """
    if model_class == 0:
        return 0
    return model_class + (settings.unetpp_first_vertebra_id - 1)


# ---------------------------------------------------------------------------
# Carga de checkpoint
# ---------------------------------------------------------------------------
def _build_model() -> nn.Module:
    # Import perezoso: `segmentation_models_pytorch` solo se necesita para
    # construir la arquitectura cuando se carga el checkpoint real. Los tests
    # que inyectan un nn.Module dummy en el adapter no requieren el paquete.
    import segmentation_models_pytorch as smp

    return smp.UnetPlusPlus(
        encoder_name=settings.unetpp_encoder_name,
        encoder_weights=None,        # pesos vienen del checkpoint
        in_channels=settings.unetpp_in_channels,
        classes=settings.unetpp_num_model_classes,
        decoder_attention_type=None,
    )


def _load_checkpoint(path: Path, device: torch.device) -> nn.Module:
    """Carga el checkpoint del notebook.

    Acepta tanto el formato ``state_dict`` puro (cell 24) como el módulo
    completo pickleado (caso del archivo en ``model-pkg/unet++_patches/``,
    que MLflow/Colab guardó con la clase ``UnetPlusPlus`` referenciada). En
    cualquiera de los dos casos extraemos un ``state_dict`` plano y lo
    cargamos sobre una instancia limpia construida localmente.

    ``weights_only=False`` es necesario porque el pickle del módulo completo
    referencia clases (``UnetPlusPlus``, encoders de smp) que el ``Unpickler``
    seguro de PyTorch 2.6+ rechaza por defecto. Confiamos en el archivo: lo
    produjimos nosotros mismos y vive en el repositorio.
    """
    try:
        obj = torch.load(str(path), map_location=device, weights_only=False)
    except TypeError:
        # torch < 2.0 no soporta weights_only.
        obj = torch.load(str(path), map_location=device)

    if isinstance(obj, nn.Module):
        state = obj.state_dict()
    elif isinstance(obj, dict):
        state = obj
        for key in ("model_state_dict", "state_dict"):
            inner = state.get(key)
            if isinstance(inner, dict):
                state = inner
                break
    else:
        raise RuntimeError(
            f"Formato inesperado de checkpoint en {path}: {type(obj).__name__}"
        )

    model = _build_model().to(device)
    model.load_state_dict(state, strict=True)
    return model


# ---------------------------------------------------------------------------
# Preprocesamiento: CLAHE + normalización (réplica de A.CLAHE + A.Normalize)
# ---------------------------------------------------------------------------
def _apply_clahe_rgb(image_uint8: np.ndarray) -> np.ndarray:
    """CLAHE sobre canal L de LAB, replicando ``A.CLAHE(p=1.0)``."""
    lab = cv2.cvtColor(image_uint8, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(
        clipLimit=settings.unetpp_clahe_clip,
        tileGridSize=tuple(settings.unetpp_clahe_tile),
    )
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def _normalize(image_uint8: np.ndarray) -> np.ndarray:
    """``A.Normalize(mean, std)``: /255 → (x - mean) / std, dtype float32."""
    arr = image_uint8.astype(np.float32) / 255.0
    arr = (arr - np.array(settings.unetpp_mean, dtype=np.float32)) / np.array(settings.unetpp_std, dtype=np.float32)
    return arr


# ---------------------------------------------------------------------------
# Sliding window con fusión Gaussiana (port de ``patch_based_inference``)
# ---------------------------------------------------------------------------
def _gaussian_window(size: int, sigma: float, device: torch.device) -> torch.Tensor:
    coords = torch.arange(size, dtype=torch.float32, device=device) - (size - 1) / 2.0
    g1d = torch.exp(-(coords ** 2) / (2.0 * sigma * sigma))
    return torch.outer(g1d, g1d)


@torch.no_grad()
def _patch_inference(
    model: nn.Module,
    image_norm: np.ndarray,
    device: torch.device,
    patch_area: float | None = None,
    stride_ratio: int | None = None,
    sigma: float | None = None,
) -> np.ndarray:
    """Ejecuta inferencia por parches con fusión Gaussiana.

    Args:
        image_norm: (H, W, 3) float32 ya normalizada.
        Devuelve probabilidades softmax (unetpp_num_model_classes, H, W) en CPU/np.
    """
    _patch_area = patch_area if patch_area is not None else settings.unetpp_patch_area
    _stride_ratio = stride_ratio if stride_ratio is not None else settings.unetpp_stride_ratio
    _sigma = sigma if sigma is not None else settings.unetpp_sigma

    H, W, _ = image_norm.shape
    min_dim = min(H, W)
    patch_size = int(round(float(np.sqrt(_patch_area * H * W))))
    patch_size = min(patch_size, min_dim)
    patch_size = max(patch_size, 1)
    stride = max(int(round(patch_size / _stride_ratio)), 1)

    y_steps = list(range(0, H - patch_size + 1, stride))
    if not y_steps:
        y_steps = [0]
    if y_steps[-1] + patch_size < H:
        y_steps.append(H - patch_size)

    x_steps = list(range(0, W - patch_size + 1, stride))
    if not x_steps:
        x_steps = [0]
    if x_steps[-1] + patch_size < W:
        x_steps.append(W - patch_size)

    accum = torch.zeros((settings.unetpp_num_model_classes, H, W), dtype=torch.float32, device=device)
    weights = torch.zeros((H, W), dtype=torch.float32, device=device)
    window = _gaussian_window(patch_size, _sigma, device)

    for y in y_steps:
        for x in x_steps:
            patch_hw3 = image_norm[y : y + patch_size, x : x + patch_size, :]
            resized = cv2.resize(
                patch_hw3,
                (settings.unetpp_patch_size, settings.unetpp_patch_size),
                interpolation=cv2.INTER_LINEAR,
            )
            patch_t = (
                torch.from_numpy(resized).permute(2, 0, 1).unsqueeze(0).to(device).float()
            )
            logits = model(patch_t)
            probs = F.softmax(logits, dim=1)
            probs = F.interpolate(
                probs, size=(patch_size, patch_size), mode="bilinear", align_corners=False
            ).squeeze(0)

            weighted = probs * window.unsqueeze(0)
            accum[:, y : y + patch_size, x : x + patch_size] += weighted
            weights[y : y + patch_size, x : x + patch_size] += window

    final = accum / (weights.unsqueeze(0) + 1e-5)
    return final.cpu().numpy()


def _remap_to_service_contract(
    model_probs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """De ``(18, H, W)`` del modelo → ``(mask uint8 0..22, proba (23, H, W) float32)``."""
    n_model = settings.unetpp_num_model_classes
    n_service = settings.unetpp_n_service_classes
    _, H, W = model_probs.shape
    proba = np.zeros((n_service, H, W), dtype=np.float32)
    proba[0] = model_probs[0].astype(np.float32)
    for model_class in range(1, n_model):
        service_class = _model_to_service_class_id(model_class)
        proba[service_class] = model_probs[model_class].astype(np.float32)

    model_mask = np.argmax(model_probs, axis=0).astype(np.int32)
    remap = np.zeros(n_model, dtype=np.uint8)
    for k in range(n_model):
        remap[k] = _model_to_service_class_id(k)
    mask = remap[model_mask]
    return mask, proba


# ---------------------------------------------------------------------------
# Adapter principal
# ---------------------------------------------------------------------------
class UnetPlusPlusPatchesAdapter(ModelPort):
    """Adapter del Unet++ por parches sobre el contrato del servicio."""

    def __init__(self, device: str = "cpu") -> None:
        self._device = torch.device(device)
        self._model: Optional[nn.Module] = None
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
        self._model_version = f"unetpp-patches@{path.stem}"

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_version(self) -> str:
        return self._model_version

    async def predict(self, image: np.ndarray) -> ModelOutput:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_predict, image)

    def _sync_predict(self, image: np.ndarray) -> ModelOutput:
        if not self._loaded or self._model is None:
            raise RuntimeError("Modelo no cargado")
        t0 = time.perf_counter()

        # Aceptar (H,W,3) RGB uint8, RGBA (descartar alpha) o (H,W) gris (replicar canales).
        if image.ndim == 3 and image.shape[2] == 4:
            image = image[:, :, :3]
        if image.ndim == 2:
            image = np.stack([image] * 3, axis=-1)
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        image_clahe = _apply_clahe_rgb(image)
        image_norm = _normalize(image_clahe)

        model_probs = _patch_inference(self._model, image_norm, self._device)
        mask, proba = _remap_to_service_contract(model_probs)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ModelOutput(
            mask=mask,
            probabilities=proba,
            latency_ms=latency_ms,
            model_version=self._model_version,
        )
