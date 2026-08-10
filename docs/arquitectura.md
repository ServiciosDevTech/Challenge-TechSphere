# Arquitectura — PostOp Care

Documento de entregable: **diagrama de la solución** y **flujo de decisión del agente**.

Este archivo es la fuente oficial del diagrama (GitHub renderiza los bloques Mermaid). El video demo está en [Google Drive](https://drive.google.com/drive/folders/1mVbegDRf-KAdfi5Z2rJQiof30KVWQOBl?usp=sharing).

---

## 1. Arquitectura de la solución (componentes)

```mermaid
flowchart TB
  subgraph Cliente["Navegador del paciente / jurado"]
    CALL["/call — Llamada<br/>STT Web Speech · UI Beto"]
    ADMIN["/admin — Consola<br/>alta / baja de PDFs"]
    HIST["/historial — Conversación<br/>alertas · refs · métricas"]
  end

  subgraph Backend["Backend FastAPI"]
    API["API REST<br/>/api/calls · /api/documents · /api/tts"]
    AGENT["ClinicalAgent<br/>prompt + memoria de llamada"]
    RAG["Dynamic RAG<br/>Chroma + MiniLM multilingual"]
    LLM["Gemini Flash<br/>JSON: reply + criticality"]
    DE["Decision Engine<br/>heurísticas + override de seguridad"]
    TTS["edge-tts<br/>es-CO-GonzaloNeural"]
    STORE["Persistencia<br/>calls/ · metrics/ · uploads/"]
  end

  subgraph Externos["Servicios externos"]
    GAPI["Google AI Studio<br/>GEMINI_MODEL"]
    EDGE["Microsoft Edge TTS"]
  end

  CALL -->|HTTP turn / start / end| API
  ADMIN -->|upload / delete| API
  HIST -->|list / get call| API

  API --> AGENT
  API --> TTS
  AGENT --> RAG
  AGENT --> LLM
  LLM --> GAPI
  AGENT --> DE
  DE -->|verde / amarillo / rojo| API
  RAG -->|citas documentales| API
  TTS --> EDGE
  TTS -->|audio MPEG| CALL
  AGENT --> STORE
  ADMIN -.->|índice en caliente| RAG
```

### Lectura rápida

| Capa | Qué hace |
|---|---|
| **UI `/call`** | Voz/texto, saludo de Beto, criticidad, botón Ver referencias |
| **UI `/admin`** | Conocimiento vivo (G5): indexar o borrar PDF/TXT sin reiniciar |
| **UI `/historial`** | Transcript, alerta final, refs por turno, latencias |
| **ClinicalAgent** | Orquesta RAG + Gemini + memoria; anti-repetición de preguntas |
| **Decision Engine** | No se fía solo del LLM: prioriza no perder rojos |
| **RAG** | Chroma + embeddings; citas con filename / página / excerpt |

---

## 2. Flujo de un turno de llamada (secuencia)

```mermaid
sequenceDiagram
  autonumber
  actor P as Paciente
  participant UI as React /call
  participant API as FastAPI
  participant RAG as Chroma RAG
  participant LLM as Gemini Flash
  participant DE as Decision Engine
  participant TTS as edge-tts

  P->>UI: Habla o escribe
  UI->>API: POST /api/calls/turn
  API->>RAG: query(mensaje)
  RAG-->>API: top-k fragmentos + citas
  API->>LLM: system + contexto RAG + historial + mensaje
  LLM-->>API: JSON reply, criticality, escalate
  API->>DE: decide_from_text(mensaje, señal LLM, RAG)
  DE-->>API: criticidad final + escalate
  API->>TTS: sintetizar reply
  TTS-->>UI: audio MPEG
  UI-->>P: Voz + texto + ícono + referencias
  API->>API: guardar turno en calls/*.json + metrics
```

### Pasos en prosa

1. `/calls/start` crea `call_id` y saludo hablado.
2. El paciente habla (Web Speech) o escribe.
3. RAG recupera top-k fragmentos; Gemini responde en JSON corto y hablable.
4. El **Decision Engine** combina señales del relato con la salida del LLM (asimetría clínica).
5. La UI muestra respuesta, criticidad y fuentes.
6. TTS reproduce la respuesta.
7. Al finalizar, queda el resumen en `backend/data/calls/`.

---

## 3. Flujo de decisión del agente (Decision Engine)

Principio: **mejor un falso positivo controlado que un falso negativo** (no alertar cuando había que alertar).

```mermaid
flowchart TD
  IN([Mensaje del paciente<br/>+ criticality LLM<br/>+ ¿hay evidencia RAG?]) --> TEMP{¿Temperatura<br/>≥ 38 °C?}

  TEMP -->|sí| ROJO[ROJO · escalate = true<br/>Escalar a humano]
  TEMP -->|no| PAIN8{¿Dolor NRS ≥ 8?}

  PAIN8 -->|sí| ROJO
  PAIN8 -->|no| ALARM{¿Patrón de alarma?<br/>falta de aire, pecho,<br/>sangrado, pus, desmayo…<br/>¿LLM pide rojo?<br/>¿Paciente pide escalar?}

  ALARM -->|sí| ROJO
  ALARM -->|no| PAIN57{¿Dolor NRS 5–7?}

  PAIN57 -->|sí| AMA[AMARILLO · continue_care<br/>Vigilancia · indagar más]
  PAIN57 -->|no| SINRAG{¿Sin evidencia RAG<br/>útil / criticidad desconocida?}

  SINRAG -->|sí| DESC[DESCONOCIDO · insufficient_info<br/>Declarar límite · ofrecer escalar]
  SINRAG -->|no| WATCH{¿Señales de vigilancia<br/>o LLM amarillo?<br/>náuseas, herida inflamada…}

  WATCH -->|sí| AMA
  WATCH -->|no| OK{¿LLM verde<br/>o relato tranquilizador?}

  OK -->|sí| VERDE[VERDE · continue_care<br/>Cuidados en casa · 1 pregunta nueva]
  OK -->|no| AMA

  ROJO --> OUT([Respuesta al paciente<br/>+ UI rojo + historial])
  AMA --> OUT
  DESC --> OUT
  VERDE --> OUT
```

### Señales que disparan **rojo** (ejemplos)

- Fiebre / temperatura ≥ **38 °C**
- Dolor ≥ **8 / 10**
- Falta de aire, dolor de pecho, sangrado abundante, pus/secreción, desmayo
- El paciente pide explícitamente hablar con un humano / escalar
- El LLM marca `criticality=rojo` o `escalate=true` (el motor lo respeta)

### **Amarillo**

- Dolor 5–7, náuseas, herida un poco inflamada, fiebre bajita, etc.
- Seguimiento en casa + **una** pregunta concreta (sin repetir la anterior)

### **Verde**

- Evolución esperada / relato tranquilizador con evidencia RAG
- Cuidados orientados al corpus + pregunta nueva o cierre

### **Desconocido**

- Sin evidencia documental suficiente → no inventar; declarar límite u ofrecer escalar

---

## 4. Conocimiento vivo (G5)

```mermaid
flowchart LR
  A[Admin sube PDF/TXT] --> B[Extract + chunk + embed]
  B --> C[Upsert Chroma<br/>document_id]
  C --> D[Badge: Procesado y disponible]
  D --> E[Siguiente turno /call<br/>ya puede citarlo]

  F[Admin elimina documento] --> G[Borra vectores por document_id]
  G --> H[Siguiente turno<br/>ya no lo cita]
```

- Alta: `POST /api/documents`
- Baja: `DELETE /api/documents/{id}`
- Sin reinicio del agente ni del índice global

---

## 5. Decisiones técnicas clave

| Decisión | Alternativas | Elección | Riesgo |
|---|---|---|---|
| LLM | Groq Llama, Ollama, Gemini Flash | Gemini Flash | Cuota free tier (429) |
| Embeddings | BGE-M3, Gemini emb., MiniLM | MiniLM multilingual | Menos precisión que BGE; más liviano (G2) |
| STT | Whisper, Web Speech | Web Speech | Ruido / Opera |
| TTS | Kokoro, Piper, edge-tts | edge-tts Gonzalo | Dependencia Edge; sin API key |
| Orquestación | LangChain, custom | FastAPI custom | Más control de prompts y citas |

---

## 6. Persistencia

| Ruta | Contenido |
|---|---|
| `backend/data/chroma/` | Índice vectorial + registry |
| `backend/data/uploads/` | Archivos originales |
| `backend/data/calls/` | Transcripts, decisiones, sources por turno |
| `backend/data/metrics/events.json` | Latencia / tokens / costo estimado |

---

## 7. Superficies de la aplicación

| Ruta | Contrato |
|---|---|
| `/call` | Llamada de voz + chat |
| `/admin` | Conocimiento vivo |
| `/historial` | Observabilidad y métricas |
