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
async def test_execute_accepts_small_image(
    small_image_bytes, mock_model_port, mock_storage_port
):
    """El adapter reescala internamente; imágenes <512 px ya NO se rechazan."""
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    result = await use_case.execute(small_image_bytes, "small.png")
    assert isinstance(result, VertebraAnalysis)


@pytest.mark.asyncio
async def test_execute_raises_on_tiny_image(
    tiny_image_bytes, mock_model_port, mock_storage_port
):
    """Mínimo razonable: 32×32 px. Debajo de eso (thumbnails, errores) → 400."""
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    with pytest.raises(InvalidImageError, match="32"):
        await use_case.execute(tiny_image_bytes, "tiny.png")


@pytest.mark.asyncio
async def test_processing_steps_recorded(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    """Los pasos del pipeline ya no se hardcodean en el use case: vienen
    declarativos del ModelCard (registry) y el router los pasa como parámetro.
    El use case solo los propaga al análisis. Aquí simulamos al router."""
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    declared_steps = [
        "Decodificación de imagen",
        "Letterbox 1024×1024 + normalización por percentiles",
        "VertebraPrompt-Net (512×512): heatmap + wh + offset",
        "BoxRefiner: corrección local de cajas (192×192)",
        "MedSAM box_only por caja → máscaras binarias",
    ]
    result = await use_case.execute(
        dummy_image_bytes, "test.png", processing_steps=declared_steps
    )
    assert result.processing_steps == declared_steps


@pytest.mark.asyncio
async def test_processing_steps_default_to_empty(
    dummy_image_bytes, mock_model_port, mock_storage_port
):
    """Si el caller no pasa pasos, la respuesta queda con lista vacía. El
    frontend cae al placeholder genérico ('Procesando…') en ese caso."""
    use_case = AnalyzeImageUseCase(model=mock_model_port, storage=mock_storage_port)
    result = await use_case.execute(dummy_image_bytes, "test.png")
    assert result.processing_steps == []


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
