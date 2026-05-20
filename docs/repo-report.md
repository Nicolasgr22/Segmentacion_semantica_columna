 # Segmentacion_semantica_columna — Technical Documentation (L3)

> **Status:** DRAFT — pending Tech Lead signature
> **Commit:** `d3fe049a`
> **Generated:** 2026-05-20 12:13 UTC
> **Agent:** NarrativeAgent v1.0.0 | Model: (from env) | Prompt: `(computed)`

---

## Purpose

This repository appears to provide a medical imaging service for semantic segmentation of spinal columns, likely exposing a PyTorch-based model via a FastAPI API to analyze radiographs and compute scoliosis metrics such as Cobb angles. The presence of `medsam` paths and `Scoliosis_Dataset` resources suggests it builds on or extends MedSAM for vertebral segmentation and deformity assessment.

---

## Technical Stack

| Component | Technology | Role |
|---|---|---|
| Language | python | Primary development language |
| Language | javascript | Detected (likely frontend or build scripts) |
| Web framework | fastapi | HTTP API for image upload and inference |
| Server | uvicorn | ASGI server to run the FastAPI application |
| File handling | python-multipart | Multipart form parsing for image uploads |
| Deep learning | torch | Tensor computation and model execution |
| Deep learning | torchvision | PyTorch computer vision utilities |
| Deep learning | transformers | Hugging Face model loading and inference |
| Image processing | opencv-python-headless | Radiograph manipulation without GUI dependencies |
| Image processing | Pillow | Image loading and basic transformations |
| Image processing | albumentations | Image augmentation pipeline |
| Numerical computing | numpy | Array operations and data handling |
| Validation | pydantic | Request/response schema validation |
| Configuration | pydantic-settings | Environment-based application settings |
| Testing | pytest | Test runner |
| Testing | pytest-asyncio | Async test support |
| Testing | httpx | HTTP client for API tests |
| Testing | pytest-cov | Coverage reporting |
| Dev tooling | serve | Static file serving (npm dev dependency) |

---

## Code Quality Metrics

| Metric | Value | Signal |
|---|---|---|
| Files analyzed | 641 | |
| Functions / methods | 3030 | |
| Classes | 700 | |
| Avg cyclomatic complexity | 9.0 | HIGH |
| Max cyclomatic complexity | 125 | ⚠️ Exceeds threshold of 10 |
| Comment ratio | 2.9% | LOW |
| Avg function length | 10.7 lines | |
| Max function length | 259 lines | ⚠️ Exceeds threshold of 50 |

---

## Hotspots

Files with highest cyclomatic complexity — highest change risk.

- `deprecated/package-src/medsam/model/recursos/Scoliosis_Dataset/RadiographMetrics/generar_curvas_cobb_y_overlays.py` — complexity 125 ⚠️
- `.claude/worktrees/agent-aabee4b512b9860ac/deprecated/package-src/medsam/model/recursos/Scoliosis_Dataset/RadiographMetrics/generar_curvas_cobb_y_overlays.py` — complexity 125 ⚠️
- `.claude/worktrees/agent-aa6be73a3c2b69e93/deprecated/package-src/medsam/model/recursos/Scoliosis_Dataset/RadiographMetrics/generar_curvas_cobb_y_overlays.py` — complexity 125 ⚠️
- `.claude/worktrees/agent-aaaf7445c41100f17/deprecated/package-src/medsam/model/recursos/Scoliosis_Dataset/RadiographMetrics/generar_curvas_cobb_y_overlays.py` — complexity 125 ⚠️
- `.claude/worktrees/agent-a06c951f07190d29d/deprecated/package-src/medsam/model/recursos/Scoliosis_Dataset/RadiographMetrics/generar_curvas_cobb_y_overlays.py` — complexity 125 ⚠️

The file `generar_curvas_cobb_y_overlays.py` implements Cobb angle calculation and overlay generation for scoliosis radiographs; its complexity of 125 indicates extreme branching in geometric analysis and rendering logic, making any changes to angle computation, threshold tuning, or visualization overlays highly error-prone. The identical file is duplicated across `deprecated/` and `.claude/worktrees/` paths, so edits must account for stale copies to avoid metric inflation and inconsistent behavior.

---

## Dependencies

### Declared (from manifest)

- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*
- `serve` ^14.2.4 (npm) *(dev)*
- `fastapi` >=0.111.0 (pypi)
- `uvicorn` >=0.30.0 (pypi)
- `python-multipart` >=0.0.9 (pypi)
- `pydantic` >=2.7.0 (pypi)
- `pydantic-settings` >=2.3.0 (pypi)
- `transformers` >=4.40.0 (pypi)
- `torch` >=2.1.0 (pypi)
- `torchvision` >=0.16.0 (pypi)
- `Pillow` >=10.3.0 (pypi)
- `opencv-python-headless` >=4.9.0.80 (pypi)
- `numpy` >=1.26.0 (pypi)
- `albumentations` >=1.4.0 (pypi)
- `pytest` >=8.0.0 (pypi) *(dev)*
- `pytest-asyncio` >=0.23.0 (pypi) *(dev)*
- `httpx` >=0.27.0 (pypi) *(dev)*
- `pytest-cov` >=5.0.0 (pypi) *(dev)*

**Dependency groups:**
- **Web API & Serving:** `fastapi`, `uvicorn`, `python-multipart` — handle HTTP requests and image uploads for the segmentation service.
- **Deep Learning:** `torch`, `torchvision`, `transformers` — load and execute PyTorch segmentation models.
- **Image Processing & Augmentation:** `opencv-python-headless`, `Pillow`, `albumentations`, `numpy` — preprocess, augment, and manipulate radiograph images.
- **Data Validation & Configuration:** `pydantic`, `pydantic-settings` — enforce API contracts and manage runtime settings.
- **Testing:** `pytest`, `pytest-asyncio`, `httpx`, `pytest-cov` — run async tests, exercise HTTP endpoints, and measure coverage.
- **Static File Serving (Dev):** `serve` — npm dev dependency for local static asset serving.

---

## Architecture Notes

- The repository wraps a PyTorch segmentation pipeline (likely MedSAM-based, per deprecated paths) in a FastAPI service, using OpenCV and Albumentations for radiograph preprocessing.
- An average cyclomatic complexity of 9.0 across 3,030 functions, paired with a 2.9% comment ratio, indicates significant maintainability debt and high cognitive load.
- The same high-complexity file (`generar_curvas_cobb_y_overlays.py`) is replicated across `deprecated/` and multiple `.claude/worktrees/` directories, suggesting stale artifacts or AI-generated copies that distort true code health.
- With 21,920 files skipped versus only 641 analyzed, the repository likely contains large non-code artifacts (datasets, model weights, or node_modules) outside the scope of source analysis.
- No database or persistence dependencies are declared; the architecture appears to be stateless inference-over-HTTP, relying on in-memory processing and temporary file uploads.

---

## Signature

> This document is **DRAFT** until signed by a Tech Lead or Domain Architect.
> Sign with: `eaa approve <report-id> --role "Tech Lead"`

| Role | Name | Date | Signature |
|---|---|---|---|
| Tech Lead | | | |
| Domain Architect (optional) | | | |