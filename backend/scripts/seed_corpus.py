#!/usr/bin/env python
"""Indexa guías postoperatorias prioritarias (apendicectomía + samples)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import DynamicRAG  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

PRIORITY_GLOBS = [
    "**/PLAN DE CUIDADO EN CASA*.pdf",
    "**/POST OPERATIVE INSTRUCTIONS*.pdf",
    "**/Acute Care Surgery Comprehensive Recovery Guide*.pdf",
    "**/Management of complications after appendectomy*.pdf",
    "**/Establishing the need for clinical follow-up*.pdf",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed clinical corpus into Chroma")
    parser.add_argument(
        "--source",
        type=Path,
        default=REPO / "data" / "textos",
        help="Carpeta textos/ del dataset",
    )
    parser.add_argument(
        "--samples",
        type=Path,
        default=REPO / "data" / "samples",
        help="TXT de muestra versionados en el repo",
    )
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--all-priority", action="store_true")
    args = parser.parse_args()

    rag = DynamicRAG()
    paths: list[Path] = []

    if args.samples.exists():
        paths.extend(sorted(args.samples.glob("*.txt")))

    if args.source.exists():
        for pattern in PRIORITY_GLOBS:
            paths.extend(sorted(args.source.glob(pattern)))
    else:
        print(f"Corpus PDF no encontrado en {args.source}")
        print("Crea el junction/copia según data/README.md")

    # dedupe
    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        key = p.name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    if not args.all_priority:
        unique = unique[: args.limit]

    ok = 0
    for path in unique:
        scenario = path.parent.name if path.parent.name != "samples" else "demo"
        try:
            doc = rag.ingest_file(path, filename=path.name, scenario=scenario)
            print(f"OK  {doc.id}  {doc.filename}  chunks={doc.chunk_count}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {path.name}: {exc}")

    print(f"Indexed {ok}/{len(unique)}. Ready={rag.count_ready()}")


if __name__ == "__main__":
    main()
