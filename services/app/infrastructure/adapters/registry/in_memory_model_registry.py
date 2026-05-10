from __future__ import annotations

from typing import Optional

from app.core.domain.entities.model_card import ExperimentMetric, ModelCard
from app.core.domain.ports.model_registry_port import ModelRegistryPort


# Métricas reportadas en notebooks/medsam_pipeline/results_summary/comparativo_modelos.md
# para el modelo ganador `vertebraprompt_boxrefiner` evaluado en test.
_WINNER_METRICS = [
    ExperimentMetric(
        name="dice_strict",
        value=0.5530,
        description="Dice con coincidencia anatómica estricta (T1 vs T1, ...)",
    ),
    ExperimentMetric(
        name="iou_strict",
        value=0.4795,
        description="IoU con coincidencia anatómica estricta",
    ),
    ExperimentMetric(
        name="dice_flexible",
        value=0.7678,
        description="Dice flexible: mejor caja para cada GT sin importar el nombre",
    ),
    ExperimentMetric(
        name="iou_flexible",
        value=0.6615,
        description="IoU flexible: mejor caja para cada GT sin importar el nombre",
    ),
]


_VERTEBRAPROMPT_BOXREFINER = ModelCard(
    id="medsam",
    display_name="VertebraPrompt + BoxRefiner + MedSAM",
    description=(
        "Pipeline ganador del proyecto MaIA. VertebraPrompt-Net propone cajas "
        "con identidad anatómica T1–L5; BoxRefiner ajusta centro y tamaño con "
        "información local; MedSAM (decoder + último bloque del encoder ajustados) "
        "produce las máscaras vertebrales finales. Mejora consistente sobre la "
        "base NN-SAM en Dice/IoU estricto y flexible."
    ),
    architecture="VertebraPromptNet (U-Net + cabezas CenterNet) → BoxRefiner (CNN local) → MedSAM ViT-B fine-tuned",
    task="instance_segmentation_vertebrae",
    classes=[
        "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12",
        "L1", "L2", "L3", "L4", "L5",
    ],
    checkpoints=[
        "model-pkg/medsam/vertebraprompt_net_auxiliar_best.pt",
        "model-pkg/medsam/box_refiner_best.pt",
        "model-pkg/medsam/medsam_decoder_encoder_parcial_entrenado_vertebraprompt_aux.pt",
    ],
    metrics=_WINNER_METRICS,
    dataset="MaIA Scoliosis (split estratificado train/val/test)",
    notebook="notebooks/medsam_pipeline/notebooks/06_estrategia_ganadora_vertebraprompt_boxrefiner.ipynb",
    status="active",
    extra={
        "baseline_comparison": "NN-SAM + MedSAM",
        "delta_dice_strict_vs_baseline": "+0.0134",
        "delta_dice_flexible_vs_baseline": "+0.0191",
        "image_size": "1024x1024",
        "input_channels": "1 (grayscale RGB-broadcasted)",
    },
)


class InMemoryModelRegistry(ModelRegistryPort):
    """Registro en memoria con los modelos publicados por el servicio."""

    def __init__(self, models: Optional[list[ModelCard]] = None) -> None:
        seed = models if models is not None else [_VERTEBRAPROMPT_BOXREFINER]
        self._by_id: dict[str, ModelCard] = {m.id: m for m in seed}

    async def list_models(self) -> list[ModelCard]:
        return list(self._by_id.values())

    async def get_model(self, model_id: str) -> Optional[ModelCard]:
        return self._by_id.get(model_id)
