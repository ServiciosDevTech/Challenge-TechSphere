from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent import ClinicalAgent


def test_parse_valid_json():
    agent = ClinicalAgent.__new__(ClinicalAgent)
    parsed = agent._parse_llm_json(
        '{"reply":"Puedes caminar con calma.","criticality":"verde","escalate":false,"needs_more_info":false,"rationale":"ok"}'
    )
    assert parsed["reply"].startswith("Puedes caminar")
    assert parsed["criticality"] == "verde"


def test_parse_broken_json_does_not_leak_fields_as_reply():
    agent = ClinicalAgent.__new__(ClinicalAgent)
    parsed = agent._parse_llm_json("amarillo, escalate = false, needs_more_")
    assert parsed.get("reply") == ""
    assert agent._is_bad_patient_reply(str(parsed.get("reply", "")))


def test_bad_reply_detector():
    assert ClinicalAgent._is_bad_patient_reply("amarillo, escalate = false")
    assert ClinicalAgent._is_bad_patient_reply("{criticality}")
    assert not ClinicalAgent._is_bad_patient_reply(
        "Sí, puedes caminar según tu tolerancia y sin forzar."
    )
