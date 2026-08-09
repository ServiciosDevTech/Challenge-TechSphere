from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import router
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

settings = get_settings()
settings.upload_path.mkdir(parents=True, exist_ok=True)
settings.chroma_path.mkdir(parents=True, exist_ok=True)
settings.calls_path.mkdir(parents=True, exist_ok=True)
settings.metrics_path.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="PostOp Care API",
    description="Agente de voz postoperatorio con RAG dinámico — Tech Sphere 2026",
    version=__version__,
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
