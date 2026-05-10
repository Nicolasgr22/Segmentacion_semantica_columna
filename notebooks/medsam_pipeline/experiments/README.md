# Experimentos conservados

Esta carpeta no es la ruta principal del proyecto. Su funcion es mostrar las ramas validas de experimentacion que ayudaron a decidir la estrategia final.

La regla es sencilla:

- `notebooks/` contiene la ruta que se presenta como linea principal.
- `experiments/` contiene ramas que tuvieron valor metodologico, aunque no fueran la mejor opcion final.
- Los notebooks aqui estan sin salidas para evitar que el repositorio crezca innecesariamente.

| Notebook | Deriva de | Que aporta | Decision final |
|---|---|---|---|
| `01_cajas_heuristicas_curva_dinamica.ipynb` | Multiclase estratificado + MedSAM | Explora cajas por reglas geometricas y curva dinamica | Descartado como final por desplazamientos de cajas |
| `02_cajas_heuristicas_version_limpia.ipynb` | Heuristicas de curva | Cierra la etapa antes de red neuronal | Reemplazado por detectora entrenable |
| `03_final_sam_red_nombres.ipynb` | NN-SAM entrenamiento completo | Prueba red auxiliar para etiquetas anatomicas | Flexible aceptable, estricto bajo |
| `04_vertebraprompt_net_medsam.ipynb` | NN-SAM | Puente hacia prompts aprendidos + MedSAM | Base de la ruta posterior |
| `05_vertebraprompt_shift_confiado.ipynb` | VertebraPrompt-Net + MedSAM | Corrige desplazamientos de etiqueta con confianza | No supera la estrategia final |
| `06_vertebraprompt_crop_id.ipynb` | VertebraPrompt-Net + MedSAM | Identificacion por recorte local | Insuficiente por falta de contexto global |
| `07_boxrefiner_anatomyshift.ipynb` | BoxRefiner | Ajuste anatomico posterior | Diagnostico: flexible alto, estricto bajo |
| `08_boxrefiner_alignment_conservador.ipynb` | BoxRefiner | Alineacion posterior conservadora | No mejora de forma suficiente al ganador |

## Lectura recomendada

Primero leer `docs/versionamiento_git.md`. Ese archivo explica como estas ramas se conectan con la linea principal y como se podrian convertir en ramas reales de Git antes de subir a GitHub.
