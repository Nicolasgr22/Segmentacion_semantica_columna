"""
Bloque convolucional compartido entre CenterNetLite, VertebraPromptNet y BoxRefiner.

Replicado exacto del notebook 06 (CELL 10):
    Conv2d(3x3, padding=1, bias=False) → BatchNorm2d → SiLU(inplace=True)
    Conv2d(3x3, padding=1, bias=False) → BatchNorm2d → SiLU(inplace=True)
"""

from __future__ import annotations

import torch.nn as nn


class ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.SiLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.SiLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)
