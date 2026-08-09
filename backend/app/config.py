from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    chroma_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    calls_dir: str = "./data/calls"
    metrics_dir: str = "./data/metrics"

    rag_top_k: int = 5
    chunk_size: int = 800
    chunk_overlap: int = 120
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    tts_voice: str = "es-CO-SalomeNeural"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolve_path(self, relative: str) -> Path:
        path = Path(relative)
        if path.is_absolute():
            return path
        return (BACKEND_ROOT / path).resolve()

    @property
    def chroma_path(self) -> Path:
        return self.resolve_path(self.chroma_dir)

    @property
    def upload_path(self) -> Path:
        return self.resolve_path(self.upload_dir)

    @property
    def calls_path(self) -> Path:
        return self.resolve_path(self.calls_dir)

    @property
    def metrics_path(self) -> Path:
        return self.resolve_path(self.metrics_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
