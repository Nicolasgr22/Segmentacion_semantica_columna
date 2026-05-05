"""
Predicción con MedSAM fine-tuneado.

MedSAMPredictor encapsula:
  1. Carga del checkpoint
  2. Preprocesamiento (CLAHE + letterbox 1024×1024)
  3. Inferencia con prompt de bounding box
  4. Post-procesamiento (umbralización + morfología + componente mayor)

Uso rápido:
    predictor = MedSAMPredictor.from_checkpoint("medsam.pth")
    mask = predictor.predict(image_rgb)          # bbox automático
    mask = predictor.predict(image_rgb, bbox=[x1, y1, x2, y2])
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from .pipeline.preprocessing import bbox_from_mask, postprocess_mask


class MedSAMPredictor:
    """
    Wrapper de inferencia sobre un checkpoint MedSAM fine-tuneado.

    Args:
        model:  instancia de SAM ya cargada en memoria
        device: dispositivo PyTorch
    """

    def __init__(self, model, device: torch.device) -> None:
        self._model = model
        self._device = device
        self._img_size: int = model.image_encoder.img_size

        from segment_anything.utils.transforms import ResizeLongestSide

        self._transform = ResizeLongestSide(self._img_size)

    # ─── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: Path | str,
        finetuned_weights: Path | str | None = None,
        device: str = "cpu",
    ) -> "MedSAMPredictor":
        """
        Carga SAM ViT-B base y, opcionalmente, aplica pesos de fine-tuning.

        Args:
            checkpoint_path:   ruta al .pth original de SAM (sam_vit_b_01ec64.pth)
            finetuned_weights: ruta al .pth generado por train()
            device:            'cpu', 'cuda' o 'mps'
        """
        from segment_anything import sam_model_registry

        _device = torch.device(device)
        model = sam_model_registry["vit_b"](checkpoint=str(checkpoint_path))
        if finetuned_weights is not None:
            state = torch.load(
                str(finetuned_weights), map_location=_device, weights_only=True
            )
            model.load_state_dict(state)
        model = model.to(_device).eval()
        return cls(model, _device)

    # ─── Preprocesamiento ─────────────────────────────────────────────────────

    def _preprocess(
        self, image_rgb: np.ndarray
    ) -> tuple[torch.Tensor, tuple[int, int]]:
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        rgb_enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)

        original_size = rgb_enhanced.shape[:2]
        resized = self._transform.apply_image(rgb_enhanced)
        tensor = (
            torch.as_tensor(resized).permute(2, 0, 1).contiguous().float().unsqueeze(0)
        )
        return self._model.preprocess(tensor[0]).unsqueeze(0), original_size

    def _build_box_tensor(
        self,
        bbox: Sequence[float],
        original_size: tuple[int, int],
    ) -> torch.Tensor:
        box_np = np.array(bbox, dtype=np.float32)[None, :]
        box_resized = self._transform.apply_boxes(box_np, original_size)
        return torch.tensor(box_resized, device=self._device)

    # ─── Inferencia interna (evita duplicar código entre predict y predict_proba)

    @torch.no_grad()
    def _run_inference(
        self, image_rgb: np.ndarray, bbox: Sequence[float] | None
    ) -> torch.Tensor:
        """Devuelve logits interpolados [1, 1, img_size, img_size]."""
        img_tensor, original_size = self._preprocess(image_rgb)
        img_tensor = img_tensor.to(self._device)

        if bbox is None:
            bbox = self._auto_bbox(image_rgb)

        box_tensor = self._build_box_tensor(bbox, original_size).to(self._device)
        image_embedding = self._model.image_encoder(img_tensor)

        sparse_emb, dense_emb = self._model.prompt_encoder(
            points=None,
            boxes=box_tensor,
            masks=None,
        )
        low_res_mask, _ = self._model.mask_decoder(
            image_embeddings=image_embedding,
            image_pe=self._model.prompt_encoder.get_dense_pe(),
            sparse_prompt_embeddings=sparse_emb,
            dense_prompt_embeddings=dense_emb,
            multimask_output=False,
        )
        return F.interpolate(
            low_res_mask,
            size=(self._img_size, self._img_size),
            mode="bilinear",
            align_corners=False,
        )

    # ─── API pública ──────────────────────────────────────────────────────────

    def predict(
        self,
        image_rgb: np.ndarray,
        bbox: Sequence[float] | None = None,
        threshold: float = 0.5,
        apply_postprocess: bool = True,
    ) -> np.ndarray:
        """
        Segmenta la columna vertebral en una radiografía.

        Args:
            image_rgb:         imagen RGB (H, W, 3), uint8
            bbox:              [x1, y1, x2, y2] en coords originales.
                               Si es None se deriva con umbral Otsu.
            threshold:         umbral de probabilidad (default 0.5)
            apply_postprocess: morfología + componente mayor

        Returns:
            Máscara binaria uint8 (img_size × img_size)
        """
        pred = self._run_inference(image_rgb, bbox)
        prob = torch.sigmoid(pred).squeeze().cpu().numpy()
        mask = (prob > threshold).astype(np.uint8)
        if apply_postprocess:
            mask = postprocess_mask(mask)
        return mask

    def predict_proba(
        self,
        image_rgb: np.ndarray,
        bbox: Sequence[float] | None = None,
    ) -> np.ndarray:
        """
        Igual que predict() pero devuelve probabilidades float32 [0, 1].
        """
        pred = self._run_inference(image_rgb, bbox)
        return torch.sigmoid(pred).squeeze().cpu().numpy().astype(np.float32)

    # ─── Auto-bbox ────────────────────────────────────────────────────────────

    @staticmethod
    def _auto_bbox(image_rgb: np.ndarray, pad: int = 20) -> list[float]:
        """
        Deriva un bounding box automático con umbralización Otsu.
        Útil cuando no se dispone de una máscara ground-truth en inferencia.
        """
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        h, w = binary.shape
        box = bbox_from_mask(binary, pad=pad)
        return [
            float(max(0, box[0])),
            float(max(0, box[1])),
            float(min(w - 1, box[2])),
            float(min(h - 1, box[3])),
        ]
