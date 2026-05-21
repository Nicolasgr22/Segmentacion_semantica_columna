"""Tests unitarios de las funciones puras del adapter VertebraPrompt+BoxRefiner.

Cubren letterbox, decodificación anatómica (picos, y-mín cráneo, DP, plantilla,
construcción de cajas, application de deltas) y la red BoxRefiner. Todos los
tests corren sin checkpoints reales (BoxRefinerNet con pesos random basta para
verificar contratos de I/O).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from app.config import settings
from app.infrastructure.adapters.model.vertebraprompt_boxrefiner_adapter import (
    VERTEBRA_LABELS,
    BoxRefinerNet,
    _apply_delta,
    _bbox_clip,
    _build_refiner_input,
    _construir_prompts_desde_segmento,
    _estimar_y_min_anatomico,
    _extract_peaks,
    _letterbox_to_grid,
    _load_template,
    _seleccionar_camino_dp,
    _unletterbox_mask,
)

# Aliases para legibilidad en los tests
BOX_EXPAND_H = settings.medsam_box_expand_h
BOX_EXPAND_W = settings.medsam_box_expand_w
BOX_REFINER_MAX_ABS_DXY = settings.medsam_box_refiner_max_abs_dxy
BOX_REFINER_MAX_ABS_LOG_SCALE = settings.medsam_box_refiner_max_abs_log_scale
BOX_REFINER_SIZE = settings.medsam_box_refiner_size
MEDSAM_IMG_SIZE = settings.medsam_img_size
N_CLASES = settings.medsam_n_classes
PROMPT_NET_INPUT = settings.medsam_prompt_net_input


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def template() -> list[dict]:
    """Plantilla mediana real cargada del model-pkg (17 vértebras)."""
    path = Path("model-pkg/medsam/template_bbox.json")
    return _load_template(path)


@pytest.fixture
def synthetic_spine_rgb() -> np.ndarray:
    """Imagen sintética 1024×1024 con cuello angosto y tórax ancho.

    `_estimar_y_min_anatomico` usa el percentil 8 de píxeles no-cero como
    threshold; necesita que el cuerpo tenga **variación de intensidad** para
    que el threshold quede por debajo de la masa del cuerpo. Replicamos eso
    con ruido gaussiano dentro del cuerpo.
    """
    rng = np.random.default_rng(123)
    img = np.zeros((1024, 1024, 3), dtype=np.uint8)
    neck = rng.integers(180, 230, (100, 80, 3), dtype=np.uint8)
    img[40:140, 480:560, :] = neck
    thorax = rng.integers(180, 230, (760, 530, 3), dtype=np.uint8)
    img[140:900, 250:780, :] = thorax
    return img


# ---------------------------------------------------------------------------
# Letterbox
# ---------------------------------------------------------------------------
class TestLetterbox:
    def test_squared_input_no_padding(self):
        img = np.full((512, 512, 3), 200, dtype=np.uint8)
        canvas, p = _letterbox_to_grid(img, target=1024)
        assert canvas.shape == (1024, 1024, 3)
        assert p["scale"] == pytest.approx(2.0)
        assert p["pad_top"] == 0 and p["pad_left"] == 0
        assert p["valid_h"] == 1024 and p["valid_w"] == 1024

    def test_vertical_input_horizontal_padding(self):
        img = np.full((1500, 800, 3), 100, dtype=np.uint8)
        canvas, p = _letterbox_to_grid(img, target=1024)
        assert canvas.shape == (1024, 1024, 3)
        assert p["pad_top"] == 0  # alto domina
        assert p["pad_left"] > 0  # padding horizontal
        # bordes laterales deben ser 0 (canvas negro)
        assert canvas[500, 0, 0] == 0
        assert canvas[500, 1023, 0] == 0
        # área central debe tener contenido
        assert canvas[500, 512, 0] > 0

    def test_horizontal_input_vertical_padding(self):
        img = np.full((600, 1200, 3), 150, dtype=np.uint8)
        _, p = _letterbox_to_grid(img, target=1024)
        assert p["pad_left"] == 0  # ancho domina
        assert p["pad_top"] > 0
        assert p["valid_w"] == 1024

    def test_aspect_ratio_preserved(self):
        H, W = 1500, 800
        img = np.full((H, W, 3), 50, dtype=np.uint8)
        _, p = _letterbox_to_grid(img, target=1024)
        # ratio entre valid_h y valid_w debe ser ≈ H/W
        assert p["valid_h"] / p["valid_w"] == pytest.approx(H / W, rel=0.01)

    def test_unletterbox_round_trip(self):
        """Una máscara construida en grilla 1024 vuelve al tamaño original."""
        H, W = 800, 1500
        img = np.full((H, W, 3), 0, dtype=np.uint8)
        _, p = _letterbox_to_grid(img, target=1024)
        # Máscara con valor 7 en toda el área válida
        mask_grid = np.zeros((1024, 1024), dtype=np.uint8)
        mask_grid[p["pad_top"]:p["pad_top"] + p["valid_h"],
                  p["pad_left"]:p["pad_left"] + p["valid_w"]] = 7
        from PIL import Image as PILImage
        out = _unletterbox_mask(mask_grid, p, resample=PILImage.NEAREST)
        assert out.shape == (H, W)
        # mayoría de píxeles deben ser 7
        assert (out == 7).mean() > 0.95


# ---------------------------------------------------------------------------
# Template loader
# ---------------------------------------------------------------------------
class TestLoadTemplate:
    def test_loads_17_vertebrae_in_order(self, template):
        assert len(template) == N_CLASES
        names = [t["vertebra"] for t in template]
        assert names == VERTEBRA_LABELS  # orden T1..L5

    def test_template_values_in_unit_range(self, template):
        for t in template:
            assert 0.0 < t["cy_rel"] < 1.0
            assert 0.0 < t["w_rel"] < 0.5
            assert 0.0 < t["h_rel"] < 0.5

    def test_invalid_count_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps([
            {"vertebra": "T1", "id_real": 1, "cx_rel": 0.5, "cy_rel": 0.1, "w_rel": 0.05, "h_rel": 0.03}
        ]))
        with pytest.raises(RuntimeError, match="template_bbox.json inválido"):
            _load_template(bad)

    def test_out_of_order_raises(self, tmp_path):
        rows = [
            {"vertebra": "L5", "id_real": 1, "cx_rel": 0.5, "cy_rel": 0.8, "w_rel": 0.08, "h_rel": 0.05}
        ] * N_CLASES
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps(rows))
        with pytest.raises(RuntimeError, match="fuera de orden"):
            _load_template(bad)


# ---------------------------------------------------------------------------
# Extract peaks (NMS)
# ---------------------------------------------------------------------------
class TestExtractPeaks:
    def test_returns_empty_for_zero_map(self):
        sm = np.zeros((64, 64), dtype=np.float32)
        assert _extract_peaks(sm) == []

    def test_finds_isolated_peaks(self):
        sm = np.zeros((64, 64), dtype=np.float32)
        sm[10, 20] = 1.0
        sm[40, 50] = 0.8
        peaks = _extract_peaks(sm, n_peaks=10, min_dist=2, thr_rel=0.1)
        assert len(peaks) >= 2
        # ordenados por score descendente (primero el de score 1.0)
        assert peaks[0]["score"] == pytest.approx(1.0)
        assert (peaks[0]["x"], peaks[0]["y"]) == (20, 10)

    def test_nms_suppresses_neighbors(self):
        sm = np.zeros((64, 64), dtype=np.float32)
        sm[10, 20] = 1.0
        sm[10, 22] = 0.9  # vecino dentro de min_dist=5
        peaks = _extract_peaks(sm, n_peaks=10, min_dist=5, thr_rel=0.1)
        # solo debe quedar el de score 1.0
        coords = {(p["x"], p["y"]) for p in peaks}
        assert (20, 10) in coords
        assert (22, 10) not in coords

    def test_threshold_filters_low_scores(self):
        sm = np.zeros((64, 64), dtype=np.float32)
        sm[10, 10] = 1.0
        sm[30, 30] = 0.05  # debajo de thr_rel * 1.0 = 0.12
        peaks = _extract_peaks(sm, n_peaks=20, min_dist=2, thr_rel=0.12)
        coords = {(p["x"], p["y"]) for p in peaks}
        assert (30, 30) not in coords


# ---------------------------------------------------------------------------
# y_min cráneo
# ---------------------------------------------------------------------------
class TestEstimarYMinAnatomico:
    def test_returns_zero_for_uniform_noise(self):
        rng = np.random.default_rng(0)
        img = rng.integers(50, 200, (1024, 1024, 3), dtype=np.uint8)
        y_min = _estimar_y_min_anatomico(img)
        assert y_min == 0.0

    def test_detects_neck_to_thorax_widening(self, synthetic_spine_rgb):
        y_min = _estimar_y_min_anatomico(synthetic_spine_rgb)
        # debe detectar el ensanchamiento → y_min > 0
        # (la grilla de cómputo es 512, así que el rango razonable es [0, 512])
        assert 0.0 < y_min < PROMPT_NET_INPUT


# ---------------------------------------------------------------------------
# DP anatómico
# ---------------------------------------------------------------------------
class TestSeleccionarCaminoDp:
    def _candidatos_desde_template(self, template: list[dict], jitter_px: float = 1.0) -> list[dict]:
        """Genera candidatos perfectamente coherentes con la plantilla en grilla 512."""
        rng = np.random.default_rng(0)
        out = []
        for t in template:
            cx = t["cx_rel"] * PROMPT_NET_INPUT + rng.uniform(-jitter_px, jitter_px)
            cy = t["cy_rel"] * PROMPT_NET_INPUT + rng.uniform(-jitter_px, jitter_px)
            out.append({
                "x": float(cx), "y": float(cy), "score": 0.9,
                "wh_rel": (t["w_rel"], t["h_rel"]),
            })
        return out

    def test_returns_n_path_steps(self, template):
        cand = self._candidatos_desde_template(template)
        path = _seleccionar_camino_dp(cand, template)
        assert len(path) == N_CLASES

    def test_path_sorted_by_y(self, template):
        cand = self._candidatos_desde_template(template)
        path = _seleccionar_camino_dp(cand, template)
        ys = [c["y"] for c in path]
        assert ys == sorted(ys)

    def test_empty_candidates_raises(self, template):
        with pytest.raises(RuntimeError):
            _seleccionar_camino_dp([], template)

    def test_distractors_are_filtered(self, template):
        """Si agrego candidatos espurios, el DP elige los coherentes con la plantilla."""
        good = self._candidatos_desde_template(template)
        rng = np.random.default_rng(1)
        # 50 distractores con score más bajo en posiciones random (pero válidas para el DP)
        distractors = [
            {"x": float(rng.uniform(0, PROMPT_NET_INPUT)),
             "y": float(rng.uniform(0, PROMPT_NET_INPUT)),
             "score": 0.3,
             "wh_rel": (0.05, 0.04)}
            for _ in range(50)
        ]
        path = _seleccionar_camino_dp(good + distractors, template)
        assert len(path) == N_CLASES
        # los Y deben caer cerca de los del template (margen amplio: 30 px en grilla 512)
        cy_template = [t["cy_rel"] * PROMPT_NET_INPUT for t in template]
        for chosen, expected in zip(path, cy_template):
            assert abs(chosen["y"] - expected) < 30


# ---------------------------------------------------------------------------
# Construcción de cajas
# ---------------------------------------------------------------------------
class TestConstruirPromptsDesdeSegmento:
    def test_emits_t1_to_l5_in_order(self, template):
        segmento = [
            {"x": t["cx_rel"] * PROMPT_NET_INPUT,
             "y": t["cy_rel"] * PROMPT_NET_INPUT,
             "score": 0.9,
             "wh_rel": (t["w_rel"], t["h_rel"])}
            for t in template
        ]
        result = _construir_prompts_desde_segmento(segmento, template, grid_size=MEDSAM_IMG_SIZE)
        labels = [r[0] for r in result]
        assert labels == VERTEBRA_LABELS

    def test_box_expand_factor_applied(self, template):
        """Con un solo elemento en el segmento se etiqueta como T1 (orden 0).
        Si `wh_rel == template[T1]`, el ancho final debe ser w_rel·grid·BOX_EXPAND_W
        (porque blend 0.65·pred + 0.35·tpl con pred==tpl ⇒ tpl)."""
        t1 = template[0]
        seg = [{
            "x": t1["cx_rel"] * PROMPT_NET_INPUT,
            "y": t1["cy_rel"] * PROMPT_NET_INPUT,
            "score": 0.9,
            "wh_rel": (t1["w_rel"], t1["h_rel"]),
        }]
        result = _construir_prompts_desde_segmento(seg, template, grid_size=MEDSAM_IMG_SIZE)
        label, bbox, _ = result[0]
        assert label == "T1"
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        expected_w = t1["w_rel"] * MEDSAM_IMG_SIZE * BOX_EXPAND_W
        expected_h = t1["h_rel"] * MEDSAM_IMG_SIZE * BOX_EXPAND_H
        assert bw == pytest.approx(expected_w, abs=2)
        assert bh == pytest.approx(expected_h, abs=2)


# ---------------------------------------------------------------------------
# Apply delta y BoxRefiner I/O
# ---------------------------------------------------------------------------
class TestApplyDelta:
    def test_zero_delta_is_idempotent(self):
        bbox = [100, 200, 300, 500]
        out = _apply_delta(bbox, np.zeros(4, dtype=np.float32), (1024, 1024))
        assert out == _bbox_clip(bbox, 1024, 1024)

    def test_positive_dx_moves_right(self):
        bbox = [400, 400, 500, 500]
        delta = np.array([0.3, 0.0, 0.0, 0.0], dtype=np.float32)
        out = _apply_delta(bbox, delta, (1024, 1024))
        cx_orig = (bbox[0] + bbox[2]) / 2
        cx_new = (out[0] + out[2]) / 2
        assert cx_new > cx_orig

    def test_positive_dw_grows_box(self):
        bbox = [400, 400, 500, 500]
        delta = np.array([0.0, 0.0, 0.3, 0.0], dtype=np.float32)
        out = _apply_delta(bbox, delta, (1024, 1024))
        assert (out[2] - out[0]) > (bbox[2] - bbox[0])


class TestBuildRefinerInput:
    def test_shape_and_range(self):
        gray = np.full((1024, 1024), 128, dtype=np.uint8)
        bbox = [400, 500, 500, 600]
        t = _build_refiner_input(gray, bbox)
        assert t.shape == (2, BOX_REFINER_SIZE, BOX_REFINER_SIZE)
        # canal 0: imagen normalizada [0,1]
        assert 0.0 <= t[0].min() and t[0].max() <= 1.0
        # canal 1: máscara binaria
        assert set(np.unique(t[1].numpy()).tolist()).issubset({0.0, 1.0})

    def test_mask_channel_marks_box_region(self):
        gray = np.full((1024, 1024), 100, dtype=np.uint8)
        # caja exactamente al centro
        bbox = [462, 462, 562, 562]
        t = _build_refiner_input(gray, bbox)
        mask_ch = t[1].numpy()
        # debe haber píxeles a 1 (la caja) y píxeles a 0 (el contexto)
        assert mask_ch.max() == 1.0
        assert mask_ch.min() == 0.0


# ---------------------------------------------------------------------------
# BoxRefinerNet forward (saturación)
# ---------------------------------------------------------------------------
class TestBoxRefinerForward:
    def test_output_saturated_within_bounds(self):
        torch.manual_seed(0)
        net = BoxRefinerNet().eval()
        # input random — los pesos también son random, pero tanh limita la salida
        x = torch.randn(4, 2, BOX_REFINER_SIZE, BOX_REFINER_SIZE) * 5.0  # rango grande
        with torch.no_grad():
            out = net(x)
        assert out.shape == (4, 4)
        assert out[:, :2].abs().max().item() <= BOX_REFINER_MAX_ABS_DXY + 1e-6
        assert out[:, 2:].abs().max().item() <= BOX_REFINER_MAX_ABS_LOG_SCALE + 1e-6
