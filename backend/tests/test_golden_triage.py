from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.decision import decide_from_text
from app.models import Criticality


# Subconjunto golden inspirado en label_ground_truth del dataset
GOLDEN_CASES = [
    {
        "id": "verde_dolor_leve",
        "text": "La verdad, el dolor ha sido más bien un 1, apenas se nota, casi nada. Sin fiebre.",
        "expected": Criticality.verde,
        "must_escalate": False,
    },
    {
        "id": "rojo_dificultad_respirar",
        "text": "Me falta el aire, tengo dificultad para respirar y el pecho me duele mucho.",
        "expected": Criticality.rojo,
        "must_escalate": True,
    },
    {
        "id": "rojo_sangrado",
        "text": "La herida tiene sangrado abundante que no para y salió pus.",
        "expected": Criticality.rojo,
        "must_escalate": True,
    },
    {
        "id": "rojo_fiebre_39",
        "text": "Me siento mal, tengo fiebre, me medi y tengo 39 grados",
        "expected": Criticality.rojo,
        "must_escalate": True,
    },
    {
        "id": "amarillo_vigilancia",
        "text": "Tengo un poco de náuseas y el dolor está como en 6.",
        "expected": Criticality.amarillo,
        "must_escalate": False,
    },
]


def test_golden_triage_subset():
    for case in GOLDEN_CASES:
        decision = decide_from_text(case["text"], has_rag_evidence=True)
        assert decision.escalate is case["must_escalate"], case["id"]
        if case["must_escalate"]:
            assert decision.criticality == Criticality.rojo, case["id"]
        else:
            assert decision.criticality in {
                case["expected"],
                Criticality.verde,
                Criticality.amarillo,
            }, case["id"]
