# Segmentacion vertebral en radiografias de escoliosis con prompts automaticos y MedSAM

Este repositorio contiene una version curada y liviana del proyecto. La carpeta original de trabajo no fue modificada; aqui se incluyen solo los notebooks principales, documentacion y resumenes de resultados.

## Lectura del proyecto

La evolucion del proyecto se resume asi:

```text
Preparacion de datos
  -> baseline binario
  -> rama multiclase con MedSAM
  -> deteccion automatica de cajas
  -> NN-SAM + MedSAM como base robusta
  -> VertebraPrompt + BoxRefiner como estrategia ganadora por metricas
```

## Decision final

La estrategia con mejor rendimiento global en test fue **VertebraPrompt + BoxRefiner**. La mejora frente a NN-SAM robusto no es enorme, pero si es consistente y relevante: alrededor de 1.3 puntos en Dice estricto y 1.9 puntos en Dice flexible.

Por eso el repositorio conserva dos piezas centrales:

- **Entrenamiento completo NN-SAM + MedSAM:** base robusta y punto de comparacion principal.
- **VertebraPrompt + BoxRefiner:** estrategia ganadora por metricas promedio en test.

## Flujo general

```text
Radiografia
  -> detector de vertebras / prompts automaticos
  -> refinamiento de cajas con BoxRefiner en la estrategia ganadora
  -> MedSAM ajustado
  -> mascaras vertebrales
  -> evaluacion estricta y flexible
```

## Notebooks incluidos

| Notebook | Proposito | Rol dentro del proyecto |
|---|---|---|
| `01_recoleccion_preparacion_datos.ipynb` | Preparacion e inventario del dataset. | Base del proyecto. |
| `02_baseline_binario.ipynb` | Primer baseline binario. | Rama inicial de control. |
| `03_multiclase_estratificado_medsam.ipynb` | Pruebas multiclase con particion estratificada y MedSAM. | Inicio de la rama principal. |
| `04_cajas_nn_centernetlite.ipynb` | Red CenterNetLite para detectar cajas vertebrales. | Primer detector neuronal de prompts automaticos. |
| `05_nn_sam_entrenamiento_completo.ipynb` | Entrenamiento completo NN-SAM + MedSAM. | Base robusta y comparador principal. |
| `06_estrategia_ganadora_vertebraprompt_boxrefiner.ipynb` | VertebraPrompt auxiliar + BoxRefiner + MedSAM. | Estrategia ganadora por metricas promedio en test. |

## Resultados resumidos

Las metricas principales estan en:

- `results_summary/metricas_principales.csv`
- `results_summary/comparativo_modelos.md`
- `results_summary/raw_summaries/`


## Particiones de datos

La particion reproducible de train/val/test esta versionada en `data_splits/splits_estratificados_medsam.csv`. Los datos reales de imagen y mascara no se incluyen en GitHub; solo se versiona el manifiesto del split.

## Pesos entrenados

Los pesos no se incluyen en GitHub por tamano. Estan organizados en Drive:

`C:\Users\luisf\Downloads\ProyectoFinal_Drive_organizado`

Ver `checkpoints/README.md` para la correspondencia entre notebooks y pesos.

## Datos

Los datasets originales y procesados no se incluyen en este repositorio. La estructura esperada se documenta en `docs/metodologia.md`.

## Limitacion principal

Aunque BoxRefiner mejora el promedio, la asignacion anatomica estricta sigue siendo el punto mas sensible. La metrica flexible muestra que muchas vertebras se segmentan razonablemente, pero nombrarlas exactamente sigue siendo mas dificil, sobre todo en escoliosis e imagenes parciales.

## Trazabilidad experimental

El repositorio separa la historia en dos niveles:

- `notebooks/`: ruta principal y notebooks que cuentan la evolucion hacia el modelo final.
- `experiments/`: ramas experimentales conservadas. No son la estrategia final, pero explican decisiones importantes y muestran de que etapa nace cada prueba.

Para entender la derivacion de ramas, ver `docs/versionamiento_git.md`.
## Checkpoints y archivos pesados

Los pesos entrenados y checkpoints finales no se versionan en GitHub por tamaño. Para reproducir inferencia o continuar pruebas, usar la carpeta compartida de Drive:

[https://drive.google.com/drive/folders/1kf8aPQV06_A_4ROW5TwkgXL0XxcgF5KU](https://drive.google.com/drive/folders/1kf8aPQV06_A_4ROW5TwkgXL0XxcgF5KU)

La carpeta de Drive contiene los checkpoints de la base robusta NN-SAM + MedSAM y de la estrategia final VertebraPrompt + BoxRefiner + MedSAM.

