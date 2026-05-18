"""
Tests del config.yml unificado (Fase 1).

Valida que la estructura del config refleja el pipeline ganador (4 stages)
y que los valores críticos coinciden con lo reportado en NB05/NB06 CELL 2.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "model" / "config" / "config.yml"


@pytest.fixture(scope="module")
def cfg() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class TestConfigEstructura:
    def test_tiene_los_4_stages(self, cfg):
        for stage in ["stage1_centernet", "stage2_vertebra_prompt",
                      "stage3_box_refiner", "stage4_medsam"]:
            assert stage in cfg, f"Falta sección {stage}"

    def test_tiene_secciones_transversales(self, cfg):
        for section in ["reproducibility", "data", "paths",
                        "anatomical_decoder", "metrics", "mlflow"]:
            assert section in cfg, f"Falta sección {section}"

    def test_mantiene_legacy_training_para_compatibilidad(self, cfg):
        """
        El refactor por fases mantiene `training:` para que el train.py legacy
        siga funcionando hasta que Fase 4 lo reemplace.
        """
        assert "training" in cfg
        for k in ["seed", "num_epochs", "batch_size", "checkpoint_name", "optimizer"]:
            assert k in cfg["training"], f"Falta legacy training.{k}"


class TestStage1CenterNet:
    """Valores extraídos de NB05 CELL 2 (líneas ~94-112)."""

    def test_hiperparametros_match_notebook(self, cfg):
        s = cfg["stage1_centernet"]
        assert s["epochs"] == 140
        assert s["lr"] == 6.0e-4
        assert s["patience"] == 22
        assert s["batch_size"] == 2
        assert s["base_ch"] == 32
        assert s["augment_repeats"] == 6
        assert s["sigma_centro"] == 4.5

    def test_loss_weights_match_notebook(self, cfg):
        lw = cfg["stage1_centernet"]["loss_weights"]
        assert lw["heat"] == 1.00
        assert lw["wh"] == 0.40
        assert lw["offset"] == 0.12   # NB05 LAMBDA_OFF (renombrado por colisión YAML)
        assert lw["presence"] == 0.00


class TestStage2VertebraPromptNet:
    """Valores extraídos de NB06 CELL 2 (líneas ~86-105)."""

    def test_hiperparametros_match_notebook(self, cfg):
        s = cfg["stage2_vertebra_prompt"]
        assert s["epochs"] == 60
        assert s["lr"] == 3.0e-4
        assert s["patience"] == 10
        assert s["batch_size"] == 2

    def test_freeze_y_baseline_estan_activos(self, cfg):
        """Stage 2 requiere cargar Stage 1 y congelar el detector."""
        s = cfg["stage2_vertebra_prompt"]
        assert s["load_baseline_centernet"] is True
        assert s["freeze_detector_train_only_identity"] is True

    def test_class_heat_weight_match_notebook(self, cfg):
        """LAMBDA_CLASS_HEAT = 0.08 en NB06 CELL 2."""
        assert cfg["stage2_vertebra_prompt"]["loss_weights"]["class_heat"] == 0.08


class TestStage3BoxRefiner:
    """Valores extraídos de NB06 CELL 2 (líneas ~177-192)."""

    def test_hiperparametros_match_notebook(self, cfg):
        s = cfg["stage3_box_refiner"]
        assert s["enabled"] is True
        assert s["size"] == 192
        assert s["batch_size"] == 32
        assert s["epochs"] == 55
        assert s["lr"] == 5.0e-4
        assert s["max_abs_dxy"] == 0.45
        assert s["max_abs_log_scale"] == 0.45


class TestStage4MedSAM:
    """Valores extraídos de NB06 CELL 2 (líneas ~120-143)."""

    def test_2_fases_decoder_y_encoder_parcial(self, cfg):
        s = cfg["stage4_medsam"]
        assert "decoder" in s
        assert "encoder_parcial" in s

    def test_decoder_phase_match_notebook(self, cfg):
        d = cfg["stage4_medsam"]["decoder"]
        assert d["epochs"] == 12               # MEDSAM_DECODER_EPOCHS
        assert d["patience"] == 4              # MEDSAM_DECODER_PATIENCIA
        assert d["lr"] == 1.0e-4               # MEDSAM_LR_DECODER

    def test_encoder_parcial_phase_match_notebook(self, cfg):
        e = cfg["stage4_medsam"]["encoder_parcial"]
        assert e["epochs"] == 8                # MEDSAM_ENCODER_PARCIAL_EPOCHS
        assert e["patience"] == 3              # MEDSAM_ENCODER_PARCIAL_PATIENCIA
        assert e["lr_decoder"] == 5.0e-5       # MEDSAM_LR_DECODER_REFINO
        assert e["lr_encoder"] == 1.0e-5       # MEDSAM_LR_ENCODER

    def test_prompt_box_only_match_notebook(self, cfg):
        """NB06 confirma: box_only > box+points (cell 2 línea 218)."""
        assert cfg["stage4_medsam"]["prompt_mode"] == "box_only"

    def test_padding_fraccional_match_notebook(self, cfg):
        s = cfg["stage4_medsam"]
        assert s["prompt_box_frac_x"] == 0.04  # MEDSAM_TRAIN_FRAC_X
        assert s["prompt_box_frac_y"] == 0.06  # MEDSAM_TRAIN_FRAC_Y

    def test_pesos_sample_weights_match_notebook(self, cfg):
        sw = cfg["stage4_medsam"]["sample_weights"]
        assert sw["escoliosis"] == 1.25            # MEDSAM_PESO_ESCOLIOSIS
        assert sw["normal"] == 1.00                # MEDSAM_PESO_NORMAL
        assert sw["peso_vertebra_dificil"] == 1.15 # MEDSAM_PESO_VERTEBRA_DIFICIL
        assert sw["vertebras_dificiles"] == ["T1", "T2", "T3", "L4", "L5"]


class TestData:
    def test_17_clases_T1_a_L5(self, cfg):
        assert cfg["data"]["n_clases"] == 17
        names = cfg["data"]["vertebra_names"]
        assert len(names) == 17
        assert names[0] == "T1"
        assert names[-1] == "L5"
        # Verifica orden T1-T12 + L1-L5
        assert names[11] == "T12"
        assert names[12] == "L1"


class TestAnatomicalDecoder:
    """Valores extraídos de NB06 CELL 2 (líneas ~96-104, 145-165)."""

    def test_top_anchor_es_estrategia_default(self, cfg):
        ad = cfg["anatomical_decoder"]
        assert ad["etiquetado_modo"] == "top_anchor"
        assert "top_anchor" in ad["estrategias_etiquetado"]

    def test_thresholds_match_notebook(self, cfg):
        ad = cfg["anatomical_decoder"]
        assert ad["presence_thr"] == 0.35
        assert ad["min_visible_labels"] == 8
        assert ad["max_gap_rel_dy"] == 2.40
