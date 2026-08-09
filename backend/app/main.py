from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import router
from app.config import get_settings
from app.rag import get_rag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
settings.upload_path.mkdir(parents=True, exist_ok=True)
settings.chroma_path.mkdir(parents=True, exist_ok=True)
settings.calls_path.mkdir(parents=True, exist_ok=True)
settings.metrics_path.mkdir(parents=True, exist_ok=True)


def _warmup_background() -> None:
    try:
        get_rag().warmup()
    except Exception:  # noqa: BLE001
        logger.exception("Warmup de embeddings falló")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    threading.Thread(target=_warmup_background, daemon=True, name="rag-warmup").start()
    yield


app = FastAPI(
    title="PostOp Care API",
    description="Agente de voz postoperatorio con RAG dinámico — Tech Sphere 2026",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {
        "name": "PostOp Care",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/health",
    }
