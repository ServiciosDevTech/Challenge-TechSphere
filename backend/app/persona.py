from __future__ import annotations

import random
import re
from typing import Any


def first_name(full_name: str | None) -> str:
    if not full_name or not full_name.strip():
        return "paciente"
    return full_name.strip().split()[0]


def build_greeting(
    *,
    agent_name: str,
    patient_name: str | None,
    procedure: str | None = None,
    prior_summary: str | None = None,
    dia_postop: int | None = None,
) -> str:
    """Saludo hablable con variación entre llamadas."""
    name = first_name(patient_name)
    proc = (procedure or "").strip()
    proc_bit = f" después de tu {proc.lower()}" if proc else " después de tu cirugía"
    day_bit = (
        f" Estamos en el día {int(dia_postop)} después de la cirugía."
        if dia_postop is not None
        else ""
    )

    if prior_summary:
        templates = [
            (
                f"Hola {name}, qué bueno escucharte de nuevo. Soy {agent_name}. "
                f"La última vez me contaste que {prior_summary}. "
                f"¿Cómo ha evolucionado desde entonces?"
            ),
            (
                f"Hola {name}, soy {agent_name} otra vez. "
                f"Recuerdo que {prior_summary}. "
                f"Cuéntame, ¿cómo te has sentido hoy?"
            ),
            (
                f"{name}, hola de nuevo. Soy {agent_name}. "
                f"La vez pasada mencionaste que {prior_summary}. "
                f"¿Notas algo diferente hoy?"
            ),
        ]
        return random.choice(templates)

    templates = [
        (
            f"Hola {name}, soy {agent_name}. Voy a acompañarte en esta llamada "
            f"para saber cómo te has sentido{proc_bit}.{day_bit} ¿Cómo estás hoy?"
        ),
        (
            f"Hola {name}, soy {agent_name}, tu asistente de recuperación. "
            f"Cuéntame, ¿cómo te has sentido{proc_bit}?{day_bit}"
        ),
        (
            f"Buenas, {name}. Habla {agent_name}. "
            f"Estoy aquí para revisar contigo cómo va tu recuperación.{day_bit} "
            f"¿Cómo te sientes en este momento?"
        ),
        (
            f"Hola {name}, soy {agent_name}. "
            f"Quiero saber cómo ha ido tu recuperación{proc_bit}.{day_bit} "
            f"¿Has notado algo que te preocupe?"
        ),
        (
            f"{name}, hola. Soy {agent_name}. "
            f"Esta llamada es para acompañarte en el seguimiento.{day_bit} "
            f"¿Cómo has estado desde la cirugía?"
        ),
    ]
    return random.choice(templates)


def summarize_prior_call(record: dict[str, Any]) -> str | None:
    """Resume la llamada anterior en una frase corta para el saludo."""
    state = record.get("call_state") or {}
    bits: list[str] = []

    pain = state.get("pain") or {}
    if isinstance(pain, dict):
        if pain.get("intensity") is not None:
            loc = pain.get("location")
            loc_bit = f" en {loc}" if loc else ""
            bits.append(f"tenías dolor{loc_bit} de {pain['intensity']} sobre 10")
        elif pain.get("location"):
            bits.append(f"tenías molestia en {pain['location']}")

    if state.get("fever") is True:
        bits.append("habías tenido fiebre")
    elif state.get("fever") is False and bits:
        bits.append("sin fiebre")

    if state.get("swelling"):
        bits.append("había algo de inflamación")

    symptoms = record.get("symptoms") or []
    if not bits and symptoms:
        snippet = str(symptoms[-1])[:90].strip()
        if snippet:
            bits.append(snippet.lower())

    if not bits:
        decisions = record.get("decisions") or []
        if decisions:
            crit = (decisions[-1] or {}).get("criticality")
            if crit == "amarillo":
                bits.append("había síntomas a vigilar")
            elif crit == "verde":
                bits.append("la evolución iba bien")

    if not bits:
        return None
    return "; ".join(bits[:2])


def update_call_state(
    state: dict[str, Any] | None,
    patient_text: str,
    *,
    llm_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Actualiza memoria estructurada de la llamada (heurística + parche LLM)."""
    from app.decision import extract_pain_score, extract_temperature_c

    out: dict[str, Any] = dict(state or {})
    pain = dict(out.get("pain") or {})
    lower = patient_text.lower()

    score = extract_pain_score(patient_text)
    if score is not None:
        pain["intensity"] = score

    loc_match = re.search(
        r"(lado\s+)?(derecho|izquierdo|derecha|izquierda)|abdomen|herida|ombligo|pecho",
        lower,
    )
    # No marcar ubicación de dolor si el turno es solo fiebre/temperatura
    if loc_match and (
        score is not None
        or re.search(r"dolor|duele|molest", lower)
    ):
        pain["location"] = loc_match.group(0)

    if re.search(r"mejor(ando|e)|baj[oó]|disminuy", lower):
        pain["trend"] = "mejorando"
    elif re.search(r"empeor|aument|subi[oó]|peor", lower):
        pain["trend"] = "aumentando"
    elif re.search(r"igual|estable|lo mismo", lower):
        pain["trend"] = "estable"

    if pain:
        out["pain"] = pain

    temp = extract_temperature_c(patient_text)
    if temp is not None:
        out["temperature_c"] = temp
        out["fever"] = temp >= 37.5
    elif re.search(r"sin\s+fiebre|no\s+tengo\s+fiebre|no\s+he\s+tenido\s+fiebre", lower):
        out["fever"] = False
    elif re.search(r"fiebre|calentura|temperatura", lower):
        out["fever"] = True

    if re.search(r"no\s+(hay|tengo)\s+sangrado|sin\s+sangrado", lower):
        out["bleeding"] = False
    elif re.search(r"sangrado|sangre", lower):
        out["bleeding"] = True

    if re.search(r"hinchaz|inflam", lower):
        out["swelling"] = True

    if llm_patch and isinstance(llm_patch, dict):
        for key, value in llm_patch.items():
            if value is None:
                continue
            if key == "pain" and isinstance(value, dict):
                merged = dict(out.get("pain") or {})
                merged.update({k: v for k, v in value.items() if v is not None})
                out["pain"] = merged
            else:
                out[key] = value

    return out


def format_call_state(state: dict[str, Any] | None) -> str:
    if not state:
        return "(sin datos aún en esta llamada)"
    return str(state)
