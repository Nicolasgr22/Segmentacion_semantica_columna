"""
Tests unitarios de los componentes de red (Fase 1: ConvBlock).

ConvBlock se replicó EXACTAMENTE del NB06 CELL 10. Estos tests verifican
shapes, parámetros, y secuencia de operaciones.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from model.networks import ConvBlock


class TestConvBlock:
    def test_shape_preserva_resolucion_espacial(self):
        """ConvBlock no debe cambiar H ni W (padding=1, stride=1)."""
        block = ConvBlock(in_ch=1, out_ch=32)
        x = torch.randn(2, 1, 64, 64)
        y = block(x)
        assert y.shape == torch.Size([2, 32, 64, 64])

    def test_cambia_canales_correctamente(self):
        """Output channels debe coincidir con out_ch."""
        block = ConvBlock(in_ch=3, out_ch=128)
        y = block(torch.randn(1, 3, 32, 32))
        assert y.shape[1] == 128

    def test_estructura_interna_es_la_del_notebook(self):
        """
        Verifica que la secuencia es exactamente:
        Conv → BN → SiLU → Conv → BN → SiLU
        """
        block = ConvBlock(8, 16)
        layers = list(block.net)
        assert len(layers) == 6
        assert isinstance(layers[0], nn.Conv2d)
        assert isinstance(layers[1], nn.BatchNorm2d)
        assert isinstance(layers[2], nn.SiLU)
        assert isinstance(layers[3], nn.Conv2d)
        assert isinstance(layers[4], nn.BatchNorm2d)
        assert isinstance(layers[5], nn.SiLU)

    def test_conv_kernel_y_padding_son_3_y_1(self):
        """Kernel 3x3 con padding 1 (mantiene resolución)."""
        block = ConvBlock(1, 32)
        conv1, conv2 = block.net[0], block.net[3]
        assert conv1.kernel_size == (3, 3)
        assert conv1.padding == (1, 1)
        assert conv2.kernel_size == (3, 3)
        assert conv2.padding == (1, 1)

    def test_conv_no_usa_bias(self):
        """bias=False porque BatchNorm normaliza después."""
        block = ConvBlock(1, 32)
        assert block.net[0].bias is None
        assert block.net[3].bias is None

    def test_silu_es_inplace(self):
        """SiLU(inplace=True) — replicado del notebook para ahorro de memoria."""
        block = ConvBlock(1, 32)
        assert block.net[2].inplace is True
        assert block.net[5].inplace is True

    def test_conteo_parametros_esperado(self):
        """
        Para ConvBlock(1, 32):
          Conv1: 1*32*3*3 = 288 weights, 0 bias
          BN1: 32*2 = 64 (gamma + beta)
          Conv2: 32*32*3*3 = 9216 weights, 0 bias
          BN2: 32*2 = 64
          Total: 288 + 64 + 9216 + 64 = 9632
        """
        block = ConvBlock(1, 32)
        n_params = sum(p.numel() for p in block.parameters())
        assert n_params == 9632

    def test_gradientes_fluyen(self):
        """Verifica que el bloque es entrenable."""
        block = ConvBlock(1, 16)
        x = torch.randn(1, 1, 16, 16, requires_grad=True)
        y = block(x)
        loss = y.sum()
        loss.backward()
        # Todos los parámetros aprendibles deben tener gradiente
        for p in block.parameters():
            if p.requires_grad:
                assert p.grad is not None
