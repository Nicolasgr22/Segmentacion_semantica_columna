# Mapa de versionamiento sugerido

El repositorio aun no tenia historial Git inicializado. Por eso se deja primero una estructura clara en carpetas y un mapa de ramas. Si se quiere subir a GitHub con ramas reales, este mapa sirve como guia para crear los commits y ramas sin perder la historia experimental.

## Linea principal

La linea principal deberia quedar en `main` con los notebooks de `notebooks/`:

1. `01_recoleccion_preparacion_datos.ipynb`
2. `02_baseline_binario.ipynb`
3. `03_multiclase_estratificado_medsam.ipynb`
4. `04_cajas_nn_centernetlite.ipynb`
5. `05_nn_sam_entrenamiento_completo.ipynb`
6. `06_estrategia_ganadora_vertebraprompt_boxrefiner.ipynb`

## Ramas conceptuales

```text
main
?? exp/01-binario-baseline
?? exp/02-multiclase-medsam
?  ?? exp/03-cajas-heuristicas
?  ?  ?? exp/04-cajas-heuristicas-limpias
?  ?? exp/05-cajas-nn-centernetlite
?     ?? exp/06-nn-sam-entrenamiento-completo
?        ?? exp/07-final-sam-red-nombres
?        ?? exp/08-vertebraprompt-net-medsam
?           ?? exp/09-shift-confiado
?           ?? exp/10-crop-id
?           ?? exp/11-boxrefiner
?              ?? exp/12-anatomyshift
?              ?? exp/13-alignment-conservador
```

## Como leer esto en GitHub

Hay dos niveles de trazabilidad:

- **Trazabilidad documental:** la carpeta `experiments/` permite entender que se probo, de donde venia y por que no quedo como ruta final.
- **Trazabilidad Git real:** si se crean ramas en GitHub, cada rama deberia partir del commit padre indicado en el mapa. Eso permite comparar cambios con Pull Requests o con `git diff`.

## Recomendacion practica

Para la entrega, mantener `main` limpio con la estrategia final y dejar `experiments/` como evidencia metodologica. Para defensa tecnica o trabajo futuro, crear ramas reales solo de los experimentos importantes: heuristicas, NN-SAM, Final SAM/red nombres, VertebraPrompt-Net, BoxRefiner, AnatomyShift y Alignment.
