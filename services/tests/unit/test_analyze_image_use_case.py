import io

import numpy as np
import pytest
from PIL import Image

from app.core.domain.entities.analysis import VertebraAnalysis
from app.core.use_cases.analyze_image import AnalyzeImageUseCase, InvalidImageError


@pytest.mark.asyncio
async def test_execute_returns_vertebra_analysis(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    result = await use_case.execute(dummy_image_bytes, "test.png")
    assert isinstance(result, VertebraAnalysis)
    assert len(result.study_id) == 36  # UUID formato XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX


@pytest.mark.asyncio
async def test_execute_stores_in_storage(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    await use_case.execute(dummy_image_bytes, "test.png")
    mock_storage_port.save.assert_called_once()


@pytest.mark.asyncio
async def test_execute_detects_vertebrae_in_mask(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    result = await use_case.execute(dummy_image_bytes, "test.png")
    detected_labels = {v.label for v in result.vertebrae if v.detected}
    assert "C7" in detected_labels
    assert "T1" in detected_labels
    assert "L1" in detected_labels


@pytest.mark.asyncio
async def test_execute_raises_on_invalid_bytes(mock_model_port, mock_storage_port):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    with pytest.raises(InvalidImageError):
        await use_case.execute(b"esto no es una imagen", "fake.png")


@pytest.mark.asyncio
async def test_execute_raises_on_small_image(
    small_image_bytes, mock_model_port, mock_storage_port
):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    with pytest.raises(InvalidImageError, match="512"):
        await use_case.execute(small_image_bytes, "small.png")


@pytest.mark.asyncio
async def test_processing_steps_recorded(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    result = await use_case.execute(dummy_image_bytes, "test.png")
    steps_str = " ".join(result.processing_steps)
    assert "CLAHE" in steps_str
    assert "SegFormer-B2" in steps_str


@pytest.mark.asyncio
async def test_mask_data_is_valid_png(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    result = await use_case.execute(dummy_image_bytes, "test.png")
    assert len(result.mask.data) > 0
    img = Image.open(io.BytesIO(result.mask.data))
    assert img.format == "PNG"


@pytest.mark.asyncio
async def test_vertebrae_list_has_22_elements(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    result = await use_case.execute(dummy_image_bytes, "test.png")
    assert len(result.vertebrae) == 22
