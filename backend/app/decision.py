from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import AgentDecision, Criticality, DecisionAction


ALARM_PATTERNS = [
    r"fiebre\s*(alta|de\s*3[89]|de\s*4\d|mayor)",
    r"temperatura\s*(de\s*)?(3[89]|4\d)",
    r"sangrado\s*(abundante|mucho|que no para)",
    r"pus|supuraci[oó]n|secreci[oó]n\s*mal\s*oliente",
    r"dificultad\s*(para\s*)?respirar|ahogo|falta\s*de\s*aire",
    r"dolor\s*(insoportable|de\s*1[0]|del\s*diez|muy\s*fuerte|que no aguanto)",
    r"herida\s*(abierta|se\s*abri[oó]|dehis)",
    r"v[oó]mito\s*(persistente|que no para|mucho)",
    r"desmayo|me\s*desmay|p[eé]rdida\s*de\s*conocimiento",
    r"hinchaz[oó]n\s*(muy\s*)?(grande|severa)|pantorrilla\s*(roja|caliente|hinchada)",
    r"pecho\s*(me\s*)?duele|dolor\s*en\s*el\s*pecho",
]

WATCH_PATTERNS = [
    r"dolor\s*(de\s*)?[5-7]\b",
    r"fiebre\s*(bajita|leve)|calentura",
    r"n[aá]useas",
    r"herida\s*(un\s*poco\s*)?(roja|inflam)",
    r"no\s*(puedo|pude)\s*dormir",
    r"poco\s*apetito|no\s*tengo\s*hambre",
]

REASSURING_PATTERNS = [
    r"mejor(ando|e)|ya\s*estoy\s*mejor",
    r"dolor\s*(de\s*)?[0-3]\b|casi\s*nada|apenas",
    r"sin\s*fiebre|no\s*tengo\s*fiebre",
    r"herida\s*(bien|limpia|normal)",
    r"caminando|ya\s*camino",
]


@dataclass
class DecisionSignals:
    alarm_hits: list[str]
    watch_hits: list[str]
    reassure_hits: list[str]


def collect_signals(text: str) -> DecisionSignals:
    lower = text.lower()
    alarms = [p for p in ALARM_PATTERNS if re.search(p, lower, re.IGNORECASE)]
    watches = [p for p in WATCH_PATTERNS if re.search(p, lower, re.IGNORECASE)]
    reassure = [p for p in REASSURING_PATTERNS if re.search(p, lower, re.IGNORECASE)]
    return DecisionSignals(alarms, watches, reassure)


def decide_from_text(
    patient_text: str,
    *,
    llm_criticality: Criticality | None = None,
    has_rag_evidence: bool = True,
    llm_wants_escalate: bool | None = None,
) -> AgentDecision:
    """
    Motor de decisión con asimetría clínica: prioriza no perder alertas (rojo).

    Combina señales heurísticas del relato del paciente con la salida del LLM.
    """
    signals = collect_signals(patient_text)

    if signals.alarm_hits or llm_criticality == Criticality.rojo or llm_wants_escalate:
        return AgentDecision(
            criticality=Criticality.rojo,
            action=DecisionAction.escalate,
            rationale=(
                "Se detectaron signos de alarma o el modelo recomendó escalar. "
                "Se prioriza evaluación humana."
            ),
            escalate=True,
        )

    if not has_rag_evidence and llm_criticality in (
        Criticality.desconocido,
        Criticality.amarillo,
        None,
    ):
        return AgentDecision(
            criticality=Criticality.desconocido,
            action=DecisionAction.insufficient_info,
            rationale=(
                "No hay evidencia suficiente en la base de conocimiento para "
                "responder con seguridad clínica."
            ),
            escalate=False,
        )

    if signals.watch_hits or llm_criticality == Criticality.amarillo:
        return AgentDecision(
            criticality=Criticality.amarillo,
            action=DecisionAction.continue_care,
            rationale=(
                "Hay síntomas que ameritan vigilancia estrecha y seguimiento "
                "de las recomendaciones existentes."
            ),
            escalate=False,
        )

    if llm_criticality == Criticality.verde or signals.reassure_hits:
        return AgentDecision(
            criticality=Criticality.verde,
            action=DecisionAction.continue_care,
            rationale="El relato es compatible con una evolución postoperatoria esperada.",
            escalate=False,
        )

    if llm_criticality == Criticality.desconocido or not has_rag_evidence:
        return AgentDecision(
            criticality=Criticality.desconocido,
            action=DecisionAction.insufficient_info,
            rationale="Información insuficiente; se debe indagar más o escalar si persiste la duda.",
            escalate=False,
        )

    return AgentDecision(
        criticality=llm_criticality or Criticality.amarillo,
        action=DecisionAction.continue_care,
        rationale="Evolución a vigilar; se mantienen recomendaciones y seguimiento.",
        escalate=False,
    )


def parse_criticality(value: str | None) -> Criticality:
    if not value:
        return Criticality.desconocido
    normalized = value.strip().lower()
    mapping = {
        "verde": Criticality.verde,
        "green": Criticality.verde,
        "amarillo": Criticality.amarillo,
        "yellow": Criticality.amarillo,
        "rojo": Criticality.rojo,
        "red": Criticality.rojo,
        "desconocido": Criticality.desconocido,
        "unknown": Criticality.desconocido,
    }
    return mapping.get(normalized, Criticality.desconocido)
