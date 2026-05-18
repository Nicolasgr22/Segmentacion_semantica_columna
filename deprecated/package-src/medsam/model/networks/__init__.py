"""
Redes neuronales del pipeline ganador (notebook 06).

Pipeline de 3 etapas + base detector:

    [CenterNetLite]  →  [VertebraPromptNet]  →  [BoxRefiner]  →  [MedSAM ViT-B]
       cajas base       + identidad T1-L5      ajusta cajas      segmenta vértebras

A implementar en fases siguientes:
- conv_block.py            : bloque ConvBN+SiLU compartido (Fase 1)
- centernet_lite.py        : detector base de cajas (Fase 2)
- vertebra_prompt_net.py   : detector + cabeza class_heat anatómica (Fase 2)
- box_refiner.py           : CNN deltas (dx, dy, dw, dh) (Fase 3)
"""

from .conv_block import ConvBlock

__all__ = ["ConvBlock"]
