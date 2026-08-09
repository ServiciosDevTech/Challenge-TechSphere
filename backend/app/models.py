from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    error = "error"


class DocumentInfo(BaseModel):
    id: str
    filename: str
    scenario: str | None = None
    status: DocumentStatus
    chunk_count: int = 0
    created_at: datetime
    error_message: str | None = None
    ready_label: str | None = None


class Citation(BaseModel):
    document_id: str
    filename: str
    page: int | None = None
    excerpt: str
    score: float | None = None


class RagHit(BaseModel):
    text: str
    citation: Citation


class Criticality(str, Enum):
    verde = "verde"
    amarillo = "amarillo"
    rojo = "rojo"
    desconocido = "desconocido"


class DecisionAction(str, Enum):
    continue_care = "continue_care"
    escalate = "escalate"
    insufficient_info = "insufficient_info"


class AgentDecision(BaseModel):
    criticality: Criticality
    action: DecisionAction
    rationale: str
    escalate: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatTurnRequest(BaseModel):
    call_id: str | None = None
    message: str
    patient_context: dict[str, Any] | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatTurnResponse(BaseModel):
    call_id: str
    reply: str
    decision: AgentDecision
    sources: list[Citation] = Field(default_factory=list)
    needs_more_info: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    call_state: dict[str, Any] = Field(default_factory=dict)
    consulted_rag: bool = False
    agent_name: str = "Beto"


class CallSummary(BaseModel):
    call_id: str
    patient_id: str | None = None
    procedure: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    decision: AgentDecision | None = None
    sources_used: list[Citation] = Field(default_factory=list)
    next_steps: str | None = None
    transcript: list[ChatMessage] = Field(default_factory=list)
    started_at: datetime | str | None = None
    ended_at: datetime | str | None = None


class StartCallRequest(BaseModel):
    patient_id: str | None = None
    procedure: str | None = None
    patient_name: str | None = None
    dia_postop: int | None = None


class StartCallResponse(BaseModel):
    call_id: str
    greeting: str
    agent_name: str = "Beto"
    product_slogan: str = "Asistente inteligente de seguimiento postoperatorio"
    returning_patient: bool = False


class EndCallResponse(BaseModel):
    summary: CallSummary


class QueryRequest(BaseModel):
    query: str
    top_k: int | None = None


class QueryResponse(BaseModel):
    hits: list[RagHit]


class TtsRequest(BaseModel):
    text: str
    voice: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    gemini_configured: bool
    gemini_model: str
    documents_ready: int
    agent_name: str = "Beto"
    product_name: str = "PostOp Care"
    product_slogan: str = "Asistente inteligente de seguimiento postoperatorio"
    agent_tagline: str = "Tu asistente de recuperación"
