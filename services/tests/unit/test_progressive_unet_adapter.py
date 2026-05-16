"""Tests unitarios del adapter Progressive U-Net binario (Experimento B).

Estos tests NO cargan el checkpoint real (.pth pesa ~26MB y depende de Colab
para deserializar). En su lugar inyectamos un `nn.Module` dummy directamente
en el adapter via `_model` para validar el contrato I/O y el band-split.
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest
import torch
import torch.nn as nn

from app.infrastructure.adapters.model.progressive_unet_adapter import (
    FIRST_VERTEBRA_ID,
    INPUT_H,
    INPUT_W,
    LAST_VERTEBRA_ID,
    NUM_BANDS,
    N_SERVICE_CLASSES,
    PaperConvBlock,
    ProgressiveUNetBinaryAdapter,
    ProgressiveUNetBinaryPaperLike,
    _band_split_to_service_mask,
)


# ---------------------------------------------------------------------------
# Modelos dummy para inyectar sin cargar el .pth real.
# ---------------------------------------------------------------------------
class _AllForegroundModel(nn.Module):
    """Devuelve logits altos en todo el frame → sigmoid≈1, mask all-foreground."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.full((x.shape[0], 1, x.shape[2], x.shape[3]), 10.0)


class _AllBackgroundModel(nn.Module):
    """Devuelve logits negativos → sigmoid≈0, mask sin foreground."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.full((x.shape[0], 1, x.shape[2], x.shape[3]), -10.0)


class _CenteredStripeModel(nn.Module):
    """Devuelve foreground sólo en una franja vertical centrada."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        H = x.shape[2]
        logits = torch.full((x.shape[0], 1, H, x.shape[3]), -10.0)
        top = H // 4
        bottom = 3 * H // 4
        logits[:, :, top:bottom, :] = 10.0
        return logits


def _make_adapter_with_model(model: nn.Module) -> ProgressiveUNetBinaryAdapter:
    adapter = ProgressiveUNetBinaryAdapter(device="cpu")
    adapter._model = model
    adapter._loaded = True
    adapter._model_version = "test-dummy-v0"
    return adapter


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Arquitectura: forward smoke test
# ---------------------------------------------------------------------------
class TestArchitecture:
    def test_paper_conv_block_io(self):
        block = PaperConvBlock(in_channels=1, out_channels=8, dropout=0.0)
        x = torch.randn(1, 1, 32, 64)
        out = block(x)
        assert out.shape == (1, 8, 32, 64)

    def test_progressive_unet_forward_shape(self):
        # base_channels reducido para test rápido.
        model = ProgressiveUNetBinaryPaperLike(
            in_channels=1, out_channels=1, base_channels=4, dropout=0.0
        )
        model.eval()
        x = torch.randn(1, 1, INPUT_H, INPUT_W)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (1, 1, INPUT_H, INPUT_W)


# ---------------------------------------------------------------------------
# Band-split (función pura)
# ---------------------------------------------------------------------------
class TestBandSplit:
    def test_empty_foreground_returns_zero_mask(self):
        H, W = 100, 80
        binary_mask = np.zeros((H, W), dtype=np.uint8)
        prob_fg = np.zeros((H, W), dtype=np.float32)
        mask, proba = _band_split_to_service_mask(binary_mask, prob_fg)
        assert mask.shape == (H, W)
        assert mask.dtype == np.uint8
        assert mask.max() == 0
        assert proba.shape == (N_SERVICE_CLASSES, H, W)
        assert proba.dtype == np.float32
        # Canal 0 (fondo) = 1 - prob_fg = 1.0 en todos lados.
        assert np.allclose(proba[0], 1.0)
        # Canales 1..22 quedan en cero.
        assert np.allclose(proba[1:], 0.0)

    def test_full_foreground_produces_all_17_band_ids(self):
        H, W = 340, 100
        binary_mask = np.ones((H, W), dtype=np.uint8)
        prob_fg = np.full((H, W), 0.9, dtype=np.float32)
        mask, proba = _band_split_to_service_mask(binary_mask, prob_fg)
        unique = set(np.unique(mask).tolist())
        expected = set(range(FIRST_VERTEBRA_ID, LAST_VERTEBRA_ID + 1))
        assert unique == expected
        # Canales cervicales (1..5) deben quedar todos en cero.
        assert np.all(proba[1:FIRST_VERTEBRA_ID] == 0.0)
        # Cada banda recibe la prob_fg sólo en sus filas.
        for class_id in expected:
            assert proba[class_id].max() == pytest.approx(0.9, abs=1e-5)

    def test_no_pixels_below_threshold_in_cervical_band(self):
        # Caso patológico: foreground sólo en filas centrales.
        H, W = 50, 50
        binary_mask = np.zeros((H, W), dtype=np.uint8)
        binary_mask[20:30, :] = 1
        prob_fg = binary_mask.astype(np.float32) * 0.8
        mask, proba = _band_split_to_service_mask(binary_mask, prob_fg)
        # Fondo arriba/abajo: clase 0.
        assert mask[0, 0] == 0
        assert mask[-1, -1] == 0
        # Foreground en el bbox vertical: clases en [6..22].
        for y in range(20, 30):
            assert mask[y, 25] >= FIRST_VERTEBRA_ID
            assert mask[y, 25] <= LAST_VERTEBRA_ID


# ---------------------------------------------------------------------------
# Adapter end-to-end con modelo dummy
# ---------------------------------------------------------------------------
class TestAdapterPredict:
    def test_predict_returns_contract_shapes(self):
        adapter = _make_adapter_with_model(_AllForegroundModel())
        rgb = np.random.randint(0, 255, (320, 240, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        assert out.mask.shape == (320, 240)
        assert out.mask.dtype == np.uint8
        assert out.probabilities.shape == (N_SERVICE_CLASSES, 320, 240)
        assert out.probabilities.dtype == np.float32
        assert out.latency_ms > 0
        assert out.model_version == "test-dummy-v0"

    def test_all_foreground_assigns_all_t1_l5_ids(self):
        adapter = _make_adapter_with_model(_AllForegroundModel())
        rgb = np.random.randint(0, 255, (340, 200, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        unique = set(np.unique(out.mask).tolist())
        # All foreground → todas las bandas T1..L5.
        expected = set(range(FIRST_VERTEBRA_ID, LAST_VERTEBRA_ID + 1))
        assert unique == expected
        # Canales cervicales siempre cero.
        assert np.all(out.probabilities[1:FIRST_VERTEBRA_ID] == 0.0)

    def test_all_background_returns_empty_mask(self):
        adapter = _make_adapter_with_model(_AllBackgroundModel())
        rgb = np.random.randint(0, 255, (200, 150, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        assert out.mask.max() == 0
        # Canal 0 alto en todas partes.
        assert out.probabilities[0].min() > 0.9

    def test_centered_stripe_produces_subset_of_bands(self):
        adapter = _make_adapter_with_model(_CenteredStripeModel())
        rgb = np.random.randint(0, 255, (400, 200, 3), dtype=np.uint8)
        out = _run(adapter.predict(rgb))
        unique = set(np.unique(out.mask).tolist())
        # Hay fondo (0) y al menos varias bandas T-L.
        assert 0 in unique
        non_bg = unique - {0}
        assert non_bg.issubset(set(range(FIRST_VERTEBRA_ID, LAST_VERTEBRA_ID + 1)))
        # Todas las bandas deben aparecer porque la franja cubre todo el rango
        # vertical del bbox foreground y se divide en 17.
        assert len(non_bg) == NUM_BANDS

    def test_predict_accepts_grayscale_input(self):
        adapter = _make_adapter_with_model(_AllForegroundModel())
        gray = np.random.randint(0, 255, (256, 200), dtype=np.uint8)
        out = _run(adapter.predict(gray))
        assert out.mask.shape == (256, 200)
        assert out.mask.max() == LAST_VERTEBRA_ID

    def test_predict_strips_alpha_channel(self):
        adapter = _make_adapter_with_model(_AllForegroundModel())
        rgba = np.random.randint(0, 255, (180, 220, 4), dtype=np.uint8)
        out = _run(adapter.predict(rgba))
        assert out.mask.shape == (180, 220)

    def test_predict_raises_when_not_loaded(self):
        adapter = ProgressiveUNetBinaryAdapter(device="cpu")
        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        with pytest.raises(RuntimeError, match="no cargado"):
            _run(adapter.predict(rgb))


# ---------------------------------------------------------------------------
# Sanity: constantes alineadas con el contrato del servicio
# ---------------------------------------------------------------------------
def test_constants_match_service_contract():
    assert N_SERVICE_CLASSES == 23
    assert FIRST_VERTEBRA_ID == 6      # T1
    assert LAST_VERTEBRA_ID == 22      # L5
    assert NUM_BANDS == 17             # T1..L5
    assert INPUT_W == 512 and INPUT_H == 256
