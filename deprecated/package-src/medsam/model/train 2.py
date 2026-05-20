"""
Entrenamiento de MedSAM con fine-tuning del último bloque del encoder.

Estrategia (experimento final del notebook 04-medsam-exp-final-unfreeze):
  - image_encoder: todo congelado salvo el último bloque transformer (LR=1e-5)
  - prompt_encoder: congelado
  - mask_decoder: entrenable (LR=1e-4)
  - Prompts: bounding box derivado de la máscara + puntos positivos/negativos
  - Pérdida: BCE + Dice
  - MLflow sobre Databricks para tracking de métricas y artefactos
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm.auto import tqdm

from .pipeline.preprocessing import postprocess_mask


# ─── Métricas ────────────────────────────────────────────────────────────────


def dice_loss(
    logits: torch.Tensor, targets: torch.Tensor, eps: float = 1e-6
) -> torch.Tensor:
    probs = torch.sigmoid(logits).view(logits.size(0), -1)
    targets = targets.view(targets.size(0), -1)
    inter = (probs * targets).sum(dim=1)
    union = probs.sum(dim=1) + targets.sum(dim=1)
    return (1.0 - (2 * inter + eps) / (union + eps)).mean()


def dice_from_logits(
    logits: torch.Tensor, targets: torch.Tensor, eps: float = 1e-6
) -> torch.Tensor:
    preds = (torch.sigmoid(logits) > 0.5).float().view(logits.size(0), -1)
    targets = targets.view(targets.size(0), -1)
    inter = (preds * targets).sum(dim=1)
    union = preds.sum(dim=1) + targets.sum(dim=1)
    return ((2 * inter + eps) / (union + eps)).mean()


def dice_np(pred: np.ndarray, gt: np.ndarray, eps: float = 1e-6) -> float:
    pred, gt = pred.astype(bool), gt.astype(bool)
    return float(2 * np.logical_and(pred, gt).sum() / (pred.sum() + gt.sum() + eps))


def iou_np(pred: np.ndarray, gt: np.ndarray, eps: float = 1e-6) -> float:
    pred, gt = pred.astype(bool), gt.astype(bool)
    return float(np.logical_and(pred, gt).sum() / (np.logical_or(pred, gt).sum() + eps))


def precision_np(pred: np.ndarray, gt: np.ndarray, eps: float = 1e-6) -> float:
    pred, gt = pred.astype(bool), gt.astype(bool)
    tp = np.logical_and(pred, gt).sum()
    return float(tp / (tp + np.logical_and(pred, ~gt).sum() + eps))


def recall_np(pred: np.ndarray, gt: np.ndarray, eps: float = 1e-6) -> float:
    pred, gt = pred.astype(bool), gt.astype(bool)
    tp = np.logical_and(pred, gt).sum()
    return float(tp / (tp + np.logical_and(~pred, gt).sum() + eps))


# ─── Prompts SAM ─────────────────────────────────────────────────────────────


def _get_points_from_mask(
    mask_2d: torch.Tensor,
    num_pos: int = 3,
    neg_offset: int = 15,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """
    Genera puntos positivos (dentro de la máscara) y negativos (fuera)
    para usar como prompt adicional junto al bounding box.
    """
    mask_np = mask_2d.detach().cpu().numpy().astype(np.uint8)
    ys, xs = np.where(mask_np > 0)
    if len(xs) == 0:
        return None, None

    # H no se usa: solo W es necesario para clampear coordenadas x
    _, W = mask_np.shape
    sample_ys = np.linspace(ys.min(), ys.max(), num_pos).astype(int)
    pos_pts, neg_pts = [], []

    for y in sample_ys:
        row_xs = np.where(mask_np[y] > 0)[0]
        if len(row_xs) == 0:
            valid = np.where(mask_np.sum(axis=1) > 0)[0]
            if len(valid) == 0:
                continue
            y = int(valid[np.argmin(np.abs(valid - y))])
            row_xs = np.where(mask_np[y] > 0)[0]

        x_left, x_right = int(row_xs.min()), int(row_xs.max())
        pos_pts.append([(x_left + x_right) // 2, y])
        neg_pts.append([max(0, x_left - neg_offset), y])
        neg_pts.append([min(W - 1, x_right + neg_offset), y])

    if not pos_pts:
        return None, None

    coords = np.array(pos_pts + neg_pts, dtype=np.float32)
    labels = np.array([1] * len(pos_pts) + [0] * len(neg_pts), dtype=np.int64)
    return coords, labels


# ─── Forward SAM ─────────────────────────────────────────────────────────────


def _forward_batch(
    model,
    batch: list,
    device: torch.device,
    num_pos_points: int = 3,
    neg_offset: int = 15,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Procesa un batch (lista de muestras) por MedSAM.
    image_encoder corre en batch; prompt_encoder y mask_decoder muestra a muestra
    para evitar el mismatch B² del diseño original de SAM.
    """
    img_size = model.image_encoder.img_size
    imgs_pre, gt_masks, boxes, pt_coords, pt_labels = [], [], [], [], []

    for sample in batch:
        img = sample["image"].to(device)
        mask = sample["mask"].to(device)
        box = sample["box"].to(device)

        imgs_pre.append(model.preprocess(img))
        h, w = mask.shape[-2:]
        padded = torch.zeros((1, img_size, img_size), device=device)
        padded[:, :h, :w] = mask
        gt_masks.append(padded)
        boxes.append(box)

        coords_np, labels_np = _get_points_from_mask(
            mask[0], num_pos=num_pos_points, neg_offset=neg_offset
        )
        if coords_np is None:
            coords_np = np.array([[w // 2, h // 2]], dtype=np.float32)
            labels_np = np.array([1], dtype=np.int64)
        pt_coords.append(torch.tensor(coords_np, device=device))
        pt_labels.append(torch.tensor(labels_np, device=device))

    imgs_pre = torch.stack(imgs_pre)
    gt_masks = torch.stack(gt_masks)
    image_embeddings = model.image_encoder(imgs_pre)

    pred_list, iou_list = [], []
    for i in range(len(batch)):
        with torch.no_grad():
            sparse_emb, dense_emb = model.prompt_encoder(
                points=(pt_coords[i].unsqueeze(0), pt_labels[i].unsqueeze(0)),
                boxes=boxes[i].unsqueeze(0),
                masks=None,
            )
        low_res_mask, iou_pred = model.mask_decoder(
            image_embeddings=image_embeddings[i : i + 1],
            image_pe=model.prompt_encoder.get_dense_pe(),
            sparse_prompt_embeddings=sparse_emb,
            dense_prompt_embeddings=dense_emb,
            multimask_output=False,
        )
        pred_list.append(low_res_mask)
        iou_list.append(iou_pred)

    pred_masks = F.interpolate(
        torch.cat(pred_list),
        size=(img_size, img_size),
        mode="bilinear",
        align_corners=False,
    )
    return pred_masks, gt_masks, torch.cat(iou_list)


# ─── Loops de entrenamiento ───────────────────────────────────────────────────


def _train_epoch(
    model,
    loader,
    optimizer: torch.optim.Optimizer,
    bce_fn: nn.Module,
    device: torch.device,
    num_pos_points: int,
    neg_offset: int,
    epoch_idx: int,
    total_epochs: int,
) -> tuple[float, float]:
    model.train()
    running_loss = running_dice = 0.0
    pbar = tqdm(loader, desc=f"Train {epoch_idx + 1}/{total_epochs}", leave=True)

    for i, batch in enumerate(pbar):
        optimizer.zero_grad()
        pred, gt, _ = _forward_batch(model, batch, device, num_pos_points, neg_offset)
        loss = bce_fn(pred, gt) + dice_loss(pred, gt)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        running_dice += dice_from_logits(pred.detach(), gt).item()
        pbar.set_postfix(
            loss=f"{running_loss / (i + 1):.4f}", dice=f"{running_dice / (i + 1):.4f}"
        )

    n = len(loader)
    return running_loss / n, running_dice / n


@torch.no_grad()
def _val_epoch(
    model,
    loader,
    bce_fn: nn.Module,
    device: torch.device,
    num_pos_points: int,
    neg_offset: int,
    epoch_idx: int,
    total_epochs: int,
) -> tuple[float, float]:
    model.eval()
    running_loss = running_dice = 0.0
    pbar = tqdm(loader, desc=f"Val   {epoch_idx + 1}/{total_epochs}", leave=True)

    for i, batch in enumerate(pbar):
        pred, gt, _ = _forward_batch(model, batch, device, num_pos_points, neg_offset)
        loss = bce_fn(pred, gt) + dice_loss(pred, gt)
        running_loss += loss.item()
        running_dice += dice_from_logits(pred, gt).item()
        pbar.set_postfix(
            loss=f"{running_loss / (i + 1):.4f}", dice=f"{running_dice / (i + 1):.4f}"
        )

    n = len(loader)
    return running_loss / n, running_dice / n


# ─── Evaluación en test ───────────────────────────────────────────────────────


@torch.no_grad()
def evaluate(
    model,
    loader,
    device: torch.device,
    num_pos_points: int = 3,
    neg_offset: int = 15,
) -> pd.DataFrame:
    """Evalúa el modelo sobre un loader y devuelve DataFrame con métricas por imagen."""
    model.eval()
    results = []
    for batch in tqdm(loader, desc="Evaluando", leave=True):
        pred_logits, gt_masks, _ = _forward_batch(
            model, batch, device, num_pos_points, neg_offset
        )
        probs = torch.sigmoid(pred_logits)
        preds = (probs > 0.5).float()

        for i, sample in enumerate(batch):
            pred = postprocess_mask(preds[i, 0].cpu().numpy().astype(np.uint8))
            gt = gt_masks[i, 0].cpu().numpy().astype(np.uint8)
            results.append(
                {
                    "id": sample["id"],
                    "dice": dice_np(pred, gt),
                    "iou": iou_np(pred, gt),
                    "precision": precision_np(pred, gt),
                    "recall": recall_np(pred, gt),
                }
            )
    return pd.DataFrame(results)


# ─── Punto de entrada principal ───────────────────────────────────────────────


def train(
    splits_csv: Path | str,
    checkpoint_path: Path | str,
    save_dir: Path | str,
    *,
    device: str = "cpu",
    num_epochs: int = 20,  # hardcodeado en notebook: num_epochs_final = 20
    batch_size: int = 2,  # hardcodeado en notebook: batch_size=2 en DataLoader
    num_workers: int = 0,
    box_pad: int = 10,
    num_pos_points: int = 3,
    neg_offset: int = 15,
    decoder_lr: float = 1e-4,
    encoder_lr: float = 1e-5,
    weight_decay: float = 1e-4,
    scheduler_patience: int = 3,
    early_stopping_patience: int = 5,
    min_delta: float = 0.001,
    checkpoint_name: str = "medsam_lastblock_unfrozen.pth",
    mlflow_run_name: str = "exp_final_lastblock_unfrozen",
    seed: int = 42,
    no_upload: bool = False,
    force_upload: bool = False,
) -> dict:
    """
    Fine-tuning de MedSAM con el último bloque del encoder descongelado.

    Args:
        splits_csv:       CSV con columnas [patient_id, tipo, split, ruta_img, ruta_mask_id]
        checkpoint_path:  ruta al .pth base de SAM ViT-B
        save_dir:         directorio donde guardar el mejor modelo y reportes
        device:           'cpu', 'cuda' o 'mps' (notebook: auto-detectado)
        num_epochs:       épocas máximas (notebook: 20 hardcodeado)
        batch_size:       muestras por batch (notebook: 2 hardcodeado en DataLoader)

    Returns:
        dict con history, best_val_dice, test_metrics y rutas de artefactos
    """
    from segment_anything import sam_model_registry

    from .pipeline.dataset import make_dataloaders

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    _device = torch.device(device)
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    best_path = save_dir / checkpoint_name

    # Cargar modelo
    model = sam_model_registry["vit_b"](checkpoint=str(checkpoint_path))
    model = model.to(_device).train()

    # Congelar todo excepto mask_decoder y último bloque del encoder
    for p in model.image_encoder.parameters():
        p.requires_grad = False
    for p in model.prompt_encoder.parameters():
        p.requires_grad = False
    for p in model.mask_decoder.parameters():
        p.requires_grad = True
    if hasattr(model.image_encoder, "blocks"):
        for p in model.image_encoder.blocks[-1].parameters():
            p.requires_grad = True

    # DataLoaders
    train_loader, val_loader, test_loader = make_dataloaders(
        splits_csv,
        model,
        batch_size=batch_size,
        num_workers=num_workers,
        box_pad=box_pad,
    )

    # Optimizer con dos LR (notebook: decoder=1e-4, encoder_last=1e-5)
    optimizer = torch.optim.AdamW(
        [
            {"params": list(model.mask_decoder.parameters()), "lr": decoder_lr},
            {
                "params": list(model.image_encoder.blocks[-1].parameters()),
                "lr": encoder_lr,
            },
        ],
        weight_decay=weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=scheduler_patience,
        threshold=1e-3,
        min_lr=1e-6,
    )
    bce_fn = nn.BCEWithLogitsLoss()

    history: dict[str, list] = {
        "train_loss": [],
        "train_dice": [],
        "val_loss": [],
        "val_dice": [],
        "lr_decoder": [],
        "lr_encoder": [],
    }
    best_val_dice = -1.0
    epochs_no_improve = 0

    # Inicializar para que el return sea seguro aunque ocurra una excepción
    test_metrics: dict = {}
    report_path = save_dir / "test_report.csv"
    summary_path = save_dir / "test_summary.json"

    with mlflow.start_run(run_name=mlflow_run_name):
        mlflow.log_params(
            {
                "model": "MedSAM-ViT-B",
                "estrategia": "lastblock_encoder_unfrozen",
                "num_epochs": num_epochs,
                "decoder_lr": decoder_lr,
                "encoder_lr": encoder_lr,
                "weight_decay": weight_decay,
                "batch_size": batch_size,
                "seed": seed,
                "early_stopping_patience": early_stopping_patience,
            }
        )

        for epoch in range(num_epochs):
            t0 = time.time()

            train_loss, train_dice = _train_epoch(
                model,
                train_loader,
                optimizer,
                bce_fn,
                _device,
                num_pos_points,
                neg_offset,
                epoch,
                num_epochs,
            )
            val_loss, val_dice = _val_epoch(
                model,
                val_loader,
                bce_fn,
                _device,
                num_pos_points,
                neg_offset,
                epoch,
                num_epochs,
            )
            scheduler.step(val_dice)

            lr_dec = optimizer.param_groups[0]["lr"]
            lr_enc = optimizer.param_groups[1]["lr"]
            elapsed = time.time() - t0

            history["train_loss"].append(train_loss)
            history["train_dice"].append(train_dice)
            history["val_loss"].append(val_loss)
            history["val_dice"].append(val_dice)
            history["lr_decoder"].append(lr_dec)
            history["lr_encoder"].append(lr_enc)

            mlflow.log_metrics(
                {
                    "train_loss": train_loss,
                    "train_dice": train_dice,
                    "val_loss": val_loss,
                    "val_dice": val_dice,
                    "lr_decoder": lr_dec,
                    "lr_encoder": lr_enc,
                },
                step=epoch,
            )

            print(
                f"[Epoch {epoch + 1:02d}/{num_epochs}] "
                f"train_loss={train_loss:.4f} train_dice={train_dice:.4f} | "
                f"val_loss={val_loss:.4f} val_dice={val_dice:.4f} | "
                f"lr_dec={lr_dec:.2e} lr_enc={lr_enc:.2e} | "
                f"{elapsed / 60:.2f} min"
            )

            if val_dice > best_val_dice + min_delta:
                best_val_dice = val_dice
                epochs_no_improve = 0
                torch.save(model.state_dict(), best_path)
                print(f"  -> Mejor modelo guardado: val_dice={best_val_dice:.4f}")
            else:
                epochs_no_improve += 1
                print(f"  -> Sin mejora por {epochs_no_improve} época(s)")

            if epochs_no_improve >= early_stopping_patience:
                print(
                    f"\nEarly stopping en época {epoch + 1}. "
                    f"Mejor Val Dice: {best_val_dice:.4f}"
                )
                break

        mlflow.log_metric("best_val_dice", best_val_dice)

        # ── Reporte en test con el mejor modelo ───────────────────────────────
        print("\nEvaluando en test con el mejor modelo...")
        model.load_state_dict(
            torch.load(best_path, map_location=_device, weights_only=True)
        )

        df_test = evaluate(model, test_loader, _device, num_pos_points, neg_offset)

        test_metrics = {
            "test_dice": float(df_test["dice"].mean()),
            "test_iou": float(df_test["iou"].mean()),
            "test_precision": float(df_test["precision"].mean()),
            "test_recall": float(df_test["recall"].mean()),
        }
        mlflow.log_metrics(test_metrics)

        print(
            f"  test_dice={test_metrics['test_dice']:.4f} "
            f"test_iou={test_metrics['test_iou']:.4f} "
            f"test_precision={test_metrics['test_precision']:.4f} "
            f"test_recall={test_metrics['test_recall']:.4f}"
        )

        df_test.to_csv(report_path, index=False)
        mlflow.log_artifact(str(report_path))

        summary = {
            "run_name": mlflow_run_name,
            "best_val_dice": best_val_dice,
            **test_metrics,
            "n_test_images": len(df_test),
        }
        summary_path.write_text(json.dumps(summary, indent=2))
        mlflow.log_artifact(str(summary_path))

        # ── Registro del modelo en Unity Catalog (mismo run) ──────────────────
        registration: dict = {}
        if no_upload:
            print("\n[--no-upload] Registro en Unity Catalog omitido.")
        else:
            try:
                from .upload_to_databricks import register_in_uc
                model.cpu()
                registration = register_in_uc(model, force=force_upload)
            except Exception as e:
                print(f"\n[AVISO] El registro en Unity Catalog falló: {e}")
                print("        Métricas y artefactos sí quedaron en el run MLflow.")

    return {
        "history": history,
        "best_val_dice": best_val_dice,
        "best_model_path": str(best_path),
        "test_metrics": test_metrics,
        "test_report_path": str(report_path),
        "registration": registration,
    }
