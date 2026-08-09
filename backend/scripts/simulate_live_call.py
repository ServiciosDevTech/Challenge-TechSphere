"""Simulación live de llamada contra el API de PostOp Care / Beto."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8000/api"


def post(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def start(name: str = "Sebastian Sim", procedure: str = "Apendicectomía") -> dict[str, Any]:
    return post("/calls/start", {"patient_name": name, "procedure": procedure})


def turn(call_id: str, message: str, history: list[dict[str, str]]) -> dict[str, Any]:
    return post(
        "/calls/turn",
        {
            "call_id": call_id,
            "message": message,
            "history": history,
            "patient_context": {
                "patient_name": "Sebastian Sim",
                "procedure": "Apendicectomía",
            },
        },
    )


def end(call_id: str) -> None:
    post(f"/calls/{call_id}/end", {})


SCENARIOS = [
    {
        "id": "verde_caminar",
        "message": "Hola Beto, me operaron de apéndice, ¿puedo caminar?",
        "expect_escalate": False,
        "expect_crit": {"verde", "amarillo"},
        "reply_must_not": ["dolor de 0"],
        "reply_should_any": ["camin", "toleran", "pase"],
    },
    {
        "id": "amarillo_dolor_6",
        "message": "El dolor de la herida es un seis",
        "expect_escalate": False,
        "expect_crit": {"amarillo"},
        "reply_must_not": [],
        "reply_should_any": ["vigil", "dolor", "seis", "6", "fiebre", "casa", "entend"],
    },
    {
        "id": "rojo_fiebre_39",
        "message": (
            "hola beto hoy me siento un poco mal tengo algo de fiebre me medi "
            "con el termómetro y tengo 39 grados"
        ),
        "expect_escalate": True,
        "expect_crit": {"rojo"},
        "reply_must_not": ["dolor de 0"],
        "reply_should_any": [
            "escal",
            "médic",
            "medic",
            "alarma",
            "grados",
            "fiebre",
            "temperatura",
            "profesional",
        ],
        "seed_history": [
            {
                "role": "agent",
                "content": (
                    "Hola Sebastian, soy Beto otra vez. Recuerdo que tenías dolor "
                    "en herida de 0 sobre 10. Cuéntame, ¿cómo te has sentido hoy?"
                ),
            }
        ],
    },
    {
        "id": "rojo_faltando_aire",
        "message": "Me está faltando el aire",
        "expect_escalate": True,
        "expect_crit": {"rojo"},
        "reply_must_not": ["caminar según"],
        "reply_should_any": ["escal", "médic", "medic", "alarma", "urgenc", "humano"],
    },
    {
        "id": "rojo_dolor_9",
        "message": "El dolor es un nueve",
        "expect_escalate": True,
        "expect_crit": {"rojo"},
        "reply_must_not": [],
        "reply_should_any": ["escal", "médic", "medic", "intenso", "alarma"],
    },
    {
        "id": "rojo_pedir_medico",
        "message": "Quiero hablar con un médico",
        "expect_escalate": True,
        "expect_crit": {"rojo"},
        "reply_must_not": [],
        "reply_should_any": ["escal", "médic", "medic", "humano"],
    },
    {
        "id": "amarillo_nauseas",
        "message": "Tengo un poco de náuseas",
        "expect_escalate": False,
        "expect_crit": {"amarillo", "verde"},
        "reply_must_not": [],
        "reply_should_any": [
            "náuse",
            "nause",
            "vigil",
            "cómo",
            "cuándo",
            "fiebre",
            "líquid",
            "entend",
            "listo",
        ],
    },
]


def main() -> None:
    results: list[tuple[str, bool, str | None, bool | None, str]] = []
    print("=== SIMULACIÓN LIVE CONTRA /api ===\n")

    for sc in SCENARIOS:
        started = start(name=f"Sim {sc['id']}")
        call_id = started["call_id"]
        greeting = started["greeting"]
        history = list(
            sc.get("seed_history")
            or [{"role": "agent", "content": greeting}]
        )
        try:
            res = turn(call_id, sc["message"], history)
            reply = res.get("reply") or ""
            decision = res.get("decision") or {}
            crit = decision.get("criticality")
            esc = bool(decision.get("escalate"))
            lower = reply.lower()

            ok_esc = esc is sc["expect_escalate"]
            ok_crit = crit in sc["expect_crit"]
            ok_not = all(bad.lower() not in lower for bad in sc["reply_must_not"])
            ok_any = (not sc["reply_should_any"]) or any(
                x in lower for x in sc["reply_should_any"]
            )
            ok = ok_esc and ok_crit and ok_not and ok_any

            results.append((sc["id"], ok, crit, esc, reply))
            mark = "PASS" if ok else "FAIL"
            print(f"[{mark}] {sc['id']}")
            print(f"  paciente: {sc['message'][:100]}")
            print(f"  decision: {crit} escalate={esc}")
            print(f"  beto: {reply[:260]}")
            if not ok:
                print(
                    f"  checks: esc={ok_esc} crit={ok_crit} "
                    f"must_not={ok_not} should_any={ok_any}"
                )
            print()
        except Exception as exc:  # noqa: BLE001
            results.append((sc["id"], False, None, None, str(exc)))
            print(f"[FAIL] {sc['id']} ERROR: {exc}\n")
        finally:
            try:
                end(call_id)
            except Exception:  # noqa: BLE001
                pass

    print("=== CONVERSACIÓN MULTI-TURNO ===\n")
    started = start(name="Sebastian Multi")
    call_id = started["call_id"]
    history = [{"role": "agent", "content": started["greeting"]}]
    print(f"Beto: {started['greeting']}\n")

    script = [
        ("Me siento más o menos bien, el dolor es un 2", False, {"verde", "amarillo"}),
        ("Bueno, ahora el dolor subió a un seis", False, {"amarillo"}),
        ("Además me medi y tengo 39 grados", True, {"rojo"}),
    ]
    multi_ok = True
    for msg, exp_esc, exp_crit in script:
        res = turn(call_id, msg, history)
        history = history + [
            {"role": "paciente", "content": msg},
            {"role": "agent", "content": res["reply"]},
        ]
        crit = res["decision"]["criticality"]
        esc = res["decision"]["escalate"]
        ok = esc is exp_esc and crit in exp_crit
        multi_ok = multi_ok and ok
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] paciente: {msg}")
        print(f"  -> {crit} escalate={esc}")
        print(f"  Beto: {res['reply'][:260]}\n")

    try:
        end(call_id)
    except Exception:  # noqa: BLE001
        pass

    passed = sum(1 for _, ok, *_ in results if ok)
    total = len(results)
    print("=== RESUMEN ===")
    print(f"Escenarios independientes: {passed}/{total} OK")
    print(f"Multi-turno: {'OK' if multi_ok else 'FALLÓ'}")
    print(f"TOTAL LIVE: {passed + (1 if multi_ok else 0)}/{total + 1}")
    if passed < total or not multi_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
