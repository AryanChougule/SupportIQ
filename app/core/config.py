from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SupportIQ"
    environment: str = "development"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    data_path: str = "data/support_tickets.csv"
    duckdb_path: str = "data/supportiq.duckdb"
    anomaly_iqr_multiplier: float = 1.5
    unresolved_age_hours: float = 24.0
    max_result_rows: int = 100
    enable_gemini: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def absolute_data_path(self) -> Path:
        path = Path(self.data_path)
        return path if path.is_absolute() else self.project_root / path

    def absolute_duckdb_path(self) -> Path:
        path = Path(self.duckdb_path)
        return path if path.is_absolute() else self.project_root / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
