from __future__ import annotations

import logging
import threading
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.config import Settings, get_settings
from app.models import Citation, DocumentInfo, DocumentStatus, RagHit
from app.registry import DocumentRegistry, utcnow
from app.utils import chunk_text, extract_scenario_from_path, new_id

logger = logging.getLogger(__name__)

COLLECTION_NAME = "clinical_knowledge"


class EmbeddingModel:
    """Lazy singleton for sentence-transformers."""

    _lock = threading.Lock()
    _model: SentenceTransformer | None = None
    _name: str | None = None

    @classmethod
    def get(cls, model_name: str) -> SentenceTransformer:
        with cls._lock:
            if cls._model is None or cls._name != model_name:
                logger.info("Loading embedding model: %s", model_name)
                cls._model = SentenceTransformer(model_name)
                cls._name = model_name
            return cls._model


class DynamicRAG:
    """RAG con alta/baja en caliente y citas por documento."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self.settings.upload_path.mkdir(parents=True, exist_ok=True)

        self.registry = DocumentRegistry(self.settings.chroma_path / "documents.json")
        self._client = chromadb.PersistentClient(
            path=str(self.settings.chroma_path / "store"),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._embed_lock = threading.Lock()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        model = EmbeddingModel.get(self.settings.embedding_model)
        with self._embed_lock:
            vectors = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def list_documents(self) -> list[DocumentInfo]:
        return self.registry.list()

    def get_document(self, document_id: str) -> DocumentInfo | None:
        return self.registry.get(document_id)

    def extract_pdf_text(self, path: Path) -> list[tuple[int, str]]:
        reader = PdfReader(str(path))
        pages: list[tuple[int, str]] = []
        for idx, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                text = ""
            pages.append((idx, text))
        return pages

    def _index_chunks(
        self,
        *,
        doc_id: str,
        name: str,
        scenario_name: str | None,
        pages: list[tuple[int, str]],
        doc: DocumentInfo,
    ) -> DocumentInfo:
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for page_num, page_text in pages:
            for i, chunk in enumerate(
                chunk_text(
                    page_text,
                    self.settings.chunk_size,
                    self.settings.chunk_overlap,
                )
            ):
                ids.append(f"{doc_id}_p{page_num}_{i}")
                documents.append(chunk)
                metadatas.append(
                    {
                        "document_id": doc_id,
                        "filename": name,
                        "scenario": scenario_name or "",
                        "page": page_num,
                        "chunk_index": i,
                    }
                )

        if not documents:
            raise ValueError(
                "No se pudo extraer texto del PDF (posible escaneo sin OCR)."
            )

        embeddings = self._embed(documents)
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        doc.status = DocumentStatus.ready
        doc.chunk_count = len(documents)
        doc.error_message = None
        self.registry.upsert(doc)
        logger.info("Ingested %s (%s chunks)", name, doc.chunk_count)
        return self.registry.get(doc_id) or doc

    def ingest_text(
        self,
        text: str,
        *,
        filename: str,
        scenario: str | None = None,
        document_id: str | None = None,
    ) -> DocumentInfo:
        doc_id = document_id or new_id("doc_")
        scenario_name = extract_scenario_from_path(filename, scenario)
        dest = self.settings.upload_path / f"{doc_id}_{filename}"
        dest.write_text(text, encoding="utf-8")

        doc = DocumentInfo(
            id=doc_id,
            filename=filename,
            scenario=scenario_name,
            status=DocumentStatus.processing,
            chunk_count=0,
            created_at=utcnow(),
        )
        self.registry.upsert(doc)
        try:
            return self._index_chunks(
                doc_id=doc_id,
                name=filename,
                scenario_name=scenario_name,
                pages=[(1, text)],
                doc=doc,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingest failed for %s", filename)
            doc.status = DocumentStatus.error
            doc.error_message = str(exc)
            self.registry.upsert(doc)
            raise

    def ingest_file(
        self,
        source_path: Path,
        *,
        filename: str | None = None,
        scenario: str | None = None,
        document_id: str | None = None,
    ) -> DocumentInfo:
        doc_id = document_id or new_id("doc_")
        name = filename or source_path.name
        scenario_name = extract_scenario_from_path(name, scenario)

        dest = self.settings.upload_path / f"{doc_id}_{name}"
        if source_path.resolve() != dest.resolve():
            dest.write_bytes(source_path.read_bytes())

        doc = DocumentInfo(
            id=doc_id,
            filename=name,
            scenario=scenario_name,
            status=DocumentStatus.processing,
            chunk_count=0,
            created_at=utcnow(),
        )
        self.registry.upsert(doc)

        try:
            if name.lower().endswith(".txt"):
                pages = [(1, dest.read_text(encoding="utf-8", errors="ignore"))]
            else:
                pages = self.extract_pdf_text(dest)
            return self._index_chunks(
                doc_id=doc_id,
                name=name,
                scenario_name=scenario_name,
                pages=pages,
                doc=doc,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingest failed for %s", name)
            doc.status = DocumentStatus.error
            doc.error_message = str(exc)
            self.registry.upsert(doc)
            raise

    def delete_document(self, document_id: str) -> bool:
        existing = self.registry.get(document_id)
        if not existing:
            return False

        try:
            self._collection.delete(where={"document_id": document_id})
        except Exception:  # noqa: BLE001
            logger.exception("Chroma delete failed for %s", document_id)

        for path in self.settings.upload_path.glob(f"{document_id}_*"):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove upload %s", path)

        return self.registry.delete(document_id)

    def query(self, query: str, top_k: int | None = None) -> list[RagHit]:
        k = top_k or self.settings.rag_top_k
        if self._collection.count() == 0:
            return []

        embeddings = self._embed([query])
        result = self._collection.query(
            query_embeddings=embeddings,
            n_results=min(k, max(1, self._collection.count())),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[RagHit] = []
        docs = result.get("documents") or [[]]
        metas = result.get("metadatas") or [[]]
        dists = result.get("distances") or [[]]
        min_score = self.settings.rag_min_score

        for text, meta, dist in zip(docs[0], metas[0], dists[0], strict=False):
            score = 1.0 - float(dist) if dist is not None else None
            # Con un solo documento indexado no filtramos por score (demo G5).
            if (
                self._collection.count() > 1
                and score is not None
                and score < min_score
            ):
                continue
            citation = Citation(
                document_id=str(meta.get("document_id", "")),
                filename=str(meta.get("filename", "")),
                page=int(meta["page"]) if meta.get("page") not in (None, "") else None,
                excerpt=(text[:280] + "…") if len(text) > 280 else text,
                score=score,
            )
            hits.append(RagHit(text=text, citation=citation))
        return hits

    def warmup(self) -> None:
        """Precarga el modelo de embeddings para evitar cold start en la 1.ª llamada."""
        self._embed(["warmup postoperatorio dolor fiebre"])
        logger.info("RAG embeddings warmed up")

    def count_ready(self) -> int:
        return self.registry.count_ready()


_rag: DynamicRAG | None = None
_rag_lock = threading.Lock()


def get_rag() -> DynamicRAG:
    global _rag
    with _rag_lock:
        if _rag is None:
            _rag = DynamicRAG()
        return _rag
