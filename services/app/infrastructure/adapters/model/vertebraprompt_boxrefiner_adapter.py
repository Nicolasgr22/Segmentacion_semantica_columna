"""Adapter para el pipeline ganador VertebraPrompt-Net + BoxRefiner + MedSAM.

Las arquitecturas de VertebraPromptNet y BoxRefiner se portan desde
``notebooks/medsam_pipeline/notebooks/06_estrategia_ganadora_vertebraprompt_boxrefiner.ipynb``.
La etapa MedSAM usa el predictor de ``segment_anything`` con el ViT-B base más
los pesos finetuneados (decoder + último bloque del encoder).

La inferencia implementada aquí es una versión simplificada del decodificador
del notebook (heatmap → picos top-N con NMS → top-anchor T1..L5 → BoxRefiner →
MedSAM por caja). No incluye programación dinámica anatómica ni shift-fix.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from app.core.domain.ports.model_port import ModelOutput, ModelPort

_executor = ThreadPoolExecutor(max_workers=2)


# ---------------------------------------------------------------------------
# Constantes anatómicas — alineadas con el notebook 06.
# ---------------------------------------------------------------------------
IMG_SIZE = 1024  # tamaño de inferencia heredado de la exportación MedSAM
BASE_CH = 32
N_CLASES = 17  # T1..T12 + L1..L5
TOP_PICOS = 90
MIN_DIST_PICOS = 8
THR_REL_PEAKS = 0.12

# Map T1..L5 → IDs ID2LABEL del servicio (T1=6, ..., L5=22).
# Las clases cervicales (1-5, C7..C3) no las cubre este pipeline.
VERTEBRA_LABELS = [
    "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12",
    "L1", "L2", "L3", "L4", "L5",
]
LABEL_TO_SERVICE_ID = {
    "T1": 6, "T2": 7, "T3": 8, "T4": 9, "T5": 10, "T6": 11,
    "T7": 12, "T8": 13, "T9": 14, "T10": 15, "T11": 16, "T12": 17,
    "L1": 18, "L2": 19, "L3": 20, "L4": 21, "L5": 22,
}

BOX_REFINER_SIZE = 96
BOX_REFINER_BLEND = 0.6
BOX_REFINER_MAX_ABS_DXY = 0.35
BOX_REFINER_MAX_ABS_LOG_SCALE = 0.4
BOX_REFINER_CONTEXT_FRAC = 0.6


# ---------------------------------------------------------------------------
# Arquitectura VertebraPrompt-Net (port directo del notebook 06, celda 10).
# ---------------------------------------------------------------------------
class _ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.SiLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.SiLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class VertebraPromptNet(nn.Module):
    """U-Net ligera multi-tarea: heat, class_heat (T1-L5), wh, off, presence."""

    def __init__(self, base: int = BASE_CH, n_classes: int = N_CLASES) -> None:
        super().__init__()
        self.e1 = _ConvBlock(1, base)
        self.e2 = _ConvBlock(base, base * 2)
        self.e3 = _ConvBlock(base * 2, base * 4)
        self.e4 = _ConvBlock(base * 4, base * 6)
        self.b = _ConvBlock(base * 6, base * 8)

        self.u4 = _ConvBlock(base * 8 + base * 6, base * 6)
        self.u3 = _ConvBlock(base * 6 + base * 4, base * 4)
        self.u2 = _ConvBlock(base * 4 + base * 2, base * 2)
        self.u1 = _ConvBlock(base * 2 + base, base)

        self.heat_head = nn.Conv2d(base, 1, 1)
        self.class_heat_head = nn.Conv2d(base, n_classes, 1)
        self.wh_head = nn.Conv2d(base, 2, 1)
        self.off_head = nn.Conv2d(base, 2, 1)
        self.presence_head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(base * 8, n_classes),
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        e1 = self.e1(x)
        e2 = self.e2(F.max_pool2d(e1, 2))
        e3 = self.e3(F.max_pool2d(e2, 2))
        e4 = self.e4(F.max_pool2d(e3, 2))
        b = self.b(F.max_pool2d(e4, 2))

        u4 = F.interpolate(b, size=e4.shape[-2:], mode="bilinear", align_corners=False)
        u4 = self.u4(torch.cat([u4, e4], dim=1))
        u3 = F.interpolate(u4, size=e3.shape[-2:], mode="bilinear", align_corners=False)
        u3 = self.u3(torch.cat([u3, e3], dim=1))
        u2 = F.interpolate(u3, size=e2.shape[-2:], mode="bilinear", align_corners=False)
        u2 = self.u2(torch.cat([u2, e2], dim=1))
        u1 = F.interpolate(u2, size=e1.shape[-2:], mode="bilinear", align_corners=False)
        u1 = self.u1(torch.cat([u1, e1], dim=1))

        return {
            "heat": self.heat_head(u1),
            "class_heat": self.class_heat_head(u1),
            "wh": self.wh_head(u1),
            "off": self.off_head(u1),
            "presence": self.presence_head(b),
        }


# ---------------------------------------------------------------------------
# Arquitectura BoxRefiner: CNN local sobre crop+mask → (dx, dy, dw, dh).
# Reproduce el contrato del notebook 06: entrada 2 canales (crop normalizado +
# máscara binaria del bbox propuesto) en BOX_REFINER_SIZE × BOX_REFINER_SIZE.
# ---------------------------------------------------------------------------
class BoxRefiner(nn.Module):
    def __init__(self, base: int = 32) -> None:
        super().__init__()
        self.backbone = nn.Sequential(
            _ConvBlock(2, base),
            nn.MaxPool2d(2),
            _ConvBlock(base, base * 2),
            nn.MaxPool2d(2),
            _ConvBlock(base * 2, base * 4),
            nn.MaxPool2d(2),
            _ConvBlock(base * 4, base * 6),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
        )
        self.head = nn.Sequential(
            nn.Linear(base * 6, base * 4),
            nn.SiLU(inplace=True),
            nn.Linear(base * 4, 4),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone(x))


# ---------------------------------------------------------------------------
# Helpers de geometría — port simplificado del notebook 06.
# ---------------------------------------------------------------------------
def _bbox_clip(bbox: list[float], H: int, W: int) -> list[float]:
    x0, y0, x1, y1 = bbox
    x0 = float(np.clip(x0, 0, W - 1))
    y0 = float(np.clip(y0, 0, H - 1))
    x1 = float(np.clip(x1, x0 + 1, W - 1))
    y1 = float(np.clip(y1, y0 + 1, H - 1))
    return [x0, y0, x1, y1]


def _expand_context(bbox: list[float], img_shape, frac: float = BOX_REFINER_CONTEXT_FRAC) -> list[float]:
    H, W = img_shape[:2]
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = max(x1 - x0, 2.0), max(y1 - y0, 2.0)
    side = max(bw, bh) * (1.0 + frac)
    return _bbox_clip([cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2], H, W)


def _extract_peaks(score_map: np.ndarray, n_peaks: int = TOP_PICOS,
                   min_dist: int = MIN_DIST_PICOS, thr_rel: float = THR_REL_PEAKS) -> list[dict]:
    work = score_map.astype(np.float32).copy()
    peaks: list[dict] = []
    max0 = float(work.max())
    if max0 <= 0:
        return peaks
    thr = max(max0 * thr_rel, float(np.percentile(work, 90)))
    for _ in range(n_peaks):
        idx = int(np.argmax(work))
        y, x = np.unravel_index(idx, work.shape)
        score = float(work[y, x])
        if score < thr:
            break
        peaks.append({"x": int(x), "y": int(y), "score": score})
        y0 = max(0, y - min_dist)
        y1 = min(work.shape[0], y + min_dist + 1)
        x0 = max(0, x - min_dist)
        x1 = min(work.shape[1], x + min_dist + 1)
        work[y0:y1, x0:x1] = -np.inf
    return peaks


def _build_refiner_input(img_gray: np.ndarray, bbox_pred: list[float]) -> torch.Tensor:
    """Construye tensor (2, BOX_REFINER_SIZE, BOX_REFINER_SIZE) crop + mask."""
    ctx = _expand_context(bbox_pred, img_gray.shape)
    x0, y0, x1, y1 = ctx
    crop = (
        Image.fromarray(img_gray)
        .crop((int(x0), int(y0), int(x1) + 1, int(y1) + 1))
        .resize((BOX_REFINER_SIZE, BOX_REFINER_SIZE), Image.BILINEAR)
    )
    arr = np.asarray(crop).astype(np.float32)
    p1, p99 = np.percentile(arr, [1, 99.5])
    arr = np.clip((arr - p1) / (p99 - p1 + 1e-6), 0, 1)

    mask_box = np.zeros((BOX_REFINER_SIZE, BOX_REFINER_SIZE), dtype=np.float32)
    bx0, by0, bx1, by1 = bbox_pred
    sx = BOX_REFINER_SIZE / max(x1 - x0 + 1, 1)
    sy = BOX_REFINER_SIZE / max(y1 - y0 + 1, 1)
    rx0 = int(np.clip(round((bx0 - x0) * sx), 0, BOX_REFINER_SIZE - 1))
    rx1 = int(np.clip(round((bx1 - x0) * sx), 0, BOX_REFINER_SIZE - 1))
    ry0 = int(np.clip(round((by0 - y0) * sy), 0, BOX_REFINER_SIZE - 1))
    ry1 = int(np.clip(round((by1 - y0) * sy), 0, BOX_REFINER_SIZE - 1))
    if rx1 > rx0 and ry1 > ry0:
        mask_box[ry0:ry1 + 1, rx0:rx1 + 1] = 1.0

    return torch.from_numpy(np.stack([arr, mask_box], axis=0).astype(np.float32))


def _apply_delta(bbox_pred: list[float], delta: np.ndarray, img_shape, blend: float = BOX_REFINER_BLEND) -> list[float]:
    H, W = img_shape[:2]
    dx = float(np.clip(delta[0], -BOX_REFINER_MAX_ABS_DXY, BOX_REFINER_MAX_ABS_DXY)) * blend
    dy = float(np.clip(delta[1], -BOX_REFINER_MAX_ABS_DXY, BOX_REFINER_MAX_ABS_DXY)) * blend
    dw = float(np.clip(delta[2], -BOX_REFINER_MAX_ABS_LOG_SCALE, BOX_REFINER_MAX_ABS_LOG_SCALE)) * blend
    dh = float(np.clip(delta[3], -BOX_REFINER_MAX_ABS_LOG_SCALE, BOX_REFINER_MAX_ABS_LOG_SCALE)) * blend
    x0, y0, x1, y1 = bbox_pred
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    cx2 = cx + dx * bw
    cy2 = cy + dy * bh
    bw2 = bw * float(np.exp(dw))
    bh2 = bh * float(np.exp(dh))
    return _bbox_clip([cx2 - bw2 / 2, cy2 - bh2 / 2, cx2 + bw2 / 2, cy2 + bh2 / 2], H, W)


def _load_state_dict_compat(path: Path, map_location) -> dict:
    try:
        state = torch.load(str(path), map_location=map_location, weights_only=False)
    except TypeError:
        state = torch.load(str(path), map_location=map_location)
    if isinstance(state, dict):
        for key in ("model", "model_state_dict", "state_dict"):
            if key in state and isinstance(state[key], dict):
                return state[key]
    return state


# ---------------------------------------------------------------------------
# Adapter principal.
# ---------------------------------------------------------------------------
class VertebraPromptBoxRefinerAdapter(ModelPort):
    def __init__(self, device: str = "cpu") -> None:
        self._device = torch.device(device)
        self._prompt_net: Optional[VertebraPromptNet] = None
        self._box_refiner: Optional[BoxRefiner] = None
        self._sam_predictor = None
        self._loaded = False
        self._model_version = "not-loaded"

    def load_model(
        self,
        prompt_net_checkpoint: str,
        box_refiner_checkpoint: str,
        sam_base_checkpoint: str,
        medsam_finetuned_checkpoint: str,
    ) -> None:
        prompt_path = Path(prompt_net_checkpoint)
        refiner_path = Path(box_refiner_checkpoint)
        sam_path = Path(sam_base_checkpoint)
        medsam_path = Path(medsam_finetuned_checkpoint)

        for p in (prompt_path, refiner_path, sam_path, medsam_path):
            if not p.exists():
                raise FileNotFoundError(f"Checkpoint no encontrado: {p}")

        # 1) VertebraPromptNet
        self._prompt_net = VertebraPromptNet().to(self._device)
        prompt_state = _load_state_dict_compat(prompt_path, self._device)
        self._prompt_net.load_state_dict(prompt_state, strict=False)
        self._prompt_net.eval()

        # 2) BoxRefiner
        self._box_refiner = BoxRefiner().to(self._device)
        refiner_state = _load_state_dict_compat(refiner_path, self._device)
        self._box_refiner.load_state_dict(refiner_state, strict=False)
        self._box_refiner.eval()

        # 3) MedSAM (segment_anything ViT-B base + pesos finetuneados).
        from segment_anything import SamPredictor, sam_model_registry

        sam_model = sam_model_registry["vit_b"](checkpoint=str(sam_path)).to(self._device)
        medsam_state = _load_state_dict_compat(medsam_path, self._device)
        sam_model.load_state_dict(medsam_state, strict=False)
        sam_model.eval()
        self._sam_predictor = SamPredictor(sam_model)

        self._loaded = True
        self._model_version = (
            f"vertebraprompt+boxrefiner+{medsam_path.stem}"
        )

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_version(self) -> str:
        return self._model_version

    async def predict(self, image: np.ndarray) -> ModelOutput:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_predict, image)

    # ------------------------------------------------------------------
    # Inferencia
    # ------------------------------------------------------------------
    @torch.no_grad()
    def _sync_predict(self, image: np.ndarray) -> ModelOutput:
        if not self._loaded:
            raise RuntimeError("Modelo no cargado")

        t0 = time.perf_counter()

        # El use case entrega image RGB letterboxed a 512×512. Aquí elevamos a
        # IMG_SIZE para alimentar VertebraPromptNet con la resolución del
        # notebook, y luego volvemos a la grilla original al construir la mask.
        H_out, W_out = image.shape[:2]

        gray_full = np.array(Image.fromarray(image).convert("L"))
        gray_resized = np.array(
            Image.fromarray(gray_full).resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)
        ).astype(np.float32)
        p1, p99 = np.percentile(gray_resized, [1, 99.5])
        gray_norm = np.clip((gray_resized - p1) / (p99 - p1 + 1e-6), 0, 1)
        x = torch.from_numpy(gray_norm[None, None, ...].astype(np.float32)).to(self._device)

        out = self._prompt_net(x)
        heat = torch.sigmoid(out["heat"])[0, 0].cpu().numpy()
        class_heat = torch.sigmoid(out["class_heat"])[0].cpu().numpy()  # (17, H, W)
        wh = torch.sigmoid(out["wh"])[0].cpu().numpy()                  # (2, H, W)

        # Picos top-N con NMS espacial.
        peaks = _extract_peaks(heat)

        # Top-anchor: ordenar por Y ascendente y mapear a T1..L5.
        peaks_sorted = sorted(peaks, key=lambda p: p["y"])[:N_CLASES]

        boxes_pred: list[tuple[str, list[float]]] = []
        for label, peak in zip(VERTEBRA_LABELS, peaks_sorted):
            cx, cy = peak["x"], peak["y"]
            bw_rel = float(wh[0, cy, cx])
            bh_rel = float(wh[1, cy, cx])
            bw = max(bw_rel * IMG_SIZE, 12.0)
            bh = max(bh_rel * IMG_SIZE, 12.0)
            bbox = _bbox_clip(
                [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2],
                IMG_SIZE, IMG_SIZE,
            )
            boxes_pred.append((label, bbox))

        # BoxRefiner sobre cada caja propuesta.
        boxes_refined: list[tuple[str, list[float]]] = []
        gray_uint8 = (gray_norm * 255).astype(np.uint8)
        for label, bbox in boxes_pred:
            inp = _build_refiner_input(gray_uint8, bbox).unsqueeze(0).to(self._device)
            delta = self._box_refiner(inp)[0].cpu().numpy()
            refined = _apply_delta(bbox, delta, gray_uint8.shape)
            boxes_refined.append((label, refined))

        # MedSAM por caja: produce máscara binaria por vértebra y se compone la
        # máscara multiclase escalada a la grilla de salida (H_out × W_out).
        rgb_for_sam = np.stack([gray_uint8] * 3, axis=-1)
        self._sam_predictor.set_image(rgb_for_sam)

        mask_full = np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.uint8)
        proba_full = np.zeros((23, IMG_SIZE, IMG_SIZE), dtype=np.float32)
        proba_full[0] = 1.0

        for label, bbox in boxes_refined:
            class_id = LABEL_TO_SERVICE_ID[label]
            box_np = np.array(bbox, dtype=np.float32)
            masks, scores, _ = self._sam_predictor.predict(
                box=box_np[None, :],
                multimask_output=False,
            )
            m = masks[0].astype(bool)
            score = float(scores[0]) if scores.size else 0.5
            mask_full[m] = class_id
            proba_full[class_id, m] = score
            proba_full[0, m] = 1.0 - score

        # Reescalado a la grilla del use case.
        mask_out = np.array(
            Image.fromarray(mask_full).resize((W_out, H_out), Image.NEAREST),
            dtype=np.uint8,
        )
        proba_out = np.zeros((23, H_out, W_out), dtype=np.float32)
        proba_out[0] = 1.0
        for class_id in range(1, 23):
            proba_band = proba_full[class_id]
            if proba_band.max() <= 0:
                continue
            band_resized = np.array(
                Image.fromarray((proba_band * 255).astype(np.uint8)).resize(
                    (W_out, H_out), Image.BILINEAR
                ),
                dtype=np.float32,
            ) / 255.0
            proba_out[class_id] = band_resized
            proba_out[0] = np.minimum(proba_out[0], 1.0 - band_resized)

        latency_ms = (time.perf_counter() - t0) * 1000
        return ModelOutput(
            mask=mask_out,
            probabilities=proba_out,
            latency_ms=round(latency_ms, 2),
            model_version=self._model_version,
        )
