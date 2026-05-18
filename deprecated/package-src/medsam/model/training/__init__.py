"""
Loops de entrenamiento por etapa.

A implementar en fases siguientes:
- train_centernet.py        : entrena CenterNetLite (NB05, Fase 2)
- train_vertebra_prompt.py  : carga CenterNetLite + entrena cabezas anatómicas (NB06, Fase 2)
- train_box_refiner.py      : entrena BoxRefiner (NB06, Fase 3)
- train_medsam.py           : refactor MedSAM 2 fases multi-vertebra (NB05/NB06, Fase 4)

El módulo `model/train.py` queda como entry-point que orquesta los 4 trainings.
"""
