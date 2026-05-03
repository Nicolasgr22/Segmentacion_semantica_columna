import io

import numpy as np
import pytest
from PIL import Image

_XRAYS_URL = "/api/vertebraai/xrays"


def test_create_analysis_returns_201(test_client, dummy_image_bytes):
    response = test_client.post(
        _XRAYS_URL,
        files={"file": ("test.png", dummy_image_bytes, "image/png")},
    )
    assert response.status_code == 201


def test_create_analysis_response_has_required_fields(test_client, dummy_image_bytes):
    response = test_client.post(
        _XRAYS_URL,
        files={"file": ("test.png", dummy_image_bytes, "image/png")},
    )
    data = response.json()
    for field in ("study_id", "timestamp", "mask", "metrics", "vertebrae", "processing"):
        assert field in data, f"Campo faltante en respuesta: {field}"


def test_create_analysis_vertebrae_count_is_22(test_client, dummy_image_bytes):
    response = test_client.post(
        _XRAYS_URL,
        files={"file": ("test.png", dummy_image_bytes, "image/png")},
    )
    assert len(response.json()["vertebrae"]) == 22


def test_create_analysis_rejects_jpeg(test_client):
    img = Image.fromarray(np.zeros((512, 512, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    response = test_client.post(
        _XRAYS_URL,
        files={"file": ("test.jpg", buf.getvalue(), "image/jpeg")},
    )
    assert response.status_code == 400


def test_create_analysis_rejects_small_image(test_client, small_image_bytes):
    response = test_client.post(
        _XRAYS_URL,
        files={"file": ("small.png", small_image_bytes, "image/png")},
    )
    assert response.status_code == 400


def test_health_endpoint_returns_ok(test_client):
    response = test_client.get("/api/vertebraai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True


def test_export_endpoint_returns_404_for_unknown_analysis(test_client, mock_storage_port):
    from unittest.mock import AsyncMock
    mock_storage_port.get = AsyncMock(return_value=None)
    response = test_client.get(f"{_XRAYS_URL}/unknown-xray-id/exports/mask")
    assert response.status_code == 404
