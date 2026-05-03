from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VertebraAI"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    model_checkpoint: str = "nvidia/mit-b2"
    model_local_path: str = ""
    model_device: str = "cpu"
    model_input_size: int = 512
    n_classes: int = 23

    max_upload_mb: int = 50
    inference_timeout_s: int = 60

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
