# Metodologia

1. Preparacion del dataset y revision de etiquetas.
2. Baseline binario para validar lectura, mascaras y evaluacion.
3. Rama multiclase para evaluar vertebras individuales.
4. Integracion inicial con MedSAM.
5. Entrenamiento de detector neuronal de cajas vertebrales.
6. Entrenamiento completo NN-SAM + MedSAM como base robusta.
7. Implementacion de VertebraPrompt + BoxRefiner como estrategia ganadora.
8. Evaluacion en test con metricas estrictas y flexibles.

## Evaluacion

- **Metrica estricta:** exige coincidencia con la etiqueta anatomica correcta.
- **Metrica flexible:** evalua si la vertebra fue segmentada espacialmente aunque exista confusion de nombre anatomico.

Esta doble evaluacion es importante porque en escoliosis o imagenes parciales el modelo puede segmentar una vertebra razonable, pero asignarle una etiqueta diferente.

Los datos no se incluyen en el repositorio por tamano y restricciones de distribucion.
