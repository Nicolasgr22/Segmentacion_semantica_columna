# model-medsam

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![SAM](https://img.shields.io/badge/SAM-ViT--B-FF6B6B)](https://github.com/facebookresearch/segment-anything)
[![MLflow](https://img.shields.io/badge/MLflow-Databricks-0194E2?logo=mlflow&logoColor=white)](https://dbc-250dea69-0463.cloud.databricks.com)
[![tox](https://img.shields.io/badge/tox-4.x-brightgreen)](https://tox.wiki/)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](dist/)

Paquete Python de fine-tuning e inferencia de **MedSAM** para segmentación binaria de columna vertebral en radiografías. Proyecto de grado **MaIA — Universidad de los Andes, 2026**.

---

## Resultados del entrenamiento

Experimento `exp_final_lastblock_unfrozen` — último bloque del encoder descongelado + mask decoder:

| Métrica | Validación | Test |
|---------|-----------|------|
| Dice | 0.847 | **0.838** |
| IoU | — | **0.732** |
| Precision | — | **0.821** |
| Recall | — | **0.867** |

Experimento registrado en Databricks:
- **Host:** `https://dbc-250dea69-0463.cloud.databricks.com`
- **Experimento:** `/Users/anferiro@gmail.com/columna-vertebral-medsam`

---

## Estructura del paquete

```
package-src/medsam/
├── model/
│   ├── __init__.py               ← exporta MedSAMPredictor, train, evaluate
│   ├── train.py                  ← fine-tuning + evaluación + reporte MLflow
│   ├── predict.py                ← MedSAMPredictor (inferencia)
│   ├── train_runner.py           ← CLI entry point (medsam-train)
│   ├── config/config.yml         ← hiperparámetros del experimento
│   └── pipeline/
│       ├── preprocessing.py      ← CLAHE + letterbox + postprocess
│       ├── dataset.py            ← SpineMedSAMDataset + DataLoaders
│       ├── augmentation.py       ← albumentations para train
│       └── generar_splits.py     ← QC + splits train/val/test
├── requirements/
│   └── requirements.txt
├── dist/
│   ├── model_medsam-0.1.0-py3-none-any.whl
│   └── model_medsam-0.1.0.tar.gz
├── MANIFEST.in
├── setup.py
└── tox.ini
```

---

## Instalación

### Desde el wheel (recomendado para el servicio)

```bash
pip install dist/model_medsam-0.1.0-py3-none-any.whl
```

### Desde fuente

```bash
cd package-src/medsam
pip install -r requirements/requirements.txt
pip install git+https://github.com/facebookresearch/segment-anything.git
```

---

## Configuración

Crear `.env` en `package-src/medsam/` con las credenciales de Databricks:

```bash
cp notebooks/.env package-src/medsam/.env
```

```env
DATABRICKS_HOST=https://dbc-250dea69-0463.cloud.databricks.com
DATABRICKS_TOKEN=<tu-personal-access-token>
MLFLOW_EXPERIMENT_NAME=/Users/anferiro@gmail.com/columna-vertebral-medsam
```

---

## Entrenamiento

```bash
cd package-src/medsam

# Entrenamiento completo (20 épocas, device auto-detectado)
tox -e train

# Prueba rápida
tox -e train -- --epochs 3
```

El runner:
1. Genera `splits.csv` automáticamente si no existe (con control de calidad)
2. Conecta con Databricks/MLflow usando el `.env`
3. Entrena con el último bloque del encoder + mask decoder
4. Evalúa en test y sube checkpoint, CSV y JSON de resultados a Databricks

---

## Construir el paquete

```bash
tox -e build
# Genera dist/model_medsam-0.1.0-py3-none-any.whl
```

---

## Pruebas unitarias

```bash
cd package-src/medsam

# Todas las pruebas
tox -e py310

# Solo predict.py (rápido, sin GPU)
python -m pytest tests/unit/test_predict.py -v

# Con reporte de cobertura
python -m pytest tests/unit/test_predict.py -v --cov=model --cov-report=term-missing
```

Las pruebas siguen los principios **FIRST** — todo el modelo SAM está mockeado, no requieren GPU ni archivos `.pth`. 18 tests se ejecutan en ~2 segundos.

---

## Uso en inferencia

```python
from model.predict import MedSAMPredictor
import cv2

predictor = MedSAMPredictor.from_checkpoint(
    checkpoint_path="model/recursos/models/sam_vit_b_01ec64.pth",
    finetuned_weights="model/recursos/medsam_checkpoints/medsam_lastblock_unfrozen.pth",
    device="cpu",
)

image = cv2.cvtColor(cv2.imread("radiografia.png"), cv2.COLOR_BGR2RGB)
mask = predictor.predict(image)               # máscara binaria uint8
proba = predictor.predict_proba(image)        # probabilidades float32 [0,1]
```

---

## Comandos tox disponibles

| Comando | Descripción |
|---------|-------------|
| `tox -e train` | Entrenar el modelo |
| `tox -e py310` | Ejecutar pruebas unitarias con cobertura |
| `tox -e build` | Generar `.whl` y `.tar.gz` en `dist/` |
| `tox -e lint` | Verificar estilo de código |
| `tox -e type` | Chequeo de tipos con mypy |
| `tox -e format` | Formatear código con ruff |

---

## Aviso clínico

Esta herramienta es un apoyo diagnóstico exclusivamente. Toda decisión clínica debe ser revisada por un radiólogo o especialista cualificado.
