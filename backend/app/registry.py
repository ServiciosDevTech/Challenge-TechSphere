from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.models import DocumentInfo, DocumentStatus


class DocumentRegistry:
    """Registro persistente de documentos indexados (metadata fuera de Chroma)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({})

    def _read(self) -> dict[str, dict]:
        with self.path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write(self, data: dict[str, dict]) -> None:
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, default=str)

    def list(self) -> list[DocumentInfo]:
        with self._lock:
            data = self._read()
        docs = [DocumentInfo.model_validate(v) for v in data.values()]
        docs.sort(key=lambda d: d.created_at, reverse=True)
        for doc in docs:
            if doc.status == DocumentStatus.ready:
                doc.ready_label = "Procesado y disponible"
        return docs

    def get(self, document_id: str) -> DocumentInfo | None:
        with self._lock:
            data = self._read()
        raw = data.get(document_id)
        if not raw:
            return None
        doc = DocumentInfo.model_validate(raw)
        if doc.status == DocumentStatus.ready:
            doc.ready_label = "Procesado y disponible"
        return doc

    def upsert(self, doc: DocumentInfo) -> DocumentInfo:
        with self._lock:
            data = self._read()
            data[doc.id] = json.loads(doc.model_dump_json())
            self._write(data)
        return self.get(doc.id) or doc

    def delete(self, document_id: str) -> bool:
        with self._lock:
            data = self._read()
            if document_id not in data:
                return False
            del data[document_id]
            self._write(data)
            return True

    def count_ready(self) -> int:
        return sum(1 for d in self.list() if d.status == DocumentStatus.ready)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
