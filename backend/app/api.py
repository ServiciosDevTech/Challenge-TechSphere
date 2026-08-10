from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app import __version__
from app.agent import get_agent
from app.calls import get_call_store
from app.config import get_settings
from app.models import (
    ChatTurnRequest,
    ChatTurnResponse,
    DocumentInfo,
    EndCallResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    StartCallRequest,
    StartCallResponse,
    TtsRequest,
)
from app.rag import get_rag
from app.tts import synthesize_speech

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    rag = get_rag()
    agent = get_agent()
    active_model = agent._resolved_model or settings.gemini_model
    return HealthResponse(
        status="ok",
        version=__version__,
        gemini_configured=bool(settings.google_api_key),
        gemini_model=active_model,
        documents_ready=rag.count_ready(),
        agent_name=settings.agent_name,
        product_name=settings.product_name,
        product_slogan=settings.product_slogan,
        agent_tagline=settings.agent_tagline,
    )


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents() -> list[DocumentInfo]:
    return get_rag().list_documents()


@router.get("/documents/{document_id}", response_model=DocumentInfo)
def get_document(document_id: str) -> DocumentInfo:
    doc = get_rag().get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


@router.post("/documents", response_model=DocumentInfo)
async def upload_document(
    file: UploadFile = File(...),
    scenario: str | None = Form(default=None),
) -> DocumentInfo:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")
    lower = file.filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Solo se aceptan PDF o TXT")

    suffix = Path(file.filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(file.file, tmp)

    try:
        doc = get_rag().ingest_file(
            tmp_path,
            filename=file.filename,
            scenario=scenario,
        )
        return doc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete("/documents/{document_id}")
def delete_document(document_id: str) -> dict:
    ok = get_rag().delete_document(document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return {"deleted": True, "id": document_id}


@router.post("/rag/query", response_model=QueryResponse)
def rag_query(body: QueryRequest) -> QueryResponse:
    hits = get_rag().query(body.query, top_k=body.top_k)
    return QueryResponse(hits=hits)


@router.get("/dataset/stats")
def dataset_stats() -> dict:
    from app.dataset import load_dataset_bundle

    return load_dataset_bundle()["stats"]


@router.get("/dataset/patients")
def dataset_patients(limit: int | None = 40) -> list[dict]:
    from app.dataset import list_patients

    return list_patients(limit=limit)


@router.get("/dataset/cases/{caso_id}")
def dataset_case(caso_id: str) -> dict:
    from app.dataset import get_case, get_trajectory_for_case, resolve_call_context

    case = get_case(caso_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    resolved = resolve_call_context(caso_id=caso_id)
    return {
        "caso_id": caso_id,
        "paciente_id": case["paciente_id"],
        "dia_postop": case["dia_postop"],
        "label_ground_truth": case["label_ground_truth"],
        "trajectory": get_trajectory_for_case(caso_id),
        "agent_context": resolved["agent_context"],
        "demo_script": resolved["demo_script"],
        "turn_counts": {k: len(v) for k, v in case["turns"].items()},
    }


@router.post("/calls/start", response_model=StartCallResponse)
def start_call(body: StartCallRequest) -> StartCallResponse:
    settings = get_settings()
    started = get_call_store().start(body)
    return StartCallResponse(
        call_id=started["call_id"],
        greeting=started["greeting"],
        agent_name=settings.agent_name,
        product_slogan=settings.product_slogan,
        returning_patient=started["returning_patient"],
        patient_context=started.get("patient_context") or {},
        demo_script=started.get("demo_script"),
    )


@router.post("/calls/turn", response_model=ChatTurnResponse)
def call_turn(body: ChatTurnRequest) -> ChatTurnResponse:
    store = get_call_store()
    call_id = body.call_id
    if not call_id:
        started = store.start(StartCallRequest())
        call_id = started["call_id"]

    # Preferir contexto persistido de la llamada (dataset) sobre el del cliente
    record = store.get(call_id) or {}
    patient_context = body.patient_context or record.get("patient_context") or {}

    result = get_agent().respond(
        message=body.message,
        history=body.history,
        patient_context=patient_context,
        call_id=call_id,
        call_state=store.get_call_state(call_id),
    )
    result.call_id = call_id
    store.append_turn(
        call_id=call_id,
        user_message=body.message,
        agent_reply=result.reply,
        decision=result.decision,
        sources=result.sources,
        metrics=result.metrics,
        call_state=result.call_state,
    )
    return result

@router.post("/calls/{call_id}/end", response_model=EndCallResponse)
def end_call(call_id: str) -> EndCallResponse:
    try:
        summary = get_call_store().end(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EndCallResponse(summary=summary)


@router.get("/calls")
def list_calls() -> list[dict]:
    return get_call_store().list_calls()


@router.get("/calls/{call_id}")
def get_call(call_id: str) -> dict:
    data = get_call_store().get(call_id)
    if not data:
        raise HTTPException(status_code=404, detail="Llamada no encontrada")
    return data


@router.get("/metrics")
def metrics() -> dict:
    return get_call_store().metrics.summary()


@router.post("/tts")
async def tts(body: TtsRequest) -> Response:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")
    try:
        audio = await synthesize_speech(body.text, body.voice)
    except Exception as exc:  # noqa: BLE001
        logger.exception("TTS failed")
        raise HTTPException(
            status_code=503,
            detail=f"TTS no disponible: {exc}",
        ) from exc
    return Response(content=audio, media_type="audio/mpeg")
