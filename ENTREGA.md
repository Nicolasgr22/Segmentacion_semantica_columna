# VertebraAI — Entrega Proyecto de Grado

**Maestría en Inteligencia Artificial (MaIA)**  
Universidad de los Andes — 2026

---

## Equipo

| Nombre |
|---|
| Nicolás Garzón |
| Sandra Lancheros |
| Luis Felipe Millán |
| Andrés Felipe Rincón |
| Juan Arenas |

---

## Repositorio GitHub

[https://github.com/Nicolasgr22/Segmentacion_semantica_columna](https://github.com/Nicolasgr22/Segmentacion_semantica_columna)

---

## Aplicación Funcional Desplegada

[https://dfhufk420fyn.cloudfront.net](https://dfhufk420fyn.cloudfront.net)

**Credenciales de acceso:**

| Campo | Valor |
|---|---|
| Usuario | `maia_grupo5` |
| Contraseña | _(compartida con el docente por canal seguro)_ |

---

## Carpetas Obligatorias

| Carpeta | Ubicación | Contenido |
|---|---|---|
| `Notebooks/` | [`notebooks/`](https://github.com/Nicolasgr22/Segmentacion_semantica_columna/tree/main/notebooks) — en este repositorio | Cuadernos con análisis, entrenamiento y pruebas. Pipeline VertebraPrompt-Net + BoxRefiner + MedSAM (notebooks 01–06), barrido de hiperparámetros UNet++ y experimentos de evaluación. |
| `Modelos/` | `s3://maia-proyecto-final-models/models/` — **no se incluye en el repositorio git por restricciones de tamaño** | Archivos del modelo final guardado (`.pt`, `.pth`). Checkpoints de VertebraPrompt-Net, BoxRefiner, MedSAM ViT-B fine-tuned y UNet++ EfficientNet-B7. |
| `Datos/` | [`data/`](https://github.com/Nicolasgr22/Segmentacion_semantica_columna/tree/main/data) — en este repositorio | Muestras y estructura de los datos usados: radiografías preprocesadas (grilla 1024×1024 RGB), máscaras de segmentación etiquetadas y resultados de evaluación. |

Para descargar los modelos:
```bash
aws s3 cp s3://maia-proyecto-final-models/models/ ./models/ --recursive --profile vertebraai-models
```

**Credenciales S3 (solo lectura):**

| Campo | Valor |
|---|---|
| Bucket | `s3://maia-proyecto-final-models` |
| Región | `us-east-1` |
| AWS Access Key ID | `AKIAZQ3DPKVWU4CKQKNG` |
| AWS Secret Access Key | _(compartida con el docente por canal seguro)_ |

---

*Documento generado: 2026-05-20*
