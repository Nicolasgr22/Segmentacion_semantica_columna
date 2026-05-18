"""
Sube el modelo entrenado (medsam_lastblock_unfrozen.pth) a Databricks via MLflow.
El nombre del modelo en Unity Catalog se deriva del experimento configurado en .env.
La versión se lee del archivo model/VERSION.

Si ya existe una versión registrada con el mismo nombre y número de VERSION,
el upload se omite. Para forzarlo usa --force.

Uso desde terminal:
    cd package-src/medsam
    python -m model.upload_to_databricks            # omite si ya existe v0.1.0
    python -m model.upload_to_databricks --force    # sube aunque ya exista

Configuración requerida:
    Ajusta UC_CATALOG y UC_SCHEMA al catálogo y schema de tu workspace.
    El nombre del modelo se toma automáticamente del MLFLOW_EXPERIMENT_NAME en .env.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from pathlib import Path

import mlflow
import yaml
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient

# ─── Rutas ───────────────────────────────────────────────────────────────────

MODEL_DIR = Path(__file__).resolve().parent
PKG_ROOT  = MODEL_DIR.parent
CONFIG    = MODEL_DIR / "config" / "config.yml"
VERSION_FILE = MODEL_DIR / "VERSION"

# ─── Configuración Unity Catalog ─────────────────────────────────────────────
UC_CATALOG = "workspace"   # catálogos disponibles: workspace, system, samples
UC_SCHEMA  = "default"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _read_version() -> str:
    return VERSION_FILE.read_text().strip()


def _load_config() -> dict:
    with open(CONFIG) as f:
        return yaml.safe_load(f)


def _connect_databricks() -> tuple[str, str]:
    env_file = PKG_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    host     = os.getenv("DATABRICKS_HOST", "").rstrip("/")
    token    = os.getenv("DATABRICKS_TOKEN", "")
    exp_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/columna-vertebral-medsam")

    if not host or not token:
        raise EnvironmentError(
            "DATABRICKS_HOST y DATABRICKS_TOKEN deben estar definidos en .env."
        )

    os.environ["MLFLOW_TRACKING_URI"]   = host
    os.environ["DATABRICKS_HOST"]       = host
    os.environ["DATABRICKS_TOKEN"]      = token
    os.environ["MLFLOW_TRACKING_TOKEN"] = token
    mlflow.set_registry_uri("databricks-uc")

    return host, exp_name


def _derive_uc_model_name(exp_name: str, file_version: str) -> str:
    """Construye el nombre del modelo en Unity Catalog incluyendo la versión.

    Ejemplo:
        exp_name="/Users/anferiro@gmail.com/columna-vertebral-medsam"
        file_version="0.1.0"
        → "workspace.default.columna-vertebral-medsam-0_1_0"

    Nota: los puntos del número de versión se reemplazan por '_' porque
    Unity Catalog no permite '.' dentro del nombre del modelo (solo como
    separador catalog.schema.nombre).
    """
    base = exp_name.rstrip("/").split("/")[-1]
    base = re.sub(r"[^a-zA-Z0-9_-]", "_", base)
    version_suffix = file_version.replace(".", "_")
    return f"{UC_CATALOG}.{UC_SCHEMA}.{base}-{version_suffix}"


def _model_exists(uc_model_name: str) -> str | None:
    """Verifica si el modelo ya está registrado en Unity Catalog.
    Retorna la última versión MLflow si existe, None si no."""
    try:
        client   = MlflowClient()
        versions = client.search_model_versions(f"name='{uc_model_name}'")
        if not versions:
            return None
        return str(max(int(v.version) for v in versions))
    except Exception:
        return None


def _list_uc_catalogs(host: str, token: str) -> list[str]:
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient(host=host, token=token)
        return [c.name for c in w.catalogs.list()]
    except Exception:
        return []


def _list_uc_schemas(host: str, token: str, catalog: str) -> list[str]:
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient(host=host, token=token)
        return [s.name for s in w.schemas.list(catalog_name=catalog)]
    except Exception:
        return []


def _classify_error(e: Exception, host: str = "", token: str = "", uc_model_name: str = "") -> str:
    msg = str(e)
    if "CATALOG_DOES_NOT_EXIST" in msg:
        catalogs = _list_uc_catalogs(host, token)
        hint = (
            "\n  Catálogos disponibles en tu workspace:\n    " +
            "\n    ".join(catalogs)
            if catalogs else
            "\n  No se pudieron listar los catálogos (verifica permisos)."
        )
        if catalogs:
            first   = catalogs[0]
            schemas = _list_uc_schemas(host, token, first)
            schema  = schemas[0] if schemas else "default"
            hint += f"\n\n  → Actualiza UC_CATALOG y UC_SCHEMA en upload_to_databricks.py:\n"
            hint += f'    UC_CATALOG = "{first}"\n'
            hint += f'    UC_SCHEMA  = "{schema}"'
        return f"El catálogo especificado no existe.{hint}"
    if "SCHEMA_DOES_NOT_EXIST" in msg:
        return (
            f"El schema '{UC_SCHEMA}' no existe en el catálogo '{UC_CATALOG}'.\n"
            "  → Verifica los schemas en Databricks > Data > (tu catálogo)\n"
            "  → Actualiza UC_SCHEMA en upload_to_databricks.py"
        )
    if "PERMISSION_DENIED" in msg:
        return (
            "Sin permisos sobre el catálogo/schema.\n"
            f"  → Verifica que tu token tiene acceso a {UC_CATALOG}.{UC_SCHEMA}"
        )
    if "ModuleNotFoundError" in msg or "No module named" in msg:
        return (
            "Falta una dependencia Python.\n"
            "  → Instala con: pip install segment-anything"
        )
    if "INVALID_PARAMETER_VALUE" in msg and "three-level" in msg:
        return (
            "El nombre del modelo no tiene el formato Unity Catalog requerido.\n"
            f"  → Debe ser catalog.schema.nombre\n"
            f"  → Valor actual: '{uc_model_name}'"
        )
    if "UNAUTHENTICATED" in msg or "401" in msg:
        return "Token inválido o expirado. Genera uno nuevo en Databricks > Settings > Developer."
    return str(e)


# ─── Registro Unity Catalog (asume run MLflow activo) ─────────────────────────

def register_in_uc(
    model,
    *,
    exp_name: str | None = None,
    file_version: str | None = None,
    force: bool = False,
) -> dict:
    """
    Registra un modelo PyTorch ya cargado en memoria en Unity Catalog,
    DENTRO del run MLflow que esté activo. No crea un run nuevo.

    Pensada para llamarse al final de train() en el mismo run del entrenamiento.

    Args:
        model:        modelo PyTorch ya cargado (con state_dict del best checkpoint).
        exp_name:     nombre del experimento; si None se lee de MLFLOW_EXPERIMENT_NAME.
        file_version: versión semántica; si None se lee de model/VERSION.
        force:       True para subir aunque el modelo ya exista en UC.

    Returns:
        dict con: skipped (bool), uc_model_name, version (str|None), uc_url, reason
    """
    # Configurar registry UC y resolver nombres
    mlflow.set_registry_uri("databricks-uc")

    if exp_name is None:
        exp_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/columna-vertebral-medsam")
    if file_version is None:
        file_version = _read_version()

    host = os.getenv("DATABRICKS_HOST", "").rstrip("/")
    uc_model_name  = _derive_uc_model_name(exp_name, file_version)
    exp_base       = exp_name.rstrip("/").split("/")[-1]
    artifact_name  = f"{exp_base}-{file_version.replace('.', '_')}"
    uc_url         = f"{host}/explore/data/models/{uc_model_name.replace('.', '/')}"

    # Verificar existencia
    existing = _model_exists(uc_model_name)
    if existing and not force:
        print(f"\n[OMITIDO] El modelo '{uc_model_name}' ya existe en Unity Catalog (v{existing}).")
        print(f"  Modelo: {uc_url}")
        print(f"  Para nueva versión: actualiza model/VERSION (ej: 0.2.0)")
        print(f"  Para forzar (nueva versión MLflow del mismo modelo): pasa force=True")
        return {
            "skipped":       True,
            "uc_model_name": uc_model_name,
            "version":       existing,
            "uc_url":        uc_url,
            "reason":        "already_exists",
        }

    if existing and force:
        print(f"\n[--force] Modelo ya existía como v{existing}. Subiendo nueva versión MLflow...")

    # Loguear parámetros descriptivos en el run activo
    mlflow.log_params({
        "version_file":  file_version,
        "uc_model_name": uc_model_name,
    })

    print(f"\n  Registrando en Unity Catalog: {uc_model_name} ...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mlflow.pytorch.log_model(
            pytorch_model=model,
            name=artifact_name,
            registered_model_name=uc_model_name,
        )

    new_version = _model_exists(uc_model_name)
    if new_version:
        client = MlflowClient()
        client.set_model_version_tag(uc_model_name, new_version, "version_file", file_version)

    print(f"  ✓ Registrado: {uc_model_name} → v{new_version or '?'}")
    print(f"  Ver en: {uc_url}")

    return {
        "skipped":       False,
        "uc_model_name": uc_model_name,
        "version":       new_version,
        "uc_url":        uc_url,
        "reason":        "registered",
    }


# ─── Upload standalone (re-sube .pth desde disco, crea su propio run) ─────────

def upload_model(*, run_name: str | None = None, force: bool = False) -> str:
    """
    Carga el checkpoint fine-tuneado, lo sube a Databricks MLflow y lo registra
    en Unity Catalog. Usa el archivo VERSION para etiquetar la versión.

    Si ya existe una versión con el mismo número de VERSION, omite el upload
    a menos que force=True.

    Returns:
        run_id del run creado, o "" si se omitió o falló.
    """
    cfg            = _load_config()
    host, exp_name = _connect_databricks()
    save_dir       = MODEL_DIR / cfg["paths"]["save_dir"]
    file_version   = _read_version()

    model_path   = save_dir / cfg["training"]["checkpoint_name"]
    summary_path = save_dir / "test_summary.json"
    report_path  = save_dir / "test_report.csv"

    uc_model_name = _derive_uc_model_name(exp_name, file_version)   # incluye versión
    exp_base      = exp_name.rstrip("/").split("/")[-1]              # "columna-vertebral-medsam"
    artifact_name = f"{exp_base}-{file_version.replace('.', '_')}"   # mismo que el modelo UC

    if run_name is None:
        run_name = exp_base

    if not model_path.exists():
        raise FileNotFoundError(
            f"\n[ERROR] Checkpoint no encontrado:\n  {model_path}\n"
            "Completa el entrenamiento primero."
        )

    print(f"\n{'=' * 60}")
    print(f"  Subiendo modelo a Databricks MLflow + Unity Catalog")
    print(f"  Host:        {host}")
    print(f"  Experimento: {exp_name}")
    print(f"  Modelo UC:   {uc_model_name}")
    print(f"  Versión:     {file_version}  (model/VERSION)")
    print(f"  Archivo:     {model_path.name}  ({model_path.stat().st_size / 1e6:.1f} MB)")
    print(f"{'=' * 60}\n")

    # ── Verificar si ya existe este modelo (nombre incluye versión) ──────────
    existing_uc_version = _model_exists(uc_model_name)
    if existing_uc_version and not force:
        uc_url = f"{host}/explore/data/models/{uc_model_name.replace('.', '/')}"
        print(f"[OMITIDO] El modelo '{uc_model_name}' ya existe en Unity Catalog.")
        print(f"  Última versión MLflow: v{existing_uc_version}")
        print(f"  Modelo: {uc_url}")
        print(f"\n  Para forzar (crea nueva versión MLflow del mismo modelo):")
        print(f"    python -m model.upload_to_databricks --force")
        print(f"  Para registrar una versión nueva, actualiza model/VERSION (ej: 0.2.0).")
        return ""

    if existing_uc_version and force:
        print(f"[--force] El modelo ya existe como v{existing_uc_version}. Subiendo nueva versión MLflow...\n")

    # ── Upload ────────────────────────────────────────────────────────────────
    metrics: dict = {}
    if summary_path.exists():
        metrics = json.loads(summary_path.read_text())

    mlflow.set_experiment(exp_name)
    experiment    = mlflow.get_experiment_by_name(exp_name)
    experiment_id = experiment.experiment_id if experiment else "unknown"

    run_id: str = ""
    new_uc_version: int | None = None
    upload_error: Exception | None = None

    try:
        from segment_anything import sam_model_registry
        import torch

        print("  Cargando modelo en memoria...")
        sam_ckpt   = MODEL_DIR / cfg["paths"]["sam_checkpoint"]
        model      = sam_model_registry["vit_b"](checkpoint=str(sam_ckpt))
        state_dict = torch.load(str(model_path), map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()
        print("  Modelo cargado.\n")

        with mlflow.start_run(run_name=run_name) as run:
            run_id = run.info.run_id

            mlflow.log_params({
                "model_type":    "MedSAM-ViT-B",
                "estrategia":    cfg["mlflow"]["params"]["estrategia"],
                "checkpoint":    model_path.name,
                "version_file":  file_version,
                "uc_model_name": uc_model_name,
            })

            if metrics:
                mlflow.log_metrics({
                    k: v for k, v in metrics.items()
                    if isinstance(v, (int, float))
                })

            print("  Subiendo a MLflow Models (puede tardar ~1 min)...")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mlflow.pytorch.log_model(
                    pytorch_model=model,
                    name=artifact_name,
                    registered_model_name=uc_model_name,
                )

            if summary_path.exists():
                mlflow.log_artifact(str(summary_path), artifact_path="reports")
            if report_path.exists():
                mlflow.log_artifact(str(report_path), artifact_path="reports")

        # Etiquetar la versión recién registrada con el número de VERSION
        latest = _model_exists(uc_model_name)
        if latest:
            new_uc_version = int(latest)
            client = MlflowClient()
            client.set_model_version_tag(uc_model_name, str(new_uc_version), "version_file", file_version)

    except Exception as e:
        upload_error = e

    # ── Resultado ─────────────────────────────────────────────────────────────
    print()
    if upload_error:
        print(f"[ERROR] El upload falló:\n  {_classify_error(upload_error, host, os.getenv('DATABRICKS_TOKEN', ''), uc_model_name)}")
        if run_id:
            run_url = f"{host}/#/experiments/{experiment_id}/runs/{run_id}"
            print(f"\n  El run sí existe en MLflow (artefactos subidos):")
            print(f"  {run_url}")
        return ""

    client = MlflowClient()
    try:
        found = [a.path for a in client.list_artifacts(run_id, path=artifact_name)]
    except Exception:
        found = []

    run_url = f"{host}/#/experiments/{experiment_id}/runs/{run_id}"
    uc_url  = f"{host}/explore/data/models/{uc_model_name.replace('.', '/')}"
    version_str = f"v{new_uc_version}" if new_uc_version else "(versión no disponible)"

    if found:
        print("  Artefactos confirmados en Databricks:")
        for p in found:
            print(f"    ✓ {p}")
    else:
        print("  [AVISO] No se pudieron listar artefactos via API.")

    print(f"\n{'=' * 60}")
    print(f"  Modelo:           {uc_model_name}")
    print(f"  VERSION (archivo): {file_version}")
    print(f"  Versión MLflow:   {version_str}")
    print(f"  Run ID:           {run_id}\n")
    print(f"  Ver el run en MLflow:")
    print(f"  {run_url}\n")
    print(f"  Ver el modelo en Unity Catalog (Models):")
    print(f"  {uc_url}")
    print(f"{'=' * 60}\n")

    return run_id


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sube el modelo MedSAM a Databricks Unity Catalog.")
    p.add_argument(
        "--force",
        action="store_true",
        help="Fuerza el upload aunque ya exista una versión con el mismo VERSION.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    upload_model(force=args.force)


# ══════════════════════════════════════════════════════════════════════════════
# ── NOTEBOOK ─ Copiar este bloque al final de tu notebook de entrenamiento ──
# ══════════════════════════════════════════════════════════════════════════════
#
# import os, re, warnings, torch, mlflow
# from pathlib import Path
# from segment_anything import sam_model_registry
# from mlflow.tracking import MlflowClient
#
# DATABRICKS_HOST  = "https://dbc-250dea69-0463.cloud.databricks.com"
# DATABRICKS_TOKEN = "<tu-token>"        # o: dbutils.secrets.get("scope", "key")
# EXPERIMENT_NAME  = "/Users/anferiro@gmail.com/columna-vertebral-medsam"
# SAM_CHECKPOINT   = "ruta/a/sam_vit_b_01ec64.pth"
# FINETUNED_PATH   = "ruta/a/tu_modelo.pth"
# VERSION_FILE     = "ruta/a/model/VERSION"          # ajustar por equipo
# UC_CATALOG       = "hive_metastore"
# UC_SCHEMA        = "default"
# FORCE            = False                            # True para re-subir aunque exista
#
# file_version    = Path(VERSION_FILE).read_text().strip()
# exp_base        = re.sub(r"[^a-zA-Z0-9_-]", "_", EXPERIMENT_NAME.rstrip("/").split("/")[-1])
# version_suffix  = file_version.replace(".", "_")
# UC_MODEL_NAME   = f"{UC_CATALOG}.{UC_SCHEMA}.{exp_base}-{version_suffix}"   # ← incluye versión
#
# os.environ["MLFLOW_TRACKING_URI"]   = DATABRICKS_HOST
# os.environ["DATABRICKS_HOST"]       = DATABRICKS_HOST
# os.environ["DATABRICKS_TOKEN"]      = DATABRICKS_TOKEN
# os.environ["MLFLOW_TRACKING_TOKEN"] = DATABRICKS_TOKEN
# mlflow.set_registry_uri("databricks-uc")
#
# # Verificar si el modelo ya existe (el nombre incluye la versión del archivo VERSION)
# client   = MlflowClient()
# versions = client.search_model_versions(f"name='{UC_MODEL_NAME}'")
#
# if versions and not FORCE:
#     latest = max(int(v.version) for v in versions)
#     print(f"[OMITIDO] {UC_MODEL_NAME} ya existe (v{latest}). Cambia VERSION o usa FORCE=True.")
# else:
#     model = sam_model_registry["vit_b"](checkpoint=SAM_CHECKPOINT)
#     model.load_state_dict(torch.load(FINETUNED_PATH, map_location="cpu", weights_only=True))
#     model.eval()
#
#     mlflow.set_experiment(EXPERIMENT_NAME)
#     with mlflow.start_run(run_name=exp_base) as run:
#         mlflow.log_params({"version_file": file_version, "uc_model_name": UC_MODEL_NAME})
#         mlflow.log_metrics({"test_dice": 0.838, "test_iou": 0.732})
#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore")
#             mlflow.pytorch.log_model(model, name=f"{exp_base}-{version_suffix}", registered_model_name=UC_MODEL_NAME)
#         run_id = run.info.run_id
#
#     new_versions = client.search_model_versions(f"name='{UC_MODEL_NAME}'")
#     latest = max(int(v.version) for v in new_versions)
#     client.set_model_version_tag(UC_MODEL_NAME, str(latest), "version_file", file_version)
#     print(f"Registrado: {UC_MODEL_NAME} → v{latest}  (VERSION={file_version})")
#     print(f"{DATABRICKS_HOST}/explore/data/models/{UC_MODEL_NAME.replace('.', '/')}")
