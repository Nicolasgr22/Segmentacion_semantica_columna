"""Tests unitarios del adapter Unet++ por parches.

No se carga el checkpoint real (~262MB y requiere `segmentation_models_pytorch`).
Se inyecta un `nn.Module` dummy directamente en el adapter via `_model` para
validar el contrato I/O, la fusión Gaussiana y el remap de clases.
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest
import torch
import torch.nn as nn

from app.infrastructure.adapters.model.unetpp_patches_adapter import (
    FIRST_VERTEBRA_ID,
    LAST_VERTEBRA_ID,
    NUM_MODEL_CLASSES,
    N_SERVICE_CLASSES,
    PATCH_AREA,
    PATCH_SIZE,
    SIGMA,
    STRIDE_RATIO,
    UnetPlusPlusPatchesAdapter,
    _apply_clahe_rgb,
    _gaussian_window,
    _model_to_service_class_id,
    _normalize,
    _patch_inference,
    _remap_to_service_contract,
)


# ---------------------------------------------------------------------------
# Modelos dummy
# ---------------------------------------------------------------------------
class _ConstantClassModel(nn.Module):
    """Modelo que asigna el grueso de la probabilidad a una clase fija."""

    def __init__(self, target_class: int) -> None:
        super().__init__()
        self.target_class = target_class

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, _, H, W = x.shape
        logits = torch.full((B, NUM_MODEL_CLASSES, H, W), -5.0)
        logits[:, self.target_class, :, :] = 10.0
        return logits


class _StripeClassModel(nn.Module):
    """Distintas clases en distintas franjas verticales (para validar argmax)."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, _, H, W = x.shape
        logits = torch.full((B, NUM_MODEL_CLASSES, H, W), -5.0)
        # Tercio superior: clase 1 (T1 → service 6)
        logits[:, 1, : H // 3, :] = 10.0
        # Tercio medio: clase 7 (T7 → service 12)
        logits[:, 7, H // 3 : 2 * H // 3, :] = 10.0
        # Tercio inferior: clase 17 (L5 → service 22)
        logits[:, 17, 2 * H // 3 :, :] = 10.0
        return logits


def _make_adapter_with_model(model: nn.Module) -> UnetPlusPlusPatchesAdapter:
    adapter = UnetPlusPlusPatchesAdapter(device="cpu")
    adapter._model = model
    adapter._loaded = True
    adapter._model_version = "test-dummy-v0"
    return adapter


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Constantes alineadas con el contrato del servicio y el notebook
# ---------------------------------------------------------------------------
def test_constants_match_contract():
    assert N_SERVICE_CLASSES == 23
    assert FIRST_VERTEBRA_ID == 6      # T1
    assert LAST_VERTEBRA_ID == 22      # L5
    assert NUM_MODEL_CLASSES == 18     # bg + T1..T12 + L1..L5
    assert PATCH_SIZE == 128
    assert PATCH_AREA == 0.5
    assert SIGMA == 50.0
    assert STRIDE_RATIO == 4


def test_class_remap_is_bijective_to_service_ids():
    # 0 → 0, 1..12 → 6..17 (T1..T12), 13..17 → 18..22 (L1..L5)
    assert _model_to_service_class_id(0) == 0
    assert _model_to_service_class_id(1) == 6
    assert _model_to_service_class_id(12) == 17
    assert _model_to_service_class_id(13) == 18
    assert _model_to_service_class_id(17) == 22
    seen = {_model_to_service_class_id(k) for k in range(NUM_MODEL_CLASSES)}
    assert len(seen) == NUM_MODEL_CLASSES


# ---------------------------------------------------------------------------
# Preprocesamiento
# ---------------------------------------------------------------------------
class TestPreprocessing:
    def test_clahe_preserves_shape_and_dtype(self):
        rgb = np.random.randint(0, 255, (200, 150, 3), dtype=np.uint8)
        out = _apply_clahe_rgb(rgb)
        assert out.shape == rgb.shape
        assert out.dtype == np.uint8

    def test_normalize_returns_float32_in_imagenet_range(self):
        rgb = np.full((10, 10, 3), 128, dtype=np.uint8)
        out = _normalize(rgb)
        assert out.dtype == np.float32
        # 128/255 ≈ 0.502, (0.502 - 0.485)/0.229 ≈ 0.074 para canal R.
        assert abs(out[0, 0, 0] - (128 / 255.0 - 0.485) / 0.229) < 1e-5

    def test_gaussian_window_is_symmetric_and_positive(self):
        w = _gaussian_window(64, 10.0, torch.device("cpu"))
        assert w.shape == (64, 64)
        assert torch.all(w > 0)
        assert torch.allclose(w, w.t())          # simétrico
        assert w[32, 32] == w.max()              # máximo en el centro


# ---------------------------------------------------------------------------
# Remap a contrato del servicio
# ---------------------------------------------------------------------------
class TestRemapToServiceContract:
    def test_background_only_keeps_class_zero(self):
        probs = np.zeros((NUM_MODEL_CLASSES, 40, 30), dtype=np.float32)
        probs[0] = 0.95
        for k in range(1, NUM_MODEL_CLASSES):
            probs[k] = 0.05 / (NUM_MODEL_CLASSES - 1)
        mask, proba = _remap_to_service_contract(probs)
        assert mask.dtype == np.uint8
        assert mask.shape == (40, 30)
        assert mask.max() == 0
        assert proba.shape == (N_SERVICE_CLASSES, 40, 30)
        assert proba.dtype == np.float32
        # Cervicales (1..5) deben permanecer en cero porque el modelo no los emite.
        assert np.all(proba[1:FIRST_VERTEBRA_ID] == 0.0)

    def test_l5_class_remaps_to_service_22(self):
        # Mayor prob en clase del modelo 17 = L5 → service 22.
        probs = np.full((NUM_MODEL_CLASSES, 20, 20), 0.01, dtype=np.float32)
        probs[17] = 0.9
        mask, proba = _remap_to_service_contract(probs)
        assert np.all(mask == LAST_VERTEBRA_ID)
        assert np.allclose(proba[LAST_VERTEBRA_ID], 0.9)
        assert np.allclose(proba[1:FIRST_VERTEBRA_ID], 0.0)

    def test_all_thoracic_classes_map_to_service_6_through_17(self):
        H, W = 18, 4
        probs = np.full((NUM_MODEL_CLASSES, H, W), 0.001, dtype=np.float32)
        for k in range(1, NUM_MODEL_CLASSES):
            probs[k, k - 1, :] = 0.9
        mask, _ = _remap_to_service_contract(probs)
        expected = set(range(FIRST_VERTEBRA_ID, LAST_VERTEBRA_ID + 1))
        assert set(np.unique(mask)).issubset(expected | {0})


# ---------------------------------------------------------------------------
# Sliding window (función pura)
# ---------------------------------------------------------------------------
class TestPatchInference:
    def test_constant_class_model_produces_target_after_remap(self):
        model = _ConstantClassModel(target_class=5)
        image_norm = np.zeros((96, 96, 3), dtype=np.float32)
        probs = _patch_inference(
            model, image_norm, torch.device("cpu"),
            patch_area=0.5, stride_ratio=2, sigma=10.0,
        )
        assert probs.shape == (NUM_MODEL_CLASSES, 96, 96)
        # La clase target debe dominar en cada pixel.
        argmax = probs.argmax(axis=0)
        assert np.all(argmax == 5)

    def test_output_probabilities_are_normalized(self):
        # Tras la fusión (accum / weights) la prob debe estar ~en [0, 1].
        model = _ConstantClassModel(target_class=3)
        image_norm = np.zeros((80, 60, 3), dtype=np.float32)
        probs = _patch_inference(
            model, image_norm, torch.device("cpu"),
            patch_area=0.5, stride_ratio=2, sigma=10.0,
        )
        # Cada pixel: sumando los 18 canales debería estar muy cerca de 1.0,
        # porque las probabilidades de cada parche eran softmax (suman 1) y la
        # fusión ponderada se normaliza al final. El eps=1e-5 del denominador
        # rebaja ligeramente la suma en píxeles de borde donde la Gaussiana
        # acumula poco peso, por eso la tolerancia es ~1%.
        sums = probs.sum(axis=0)
        assert np.allclose(sums, 1.0, atol=1e-2)


# ---------------------------------------------------------------------------
# Adapter end-to-end con modelo dummy
# ---------------------------------------------------------------------------
class TestAdapterPredict:
    def test_predict_returns_contract_shapes(self):
        adapter = _make_adapter_with_model(_ConstantClassModel(target_class=0))
        rgb = np.random.randint(0, 255, (160, 120, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        assert out.mask.shape == (160, 120)
        assert out.mask.dtype == np.uint8
        assert out.probabilities.shape == (N_SERVICE_CLASSES, 160, 120)
        assert out.probabilities.dtype == np.float32
        assert out.latency_ms > 0
        assert out.model_version == "test-dummy-v0"

    def test_predict_background_only_returns_empty_mask(self):
        adapter = _make_adapter_with_model(_ConstantClassModel(target_class=0))
        rgb = np.random.randint(0, 255, (160, 120, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        assert out.mask.max() == 0

    def test_predict_t1_class_remaps_to_service_6(self):
        adapter = _make_adapter_with_model(_ConstantClassModel(target_class=1))
        rgb = np.random.randint(0, 255, (160, 120, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        assert np.all(out.mask == FIRST_VERTEBRA_ID)

    def test_predict_cervical_channels_stay_zero(self):
        adapter = _make_adapter_with_model(_StripeClassModel())
        rgb = np.random.randint(0, 255, (180, 100, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        # El modelo nunca emite cervicales → canales 1..5 en cero.
        assert np.all(out.probabilities[1:FIRST_VERTEBRA_ID] == 0.0)
        # La máscara mezcla T1 (6), T7 (12) y L5 (22).
        unique = set(np.unique(out.mask).tolist()) - {0}
        assert unique.issubset({6, 12, 22})

    def test_predict_accepts_grayscale_input(self):
        adapter = _make_adapter_with_model(_ConstantClassModel(target_class=1))
        gray = np.random.randint(0, 255, (140, 100), dtype=np.uint8)
        out = _run(adapter.predict(gray))
        assert out.mask.shape == (140, 100)
        assert out.mask.max() == FIRST_VERTEBRA_ID

    def test_predict_strips_alpha_channel(self):
        adapter = _make_adapter_with_model(_ConstantClassModel(target_class=1))
        rgba = np.random.randint(0, 255, (130, 110, 4), dtype=np.uint8)
        out = _run(adapter.predict(rgba))
        assert out.mask.shape == (130, 110)

    def test_predict_raises_when_not_loaded(self):
        adapter = UnetPlusPlusPatchesAdapter(device="cpu")
        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        with pytest.raises(RuntimeError, match="no cargado"):
            _run(adapter.predict(rgb))
