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

    # Experimento B del notebook unet (Progressive U-Net binaria estilo paper).
    progressive_unet_checkpoint: str = "model-pkg/exp_b_progressive_unet_binary_paper_like_logged_model/model.pth"

    max_upload_mb: int = 50
    inference_timeout_s: int = 60

    cors_origins: list[str] = ["*"]

    # Rate limiting (slowapi). Default global aplica a todos los endpoints; el de
    # análisis es más estricto porque cada request consume CPU/RAM por ~30s.
    rate_limit_default: str = "120/minute"
    rate_limit_analyze: str = "5/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
