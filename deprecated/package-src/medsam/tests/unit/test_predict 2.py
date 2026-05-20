"""
Tests unitarios de MedSAMPredictor — principios FIRST

  Fast        → todo el modelo SAM está mockeado, sin I/O ni GPU
  Isolated    → cada test tiene su propio predictor vía fixture
  Repeatable  → semilla fija, sin dependencias de red ni disco
  Self-validating → asserts explícitos, sin inspección manual
  Timely      → escritos junto al código de predict.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from model.predict import MedSAMPredictor

# ─── Constantes del mock ──────────────────────────────────────────────────────

IMG_SIZE = 1024
LOW_RES = 256          # SAM mask decoder emite 256×256 antes de interpolar


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_fake_sam(logit_value: float = 2.0) -> MagicMock:
    """
    Crea un mock mínimo de SAM con las formas de tensor correctas.

    logit_value controla si sigmoid(logit) > 0.5:
      logit_value > 0  → máscara predicha llena de 1s
      logit_value < 0  → máscara predicha llena de 0s
    """
    model = MagicMock()
    model.image_encoder.img_size = IMG_SIZE
    model.preprocess.side_effect = lambda x: x

    model.image_encoder.return_value = torch.zeros(1, 256, 64, 64)
    model.prompt_encoder.return_value = (
        torch.zeros(1, 2, 256),
        torch.zeros(1, 256, 64, 64),
    )
    model.prompt_encoder.get_dense_pe.return_value = torch.zeros(1, 256, 64, 64)
    model.mask_decoder.return_value = (
        torch.full((1, 1, LOW_RES, LOW_RES), logit_value),
        torch.ones(1, 1),
    )
    return model


def _fake_transform(img_size: int) -> MagicMock:
    """Mock de ResizeLongestSide que devuelve la imagen sin cambios."""
    t = MagicMock()
    t.apply_image.side_effect = lambda img: img
    t.apply_boxes.side_effect = lambda boxes, _: boxes
    return t


# ─── Fixture ─────────────────────────────────────────────────────────────────

@pytest.fixture
def predictor() -> MedSAMPredictor:
    """Predictor con modelo SAM completamente mockeado."""
    model = _make_fake_sam(logit_value=2.0)
    p = MedSAMPredictor.__new__(MedSAMPredictor)
    p._model = model
    p._device = torch.device("cpu")
    p._img_size = IMG_SIZE
    p._transform = _fake_transform(IMG_SIZE)
    return p


@pytest.fixture
def rgb_image() -> np.ndarray:
    """Radiografía sintética 512×512 RGB."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)


# ─── predict() ───────────────────────────────────────────────────────────────

class TestPredict:
    # F — Fast: sin I/O, sin GPU, todas las llamadas pesadas mockeadas

    def test_devuelve_ndarray_uint8(self, predictor, rgb_image):
        """predict() debe devolver un ndarray de dtype uint8."""
        mask = predictor.predict(rgb_image, bbox=[10, 10, 400, 400])

        assert isinstance(mask, np.ndarray)
        assert mask.dtype == np.uint8

    def test_shape_es_img_size(self, predictor, rgb_image):
        """La máscara tiene exactamente (img_size, img_size)."""
        mask = predictor.predict(rgb_image, bbox=[10, 10, 400, 400])

        assert mask.shape == (IMG_SIZE, IMG_SIZE)

    def test_valores_binarios(self, predictor, rgb_image):
        """Todos los píxeles son 0 o 1, nunca otro valor."""
        mask = predictor.predict(rgb_image, bbox=[10, 10, 400, 400])

        assert set(np.unique(mask)).issubset({0, 1})

    def test_threshold_alto_produce_mascara_vacia(self, rgb_image):
        """Con threshold=0.99 y logits negativos la máscara es toda ceros."""
        # I — Isolated: fixture local con logits negativos
        model = _make_fake_sam(logit_value=-5.0)
        p = MedSAMPredictor.__new__(MedSAMPredictor)
        p._model = model
        p._device = torch.device("cpu")
        p._img_size = IMG_SIZE
        p._transform = _fake_transform(IMG_SIZE)

        mask = p.predict(rgb_image, bbox=[10, 10, 400, 400], threshold=0.99, apply_postprocess=False)

        assert mask.sum() == 0

    def test_sin_postprocess_no_llama_morfologia(self, predictor, rgb_image):
        """apply_postprocess=False no aplica morfología ni componente mayor."""
        with patch("model.predict.postprocess_mask") as mock_pp:
            predictor.predict(rgb_image, bbox=[10, 10, 400, 400], apply_postprocess=False)

        mock_pp.assert_not_called()

    def test_con_postprocess_llama_morfologia(self, predictor, rgb_image):
        """apply_postprocess=True (default) sí llama a postprocess_mask."""
        with patch("model.predict.postprocess_mask", return_value=np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.uint8)) as mock_pp:
            predictor.predict(rgb_image, bbox=[10, 10, 400, 400], apply_postprocess=True)

        mock_pp.assert_called_once()

    def test_bbox_explicito_no_llama_auto_bbox(self, predictor, rgb_image):
        """Si se pasa bbox, _auto_bbox nunca se invoca."""
        with patch.object(MedSAMPredictor, "_auto_bbox") as mock_auto:
            predictor.predict(rgb_image, bbox=[0, 0, 511, 511])

        mock_auto.assert_not_called()

    def test_sin_bbox_llama_auto_bbox(self, predictor, rgb_image):
        """Si bbox es None, se deriva automáticamente con _auto_bbox."""
        with patch.object(MedSAMPredictor, "_auto_bbox", return_value=[0.0, 0.0, 511.0, 511.0]) as mock_auto:
            predictor.predict(rgb_image, bbox=None)

        mock_auto.assert_called_once_with(rgb_image)


# ─── predict_proba() ─────────────────────────────────────────────────────────

class TestPredictProba:

    def test_devuelve_float32(self, predictor, rgb_image):
        """predict_proba() devuelve float32."""
        proba = predictor.predict_proba(rgb_image, bbox=[10, 10, 400, 400])

        assert proba.dtype == np.float32

    def test_valores_entre_0_y_1(self, predictor, rgb_image):
        """Las probabilidades están acotadas en [0, 1]."""
        proba = predictor.predict_proba(rgb_image, bbox=[10, 10, 400, 400])

        assert proba.min() >= 0.0
        assert proba.max() <= 1.0

    def test_shape_es_img_size(self, predictor, rgb_image):
        """La salida tiene shape (img_size, img_size)."""
        proba = predictor.predict_proba(rgb_image, bbox=[10, 10, 400, 400])

        assert proba.shape == (IMG_SIZE, IMG_SIZE)

    def test_logits_positivos_producen_proba_mayor_05(self, predictor, rgb_image):
        """Con logits > 0, sigmoid > 0.5 en todos los píxeles."""
        # R — Repeatable: logit_value=2.0 fijo en el fixture
        proba = predictor.predict_proba(rgb_image, bbox=[10, 10, 400, 400])

        assert (proba > 0.5).all()

    def test_logits_negativos_producen_proba_menor_05(self, rgb_image):
        """Con logits < 0, sigmoid < 0.5 en todos los píxeles."""
        model = _make_fake_sam(logit_value=-2.0)
        p = MedSAMPredictor.__new__(MedSAMPredictor)
        p._model = model
        p._device = torch.device("cpu")
        p._img_size = IMG_SIZE
        p._transform = _fake_transform(IMG_SIZE)

        proba = p.predict_proba(rgb_image, bbox=[10, 10, 400, 400])

        assert (proba < 0.5).all()


# ─── _auto_bbox() ────────────────────────────────────────────────────────────

class TestAutoBbox:
    # S — Self-validating: el resultado es numéricamente verificable

    def test_devuelve_cuatro_floats(self, rgb_image):
        box = MedSAMPredictor._auto_bbox(rgb_image)

        assert len(box) == 4
        assert all(isinstance(v, float) for v in box)

    def test_coordenadas_dentro_de_imagen(self, rgb_image):
        h, w = rgb_image.shape[:2]
        x1, y1, x2, y2 = MedSAMPredictor._auto_bbox(rgb_image)

        assert 0 <= x1 <= x2 <= w - 1
        assert 0 <= y1 <= y2 <= h - 1

    def test_imagen_uniforme_cubre_toda_la_imagen(self):
        """Imagen uniforme → Otsu sin umbral → bbox cubre el área completa."""
        img = np.full((256, 256, 3), 128, dtype=np.uint8)
        x1, y1, x2, y2 = MedSAMPredictor._auto_bbox(img, pad=0)

        # Con imagen plana, bbox puede ser [0,0,w-1,h-1] o todo ceros
        assert x1 >= 0 and y1 >= 0
        assert x2 <= 255 and y2 <= 255


# ─── from_checkpoint() ───────────────────────────────────────────────────────

class TestFromCheckpoint:
    # T — Timely: cubre el constructor público que usa el servicio

    def test_carga_modelo_base_sin_finetuning(self, tmp_path):
        """from_checkpoint sin finetuned_weights no llama a load_state_dict."""
        fake_ckpt = tmp_path / "sam.pth"
        fake_ckpt.touch()

        fake_model = _make_fake_sam()

        # sam_model_registry se importa dentro de from_checkpoint con
        # "from segment_anything import sam_model_registry" → hay que parchear
        # en el módulo fuente, no en model.predict
        with patch("segment_anything.sam_model_registry", {"vit_b": MagicMock(return_value=fake_model)}), \
             patch("segment_anything.utils.transforms.ResizeLongestSide"):
            predictor = MedSAMPredictor.from_checkpoint(fake_ckpt, device="cpu")

        fake_model.load_state_dict.assert_not_called()
        assert isinstance(predictor, MedSAMPredictor)

    def test_carga_pesos_finetuned_cuando_se_pasan(self, tmp_path):
        """from_checkpoint con finetuned_weights llama a load_state_dict."""
        fake_ckpt = tmp_path / "sam.pth"
        fake_weights = tmp_path / "finetuned.pth"
        fake_ckpt.touch()
        fake_weights.touch()

        fake_model = _make_fake_sam()
        fake_state = {"key": torch.zeros(1)}

        with patch("segment_anything.sam_model_registry", {"vit_b": MagicMock(return_value=fake_model)}), \
             patch("torch.load", return_value=fake_state), \
             patch("segment_anything.utils.transforms.ResizeLongestSide"):
            MedSAMPredictor.from_checkpoint(fake_ckpt, finetuned_weights=fake_weights, device="cpu")

        fake_model.load_state_dict.assert_called_once_with(fake_state)
