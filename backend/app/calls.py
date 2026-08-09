from __future__ import annotations

import json
import statistics
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.models import (
    AgentDecision,
    CallSummary,
    ChatMessage,
    Citation,
    StartCallRequest,
)
from app.persona import build_greeting, summarize_prior_call, update_call_state
from app.utils import mask_pii, new_id


class MetricsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def record(self, event: dict[str, Any]) -> None:
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
        with self._lock:
            data = json.loads(self.path.read_text(encoding="utf-8") or "[]")
            data.append(event)
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def summary(self) -> dict[str, Any]:
        with self._lock:
            data = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        latencies = [e["latency_ms"] for e in data if e.get("latency_ms") is not None]
        prompt_tokens = [e["prompt_tokens"] for e in data if e.get("prompt_tokens")]
        completion_tokens = [
            e["completion_tokens"] for e in data if e.get("completion_tokens")
        ]
        rag_queries = sum(e.get("rag_queries", 0) for e in data)
        llm_invocations = sum(e.get("llm_invocations", 0) for e in data)
        calls = {e.get("call_id") for e in data if e.get("call_id")}

        def pct(values: list[float], p: float) -> float | None:
            if not values:
                return None
            ordered = sorted(values)
            idx = int(round((p / 100) * (len(ordered) - 1)))
            return round(ordered[idx], 2)

        avg_prompt = round(statistics.mean(prompt_tokens), 2) if prompt_tokens else None
        avg_completion = (
            round(statistics.mean(completion_tokens), 2) if completion_tokens else None
        )

        # Extrapolated cost using public Gemini Flash-ish pricing (USD / 1M tokens)
        # Documented estimate for README; free tier actual cost = $0.
        in_price = 0.10
        out_price = 0.40
        total_in = sum(prompt_tokens)
        total_out = sum(completion_tokens)
        estimated_usd = (total_in / 1_000_000) * in_price + (total_out / 1_000_000) * out_price
        per_call = estimated_usd / max(1, len(calls))

        return {
            "events": len(data),
            "calls": len(calls),
            "latency_p50_ms": pct(latencies, 50),
            "latency_p95_ms": pct(latencies, 95),
            "avg_prompt_tokens": avg_prompt,
            "avg_completion_tokens": avg_completion,
            "rag_queries_total": rag_queries,
            "llm_invocations_total": llm_invocations,
            "estimated_cost_usd_total": round(estimated_usd, 6),
            "estimated_cost_usd_per_call": round(per_call, 6),
            "pricing_note": (
                "Costo extrapolado a precios de API de producción orientativos "
                "($0.10/1M input, $0.40/1M output). En free tier el costo real es $0."
            ),
        }


class CallStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.calls_path.mkdir(parents=True, exist_ok=True)
        self.metrics = MetricsStore(self.settings.metrics_path / "events.json")
        self._lock = threading.Lock()
        self._active: dict[str, dict[str, Any]] = {}

    def _path(self, call_id: str) -> Path:
        return self.settings.calls_path / f"{call_id}.json"

    def start(self, req: StartCallRequest) -> tuple[str, str, bool]:
        call_id = new_id("call_")
        prior = self.find_latest_for_patient(req.patient_name)
        prior_summary = summarize_prior_call(prior) if prior else None
        greeting = build_greeting(
            agent_name=self.settings.agent_name,
            patient_name=req.patient_name,
            procedure=req.procedure,
            prior_summary=prior_summary,
        )
        seed_state: dict[str, Any] = {}
        record = {
            "call_id": call_id,
            "patient_id": req.patient_id,
            "procedure": req.procedure,
            "patient_name": req.patient_name,
            "dia_postop": req.dia_postop,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "transcript": [{"role": "agent", "content": greeting}],
            "sources_used": [],
            "decisions": [],
            "symptoms": [],
            # Memoria de llamada empieza limpia; el saludo ya menciona el resumen previo.
            "call_state": seed_state,
            "prior_call_id": (prior or {}).get("call_id"),
            "prior_summary": prior_summary,
        }
        with self._lock:
            self._active[call_id] = record
            self._path(call_id).write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return call_id, greeting, bool(prior_summary)

    def find_latest_for_patient(self, patient_name: str | None) -> dict[str, Any] | None:
        if not patient_name or not patient_name.strip():
            return None
        needle = patient_name.strip().lower()
        best: dict[str, Any] | None = None
        best_ts = ""
        for path in self.settings.calls_path.glob("call_*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            name = (data.get("patient_name") or "").strip().lower()
            if name != needle:
                continue
            if not data.get("ended_at"):
                continue
            ts = str(data.get("ended_at") or data.get("started_at") or "")
            if ts >= best_ts:
                best_ts = ts
                best = data
        return best

    def get_call_state(self, call_id: str) -> dict[str, Any]:
        record = self.get(call_id) or {}
        return dict(record.get("call_state") or {})

    def append_turn(
        self,
        call_id: str,
        user_message: str,
        agent_reply: str,
        decision: AgentDecision,
        sources: list[Citation],
        metrics: dict[str, Any],
        call_state: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._active.get(call_id)
            if record is None and self._path(call_id).exists():
                record = json.loads(self._path(call_id).read_text(encoding="utf-8"))
                self._active[call_id] = record
            if record is None:
                raise KeyError(f"call_id desconocido: {call_id}")

            record["transcript"].append(
                {"role": "paciente", "content": mask_pii(user_message)}
            )
            record["transcript"].append(
                {"role": "agent", "content": mask_pii(agent_reply)}
            )
            record["decisions"].append(decision.model_dump())
            if call_state is not None:
                record["call_state"] = call_state
            else:
                record["call_state"] = update_call_state(
                    record.get("call_state"),
                    user_message,
                )
            for src in sources:
                dumped = src.model_dump()
                if dumped not in record["sources_used"]:
                    record["sources_used"].append(dumped)
            if decision.criticality.value in ("amarillo", "rojo"):
                record["symptoms"].append(mask_pii(user_message)[:200])

            self._path(call_id).write_text(
                json.dumps(record, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

        self.metrics.record(
            {
                "call_id": call_id,
                "latency_ms": metrics.get("total_ms"),
                "prompt_tokens": metrics.get("prompt_tokens"),
                "completion_tokens": metrics.get("completion_tokens"),
                "rag_queries": metrics.get("rag_queries", 1),
                "llm_invocations": metrics.get("llm_invocations", 0),
                "decision": decision.criticality.value,
            }
        )

    def end(self, call_id: str) -> CallSummary:
        with self._lock:
            record = self._active.get(call_id)
            if record is None and self._path(call_id).exists():
                record = json.loads(self._path(call_id).read_text(encoding="utf-8"))
            if record is None:
                raise KeyError(f"call_id desconocido: {call_id}")

            record["ended_at"] = datetime.now(timezone.utc).isoformat()
            last_decision = None
            if record.get("decisions"):
                last_decision = AgentDecision.model_validate(record["decisions"][-1])

            next_steps = "Continuar cuidados en casa y nueva llamada de seguimiento."
            if last_decision and last_decision.escalate:
                next_steps = "Caso escalado a personal médico humano."
            elif last_decision and last_decision.action.value == "insufficient_info":
                next_steps = "Completar evaluación clínica humana por información insuficiente."

            summary = CallSummary(
                call_id=call_id,
                patient_id=record.get("patient_id"),
                procedure=record.get("procedure"),
                symptoms=record.get("symptoms") or [],
                decision=last_decision,
                sources_used=[
                    Citation.model_validate(s) for s in record.get("sources_used", [])
                ],
                next_steps=next_steps,
                transcript=[
                    ChatMessage.model_validate(t) for t in record.get("transcript", [])
                ],
                started_at=record.get("started_at"),
                ended_at=record.get("ended_at"),
            )
            record["summary"] = json.loads(summary.model_dump_json())
            self._path(call_id).write_text(
                json.dumps(record, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            self._active.pop(call_id, None)
            return summary

    def get(self, call_id: str) -> dict[str, Any] | None:
        path = self._path(call_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return self._active.get(call_id)

    def list_calls(self) -> list[dict[str, Any]]:
        items = []
        for path in sorted(self.settings.calls_path.glob("call_*.json"), reverse=True):
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "call_id": data.get("call_id"),
                    "patient_id": data.get("patient_id"),
                    "procedure": data.get("procedure"),
                    "started_at": data.get("started_at"),
                    "ended_at": data.get("ended_at"),
                    "turns": len(data.get("transcript", [])),
                }
            )
        return items


_store: CallStore | None = None


def get_call_store() -> CallStore:
    global _store
    if _store is None:
        _store = CallStore()
    return _store
