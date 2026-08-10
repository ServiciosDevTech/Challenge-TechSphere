#!/usr/bin/env python
"""Indexa guías postoperatorias prioritarias de los 5 escenarios del reto."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import DynamicRAG  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

# Planes de cuidado / instrucciones al paciente por escenario (máximo impacto clínico)
PRIORITY_GLOBS = [
    # Appendicitis
    "**/Appendicitis/**/PLAN DE CUIDADO EN CASA*.pdf",
    "**/Appendicitis/**/POST OPERATIVE INSTRUCTIONS*.pdf",
    "**/Appendicitis/**/Acute Care Surgery Comprehensive Recovery Guide*.pdf",
    "**/Appendicitis/**/Management of complications after appendectomy*.pdf",
    "**/Appendicitis/**/Establishing the need for clinical follow-up*.pdf",
    # Cholecystitis
    "**/cholecystitis/**/PLAN DE CUIDADO COLECISTECTO*.pdf",
    "**/cholecystitis/**/Postoperative care for patie*.pdf",
    "**/cholecystitis/**/GUIA COLECISTITIS AGUDA*.pdf",
    "**/cholecystitis/**/CUIDADO ESTANDARIZADO*.pdf",
    # Colorectal
    "**/colorectal cancer/**/Your Follow-up Care afte*.pdf",
    "**/colorectal cancer/**/Colon Cancer Surgery and*.pdf",
    "**/colorectal cancer/**/Protocolo de recuperaci*.pdf",
    "**/colorectal cancer/**/A Guide to Enhancing You*.pdf",
    # Joint replacement
    "**/total joint replacement/**/PLAN CASERO REEMPL*.pdf",
    "**/total joint replacement/**/Recomendaciones P*.pdf",
    "**/total joint replacement/**/Recom endaciones P*.pdf",
    "**/total joint replacement/**/Enhanced recovery*.pdf",
    "**/total joint replacement/**/Postoperative Pain*.pdf",
    # Breast / gyn oncology (material del corpus del reto)
    "**/breast_cancer/**/cervical-es-patient*.pdf",
    "**/breast_cancer/**/Documento.pdf",
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
    parser.add_argument("--limit", type=int, default=0, help="0 = todos los prioritarios")
    parser.add_argument(
        "--appendicitis-only",
        action="store_true",
        help="Solo globs de Appendicitis (semilla rápida)",
    )
    args = parser.parse_args()

    rag = DynamicRAG()
    paths: list[Path] = []

    if args.samples.exists():
        paths.extend(sorted(args.samples.glob("*.txt")))

    globs = PRIORITY_GLOBS
    if args.appendicitis_only:
        globs = [g for g in PRIORITY_GLOBS if "Appendicitis" in g]

    if args.source.exists():
        for pattern in globs:
            paths.extend(sorted(args.source.glob(pattern)))
    else:
        print(f"Corpus PDF no encontrado en {args.source}")
        print("Crea el junction/copia según data/README.md")

    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        key = str(p.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    if args.limit and args.limit > 0:
        unique = unique[: args.limit]

    ok = 0
    for path in unique:
        scenario = path.parent.name if path.parent.name != "samples" else "demo"
        try:
            doc = rag.ingest_file(path, filename=path.name, scenario=scenario)
            print(f"OK  {doc.id}  [{scenario}] {doc.filename}  chunks={doc.chunk_count}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {path.name}: {exc}")

    print(f"Indexed {ok}/{len(unique)}. Ready={rag.count_ready()}")


if __name__ == "__main__":
    main()
