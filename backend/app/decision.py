from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import AgentDecision, Criticality, DecisionAction


ALARM_PATTERNS = [
    r"fiebre\s*(alta|mayor|muy\s*alta)",
    r"sangrado\s*(abundante|mucho|que no para)",
    # Secreción/pus (lenguaje cotidiano del dataset CO)
    r"pus|supuraci[oó]n|secreci[oó]n(\s*mal\s*oliente)?",
    r"l[ií]quido\s*(amarillo|amarillito|feo|raro)|sale\s+l[ií]quido|saliendo\s+(?:ah[ií]\s+)?de\s+la\s+herida",
    # Cubrir: "falta de aire", "faltando el aire", "me falta el aire", "sin aire"
    r"dificultad\s*(para\s*)?respirar|ahogo|ahog|falta(?:ndo)?\s+(?:el\s+)?aire|me\s+falta\s+(?:el\s+)?aire|sin\s+aire|no\s+puedo\s+respirar",
    r"dolor\s*(insoportable|de\s*1[0]|del\s*diez|muy\s*fuerte|que no aguanto)",
    r"herida\s*(abierta|se\s*abri[oó]|dehis)",
    r"v[oó]mito\s*(persistente|que no para|mucho)",
    r"desmayo|me\s*desmay|p[eé]rdida\s*de\s*conocimiento",
    r"hinchaz[oó]n\s*(muy\s*)?(grande|severa)|pantorrilla\s*(roja|caliente|hinchada)",
    r"pecho\s*(me\s*)?duele|dolor\s*en\s*el\s*pecho|duele\s+el\s+pecho|me\s+duele\s+el\s+pecho",
    # Deterioro funcional grave (artroplastia / postop)
    r"no\s+puedo\s+(?:ni\s+)?levantarme|casi\s+no\s+puedo\s+levant|necesito\s+(?:que\s+)?alguien\s+me\s+ayude\s+para\s+todo|incapacitad|no\s+responde",
]

WATCH_PATTERNS = [
    r"dolor\s*(de\s*)?[5-7]\b",
    r"(?:dolor|duele|nivel|escala).{0,24}\b([5-7]|cinco|seis|siete)\b",
    r"\b(lo\s+)?siento\s+(un\s+)?([5-7]|cinco|seis|siete)\b",
    r"\b([5-7]|cinco|seis|siete)\s*(/10|de\s*diez)\b",
    r"fiebre\s*(bajita|leve)|calentura|algo\s+de\s+fiebre|un\s+poco\s+de\s+fiebre|tengo\s+fiebre",
    r"n[aá]useas",
    r"herida\s*(un\s*poco\s*)?(roja|inflam)",
    r"no\s*(puedo|pude)\s*dormir",
    r"poco\s*apetito|no\s*tengo\s*hambre",
]

REASSURING_PATTERNS = [
    r"mejor(ando|e)|ya\s*estoy\s*mejor",
    r"dolor\s*(de\s*)?[0-3]\b|casi\s*nada|apenas",
    r"(?:dolor|duele|nivel).{0,24}\b([0-3]|cero|uno|dos|tres)\b",
    r"sin\s*fiebre|no\s*tengo\s*fiebre",
    r"herida\s*(bien|limpia|normal)",
    r"caminando|ya\s*camino",
]

# Temperatura en °C: 38, 38.5, 39, "38 y algo", "marcó 38.2"
_TEMP_TOKEN = r"(?P<temp>4\d(?:[.,]\d+)?|3[89](?:[.,]\d+)?)"
TEMPERATURE_PATTERNS = [
    re.compile(
        rf"(?:fiebre|temperatura|term[oó]metro|me\s+medi|me\s+med[ií]|marc[oó]|marcaba|afiebr|calentura|escalofr).{{0,56}}{_TEMP_TOKEN}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"{_TEMP_TOKEN}\s*(?:grados|°\s*c|celsius|cent[ií]grados|y\s*algo|algo)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:fiebre|temperatura)\s*(?:de|a|en|=|:)?\s*{_TEMP_TOKEN}",
        re.IGNORECASE,
    ),
]
# Contexto febril + número 38/39 suelto (dataset ruidoso / truncado)
_FEVER_CONTEXT = re.compile(
    r"fiebre|temperatura|term[oó]metro|afiebr|calentura|escalofr|sudad|acalor|marc[oó]|grados",
    re.IGNORECASE,
)
_BARE_TEMP = re.compile(r"\b(?P<temp>3[89](?:[.,]\d+)?)\b")

PAIN_SCORE_PATTERN = re.compile(
    r"(?:dolor|duele|nivel\s+de\s+dolor|escala|es\s+un|como\s+un).{0,24}?"
    r"\b(?P<num>10|[0-9]|cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b"
    r"|\b(?P<num2>10|[0-9]|cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
    r"\s*(?:/10|de\s*diez|sobre\s*10|sobre\s*diez)\b",
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

# Guías del corpus + trayectorias del reto: ≥38 °C ya es alarma postoperatoria frecuente
FEVER_ALARM_C = 38.0

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


def _parse_temp_token(token: str) -> float:
    return float(token.replace(",", "."))


def extract_temperature_c(text: str) -> float | None:
    """Extrae temperatura corporal en °C del mensaje actual (no del historial)."""
    lower = text.lower()
    found: list[float] = []
    for pattern in TEMPERATURE_PATTERNS:
        for match in pattern.finditer(lower):
            raw = match.group("temp")
            if raw:
                found.append(_parse_temp_token(raw))
    if _FEVER_CONTEXT.search(lower):
        for match in _BARE_TEMP.finditer(lower):
            found.append(_parse_temp_token(match.group("temp")))
    if not found:
        return None
    return max(found)


def history_asks_pain_scale(history_text: str) -> bool:
    lower = history_text.lower()
    return bool(
        re.search(
            r"(cero\s+al\s+diez|0\s+al\s+10|escala|nivel\s+de\s+dolor|"
            r"del\s+0\s+al\s+10|cu[aá]nto\s+te\s+duele|n[uú]mero)",
            lower,
        )
    )


def extract_pain_score(text: str, history_text: str = "") -> int | None:
    """
    Extrae NRS 0-10 del mensaje actual.
    Solo usa historial si el paciente responde corto a una pregunta de escala
    (evita arrastrar 'dolor 0' de saludos o llamadas anteriores).
    """
    lower = text.lower().strip()

    # No interpretar temperaturas (39 grados) como dolor
    if extract_temperature_c(text) is not None and not re.search(
        r"dolor|duele|/10|de\s*diez", lower
    ):
        return None

    match = PAIN_SCORE_PATTERN.search(lower)
    if match:
        token = match.group("num") or match.group("num2")
        if token:
            return int(token) if token.isdigit() else _WORD_TO_SCORE.get(token)

    # Respuesta corta tipo "un seis" / "6" solo si el agente preguntó la escala
    if history_asks_pain_scale(history_text):
        short = re.search(
            r"^\s*(?:lo\s+)?(?:siento\s+)?(?:un\s+)?(?P<n>10|[0-9]|cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s*\.?\s*$",
            lower,
        )
        if not short:
            short = re.search(
                r"\b(?:lo\s+)?siento\s+(?:un\s+)?(?P<n>10|[0-9]|cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b",
                lower,
            )
        if short:
            token = short.group("n")
            return int(token) if token.isdigit() else _WORD_TO_SCORE.get(token)

    return None


def collect_signals(text: str) -> DecisionSignals:
    lower = text.lower()
    alarms = [p for p in ALARM_PATTERNS if re.search(p, lower, re.IGNORECASE)]
    watches = [p for p in WATCH_PATTERNS if re.search(p, lower, re.IGNORECASE)]
    reassure = [p for p in REASSURING_PATTERNS if re.search(p, lower, re.IGNORECASE)]

    temp = extract_temperature_c(text)
    if temp is not None and temp >= FEVER_ALARM_C:
        alarms.append(f"temperatura>={FEVER_ALARM_C}:{temp}")
    elif temp is not None and 37.5 <= temp < FEVER_ALARM_C:
        watches.append(f"temperatura_subfebril:{temp}")

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
    temp = extract_temperature_c(patient_text)

    if temp is not None and temp >= FEVER_ALARM_C:
        return AgentDecision(
            criticality=Criticality.rojo,
            action=DecisionAction.escalate,
            rationale=(
                f"Fiebre/temperatura de alarma reportada ({temp} °C ≥ {FEVER_ALARM_C}). "
                "Se prioriza evaluación humana."
            ),
            escalate=True,
        )

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


def reply_matches_escalation_intent(reply: str) -> bool:
    lower = (reply or "").lower()
    return any(
        k in lower
        for k in ("médic", "medic", "urgenc", "escal", "profesional", "humano")
    )


def reply_ignores_current_alarm(patient_text: str, reply: str) -> bool:
    """True si el paciente reportó alarma y el reply habla de otra cosa (p. ej. dolor viejo)."""
    temp = extract_temperature_c(patient_text)
    lower_reply = (reply or "").lower()
    lower_msg = patient_text.lower()
    if temp is not None and temp >= FEVER_ALARM_C:
        if "fiebre" not in lower_reply and "temperatura" not in lower_reply:
            if re.search(r"dolor\s+de\s+[0-4]|dolor\s+de\s+0", lower_reply):
                return True
            if "escal" not in lower_reply and "médic" not in lower_reply:
                return True
    if re.search(r"falta(?:ndo)?\s+(?:el\s+)?aire|pecho|sangrado", lower_msg):
        if not reply_matches_escalation_intent(reply):
            return True
    return False
