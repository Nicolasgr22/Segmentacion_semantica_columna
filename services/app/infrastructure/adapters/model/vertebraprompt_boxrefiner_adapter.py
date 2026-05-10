"""Adapter del pipeline ganador VertebraPrompt-Net + BoxRefiner + MedSAM.

Replica fielmente la estrategia del notebook
``notebooks/medsam_pipeline/notebooks/06_estrategia_ganadora_vertebraprompt_boxrefiner.ipynb``
para producción:

1. **Letterbox a 1024×1024 RGB** preservando aspect ratio (espacio del dataset
   preprocesado del notebook 03 — sobre el que se entrenó todo).
2. **VertebraPrompt-Net** corre a 512×512 sobre la versión gris-normalizada por
   percentiles 1/99.5 (idéntico al notebook).
3. Decodificación anatómica completa: extracción de picos top-N con NMS,
   penalización de cráneo (``estimar_y_min_anatomico``), programación dinámica
   con plantilla mediana de bboxes (``seleccionar_camino_dp``), top-anchor T1..L5
   y mezcla 0.65·predicción + 0.35·plantilla con expansión ``BOX_EXPAND_W/H``.
4. **BoxRefiner** sobre crops 192×192 de cada caja (con ``CONTEXT_FRAC=0.85``);
   produce deltas (dx, dy, dw, dh) ya saturados con ``tanh·max_abs``.
5. **MedSAM** prompt-mode ``box_only`` (sin puntos), bbox sin expansión adicional
   (``sin_pad``), aplicado por vértebra sobre la imagen RGB 1024×1024.
6. La máscara final se compone en grilla 1024 y luego se devuelve al espacio del
   cliente deshaciendo el letterbox (recorte del área válida + resize NEAREST).

Notas:

- ``mejor_shift_anatomico`` del notebook depende de la máscara GT, así que NO
  se aplica aquí (solo aplica para evaluación). En producción se mantiene la
  asignación top-anchor T1..L5 del DP.
- El template mediano se carga desde ``model-pkg/medsam/template_bbox.json``,
  generado offline con ``services/scripts/generate_template_bbox.py`` a partir
  del split train del dataset preprocesado.
"""

from __future__ import annotations

import asyncio
import json
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
# Constantes (alineadas con notebook 06, celda 2).
# ---------------------------------------------------------------------------
PROMPT_NET_INPUT = 512   # entrada VertebraPromptNet (IMG_SIZE en el notebook)
MEDSAM_IMG_SIZE = 1024   # grilla del dataset preprocesado y de MedSAM
BASE_CH = 32
N_CLASES = 17

# Decodificación
TOP_PICOS = 90
MIN_DIST_PICOS = 8
THR_REL_PEAKS = 0.12
N_CAJAS_CAMINO = 17
MAX_CANDIDATOS = 120
MAX_GAP_REL_DY = 2.40
Y_MIN_ANATOMICO_MARGEN = 0.06
CRANEO_SCORE_FACTOR = 0.12

# Construcción de cajas desde wh-map
BOX_EXPAND_W = 1.12
BOX_EXPAND_H = 1.12
WH_PRED_BLEND = 0.65          # peso predicción del wh-map
WH_TEMPLATE_BLEND = 0.35      # peso plantilla mediana
WH_CLIP_W = (0.03, 0.28)      # límites razonables sobre w_rel
WH_CLIP_H = (0.025, 0.18)     # límites razonables sobre h_rel

# BoxRefiner
BOX_REFINER_SIZE = 192
BOX_REFINER_BLEND = 0.80
BOX_REFINER_MAX_ABS_DXY = 0.45
BOX_REFINER_MAX_ABS_LOG_SCALE = 0.45
BOX_REFINER_CONTEXT_FRAC = 0.85

# Etiquetas T1..L5 → IDs del servicio (T1=6, ..., L5=22).
VERTEBRA_LABELS = [
    "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12",
    "L1", "L2", "L3", "L4", "L5",
]
LABEL_TO_SERVICE_ID = {
    "T1": 6, "T2": 7, "T3": 8, "T4": 9, "T5": 10, "T6": 11,
    "T7": 12, "T8": 13, "T9": 14, "T10": 15, "T11": 16, "T12": 17,
    "L1": 18, "L2": 19, "L3": 20, "L4": 21, "L5": 22,
}
N_SERVICE_CLASSES = 23  # 0..22


# ---------------------------------------------------------------------------
# Arquitecturas (port directo del notebook 06).
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
    """U-Net multi-tarea (notebook 06, celda 10)."""

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


class BoxRefinerNet(nn.Module):
    """Refinador local de cajas (notebook 06, celda 24).

    Importante: el ``tanh·max_abs`` se aplica DENTRO del forward para que el
    checkpoint se cargue exactamente como fue entrenado.
    """

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            _ConvBlock(2, 24),
            nn.MaxPool2d(2),
            _ConvBlock(24, 48),
            nn.MaxPool2d(2),
            _ConvBlock(48, 96),
            nn.MaxPool2d(2),
            _ConvBlock(96, 128),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.15),
            nn.Linear(128, 96),
            nn.SiLU(inplace=True),
            nn.Linear(96, 4),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.net(x)
        dxy = torch.tanh(out[:, :2]) * BOX_REFINER_MAX_ABS_DXY
        dwh = torch.tanh(out[:, 2:]) * BOX_REFINER_MAX_ABS_LOG_SCALE
        return torch.cat([dxy, dwh], dim=1)


# ---------------------------------------------------------------------------
# Letterbox (preserva aspect ratio).
# ---------------------------------------------------------------------------
def _letterbox_to_grid(image_rgb: np.ndarray, target: int = MEDSAM_IMG_SIZE) -> tuple[np.ndarray, dict]:
    """Encajona ``image_rgb`` en un canvas cuadrado ``target × target`` RGB.

    Devuelve el canvas y los parámetros para revertir el letterbox sobre
    máscaras posteriores.
    """
    H, W = image_rgb.shape[:2]
    scale = target / max(H, W)
    new_h, new_w = int(round(H * scale)), int(round(W * scale))
    resized = np.array(
        Image.fromarray(image_rgb).resize((new_w, new_h), Image.BILINEAR)
    )
    pad_top = (target - new_h) // 2
    pad_left = (target - new_w) // 2
    canvas = np.zeros((target, target, 3), dtype=np.uint8)
    canvas[pad_top:pad_top + new_h, pad_left:pad_left + new_w, :] = resized
    return canvas, {
        "scale": scale,
        "pad_top": pad_top,
        "pad_left": pad_left,
        "valid_h": new_h,
        "valid_w": new_w,
        "orig_h": H,
        "orig_w": W,
    }


def _unletterbox_mask(mask_grid: np.ndarray, params: dict, resample: int) -> np.ndarray:
    """Recorta el área válida del canvas y reescala al tamaño original."""
    pad_top = params["pad_top"]
    pad_left = params["pad_left"]
    valid_h = params["valid_h"]
    valid_w = params["valid_w"]
    orig_h = params["orig_h"]
    orig_w = params["orig_w"]
    cropped = mask_grid[pad_top:pad_top + valid_h, pad_left:pad_left + valid_w]
    return np.array(
        Image.fromarray(cropped).resize((orig_w, orig_h), resample)
    )


# ---------------------------------------------------------------------------
# Helpers geométricos.
# ---------------------------------------------------------------------------
def _bbox_clip(bbox: list[float], H: int, W: int) -> list[int]:
    x0, y0, x1, y1 = (int(round(float(v))) for v in bbox)
    x0 = int(np.clip(x0, 0, W - 1))
    x1 = int(np.clip(x1, 0, W - 1))
    y0 = int(np.clip(y0, 0, H - 1))
    y1 = int(np.clip(y1, 0, H - 1))
    if x1 <= x0:
        x1 = min(W - 1, x0 + 1)
    if y1 <= y0:
        y1 = min(H - 1, y0 + 1)
    return [x0, y0, x1, y1]


def _expand_context(bbox: list[float], img_shape: tuple, frac: float = BOX_REFINER_CONTEXT_FRAC) -> list[int]:
    H, W = img_shape[:2]
    x0, y0, x1, y1 = (float(v) for v in bbox)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = max(x1 - x0, 2.0), max(y1 - y0, 2.0)
    side = max(bw, bh) * (1.0 + float(frac))
    return _bbox_clip([cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2], H, W)


# ---------------------------------------------------------------------------
# Decodificación: picos, y-mín cráneo, DP, segmento, construcción de cajas.
# ---------------------------------------------------------------------------
def _imagen_inferencia_tensor(img_rgb_grid: np.ndarray, device: torch.device) -> torch.Tensor:
    """RGB letterboxed (1024) → tensor (1, 1, 512, 512) gris-normalizado."""
    gray = np.array(
        Image.fromarray(img_rgb_grid).convert("L").resize(
            (PROMPT_NET_INPUT, PROMPT_NET_INPUT), Image.BILINEAR
        )
    ).astype(np.float32)
    p1, p99 = np.percentile(gray, [1, 99.5])
    gray = np.clip((gray - p1) / (p99 - p1 + 1e-6), 0, 1)
    return torch.from_numpy(gray[None, None, ...].astype(np.float32)).to(device)


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


def _estimar_y_min_anatomico(img_rgb_grid: np.ndarray) -> float:
    """Detecta el límite superior por debajo del cuello/cráneo (en grilla 512)."""
    gray = np.array(
        Image.fromarray(img_rgb_grid).convert("L").resize(
            (PROMPT_NET_INPUT, PROMPT_NET_INPUT), Image.BILINEAR
        )
    ).astype(np.float32)
    valores = gray[gray > 0]
    if len(valores) == 0:
        return 0.0
    thr = max(5.0, float(np.percentile(valores, 8)))
    active = (gray > thr).astype(np.float32)
    width = active.mean(axis=1)
    kernel = np.ones(21, dtype=np.float32) / 21
    width_s = np.convolve(width, kernel, mode="same")

    h = PROMPT_NET_INPUT
    top_med = float(np.median(width_s[: int(0.16 * h)]))
    search0 = int(0.12 * h)
    search1 = int(0.55 * h)
    search = width_s[search0:search1]
    if len(search) == 0:
        return 0.0
    mid_p85 = float(np.percentile(search, 85))
    umbral_ensanche = max(0.24, top_med * 1.35)
    if top_med > 0.30 or mid_p85 < umbral_ensanche:
        return 0.0
    idx = np.where(search > umbral_ensanche)[0]
    if len(idx) == 0:
        return 0.0
    y_ensanche = float(search0 + idx[0])
    return max(0.0, y_ensanche - Y_MIN_ANATOMICO_MARGEN * h)


def _seleccionar_camino_dp(candidatos: list[dict], template: list[dict],
                           n_pasos: int = N_CAJAS_CAMINO,
                           max_gap_rel: float = MAX_GAP_REL_DY) -> list[dict]:
    """Programación dinámica: elige n_pasos picos coherentes con la plantilla."""
    if not candidatos:
        raise RuntimeError("No hay candidatos de centro.")

    candidatos = sorted(candidatos, key=lambda c: (c["y"], c["x"]))[:MAX_CANDIDATOS]
    n = len(candidatos)
    k = min(int(n_pasos), n)
    if k <= 0:
        raise RuntimeError("No hay suficientes candidatos.")

    xs = np.array([c["x"] for c in candidatos], dtype=np.float32)
    ys = np.array([c["y"] for c in candidatos], dtype=np.float32)
    sc = np.array([c["score"] for c in candidatos], dtype=np.float32)

    cy_template = np.array([t["cy_rel"] for t in template], dtype=np.float32) * PROMPT_NET_INPUT
    dy_template = np.diff(cy_template)
    dy_default = float(np.median(dy_template)) if len(dy_template) else 30.0

    dp = np.full((k, n), -1e9, dtype=np.float32)
    prev = np.full((k, n), -1, dtype=np.int32)
    dp[0] = sc

    for j in range(1, k):
        expected_dy = float(dy_template[j - 1]) if j - 1 < len(dy_template) else dy_default
        expected_dy = max(expected_dy, 4.0)
        min_gap = max(3.0, expected_dy * 0.35)
        max_gap = max(min_gap + 1.0, expected_dy * max_gap_rel)

        for i in range(n):
            dy = ys[i] - ys[:i]
            valid = (dy >= min_gap) & (dy <= max_gap)
            if not valid.any():
                continue
            dx = np.abs(xs[i] - xs[:i])
            dy_pen = np.abs(dy - expected_dy) / expected_dy
            dx_pen = dx / max(PROMPT_NET_INPUT * 0.22, 1.0)
            trans = dp[j - 1, :i] - 0.34 * dy_pen - 0.08 * dx_pen
            trans[~valid] = -1e9
            best = int(np.argmax(trans))
            dp[j, i] = sc[i] + trans[best]
            prev[j, i] = best

    end = int(np.argmax(dp[k - 1]))
    if dp[k - 1, end] < -1e8 and max_gap_rel < 8.0:
        return _seleccionar_camino_dp(candidatos, template, n_pasos=n_pasos, max_gap_rel=8.0)

    path = [end]
    for j in range(k - 1, 0, -1):
        end = int(prev[j, end])
        if end < 0:
            break
        path.append(end)
    path = path[::-1]

    if len(path) != k:
        orden = np.argsort(sc)[-k:]
        path = sorted(orden.tolist(), key=lambda i: ys[i])

    return [candidatos[i] for i in path]


def _construir_prompts_desde_segmento(segmento: list[dict], template: list[dict],
                                      grid_size: int) -> list[tuple[str, list[int], float]]:
    """Convierte centros DP a cajas etiquetadas T1..L5 en grilla ``grid_size``.

    Replica la fórmula del notebook 06:
        bw = (0.65 · pred_w + 0.35 · tpl_w) · BOX_EXPAND_W
        bh = (0.65 · pred_h + 0.35 · tpl_h) · BOX_EXPAND_H
    con `pred_w/h` recortados a rangos anatómicos razonables.
    """
    n_use = min(N_CLASES, len(segmento))
    segmento = sorted(segmento, key=lambda c: (c["y"], c["x"]))[:n_use]
    out: list[tuple[str, list[int], float]] = []
    scale = grid_size / PROMPT_NET_INPUT
    for orden, cand in enumerate(segmento):
        vertebra = VERTEBRA_LABELS[orden]
        trow = template[orden]
        cx = cand["x"] * scale
        cy = cand["y"] * scale
        wh_rel = cand.get("wh_rel", (trow["w_rel"], trow["h_rel"]))
        pred_w = float(np.clip(wh_rel[0], *WH_CLIP_W)) * grid_size
        pred_h = float(np.clip(wh_rel[1], *WH_CLIP_H)) * grid_size
        tpl_w = float(trow["w_rel"]) * grid_size
        tpl_h = float(trow["h_rel"]) * grid_size
        bw = (WH_PRED_BLEND * pred_w + WH_TEMPLATE_BLEND * tpl_w) * BOX_EXPAND_W
        bh = (WH_PRED_BLEND * pred_h + WH_TEMPLATE_BLEND * tpl_h) * BOX_EXPAND_H
        bbox = _bbox_clip(
            [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2],
            grid_size, grid_size,
        )
        out.append((vertebra, bbox, float(cand["score"])))
    return out


def _prompts_desde_outputs(img_rgb_grid: np.ndarray, outputs: dict[str, np.ndarray],
                           template: list[dict]) -> list[tuple[str, list[int], float]]:
    """Orquesta picos + cráneo + DP + construcción de cajas en grilla 1024."""
    heat = outputs["heat"]
    wh_map = outputs["wh"]
    off_map = outputs["off"]

    picos = _extract_peaks(heat)
    if not picos:
        return []

    y_min_hm = _estimar_y_min_anatomico(img_rgb_grid)

    candidatos: list[dict] = []
    for p in picos:
        x, y = p["x"], p["y"]
        cx_hm = x + float(off_map[0, y, x])
        cy_hm = y + float(off_map[1, y, x])
        score = float(p["score"])
        if cy_hm < y_min_hm:
            if cy_hm < y_min_hm - PROMPT_NET_INPUT * 0.06:
                continue
            score *= CRANEO_SCORE_FACTOR
        candidatos.append({
            "x": cx_hm,
            "y": cy_hm,
            "score": score,
            "wh_rel": (float(wh_map[0, y, x]), float(wh_map[1, y, x])),
        })

    if not candidatos:
        return []

    camino = _seleccionar_camino_dp(candidatos, template)
    return _construir_prompts_desde_segmento(camino, template, grid_size=MEDSAM_IMG_SIZE)


# ---------------------------------------------------------------------------
# BoxRefiner I/O.
# ---------------------------------------------------------------------------
def _build_refiner_input(img_gray_grid: np.ndarray, bbox_pred: list[int]) -> torch.Tensor:
    """Tensor (2, BOX_REFINER_SIZE, BOX_REFINER_SIZE) = [crop normalizado, máscara box]."""
    ctx = _expand_context(bbox_pred, img_gray_grid.shape)
    x0, y0, x1, y1 = ctx
    crop = (
        Image.fromarray(img_gray_grid)
        .crop((int(x0), int(y0), int(x1) + 1, int(y1) + 1))
        .resize((BOX_REFINER_SIZE, BOX_REFINER_SIZE), Image.BILINEAR)
    )
    arr = np.asarray(crop).astype(np.float32)
    p1, p99 = np.percentile(arr, [1, 99.5])
    arr = np.clip((arr - p1) / (p99 - p1 + 1e-6), 0, 1)

    mask_box = np.zeros((BOX_REFINER_SIZE, BOX_REFINER_SIZE), dtype=np.float32)
    bx0, by0, bx1, by1 = (float(v) for v in bbox_pred)
    sx = BOX_REFINER_SIZE / max(x1 - x0 + 1, 1)
    sy = BOX_REFINER_SIZE / max(y1 - y0 + 1, 1)
    rx0 = int(np.clip(round((bx0 - x0) * sx), 0, BOX_REFINER_SIZE - 1))
    rx1 = int(np.clip(round((bx1 - x0) * sx), 0, BOX_REFINER_SIZE - 1))
    ry0 = int(np.clip(round((by0 - y0) * sy), 0, BOX_REFINER_SIZE - 1))
    ry1 = int(np.clip(round((by1 - y0) * sy), 0, BOX_REFINER_SIZE - 1))
    if rx1 > rx0 and ry1 > ry0:
        mask_box[ry0:ry1 + 1, rx0:rx1 + 1] = 1.0

    return torch.from_numpy(np.stack([arr, mask_box], axis=0).astype(np.float32))


def _apply_delta(bbox_pred: list[int], delta: np.ndarray, img_shape: tuple) -> list[int]:
    """Aplica deltas (ya saturados por el modelo) con factor BLEND."""
    H, W = img_shape[:2]
    dx = float(delta[0]) * BOX_REFINER_BLEND
    dy = float(delta[1]) * BOX_REFINER_BLEND
    dw = float(delta[2]) * BOX_REFINER_BLEND
    dh = float(delta[3]) * BOX_REFINER_BLEND
    x0, y0, x1, y1 = (float(v) for v in bbox_pred)
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


def _load_template(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or len(data) != N_CLASES:
        raise RuntimeError(f"template_bbox.json inválido: se esperaban {N_CLASES} entradas")
    template = sorted(data, key=lambda r: int(r["id_real"]))
    for i, expected in enumerate(VERTEBRA_LABELS):
        if str(template[i]["vertebra"]).upper() != expected:
            raise RuntimeError(
                f"template_bbox.json fuera de orden: posición {i} es {template[i]['vertebra']}, esperado {expected}"
            )
    return template


# ---------------------------------------------------------------------------
# Adapter principal.
# ---------------------------------------------------------------------------
class VertebraPromptBoxRefinerAdapter(ModelPort):
    def __init__(self, device: str = "cpu") -> None:
        self._device = torch.device(device)
        self._prompt_net: Optional[VertebraPromptNet] = None
        self._box_refiner: Optional[BoxRefinerNet] = None
        self._sam_predictor = None
        self._template: Optional[list[dict]] = None
        self._loaded = False
        self._model_version = "not-loaded"

    def load_model(
        self,
        prompt_net_checkpoint: str,
        box_refiner_checkpoint: str,
        sam_base_checkpoint: str,
        medsam_finetuned_checkpoint: str,
        template_bbox_path: str = "model-pkg/medsam/template_bbox.json",
    ) -> None:
        prompt_path = Path(prompt_net_checkpoint)
        refiner_path = Path(box_refiner_checkpoint)
        sam_path = Path(sam_base_checkpoint)
        medsam_path = Path(medsam_finetuned_checkpoint)
        template_path = Path(template_bbox_path)

        for p in (prompt_path, refiner_path, sam_path, medsam_path, template_path):
            if not p.exists():
                raise FileNotFoundError(f"Recurso no encontrado: {p}")

        # 1) VertebraPromptNet
        self._prompt_net = VertebraPromptNet().to(self._device)
        prompt_state = _load_state_dict_compat(prompt_path, self._device)
        self._prompt_net.load_state_dict(prompt_state, strict=False)
        self._prompt_net.eval()

        # 2) BoxRefiner
        self._box_refiner = BoxRefinerNet().to(self._device)
        refiner_state = _load_state_dict_compat(refiner_path, self._device)
        self._box_refiner.load_state_dict(refiner_state, strict=False)
        self._box_refiner.eval()

        # 3) MedSAM (segment_anything ViT-B base + pesos finetuneados).
        # Construimos sin checkpoint para evitar que segment_anything llame a
        # torch.load() sin map_location (rompe en CPU si los pesos se guardaron
        # con tensores CUDA). Luego cargamos los pesos manualmente con map_location.
        from segment_anything import SamPredictor, sam_model_registry

        sam_model = sam_model_registry["vit_b"](checkpoint=None).to(self._device)
        sam_state = _load_state_dict_compat(sam_path, self._device)
        sam_model.load_state_dict(sam_state, strict=False)
        medsam_state = _load_state_dict_compat(medsam_path, self._device)
        sam_model.load_state_dict(medsam_state, strict=False)
        sam_model.eval()
        self._sam_predictor = SamPredictor(sam_model)

        # 4) Plantilla anatómica (mediana de bboxes del split train).
        self._template = _load_template(template_path)

        self._loaded = True
        self._model_version = f"vertebraprompt+boxrefiner+{medsam_path.stem}"

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_version(self) -> str:
        return self._model_version

    async def predict(self, image: np.ndarray) -> ModelOutput:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_predict, image)

    @torch.no_grad()
    def _sync_predict(self, image: np.ndarray) -> ModelOutput:
        if not self._loaded:
            raise RuntimeError("Modelo no cargado")
        t0 = time.perf_counter()

        # 1) Letterbox a 1024×1024 RGB (espacio del dataset preprocesado).
        if image.ndim == 2:
            image = np.stack([image] * 3, axis=-1)
        elif image.shape[2] == 4:
            image = image[:, :, :3]
        rgb_grid, lb_params = _letterbox_to_grid(image, MEDSAM_IMG_SIZE)

        # 2) VertebraPromptNet a 512×512 (gris-normalizado por percentiles).
        x = _imagen_inferencia_tensor(rgb_grid, self._device)
        out = self._prompt_net(x)
        outputs_np = {
            "heat": torch.sigmoid(out["heat"])[0, 0].cpu().numpy(),
            "wh": torch.sigmoid(out["wh"])[0].cpu().numpy(),
            "off": torch.sigmoid(out["off"])[0].cpu().numpy(),
        }

        # 3) Decodificación anatómica → cajas T1..L5 en grilla 1024.
        boxes_pred = _prompts_desde_outputs(rgb_grid, outputs_np, self._template)

        # 4) BoxRefiner por caja (sobre la imagen gris en grilla 1024).
        gray_grid = np.array(Image.fromarray(rgb_grid).convert("L"))
        boxes_refined: list[tuple[str, list[int], float]] = []
        for label, bbox, score in boxes_pred:
            inp = _build_refiner_input(gray_grid, bbox).unsqueeze(0).to(self._device)
            delta = self._box_refiner(inp)[0].cpu().numpy()
            refined = _apply_delta(bbox, delta, gray_grid.shape)
            boxes_refined.append((label, refined, score))

        # 5) MedSAM box_only (sin expansión adicional, "sin_pad").
        self._sam_predictor.set_image(rgb_grid)

        mask_grid = np.zeros((MEDSAM_IMG_SIZE, MEDSAM_IMG_SIZE), dtype=np.uint8)
        proba_grid = np.zeros((N_SERVICE_CLASSES, MEDSAM_IMG_SIZE, MEDSAM_IMG_SIZE), dtype=np.float32)
        proba_grid[0] = 1.0

        for label, bbox, _score_pn in boxes_refined:
            class_id = LABEL_TO_SERVICE_ID[label]
            box_np = np.array(bbox, dtype=np.float32)
            masks, scores, _ = self._sam_predictor.predict(
                box=box_np[None, :],
                multimask_output=False,
            )
            m = masks[0].astype(bool)
            sam_score = float(scores[0]) if scores.size else 0.5
            mask_grid[m] = class_id
            proba_grid[class_id, m] = sam_score
            proba_grid[0, m] = 1.0 - sam_score

        # 6) Deshacer letterbox: recortar área válida y reescalar al espacio del cliente.
        mask_out = _unletterbox_mask(mask_grid, lb_params, resample=Image.NEAREST)
        H_out, W_out = mask_out.shape[:2]

        proba_out = np.zeros((N_SERVICE_CLASSES, H_out, W_out), dtype=np.float32)
        proba_out[0] = 1.0
        for class_id in range(1, N_SERVICE_CLASSES):
            band = proba_grid[class_id]
            if band.max() <= 0:
                continue
            band_u8 = (band * 255.0).astype(np.uint8)
            band_resized = _unletterbox_mask(band_u8, lb_params, resample=Image.BILINEAR).astype(np.float32) / 255.0
            proba_out[class_id] = band_resized
            proba_out[0] = np.minimum(proba_out[0], 1.0 - band_resized)

        latency_ms = (time.perf_counter() - t0) * 1000
        return ModelOutput(
            mask=mask_out,
            probabilities=proba_out,
            latency_ms=round(latency_ms, 2),
            model_version=self._model_version,
        )
