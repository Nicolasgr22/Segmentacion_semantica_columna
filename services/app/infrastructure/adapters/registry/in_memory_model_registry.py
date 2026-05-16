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
    processing_steps=[
        "Decodificación de imagen",
        "Letterbox 1024×1024 + normalización por percentiles",
        "VertebraPrompt-Net (512×512): heatmap + wh + offset",
        "DP anatómico → cajas T1–L5 con plantilla mediana",
        "BoxRefiner: corrección local de cajas (192×192)",
        "MedSAM box_only por caja → máscaras binarias",
        "Composición y reverse-letterbox al espacio original",
        "Cálculo métricas por vértebra",
        "Generación máscara coloreada",
    ],
)


# Métricas reportadas en el notebook
# notebooks/unet/SegmentacionSemanticaImagenes_UNet_Exp_BPaper_MLFlow.ipynb
# para Experimento B (val mean K-fold).
_PROGRESSIVE_UNET_METRICS = [
    ExperimentMetric(
        name="dice_binary",
        value=0.8250,
        description="Dice binario (vértebra vs fondo), val mean K-fold (4 folds)",
    ),
    ExperimentMetric(
        name="iou_binary",
        value=0.7077,
        description="IoU binario (vértebra vs fondo), val mean K-fold (4 folds)",
    ),
]


_PROGRESSIVE_UNET_BINARY = ModelCard(
    id="progressive-unet-binary",
    display_name="Progressive U-Net (paper-like, binario)",
    description=(
        "U-Net binaria con deep-supervision (3 side outputs) que reproduce el "
        "experimento del paper 'Analysis of Scoliosis'. Entrenada en grayscale "
        "256×512 con loss BCE+Dice. El modelo distingue vértebra vs fondo "
        "pero NO identifica anatómicamente T1..L5; para encajar en el contrato "
        "multi-clase del servicio, el adapter hace un band-split top-to-bottom "
        "del foreground en 17 bandas etiquetadas T1..L5."
    ),
    architecture="Progressive U-Net (4 niveles, deep-supervision, paper-like)",
    task="binary_vertebra_segmentation",
    classes=["vertebra"],
    checkpoints=[
        "model-pkg/exp_b_progressive_unet_binary_paper_like_logged_model/model.pth",
    ],
    metrics=_PROGRESSIVE_UNET_METRICS,
    dataset="MaIA Scoliosis (máscara binarizada: cualquier vértebra → 1)",
    notebook="notebooks/unet/SegmentacionSemanticaImagenes_UNet_Exp_BPaper_MLFlow.ipynb",
    status="active",
    extra={
        "experiment": "B",
        "input_size": "1x256x512",
        "input_channels": "1 (grayscale)",
        "threshold": "0.5 sobre sigmoid(logits)",
        "loss": "BCE + Dice",
        "remap_strategy": "band-split top-to-bottom → T1..L5 (IDs 6..22)",
    },
    processing_steps=[
        "Decodificación de imagen",
        "Conversión a escala de grises",
        "Resize a 512×256 (paper-like)",
        "Forward Progressive U-Net (binary, deep-supervision)",
        "Sigmoid + threshold 0.5 → máscara binaria",
        "Resize NEAREST al tamaño original",
        "Band-split top-to-bottom → IDs T1–L5 (6..22)",
        "Cálculo métricas por vértebra",
        "Generación máscara coloreada",
    ],
)


class InMemoryModelRegistry(ModelRegistryPort):
    """Registro en memoria con los modelos publicados por el servicio."""

    def __init__(self, models: Optional[list[ModelCard]] = None) -> None:
        seed = (
            models
            if models is not None
            else [_VERTEBRAPROMPT_BOXREFINER, _PROGRESSIVE_UNET_BINARY]
        )
        self._by_id: dict[str, ModelCard] = {m.id: m for m in seed}

    async def list_models(self) -> list[ModelCard]:
        return list(self._by_id.values())

    async def get_model(self, model_id: str) -> Optional[ModelCard]:
        return self._by_id.get(model_id)
