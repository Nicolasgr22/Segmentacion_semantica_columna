"""Genera template_bbox.json a partir de prompts.json del split train.

Replica `construir_template_bbox_train` del notebook 06 (celda 7):
toma todas las cajas T1..L5 del split train, las normaliza a 1024 (espacio
del dataset preprocesado), y guarda la mediana de (cx_rel, cy_rel, w_rel,
h_rel) por vértebra. El adapter en producción carga este JSON al iniciar y
lo usa como guía anatómica para el DP.

Uso:
    python services/scripts/generate_template_bbox.py \\
        --prompts services/model-pkg/medsam/prompts.json \\
        --out services/model-pkg/medsam/template_bbox.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median

VERTEBRAE = [
    "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12",
    "L1", "L2", "L3", "L4", "L5",
]
VERTEBRA_TO_ID = {name: i + 1 for i, name in enumerate(VERTEBRAE)}
DATASET_GRID = 1024  # las cajas vienen en coordenadas 1024x1024 (notebook 03)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    with args.prompts.open("r", encoding="utf-8") as f:
        data = json.load(f)

    buckets: dict[str, list[tuple[float, float, float, float]]] = {v: [] for v in VERTEBRAE}
    for item in data:
        prompts_item = item.get("prompts", {})
        iterable = prompts_item.values() if isinstance(prompts_item, dict) else prompts_item
        for info in iterable:
            if not isinstance(info, dict):
                continue
            vertebra = str(info.get("vertebra", "")).upper()
            if vertebra not in VERTEBRA_TO_ID or "bbox_xyxy" not in info:
                continue
            x0, y0, x1, y1 = (float(v) for v in info["bbox_xyxy"])
            cx_rel = ((x0 + x1) / 2) / DATASET_GRID
            cy_rel = ((y0 + y1) / 2) / DATASET_GRID
            w_rel = (x1 - x0) / DATASET_GRID
            h_rel = (y1 - y0) / DATASET_GRID
            buckets[vertebra].append((cx_rel, cy_rel, w_rel, h_rel))

    template = []
    for v in VERTEBRAE:
        rows = buckets[v]
        if not rows:
            raise RuntimeError(f"No hay muestras para {v} en {args.prompts}")
        cx = median(r[0] for r in rows)
        cy = median(r[1] for r in rows)
        w = median(r[2] for r in rows)
        h = median(r[3] for r in rows)
        template.append({
            "vertebra": v,
            "id_real": VERTEBRA_TO_ID[v],
            "cx_rel": round(cx, 6),
            "cy_rel": round(cy, 6),
            "w_rel": round(w, 6),
            "h_rel": round(h, 6),
            "n_samples": len(rows),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    n_total = sum(r["n_samples"] for r in template)
    print(f"Template generado: {args.out}")
    print(f"Vertebras: {len(template)} | muestras totales: {n_total}")
    for r in template:
        print(
            f"  {r['vertebra']:>3s}  cy={r['cy_rel']:.4f}  w={r['w_rel']:.4f}  "
            f"h={r['h_rel']:.4f}  n={r['n_samples']}"
        )


if __name__ == "__main__":
    main()
