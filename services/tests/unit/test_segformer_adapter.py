from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from app.infrastructure.adapters.model.segformer_adapter import SegFormerAdapter


@pytest.fixture
def adapter_with_mock_model():
    adapter = SegFormerAdapter(device="cpu", n_classes=23)

    fake_logits = torch.zeros(1, 23, 128, 128)
    fake_logits[0, 6, 30:40, 50:60] = 5.0  # T1 con alta confianza

    mock_output = MagicMock()
    mock_output.logits = fake_logits

    mock_model = MagicMock(return_value=mock_output)
    mock_processor = MagicMock(
        return_value={"pixel_values": torch.zeros(1, 3, 512, 512)}
    )

    adapter._model = mock_model
    adapter._processor = mock_processor
    adapter._loaded = True
    adapter._model_version = "test-mock-v0"
    return adapter


@pytest.mark.asyncio
async def test_predict_returns_model_output(adapter_with_mock_model):
    from app.core.domain.ports.model_port import ModelOutput
    image = np.zeros((512, 512, 3), dtype=np.uint8)
    result = await adapter_with_mock_model.predict(image)
    assert isinstance(result, ModelOutput)


@pytest.mark.asyncio
async def test_mask_shape_is_512x512(adapter_with_mock_model):
    image = np.zeros((512, 512, 3), dtype=np.uint8)
    result = await adapter_with_mock_model.predict(image)
    assert result.mask.shape == (512, 512)


@pytest.mark.asyncio
async def test_mask_values_in_valid_range(adapter_with_mock_model):
    image = np.zeros((512, 512, 3), dtype=np.uint8)
    result = await adapter_with_mock_model.predict(image)
    assert result.mask.max() <= 22


@pytest.mark.asyncio
async def test_probabilities_shape(adapter_with_mock_model):
    image = np.zeros((512, 512, 3), dtype=np.uint8)
    result = await adapter_with_mock_model.predict(image)
    assert result.probabilities.shape == (23, 512, 512)


def test_is_loaded_false_before_load():
    adapter = SegFormerAdapter(device="cpu", n_classes=23)
    assert adapter.is_loaded() is False
