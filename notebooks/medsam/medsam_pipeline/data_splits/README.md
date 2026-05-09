# Data Splits

Esta carpeta versiona los manifiestos de particion usados para entrenamiento, validacion y test.

## Archivo principal

`splits_estratificados_medsam.csv` corresponde a la particion usada por la ruta final MedSAM/NN-SAM/VertebraPrompt:

- train: 174 pacientes
- val: 37 pacientes
- test: 38 pacientes

El archivo no incluye datos de imagen ni mascaras. Solo contiene IDs, tipo, estrato, Cobb cuando existe, split y rutas relativas esperadas dentro del dataset.

## Por que va en Git

El split es liviano y es parte de la reproducibilidad experimental. Debe quedar versionado junto al codigo para que otra persona pueda evaluar con exactamente los mismos pacientes.

## Que no va en Git

Las radiografias, mascaras procesadas y carpetas `medsam/train`, `medsam/val`, `medsam/test` no deben subirse a GitHub por tamano y posibles restricciones de distribucion. Si se comparten, deben ir en Drive/Zenodo/Hugging Face/OneDrive con permisos claros.
