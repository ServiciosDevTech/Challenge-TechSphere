#!/usr/bin/env python
"""Seed sample clinical PDFs into the RAG store (optional)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import DynamicRAG  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Index PDF corpus into Chroma")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "textos",
        help="Folder with scenario subfolders of PDFs",
    )
    parser.add_argument("--limit", type=int, default=8, help="Max PDFs to index")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Source not found: {args.source}")
        print("Copy ParticipantArtifacts-main/dataset/textos into data/textos")
        sys.exit(1)

    rag = DynamicRAG()
    pdfs = sorted(args.source.rglob("*.pdf"))
    if args.limit:
        pdfs = pdfs[: args.limit]

    ok = 0
    for pdf in pdfs:
        scenario = pdf.parent.name
        try:
            doc = rag.ingest_file(pdf, filename=pdf.name, scenario=scenario)
            print(f"OK  {doc.id}  {doc.filename}  chunks={doc.chunk_count}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {pdf.name}: {exc}")

    print(f"Indexed {ok}/{len(pdfs)} documents. Ready={rag.count_ready()}")


if __name__ == "__main__":
    main()
