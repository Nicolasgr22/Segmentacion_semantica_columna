from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import numpy as np
import torch
import torch.nn.functional as F

from app.core.domain.entities.vertebra import ID2LABEL, LABEL2ID
from app.core.domain.ports.model_port import ModelOutput, ModelPort

_executor = ThreadPoolExecutor(max_workers=2)


class SegFormerAdapter(ModelPort):
    def __init__(self, device: str = "cpu", n_classes: int = 23) -> None:
        self._device = torch.device(device)
        self._n_classes = n_classes
        self._model = None
        self._processor = None
        self._loaded = False
        self._model_version = "not-loaded"

    def load_model(self, checkpoint_path: str, local_path: str = "") -> None:
        from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

        source = local_path if local_path else checkpoint_path
        self._processor = SegformerImageProcessor.from_pretrained(
            source,
            do_resize=False,
            do_rescale=True,
            do_normalize=True,
        )
        self._model = SegformerForSemanticSegmentation.from_pretrained(
            source,
            num_labels=self._n_classes,
            id2label=ID2LABEL,
            label2id=LABEL2ID,
            ignore_mismatched_sizes=True,
        )
        self._model.to(self._device)
        self._model.eval()
        self._loaded = True
        self._model_version = source

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_version(self) -> str:
        return self._model_version

    async def predict(self, image: np.ndarray) -> ModelOutput:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_predict, image)

    def _sync_predict(self, image: np.ndarray) -> ModelOutput:
        t0 = time.perf_counter()

        encoding = self._processor(images=image, return_tensors="pt")
        pixel_values = encoding["pixel_values"].to(self._device)

        with torch.no_grad():
            outputs = self._model(pixel_values=pixel_values)

        logits_up = F.interpolate(
            outputs.logits,
            size=(512, 512),
            mode="bilinear",
            align_corners=False,
        )
        probs = torch.softmax(logits_up, dim=1)
        mask = logits_up.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
        probs_np = probs.squeeze(0).cpu().numpy()

        latency_ms = (time.perf_counter() - t0) * 1000
        return ModelOutput(
            mask=mask,
            probabilities=probs_np,
            latency_ms=round(latency_ms, 2),
            model_version=self._model_version,
        )
