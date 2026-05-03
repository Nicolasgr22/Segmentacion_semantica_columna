import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.domain.entities.analysis import (
    AnalysisMetrics,
    ModelMetrics,
    RegionMetrics,
    VertebraAnalysis,
    VertebralMask,
)
from app.core.domain.entities.vertebra import VertebralRegion, build_vertebrae_from_mask
from app.core.domain.ports.model_port import ModelOutput, ModelPort
from app.core.domain.ports.storage_port import StoragePort
from app.dependencies import get_model_adapter, get_storage_adapter
from app.main import app


@pytest.fixture
def dummy_image_bytes() -> bytes:
    img = Image.fromarray(
        np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def small_image_bytes() -> bytes:
    img = Image.fromarray(
        np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def dummy_mask_array() -> np.ndarray:
    mask = np.zeros((512, 512), dtype=np.uint8)
    mask[50:80, 220:260] = 1    # C7
    mask[100:140, 215:260] = 6  # T1
    mask[200:240, 210:255] = 11 # T6
    mask[350:400, 205:255] = 18 # L1
    mask[430:490, 200:260] = 22 # L5
    return mask


@pytest.fixture
def mock_model_output(dummy_mask_array) -> ModelOutput:
    probs = np.zeros((23, 512, 512), dtype=np.float32)
    probs[0] = 1.0
    for cls_id in [1, 6, 11, 18, 22]:
        rows, cols = np.where(dummy_mask_array == cls_id)
        if len(rows):
            probs[cls_id, rows, cols] = 0.95
            probs[0, rows, cols] = 0.05
    return ModelOutput(
        mask=dummy_mask_array,
        probabilities=probs,
        latency_ms=150.0,
        model_version="test-mock-v0",
    )


@pytest.fixture
def mock_model_port(mock_model_output) -> ModelPort:
    port = MagicMock(spec=ModelPort)
    port.predict = AsyncMock(return_value=mock_model_output)
    port.is_loaded.return_value = True
    port.get_model_version.return_value = "test-mock-v0"
    return port


@pytest.fixture
def mock_storage_port() -> StoragePort:
    port = MagicMock(spec=StoragePort)
    port.save = AsyncMock(side_effect=lambda a: a.study_id)
    port.get = AsyncMock(return_value=None)
    port.exists = AsyncMock(return_value=False)
    port.delete = AsyncMock(return_value=False)
    return port


@pytest.fixture
def test_client(mock_model_port, mock_storage_port) -> TestClient:
    app.dependency_overrides[get_model_adapter] = lambda: mock_model_port
    app.dependency_overrides[get_storage_adapter] = lambda: mock_storage_port
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()
