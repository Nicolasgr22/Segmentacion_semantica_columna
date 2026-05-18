# Refactor en curso: pipeline ganador (notebook 06)

> **Estado actual: Fase 1 completada.** El paquete está en transición. El código viejo (`train.py` legacy) sigue funcionando con la sección `training:` del config marcada como DEPRECATED.

## Objetivo

Replicar fielmente el modelo ganador reportado en `notebooks/medsam_pipeline/results_summary/comparativo_modelos.md`:

| Métrica | Valor objetivo (test) |
|---------|----------------------:|
| Dice estricto  | 0.5530 |
| IoU estricto   | 0.4795 |
| Dice flexible  | 0.7678 |
| IoU flexible   | 0.6615 |

## Pipeline ganador (4 etapas)

```
Imagen 1024x1024
       │
       ▼
[Stage 1] CenterNetLite              ← NB05 CELL 2 (140 ep, lr=6e-4)
       │   detector base de cajas
       ▼
[Stage 2] VertebraPromptNet          ← NB06 CELL 2 (60 ep, lr=3e-4, freeze base)
       │   añade cabeza class_heat (T1-L5)
       ▼
[Stage 3] BoxRefiner                 ← NB06 CELL 2 (55 ep, lr=5e-4)
       │   ajusta deltas (dx, dy, dw, dh)
       ▼
[Stage 4] MedSAM ViT-B 2 fases       ← NB06/NB05 CELL 2 (12 + 8 ep)
       │   - Fase 4a: solo decoder (lr 1e-4)
       │   - Fase 4b: + último bloque encoder (lr 5e-5 / 1e-5)
       ▼
17 máscaras nombradas T1-L5
```

## Fases del refactor

| Fase | Estado | Entregable |
|------|--------|------------|
| 0 | ✅ Completada | Análisis notebooks, verificación de datos disponibles |
| **1** | ✅ **Completada** | **Estructura + config.yml + ConvBlock compartido** |
| 2 | ⏳ Pendiente | VertebraPromptNet + dataset detection + train script |
| 3 | ⏳ Pendiente | BoxRefiner + dataset crops + train script |
| 4 | ⏳ Pendiente | Refactor MedSAM multi-vertebra 2 fases (reemplaza `train.py`) |
| 5 | ⏳ Pendiente | Decodificador anatómico + métricas estricta/flexible |
| 6 | ⏳ Pendiente | Orquestación 4 stages en `train_runner.py` + tox.ini envs |
| 7 | ⏳ Pendiente | Smoke tests, validación, documentación final |

## Estructura nueva

```
model/
├── config/config.yml                 [✅ Fase 1: 4 stages + legacy]
├── networks/                         [✅ Fase 1]
│   ├── conv_block.py                 [✅ Fase 1: bloque compartido]
│   ├── centernet_lite.py             [⏳ Fase 2]
│   ├── vertebra_prompt_net.py        [⏳ Fase 2]
│   └── box_refiner.py                [⏳ Fase 3]
├── pipeline/                         [parcial existente]
│   ├── dataset.py                    [legacy, refactor en Fase 4]
│   ├── dataset_detection.py          [⏳ Fase 2: targets heatmap]
│   ├── dataset_multiclass.py         [⏳ Fase 4: 1 sample = 1 vertebra]
│   ├── dataset_box_refiner.py        [⏳ Fase 3: crops 192x192]
│   ├── preprocessing.py              [parcial, ampliar Fase 2]
│   ├── prompts_builder.py            [⏳ Fase 5]
│   └── anatomical_decoder.py         [⏳ Fase 5]
├── metrics/                          [✅ Fase 1: dir creado]
│   └── strict_flexible.py            [⏳ Fase 5]
├── training/                         [✅ Fase 1: dir creado]
│   ├── train_centernet.py            [⏳ Fase 2]
│   ├── train_vertebra_prompt.py      [⏳ Fase 2]
│   ├── train_box_refiner.py          [⏳ Fase 3]
│   └── train_medsam.py               [⏳ Fase 4]
├── train.py                          [⚠️ LEGACY, refactor en Fase 4]
├── train_runner.py                   [⚠️ LEGACY, refactor en Fase 6]
├── predict.py                        [⚠️ LEGACY, refactor en Fase 6]
└── upload_to_databricks.py           [✅ funcional, sin cambios]
```

## Datos disponibles localmente

- `recursos/Scoliosis_Dataset/Normal/` + `Scoliosis/` → 995 imágenes JPG
- `recursos/Scoliosis_Dataset/LabelMultiClass_ID_PNG/` → 249 máscaras multiclase (PNG, IDs 1-17)
- `recursos/Scoliosis_Dataset/labels_dictionary.json` → mapeo IDs ↔ T1-L5
- `recursos/dataset_procesado/splits.csv` → splits estratificados (174/37/38), idénticos al notebook
- `recursos/models/sam_vit_b_01ec64.pth` → checkpoint base SAM

## Compatibilidad durante el refactor

El `config.yml` mantiene una sección `training:` marcada como DEPRECATED para que el `train.py` actual siga ejecutándose. Esa sección se eliminará cuando Fase 4 reemplace a `train.py`.

## Referencias

- Código fuente notebooks (extraído):
  - `/tmp/medsam_nb_extract/05_nn_sam_entrenamiento_completo.py`
  - `/tmp/medsam_nb_extract/06_estrategia_ganadora_vertebraprompt_boxrefiner.py`
- Configuración fuente: NB05/NB06 CELL 2 (líneas 48-200 ambos)
- Resultados objetivo: `notebooks/medsam_pipeline/results_summary/`
