from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.dataset import (
    iter_eval_cases,
    load_dataset_bundle,
    resolve_call_context,
)


def test_dataset_bundle_loads():
    bundle = load_dataset_bundle()
    if not bundle["stats"]["available"]:
        # Entorno sin junction: no fallar CI genérico
        return
    assert bundle["stats"]["patients"] == 40
    assert bundle["stats"]["cases"] == 160
    assert bundle["stats"]["dialog_rows"] == 3991


def test_resolve_call_context_hides_symptoms_from_agent():
    bundle = load_dataset_bundle()
    if not bundle["stats"]["available"]:
        return
    caso_id = next(iter(bundle["cases"]))
    resolved = resolve_call_context(caso_id=caso_id)
    ctx = resolved["agent_context"]
    assert "patient_name" in ctx
    assert "procedure" in ctx
    assert "dolor_nrs" not in ctx
    assert "label_ground_truth" not in ctx
    assert resolved["demo_script"] is not None
    assert "label_ground_truth" in resolved["demo_script"]


def test_eval_cases_have_patient_text():
    bundle = load_dataset_bundle()
    if not bundle["stats"]["available"]:
        return
    cases = iter_eval_cases()
    assert len(cases) >= 100
    assert all(c["patient_text"] for c in cases[:10])
