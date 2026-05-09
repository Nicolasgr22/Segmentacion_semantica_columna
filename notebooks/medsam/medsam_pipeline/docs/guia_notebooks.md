# Guia de lectura de notebooks

Los notebooks estan ordenados como una historia experimental, no como archivos independientes. La lectura sugerida es:

1. `01_recoleccion_preparacion_datos.ipynb`: origen de datos, limpieza y exportacion.
2. `02_baseline_binario.ipynb`: baseline de control.
3. `03_multiclase_estratificado_medsam.ipynb`: salto a vertebras individuales y protocolo MedSAM.
4. `04_cajas_nn_centernetlite.ipynb`: primer detector neuronal de cajas.
5. `05_nn_sam_entrenamiento_completo.ipynb`: base robusta NN-SAM + MedSAM.
6. `06_estrategia_ganadora_vertebraprompt_boxrefiner.ipynb`: estrategia ganadora por metricas promedio en test.

Cada notebook incluye celdas Markdown antes de las partes principales para explicar que se hace, por que se tomo esa decision y como interpretar la salida.

## Normalizaci?n y herencia entre notebooks

Los primeros notebooks (`01` y `02`) deben leerse como la etapa de preparaci?n y baseline. All? se probaron ideas de lectura, limpieza, CLAHE, resize/letterbox y preservaci?n de m?scaras. Esa etapa fue necesaria para entender el dataset, pero no todo lo probado all? se usa literalmente en la estrategia ganadora.

El punto de transici?n es `03_multiclase_estratificado_medsam.ipynb`. En ese notebook se congela la exportaci?n MedSAM que despu?s consumen `04`, `05` y `06`:

- im?genes preprocesadas a 1024x1024,
- formato RGB compatible con MedSAM,
- m?scaras multiclase con IDs preservados,
- split estratificado `train/val/test`,
- prompts y metadatos reutilizables.

Los notebooks finales (`04`, `05`, `06`) no reconstruyen la normalizaci?n original desde cero. Leen esa exportaci?n y aplican normalizaciones internas adicionales para las redes de cajas/prompts, como resize a `IMG_SIZE` y escalado por percentiles.

## Lectura por etapas

Cada notebook debe leerse como una etapa con una pregunta propia, no como si todos hubieran nacido al mismo tiempo:

1. `01`: entender y preparar el dataset.
2. `02`: validar un baseline binario.
3. `03`: pasar a multiclase, MedSAM y split estratificado.
4. `04`: resolver la generaci?n autom?tica de cajas.
5. `05`: integrar cajas autom?ticas con MedSAM como base robusta.
6. `06`: refinar prompts con VertebraPrompt + BoxRefiner y reportar la estrategia ganadora.

La narrativa correcta para el informe es progresiva: cada etapa deja una limitaci?n que justifica la siguiente. No se debe saltar directamente desde preparaci?n de datos hasta BoxRefiner sin explicar por qu? fueron necesarias las etapas intermedias.

## Ramas experimentales

La carpeta `experiments/` conserva pruebas que no quedaron como ruta principal, pero que son importantes para entender el proceso: heuristicas de cajas, red de nombres, crop-ID, shift confiado, AnatomyShift y alignment conservador. Estas ramas deben leerse como evidencia de decision, no como notebooks recomendados para ejecutar primero.

