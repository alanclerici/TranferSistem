from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    shared_root: Path = Path.home() / "CompartidoWeb"
    max_upload_size_mb: int = 512
    delete_enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LOCAL_CRT_",
        extra="ignore",
    )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.shared_root.mkdir(parents=True, exist_ok=True)
    return settings
