from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.v1.schemas.requests import ExportFormat
from app.core.use_cases.export_result import ExportResultUseCase, StudyNotFoundError
from app.dependencies import get_export_use_case

router = APIRouter(prefix="/xrays", tags=["xrays"])

_FILENAMES = {
    ExportFormat.PNG: "{xray_id}_original.png",
    ExportFormat.MASK: "{xray_id}_mask.png",
    ExportFormat.OVERLAY: "{xray_id}_overlay.png",
    ExportFormat.REPORT: "{xray_id}_report.json",
}


@router.get(
    "/{xray_id}/exports/{format}",
    summary="Exportar resultado de un análisis",
    responses={
        404: {"description": "Radiografía no encontrada"},
    },
)
async def get_xray_export(
    xray_id: str,
    format: ExportFormat,
    use_case: ExportResultUseCase = Depends(get_export_use_case),
) -> Response:
    try:
        data, media_type = await use_case.execute(xray_id, format.value)
    except StudyNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Radiografía '{xray_id}' no encontrada",
        )

    filename = _FILENAMES[format].format(xray_id=xray_id)
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
