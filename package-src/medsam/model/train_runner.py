"""
Punto de entrada CLI para el entrenamiento de MedSAM.

Lee config/config.yml y las credenciales de .env (en la raíz del paquete).
Registrado como entry_point en setup.py → disponible como comando `medsam-train`.

Uso:
    cd package-src/medsam
    python -m model.train_runner
    python -m model.train_runner --epochs 5
    medsam-train                          # si el paquete está instalado

Nota sobre device:
    El dispositivo se detecta automáticamente igual que en el notebook:
        "cuda" if torch.cuda.is_available() else "cpu"
    No se expone como argumento CLI porque no debe forzarse manualmente.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import mlflow
import torch
import yaml
from dotenv import load_dotenv

# ─── Rutas base ──────────────────────────────────────────────────────────────
MODEL_DIR = Path(__file__).resolve().parent  # package-src/medsam/model/
PKG_ROOT = MODEL_DIR.parent  # package-src/medsam/
CONFIG_PATH = MODEL_DIR / "config/config.yml"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MedSAM fine-tuning runner")
    # device: calculado automáticamente como en el notebook, no es argumento
    p.add_argument(
        "--epochs",
        type=int,
        default=20,  # hardcodeado en notebook: num_epochs_final = 20
        help="Épocas máximas de entrenamiento",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=2,  # hardcodeado en notebook: batch_size=2 en DataLoader
        help="Muestras por batch",
    )
    p.add_argument("--config", default=str(CONFIG_PATH))
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    # Credenciales MLflow / Databricks
    env_file = PKG_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
    else:
        print(f"[WARN] No se encontró .env en {env_file}. MLflow usará tracking local.")

    # Configuración
    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    tr = cfg["training"]
    paths = cfg["paths"]
    opt = tr["optimizer"]
    sched = tr["scheduler"]
    es = tr["early_stopping"]

    splits_csv = MODEL_DIR / paths["splits_csv"]
    sam_ckpt = MODEL_DIR / paths["sam_checkpoint"]
    save_dir = MODEL_DIR / paths["save_dir"]

    # Generar splits si no existen
    if not splits_csv.exists():
        print("splits.csv no encontrado — generando desde indice_dataset.csv...")
        from model.pipeline import generar_splits

        generar_splits(
            dataset_root=MODEL_DIR / paths["dataset_root"],
            output_csv=splits_csv,
            seed=tr["seed"],
        )

    # Validar checkpoint
    if not sam_ckpt.exists():
        print(f"[ERROR] Checkpoint SAM no encontrado: {sam_ckpt}")
        print(f"        Copia sam_vit_b_01ec64.pth en: {sam_ckpt.parent}")
        sys.exit(1)

    # MLflow
    host = os.getenv("DATABRICKS_HOST", "")
    token = os.getenv("DATABRICKS_TOKEN", "")
    exp_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "columna-vertebral-medsam")

    if host and token:
        os.environ["MLFLOW_TRACKING_URI"] = host
        os.environ["MLFLOW_TRACKING_TOKEN"] = token
        print(f"MLflow → Databricks: {host}")
    else:
        mlflow.set_tracking_uri(str(PKG_ROOT / "mlruns"))
        print("MLflow → local (mlruns/)")

    mlflow.set_experiment(exp_name)

    # Device: igual que en el notebook — calculado, no hardcodeado
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\n{'=' * 55}")
    print(f"  MedSAM Fine-tuning — {cfg['mlflow']['run_name']}")
    print(f"{'=' * 55}")
    print(f"  device     : {device}")
    print(f"  epochs     : {args.epochs}")
    print(f"  batch_size : {args.batch_size}")
    print(f"  splits_csv : {splits_csv}")
    print(f"  checkpoint : {sam_ckpt}")
    print(f"  save_dir   : {save_dir}")
    print(f"{'=' * 55}\n")

    from model import train

    results = train(
        splits_csv=splits_csv,
        checkpoint_path=sam_ckpt,
        save_dir=save_dir,
        device=device,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        num_workers=tr["num_workers"],
        box_pad=tr["box_pad"],
        num_pos_points=tr["num_pos_points"],
        neg_offset=tr["neg_offset"],
        decoder_lr=float(opt["decoder_lr"]),
        encoder_lr=float(opt["encoder_last_block_lr"]),
        weight_decay=float(opt["weight_decay"]),
        scheduler_patience=int(sched["patience"]),
        early_stopping_patience=int(es["patience"]),
        min_delta=float(es["min_delta"]),
        checkpoint_name=tr["checkpoint_name"],
        mlflow_run_name=cfg["mlflow"]["run_name"],
        seed=tr["seed"],
    )

    print(f"\nEntrenamiento terminado. Mejor Val Dice: {results['best_val_dice']:.4f}")
    print(f"Modelo guardado en: {results['best_model_path']}")


if __name__ == "__main__":
    main()
