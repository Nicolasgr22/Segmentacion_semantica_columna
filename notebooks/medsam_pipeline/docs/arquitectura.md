# Arquitectura

## Ruta base NN-SAM + MedSAM

La ruta base usa una red ligera tipo CenterNet/U-Net para detectar centros y cajas de vertebras. Las cajas predichas se convierten en prompts para MedSAM.

Componentes principales:

- Entrada radiografica normalizada.
- Detector de cajas vertebrales.
- Prompts tipo box.
- MedSAM ajustado para segmentacion vertebral.
- Evaluacion estricta y flexible.

## Estrategia ganadora: VertebraPrompt + BoxRefiner

La estrategia ganadora conserva la idea de prompts automaticos, pero agrega dos mejoras:

- **VertebraPrompt auxiliar:** red auxiliar que mejora la propuesta inicial de prompts vertebrales.
- **BoxRefiner:** refinador local que ajusta las cajas antes de enviarlas a MedSAM.

El objetivo no es reemplazar MedSAM, sino entregarle prompts mas adecuados para que la segmentacion final sea mas estable.
