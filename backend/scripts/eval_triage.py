#!/usr/bin/env python
"""Evalúa el Decision Engine contra label_ground_truth del dataset del reto."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.dataset import iter_eval_cases, load_dataset_bundle  # noqa: E402
from app.decision import decide_from_text  # noqa: E402
from app.models import Criticality  # noqa: E402


SEVERITY = {
    Criticality.verde: 0,
    Criticality.amarillo: 1,
    Criticality.rojo: 2,
    Criticality.desconocido: 1,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline triage eval vs dataset xlsx")
    parser.add_argument("--capa", default="capa1_limpia")
    parser.add_argument("--limit", type=int, default=0, help="0 = todos los casos")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "metrics" / "eval_triage.json",
    )
    args = parser.parse_args()

    bundle = load_dataset_bundle()
    if not bundle["stats"]["available"]:
        print("Dataset no disponible. Configura data/dataset (ver data/README.md).")
        raise SystemExit(2)

    cases = iter_eval_cases(capa=args.capa)
    if args.limit and args.limit > 0:
        cases = cases[: args.limit]

    rows = []
    conf = Counter()
    false_neg_red = 0
    red_total = 0

    for case in cases:
        label = str(case["label_ground_truth"] or "desconocido").lower()
        decision = decide_from_text(case["patient_text"], has_rag_evidence=True)
        pred = decision.criticality.value
        expected = label if label in {"verde", "amarillo", "rojo"} else "desconocido"

        # También evaluar el turno paciente más “grave” por si el join diluye señales
        worst = decision
        for utt in case["utterances"]:
            d = decide_from_text(utt, has_rag_evidence=True)
            if SEVERITY[d.criticality] > SEVERITY[worst.criticality]:
                worst = d
        pred_worst = worst.criticality.value

        exact = pred == expected or pred_worst == expected
        # Asimetría clínica: para rojo, basta con que worst escale
        if expected == "rojo":
            red_total += 1
            red_ok = worst.escalate or pred_worst == "rojo" or pred == "rojo"
            if not red_ok:
                false_neg_red += 1
            exact = red_ok

        conf[(expected, pred_worst)] += 1
        rows.append(
            {
                "caso_id": case["caso_id"],
                "expected": expected,
                "predicted": pred,
                "predicted_worst_turn": pred_worst,
                "escalate": worst.escalate,
                "ok": exact,
                "rationale": worst.rationale,
            }
        )

    ok = sum(1 for r in rows if r["ok"])
    total = len(rows)
    by_label = Counter(r["expected"] for r in rows)
    ok_by = Counter(r["expected"] for r in rows if r["ok"])

    summary = {
        "capa": args.capa,
        "dataset_root": bundle["root"],
        "cases_evaluated": total,
        "accuracy_asymmetric": round(ok / total, 4) if total else 0,
        "exact_or_safe_red_recall": {
            label: {
                "n": by_label[label],
                "ok": ok_by[label],
                "rate": round(ok_by[label] / by_label[label], 4) if by_label[label] else 0,
            }
            for label in ("verde", "amarillo", "rojo")
        },
        "false_negative_red": false_neg_red,
        "red_total": red_total,
        "confusion_expected_vs_worst_pred": {
            f"{a}->{b}": n for (a, b), n in sorted(conf.items())
        },
        "note": (
            "Métrica asimétrica: en casos rojo cuenta OK si el motor escala/detecta rojo "
            "en el relato completo o en el peor turno paciente. No usa el LLM."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"summary": summary, "rows": rows}
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nDetalle: {args.out}")
    red_rate = (red_total - false_neg_red) / red_total if red_total else 1.0
    if false_neg_red:
        print(f"ALERTA: {false_neg_red}/{red_total} rojos no detectados (recall={red_rate:.2%})")
    # Umbral asimétrico: priorizar recall de rojo ≥ 80%
    if red_total and red_rate < 0.8:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
