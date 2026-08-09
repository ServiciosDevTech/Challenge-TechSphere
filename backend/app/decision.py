from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import AgentDecision, Criticality, DecisionAction


ALARM_PATTERNS = [
    r"fiebre\s*(alta|de\s*3[89]|de\s*4\d|mayor)",
    r"temperatura\s*(de\s*)?(3[89]|4\d)",
    r"sangrado\s*(abundante|mucho|que no para)",
    r"pus|supuraci[oó]n|secreci[oó]n\s*mal\s*oliente",
    # Cubrir: "falta de aire", "faltando el aire", "me falta el aire", "sin aire"
    r"dificultad\s*(para\s*)?respirar|ahogo|ahog|falta(?:ndo)?\s+(?:el\s+)?aire|me\s+falta\s+(?:el\s+)?aire|sin\s+aire|no\s+puedo\s+respirar",
    r"dolor\s*(insoportable|de\s*1[0]|del\s*diez|muy\s*fuerte|que no aguanto)",
    r"herida\s*(abierta|se\s*abri[oó]|dehis)",
    r"v[oó]mito\s*(persistente|que no para|mucho)",
    r"desmayo|me\s*desmay|p[eé]rdida\s*de\s*conocimiento",
    r"hinchaz[oó]n\s*(muy\s*)?(grande|severa)|pantorrilla\s*(roja|caliente|hinchada)",
    r"pecho\s*(me\s*)?duele|dolor\s*en\s*el\s*pecho",
]

WATCH_PATTERNS = [
    r"dolor\s*(de\s*)?[5-7]\b",
    r"(?:dolor|duele|siento|nivel|escala).{0,24}\b([5-7]|cinco|seis|siete)\b",
    r"\b(lo\s+)?siento\s+(un\s+)?([5-7]|cinco|seis|siete)\b",
    r"\b([5-7]|cinco|seis|siete)\s*(/10|de\s*diez)?\b",
    r"fiebre\s*(bajita|leve)|calentura",
    r"n[aá]useas",
    r"herida\s*(un\s*poco\s*)?(roja|inflam)",
    r"no\s*(puedo|pude)\s*dormir",
    r"poco\s*apetito|no\s*tengo\s*hambre",
]

REASSURING_PATTERNS = [
    r"mejor(ando|e)|ya\s*estoy\s*mejor",
    r"dolor\s*(de\s*)?[0-3]\b|casi\s*nada|apenas",
    r"(?:dolor|duele|siento|nivel).{0,24}\b([0-3]|cero|uno|dos|tres)\b",
    r"sin\s*fiebre|no\s*tengo\s*fiebre",
    r"herida\s*(bien|limpia|normal)",
    r"caminando|ya\s*camino",
]

PAIN_SCORE_PATTERN = re.compile(
    r"(?:dolor|duele|siento|nivel|escala|es\s+un|como\s+un).{0,24}?"
    r"\b(?P<num>10|[0-9]|cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b"
    r"|\b(?P<num2>10|[0-9]|cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
    r"\s*(?:/10|de\s*diez)\b",
    re.IGNORECASE,
)

_WORD_TO_SCORE = {
    "cero": 0,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
}


def extract_pain_score(text: str, history_text: str = "") -> int | None:
    """Extrae NRS 0-10 del mensaje o del contexto reciente de dolor."""
    combined = f"{history_text}\n{text}".lower()
    # Preferir el mensaje actual
    for candidate in (text, combined):
        match = PAIN_SCORE_PATTERN.search(candidate.lower())
        if not match:
            # Respuesta corta tipo "un seis" / "6"
            short = re.search(
                r"\b(un\s+)?(?P<n>10|[0-9]|cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b",
                candidate.lower(),
            )
            if short and (
                "dolor" in combined
                or "herida" in combined
                or "escala" in combined
                or "cero al diez" in combined
                or "0 al 10" in combined
            ):
                token = short.group("n")
                return int(token) if token.isdigit() else _WORD_TO_SCORE.get(token)
            continue
        token = match.group("num") or match.group("num2")
        if not token:
            continue
        return int(token) if token.isdigit() else _WORD_TO_SCORE.get(token)
    return None

ESCALATE_REQUEST_PATTERNS = [
    r"esc[aá]l(?:a|alo|arlo|e|arlo|eme|amelo|ámelo)",
    r"esc[aá]melo|escamelo",
    r"pasa(?:me)?\s+(?:con\s+)?(?:un\s+)?humano",
    r"quiero\s+(?:hablar\s+con\s+)?(?:un\s+)?(?:m[eé]dico|humano|enfermer)",
    r"necesito\s+(?:un\s+)?(?:m[eé]dico|humano)",
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


def user_requests_escalation(text: str, history_text: str = "") -> bool:
    """Detecta pedido explícito de escalar (incl. 'sí, escálalo' tras oferta previa)."""
    lower = text.lower().strip()
    if any(re.search(p, lower, re.IGNORECASE) for p in ESCALATE_REQUEST_PATTERNS):
        return True

    offered = bool(
        re.search(
            r"escale|escalar|humano|personal m[eé]dic",
            history_text.lower(),
            re.IGNORECASE,
        )
    )
    affirmative = bool(
        re.search(
            r"^(s[ií]|sip|dale|ok|okay|porfa|por favor|claro|hagamos?lo)\b",
            lower,
            re.IGNORECASE,
        )
    )
    return offered and affirmative


def decide_from_text(
    patient_text: str,
    *,
    llm_criticality: Criticality | None = None,
    has_rag_evidence: bool = True,
    llm_wants_escalate: bool | None = None,
    history_text: str = "",
) -> AgentDecision:
    """
    Motor de decisión con asimetría clínica: prioriza no perder alertas (rojo).

    Combina señales heurísticas del relato del paciente con la salida del LLM.
    """
    signals = collect_signals(patient_text)
    wants_escalate = user_requests_escalation(patient_text, history_text)
    pain = extract_pain_score(patient_text, history_text)

    if pain is not None and pain >= 8:
        return AgentDecision(
            criticality=Criticality.rojo,
            action=DecisionAction.escalate,
            rationale=f"Dolor intenso reportado (NRS={pain}). Se prioriza evaluación humana.",
            escalate=True,
        )

    if (
        signals.alarm_hits
        or llm_criticality == Criticality.rojo
        or llm_wants_escalate
        or wants_escalate
    ):
        return AgentDecision(
            criticality=Criticality.rojo,
            action=DecisionAction.escalate,
            rationale=(
                "Se detectaron signos de alarma, el paciente pidió escalar, "
                "o el modelo recomendó escalar. Se prioriza evaluación humana."
            ),
            escalate=True,
        )

    if pain is not None and 5 <= pain <= 7:
        return AgentDecision(
            criticality=Criticality.amarillo,
            action=DecisionAction.continue_care,
            rationale=(
                f"Dolor moderado (NRS={pain}): vigilancia estrecha, indagar alarma "
                "y mantener cuidados en casa si no hay otros signos."
            ),
            escalate=False,
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
