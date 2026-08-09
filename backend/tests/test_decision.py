from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.decision import decide_from_text, parse_criticality
from app.models import Criticality, DecisionAction
from app.utils import chunk_text, mask_pii


def test_chunk_text_overlaps():
    text = "palabra " * 200
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_mask_pii_redacts_cc_and_email():
    raw = "Mi cédula es 944082010 y mi correo paciente@mail.com"
    masked = mask_pii(raw)
    assert "944082010" not in masked
    assert "paciente@mail.com" not in masked
    assert "[CC_REDACTED]" in masked
    assert "[EMAIL_REDACTED]" in masked


def test_parse_criticality():
    assert parse_criticality("Rojo") == Criticality.rojo
    assert parse_criticality("green") == Criticality.verde
    assert parse_criticality(None) == Criticality.desconocido


def test_decision_escalates_on_alarm():
    decision = decide_from_text(
        "Me duele el pecho y tengo dificultad para respirar",
        has_rag_evidence=True,
    )
    assert decision.escalate is True
    assert decision.criticality == Criticality.rojo
    assert decision.action == DecisionAction.escalate


def test_decision_verde_on_reassuring():
    decision = decide_from_text(
        "El dolor es de 2, casi nada, y sin fiebre",
        llm_criticality=Criticality.verde,
        has_rag_evidence=True,
    )
    assert decision.escalate is False
    assert decision.criticality == Criticality.verde


def test_decision_insufficient_without_rag():
    decision = decide_from_text(
        "¿Puedo tomar algo para el dolor?",
        has_rag_evidence=False,
        llm_criticality=Criticality.desconocido,
    )
    assert decision.action == DecisionAction.insufficient_info
