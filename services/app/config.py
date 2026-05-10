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

    max_upload_mb: int = 50
    inference_timeout_s: int = 60

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
