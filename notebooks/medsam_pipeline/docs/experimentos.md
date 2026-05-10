# Experimentos

## Lectura general

El proyecto avanzo por etapas. Primero se preparo el dataset y se valido una rama binaria. Luego la linea principal paso a multiclase, porque el objetivo real era segmentar vertebras individuales y no solo una region global de columna.

```text
preparacion
  -> baseline binario
  -> multiclase con MedSAM
  -> cajas automaticas
  -> NN-SAM + MedSAM
  -> VertebraPrompt + BoxRefiner
```

## Ruta base

La ruta NN-SAM + MedSAM fue el punto fuerte del proyecto: una red ligera detecta cajas vertebrales y esas cajas se usan como prompts para MedSAM. Esta ruta dio un Dice estricto de 0.5397 y Dice flexible de 0.7487 en test.

## Estrategia ganadora

La estrategia ganadora por metricas promedio fue **VertebraPrompt + BoxRefiner**. Esta variante parte de la misma idea de prompts automaticos, pero agrega una red auxiliar para mejorar la representacion de las vertebras y un refinador local de cajas.

En test obtuvo:

- Dice estricto: 0.5530
- IoU estricto: 0.4795
- Dice flexible: 0.7678
- IoU flexible: 0.6615

Frente a NN-SAM robusto, la mejora fue:

- +0.0134 en Dice estricto
- +0.0159 en IoU estricto
- +0.0191 en Dice flexible
- +0.0235 en IoU flexible

## Experimentos descartados o diagnosticos

Las pruebas heuristicicas, `final_sam` con red de nombres, AnatomyShift y alineamiento conservador ayudaron a entender errores, pero no se conservan como notebooks principales porque no fueron la mejor ruta final.

La conclusion es que BoxRefiner mejora la localizacion/segmentacion promedio, mientras que la asignacion anatomica estricta sigue siendo el cuello de botella mas dificil.
