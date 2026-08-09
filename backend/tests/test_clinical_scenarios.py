from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent import ClinicalAgent
from app.decision import (
    decide_from_text,
    extract_pain_score,
    extract_temperature_c,
    reply_ignores_current_alarm,
)
from app.models import ChatMessage, Criticality, DecisionAction


# ---------------------------------------------------------------------------
# Casos clínicos esperados (checklist de prueba manual → automatizado)
# ---------------------------------------------------------------------------

ROJO_CASES = [
    (
        "rojo_fiebre_39_grados",
        "hola beto hoy me siento un poco mal tengo algo de fiebre me medi con el termómetro y tengo 39 grados",
    ),
    ("rojo_fiebre_38_5", "Tengo fiebre de 38.5"),
    ("rojo_temperatura_39", "La temperatura está en 39"),
    ("rojo_faltando_aire", "Me está faltando el aire"),
    ("rojo_falta_el_aire", "Me falta el aire y me siento mal"),
    ("rojo_dolor_pecho", "Me duele el pecho"),
    ("rojo_sangrado", "Tengo sangrado abundante que no para"),
    ("rojo_pus", "La herida tiene pus y mal olor"),
    ("rojo_dolor_9", "El dolor es un nueve"),
    ("rojo_dolor_10", "Duele 10 de diez"),
    ("rojo_desmayo", "Casi me desmayo esta mañana"),
    ("rojo_escalar", "Escálalo con un médico"),
    ("rojo_quiero_medico", "Quiero hablar con un médico"),
]

AMARILLO_CASES = [
    ("amarillo_dolor_6", "El dolor es un seis"),
    ("amarillo_dolor_5", "Me duele como un 5"),
    ("amarillo_nauseas", "Tengo un poco de náuseas"),
    ("amarillo_fiebre_leve_sin_numero", "Tengo algo de fiebre"),
    ("amarillo_no_dormir", "No pude dormir bien anoche"),
]

VERDE_CASES = [
    ("verde_dolor_2", "El dolor es de 2, casi nada, y sin fiebre"),
    ("verde_mejorando", "Ya estoy mejorando y la herida está limpia"),
    ("verde_caminando", "Ya estoy caminando y me siento bien"),
]


@pytest.mark.parametrize("case_id,text", ROJO_CASES)
def test_scenarios_rojo_escalan(case_id: str, text: str):
    decision = decide_from_text(text, has_rag_evidence=True)
    assert decision.escalate is True, case_id
    assert decision.criticality == Criticality.rojo, case_id
    assert decision.action == DecisionAction.escalate, case_id


@pytest.mark.parametrize("case_id,text", AMARILLO_CASES)
def test_scenarios_amarillo_no_escalan(case_id: str, text: str):
    decision = decide_from_text(text, has_rag_evidence=True)
    assert decision.escalate is False, case_id
    assert decision.criticality == Criticality.amarillo, case_id


@pytest.mark.parametrize("case_id,text", VERDE_CASES)
def test_scenarios_verde(case_id: str, text: str):
    decision = decide_from_text(
        text,
        has_rag_evidence=True,
        llm_criticality=Criticality.verde,
    )
    assert decision.escalate is False, case_id
    assert decision.criticality == Criticality.verde, case_id


def test_fiebre_39_no_arrastrar_dolor_de_historial():
    """Regresión del bug de la demo: saludo con dolor 0 + fiebre 39."""
    history = (
        "agent: Hola Sebastian, soy Beto otra vez. Recuerdo que tenías dolor en herida "
        "de 0 sobre 10. Cuéntame, ¿cómo te has sentido hoy?"
    )
    msg = (
        "hola beto hoy me siento un poco mal tengo algo de fiebre me medi con el "
        "termómetro y tengo 39 grados"
    )
    assert extract_temperature_c(msg) == 39.0
    assert extract_pain_score(msg, history) is None

    decision = decide_from_text(msg, has_rag_evidence=True, history_text=history)
    assert decision.escalate is True
    assert decision.criticality == Criticality.rojo

    agent = ClinicalAgent.__new__(ClinicalAgent)
    reply = ClinicalAgent._spoken_summary_from_evidence(
        agent, msg, evidence_texts=["Fiebre mayor de 38.5"], history_text=history
    )
    assert "dolor de 0" not in reply.lower()
    assert any(k in reply.lower() for k in ("fiebre", "temperatura", "grados", "escal"))


def test_pain_followup_seis_sigue_funcionando():
    history = "agente: ¿En qué número del cero al diez lo sientes?"
    assert extract_pain_score("Lo siento un seis", history) == 6
    decision = decide_from_text(
        "Lo siento un seis",
        has_rag_evidence=True,
        history_text=history + " paciente: me duele la herida",
    )
    assert decision.criticality == Criticality.amarillo
    assert decision.escalate is False


def test_confirmacion_escalamiento():
    decision = decide_from_text(
        "sí",
        has_rag_evidence=True,
        history_text="agente: ¿Quieres que escale el caso a un humano?",
    )
    assert decision.escalate is True


def test_fallback_reply_fiebre_39_escala(monkeypatch):
    from app.config import get_settings

    blank = get_settings().model_copy(update={"google_api_key": ""})
    monkeypatch.setattr("app.agent.get_settings", lambda: blank)

    agent = ClinicalAgent(settings=blank)
    history = [
        ChatMessage(
            role="agent",
            content=(
                "Hola Sebastian, soy Beto otra vez. Recuerdo que tenías dolor en herida "
                "de 0 sobre 10. Cuéntame, ¿cómo te has sentido hoy?"
            ),
        )
    ]
    result = agent.respond(
        "tengo fiebre de 39 grados",
        history=history,
        patient_context={"patient_name": "Sebastian"},
        call_id="test_fever",
        call_state={},
    )
    assert result.decision.escalate is True
    assert result.decision.criticality == Criticality.rojo
    assert "dolor de 0" not in result.reply.lower()
    assert any(
        k in result.reply.lower() for k in ("escal", "médic", "medic", "alarma", "grados")
    )


def test_fallback_caminar_no_escala(monkeypatch):
    from app.config import get_settings

    blank = get_settings().model_copy(update={"google_api_key": ""})
    monkeypatch.setattr("app.agent.get_settings", lambda: blank)
    agent = ClinicalAgent(settings=blank)
    result = agent.respond(
        "¿Puedo caminar después de la apendicectomía?",
        history=[],
        call_id="test_walk",
    )
    assert result.decision.escalate is False
    lower = result.reply.lower()
    assert "camin" in lower or "tolerancia" in lower


def test_reply_ignores_fever_alarm_detector():
    msg = "tengo 39 grados de fiebre"
    bad = "Listo, un dolor de 0 suele ser manejable en casa."
    good = "39 grados es alarma; voy a escalar con personal médico."
    assert reply_ignores_current_alarm(msg, bad) is True
    assert reply_ignores_current_alarm(msg, good) is False


def test_extract_temperatures_variadas():
    assert extract_temperature_c("fiebre de 38,5") == 38.5
    assert extract_temperature_c("temperatura de 40") == 40.0
    assert extract_temperature_c("me medi y tengo 39 grados") == 39.0
    assert extract_temperature_c("dolor de 6") is None
