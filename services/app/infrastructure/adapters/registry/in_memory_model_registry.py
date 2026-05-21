from __future__ import annotations

from typing import Optional

from app.core.domain.entities.model_card import ExperimentMetric, ModelCard
from app.core.domain.ports.model_registry_port import ModelRegistryPort


# Métricas reportadas en notebooks/medsam_pipeline/results_summary/comparativo_modelos.md
# para el modelo ganador `vertebraprompt_boxrefiner` evaluado en test.
# irnos con la flexible 
_WINNER_METRICS = [
    # ExperimentMetric(
    #     name="dice_strict",
    #     value=0.5530,
    #     description="Dice con coincidencia anatómica estricta (T1 vs T1, ...)",
    # ),
    # ExperimentMetric(
    #     name="iou_strict",
    #     value=0.4795,
    #     description="IoU con coincidencia anatómica estricta",
    # ),
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


# Métricas reportadas en notebooks/unet++/Unet++_patches.ipynb. La predicción
# por parches directos sobre el dataset de test entrega un Dice promedio
# considerablemente mejor que la reconstrucción de la imagen completa por
# sliding window, pero esta última es la única viable en producción end-to-end.
_UNETPP_PATCHES_METRICS = [
    ExperimentMetric(
        name="dice",
        value=0.4568,
        description="Dice tras reconstrucción por sliding window con fusión Gaussiana ",
    ),
    ExperimentMetric(
        name="IoU",
        value=0.4016,
        description="IoU tras reconstrucción por sliding window con fusión Gaussiana ",
    ),
]


_UNETPP_PATCHES = ModelCard(
    id="unetpp-patches",
    display_name="Unet++ por parches (EfficientNet-B7)",
    description=(
        "Unet++ con encoder EfficientNet-B7 entrenado por parches de 128×128 "
        "(8 vistas por imagen) con loss combinada CE+Dice y aumentación con "
        "CLAHE, Perspective y Gaussian noise. En inferencia se ejecuta una "
        "ventana deslizante sobre la imagen completa con fusión Gaussiana de "
        "probabilidades (patch_area=0.5, sigma=50, stride_ratio=4). El modelo "
        "emite 18 clases (background + T1..T12 + L1..L5); el adapter remapea "
        "los ids al contrato 23-clases del servicio dejando las cervicales en "
        "cero porque el modelo no las distingue."
    ),
    architecture="Unet++ (smp) + EfficientNet-B7 (ImageNet pretrain, encoder fine-tuned)",
    task="instance_segmentation_vertebrae_patches",
    classes=[
        "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12",
        "L1", "L2", "L3", "L4", "L5",
    ],
    checkpoints=[
        "model-pkg/unet++_patches/unet++_patches.pth",
    ],
    metrics=_UNETPP_PATCHES_METRICS,
    dataset="MaIA Scoliosis (split estratificado train/val/test, 18 clases)",
    notebook="notebooks/unet++/Unet++_patches.ipynb",
    status="active",
    extra={
        "patch_size": "128x128",
        "num_patches_per_image": "8",
        "encoder_name": "efficientnet-b7",
        "loss": "CombinedLoss (CE + Dice)",
        "augmentations": "RandomResizedCrop, HorizontalFlip, Rotate, Brightness, Perspective, CLAHE, GaussNoise",
        "inference_protocol": "sliding window + Gaussian blending",
        "patch_area": "0.5",
        "sigma": "50.0",
        "stride_ratio": "4",
        "best_epoch": "78",
        "val_dice_best_epoch": "0.7109",
    },
    processing_steps=[
        "Decodificación de imagen",
        "CLAHE sobre canal L (LAB)",
        "Normalización ImageNet (mean/std)",
        "Sliding window: extracción de parches (patch_area=0.5, stride=patch/4)",
        "Resize parche → 128×128 + forward Unet++ EfficientNet-B7",
        "Softmax + fusión ponderada con ventana Gaussiana (σ=50)",
        "Argmax sobre probabilidades acumuladas",
        "Remap clases del modelo (0..17) → contrato del servicio (0..22)",
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
            else [
                _VERTEBRAPROMPT_BOXREFINER,
                _UNETPP_PATCHES,
            ]
        )
        self._by_id: dict[str, ModelCard] = {m.id: m for m in seed}

    async def list_models(self) -> list[ModelCard]:
        return list(self._by_id.values())

    async def get_model(self, model_id: str) -> Optional[ModelCard]:
        return self._by_id.get(model_id)
