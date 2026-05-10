# VertebraAI Frontend

SPA en React 18 + Babel standalone (sin build step) que consume el servicio
`services/` para mostrar análisis de radiografías de columna.

## Pipeline conectado

El frontend está alineado con el pipeline ganador del notebook 06:

```
[ Subir imagen PNG/JPEG ]
       │
       ▼
POST http://localhost:8000/api/vertebraai/xrays
       │
       ▼
[ VertebraPrompt-Net + BoxRefiner + MedSAM ViT-B ]
       │
       ▼
Resultados: máscara base64 + métricas + 22 vértebras (C3-L5)
```

## Cómo correr el frontend

El backend tiene CORS habilitado para `http://localhost:5500` y `http://127.0.0.1:5500`.

```bash
# 1. Asegúrate de que el backend esté corriendo (en otro terminal)
cd services
docker run -p 8000:8000 --name vertebraai vertebraai
# o:  uvicorn app.main:app --reload

# 2. Servir el frontend en localhost:5500 (elige una opción)

# Opción A — npm scripts (recomendado)
cd frontend
npm install              # instala 'serve' localmente (solo la primera vez)
npm start                # corre serve . -l 5500

# Opción B — sin instalar nada (usa npx)
cd frontend
npx serve . -l 5500

# Opción C — Python si no tienes Node
cd frontend
python3 -m http.server 5500

# 3. Abrir en el navegador (los servers estáticos sirven index.html por defecto)
open http://localhost:5500/
```

## Backend en otra URL

Si tu backend corre en otro host/puerto, sobreescribe la variable global
**antes** de que carguen los scripts:

```html
<script>window.BACKEND_URL = 'http://mi-servidor:8080';</script>
<script type="text/babel" src="app.jsx"></script>
```

## Estructura

```
frontend/
├── index.html       Entry point (HTML + tags <script>)
├── app.jsx               App principal: UploadZone, ProcessingScreen, ResultView
├── tweaks-panel.jsx      Panel de ajustes (tema)
├── styles.css            Estilos Material 3 dark mode
└── README.md             (este archivo)
```

## Qué muestra el frontend

Todo lo que el backend devuelve y nada más. Específicamente del endpoint
`POST /api/vertebraai/xrays`:

| Sección UI | Campo del backend |
|---|---|
| Imagen original | `URL.createObjectURL(file)` (local, no del backend) |
| Máscara coloreada | `mask.data` (base64 PNG) |
| Confianza global | `metrics.confidence` |
| Vértebras detectadas | `metrics.detected_count / vertebrae.length` |
| Por región | `metrics.by_region.{cervical,thoracic,lumbar}` |
| Versión modelo | `metrics.model_metrics.model_version` |
| Dice / IoU / latencia | `metrics.model_metrics.{dice, iou, latency_ms}` |
| Tiempo procesamiento | `processing.total_time_ms` |
| Lista de vértebras | `vertebrae[]` (id, label, region, detected, confidence, pixel_count) |
| Dimensiones máscara | `mask.dimensions.{width, height}` |
| Study ID + timestamp | `study_id`, `timestamp` |

Botones de exportar usan `GET /api/vertebraai/xrays/{study_id}/exports/{format}`
con format ∈ `{png, mask, overlay, report}`.

## Qué se eliminó respecto a la versión mock

- C1 y C2 (el modelo solo segmenta C3-C7)
- Ilustración SVG fake de columna y máscara → ahora son imágenes reales
- HUD con metadata DICOM hardcodeada (`kVp 75 · mA 320`, `RGBA · 16-bit`, `VIEW · LATERAL`)
- Subtítulo "v2.4" hardcodeado → ahora muestra `model_version` real
- "U-Net 3D" hardcodeado → ahora muestra el modelo real
- Métricas inventadas (Dice 0.943, IoU 0.892) → ahora vienen del análisis real
- Modos de color (Región/Gradiente/Único/Mono) — la máscara viene ya coloreada del backend
- Toggle de etiquetas — la máscara del backend ya es la final
- Tab "Historial / Modelo / Ayuda" — endpoints aún no existen
- `vertebra-assets.jsx` (componentes SVG fake) — eliminado del proyecto
