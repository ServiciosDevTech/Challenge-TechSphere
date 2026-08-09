from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.rag import DynamicRAG


@pytest.fixture()
def rag(tmp_path: Path) -> DynamicRAG:
    settings = Settings(
        chroma_dir=str(tmp_path / "chroma"),
        upload_dir=str(tmp_path / "uploads"),
        calls_dir=str(tmp_path / "calls"),
        metrics_dir=str(tmp_path / "metrics"),
        google_api_key="",
    )
    return DynamicRAG(settings=settings)


def test_hot_add_and_delete(rag: DynamicRAG):
    text = (
        "Signos de alarma postoperatorios: fiebre mayor de 38.5 y sangrado "
        "abundante requieren evaluacion medica inmediata. El paciente debe "
        "contactar urgencias si presenta dificultad para respirar."
    )
    doc = rag.ingest_text(
        text,
        filename="manual_fiebre_postop.txt",
        scenario="Appendicitis",
    )
    assert doc.status.value == "ready"
    assert doc.chunk_count >= 1
    assert any(d.id == doc.id for d in rag.list_documents())

    hits = rag.query("fiebre sangrado alarma postoperatoria")
    assert hits, "Debe recuperar el manual recién cargado"
    assert hits[0].citation.document_id == doc.id
    assert hits[0].citation.filename == "manual_fiebre_postop.txt"

    assert rag.delete_document(doc.id) is True
    assert rag.get_document(doc.id) is None
    hits_after = rag.query("fiebre sangrado alarma postoperatoria")
    assert all(h.citation.document_id != doc.id for h in hits_after)
