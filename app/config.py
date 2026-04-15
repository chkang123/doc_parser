from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "doc_parser"
    app_env: str = "development"
    max_file_size_mb: int = 100
    marker_timeout_seconds: int = 1800
    soffice_timeout_seconds: int = 300
    worker_concurrency: int = 1
    data_dir: Path = Path("data")
    database_path: Path | None = None
    allowed_extensions: tuple[str, ...] = (
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
    )

    model_config = SettingsConfigDict(
        env_prefix="DOC_PARSER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def _normalize_data_dir(cls, value: str | Path) -> Path:
        return Path(value).resolve()

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def db_path(self) -> Path:
        if self.database_path is not None:
            return Path(self.database_path).resolve()
        return self.data_dir / "jobs.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
