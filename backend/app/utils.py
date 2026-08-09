from __future__ import annotations

import re
import uuid
from typing import Iterable


def new_id(prefix: str = "") -> str:
    value = uuid.uuid4().hex[:12]
    return f"{prefix}{value}" if prefix else value


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def mask_pii(text: str) -> str:
    """Enmascara CC y patrones sensibles en logs exportables."""
    text = re.sub(r"\b\d{6,12}\b", "[CC_REDACTED]", text)
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL_REDACTED]",
        text,
    )
    return text


def extract_scenario_from_path(filename: str, parent_hint: str | None = None) -> str | None:
    if parent_hint:
        return parent_hint
    known = [
        "Appendicitis",
        "breast_cancer",
        "cholecystitis",
        "colorectal cancer",
        "total joint replacement",
    ]
    lower = filename.lower()
    for name in known:
        if name.lower() in lower:
            return name
    return None


def unique_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
