from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VertebraAI"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    model_device: str = "cpu"
    model_input_size: int = 512

    # Pipeline ganador VertebraPrompt + BoxRefiner + MedSAM (notebook 06)
    medsam_prompt_net_checkpoint: str = "model-pkg/medsam/vertebraprompt_net_auxiliar_best.pt"
    medsam_box_refiner_checkpoint: str = "model-pkg/medsam/box_refiner_best.pt"
    medsam_sam_checkpoint: str = "model-pkg/medsam/medsam_vit_b.pth"
    medsam_finetuned_checkpoint: str = "model-pkg/medsam/medsam_decoder_encoder_parcial_entrenado_vertebraprompt_aux.pt"

    # Arquitectura VertebraPrompt-Net (alineados con notebook 06, celda 2)
    medsam_prompt_net_input: int = 512        # IMG_SIZE en el notebook
    medsam_img_size: int = 1024               # grilla MedSAM y dataset preprocesado
    medsam_base_channels: int = 32            # BASE_CH de la U-Net multi-tarea
    medsam_n_classes: int = 17                # T1..T12 + L1..L5

    # Decodificación anatómica (picos + DP)
    medsam_top_peaks: int = 90                # máximo de picos extraídos del heatmap
    medsam_min_peak_dist: int = 8             # supresión no máxima: distancia mínima entre picos
    medsam_thr_rel_peaks: float = 0.12        # umbral relativo al máximo del heatmap
    medsam_n_boxes_path: int = 17             # pasos de la DP (= n_classes)
    medsam_max_candidates: int = 120          # candidatos máximos enviados a la DP
    medsam_max_gap_rel_dy: float = 2.40       # multiplicador del gap esperado en DP
    medsam_y_min_anatomic_margin: float = 0.06  # margen superior para exclusión de cráneo
    medsam_skull_score_factor: float = 0.12   # penalización de score en zona de cráneo

    # Construcción de cajas desde wh-map (mezcla predicción + plantilla mediana)
    medsam_box_expand_w: float = 1.12         # expansión horizontal de la caja final
    medsam_box_expand_h: float = 1.12         # expansión vertical de la caja final
    medsam_wh_pred_blend: float = 0.65        # peso de la predicción del wh-map
    medsam_wh_template_blend: float = 0.35    # peso de la plantilla mediana
    medsam_wh_clip_w: list[float] = [0.03, 0.28]   # límites [min, max] de w_rel
    medsam_wh_clip_h: list[float] = [0.025, 0.18]  # límites [min, max] de h_rel

    # BoxRefiner
    medsam_box_refiner_size: int = 192              # resolución del crop de entrada al refinador
    medsam_box_refiner_blend: float = 0.80          # factor de mezcla al aplicar deltas
    medsam_box_refiner_max_abs_dxy: float = 0.45    # saturación tanh para desplazamientos (dx, dy)
    medsam_box_refiner_max_abs_log_scale: float = 0.45  # saturación tanh para escala log (dw, dh)
    medsam_box_refiner_context_frac: float = 0.85   # fracción de contexto extra en el crop

    # Contrato del servicio MedSAM
    medsam_n_service_classes: int = 23              # clases totales: bg + C1..C7 + T1..T12 + L1..L5

    # Unet++ con encoder efficientnet-b7 entrenado por parches
    # (notebooks/unet++/Unet++_patches.ipynb).
    unetpp_patches_checkpoint: str = "model-pkg/unet++_patches/unet++_patches.pth"
    unetpp_encoder_name: str = "efficientnet-b7"
    unetpp_in_channels: int = 3
    unetpp_num_model_classes: int = 18        # bg + T1..T12 + L1..L5
    unetpp_patch_size: int = 128              # resolución de entrada del modelo (entreno)
    unetpp_mean: list[float] = [0.485, 0.456, 0.406]   # ImageNet stats
    unetpp_std: list[float] = [0.229, 0.224, 0.225]    # ImageNet stats
    unetpp_clahe_clip: float = 2.0
    unetpp_clahe_tile: list[int] = [8, 8]
    unetpp_patch_area: float = 0.5            # hiperparámetro ganador (notebook celdas 30-32)
    unetpp_sigma: float = 50.0                # hiperparámetro ganador (notebook celdas 30-32)
    unetpp_stride_ratio: int = 4              # hiperparámetro ganador (notebook celdas 30-32)
    unetpp_n_service_classes: int = 23
    unetpp_first_vertebra_id: int = 6         # T1 en el contrato (ver vertebra.ID2LABEL)
    unetpp_last_vertebra_id: int = 22         # L5

    max_upload_mb: int = 50
    inference_timeout_s: int = 60

    cors_origins: list[str] = ["*"]

    # Rate limiting (slowapi). Default global aplica a todos los endpoints; el de
    # análisis es más estricto porque cada request consume CPU/RAM por ~30s.
    rate_limit_default: str = "120/minute"
    rate_limit_analyze: str = "5/minute"

    # Auth / Cognito
    auth_enabled: bool = True
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_region: str = "us-east-1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
