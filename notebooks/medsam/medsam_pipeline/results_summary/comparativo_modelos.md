# Comparativo de modelos en test

| Modelo | Dice estricto | IoU estricto | Dice flexible | IoU flexible | Lectura |
|---|---:|---:|---:|---:|---|
| nn_sam_entrenamiento_completo | 0.5397 | 0.4636 | 0.7487 | 0.6380 | Base robusta NN-SAM + MedSAM |
| final_sam_red_nombres | 0.2880 | 0.2420 | 0.7453 | 0.6332 | Red de nombres: flexible aceptable, estricto bajo |
| vertebraprompt_net_medsam | 0.1635 | 0.1184 | 0.3145 | 0.2352 | Primer VertebraPrompt-Net; no consolido metricas |
| vertebraprompt_shift_confiado | 0.5450 | 0.4696 | 0.7460 | 0.6368 | Shift confiado; mejora estricto frente a ramas fallidas, no supera ganador |
| vertebraprompt_crop_id | 0.3233 | 0.2746 | 0.7562 | 0.6455 | Identificacion por crop; flexible bueno, estricto insuficiente |
| vertebraprompt_auxiliar | 0.5468 | 0.4704 | 0.7562 | 0.6455 | Variante auxiliar con mejora leve |
| vertebraprompt_boxrefiner | **0.5530** | **0.4795** | 0.7678 | 0.6615 | Estrategia ganadora por metricas promedio |
| boxrefiner_anatomyshift | 0.2443 | 0.2112 | **0.7685** | **0.6626** | Diagnostico: flexible alto, estricto bajo |
| boxrefiner_alignment_conservador | 0.3116 | 0.2687 | 0.7685 | 0.6626 | Diagnostico de alineamiento anatomico |

## Diferencia de BoxRefiner frente a NN-SAM robusto

| Comparacion | Dice estricto | IoU estricto | Dice flexible | IoU flexible |
|---|---:|---:|---:|---:|
| BoxRefiner - NN-SAM robusto | +0.0134 | +0.0159 | +0.0191 | +0.0235 |

## Conclusion

`VertebraPrompt + BoxRefiner` queda como estrategia ganadora integral porque mejora el promedio estricto frente a NN-SAM y tambien mejora el flexible. `boxrefiner_anatomyshift` y `boxrefiner_alignment_conservador` logran flexible apenas superior, pero sacrifican demasiado la asignacion estricta; por eso se conservan como diagnosticos, no como ruta final.
