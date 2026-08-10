# Informe final — PostOp Care (Tech Sphere 2026)

## 1. Problema

El seguimiento postoperatorio temprano depende de personal humano, no escala bien y deja al paciente describiendo síntomas en lenguaje cotidiano, regional y a menudo ambiguo. El conocimiento clínico vive en PDFs que cambian de versión: el agente debe usar siempre la versión vigente.

## 2. Solución

**PostOp Care** es un agente de voz en navegador que:

1. Conversa en español colombiano.
2. Recupera evidencia de un RAG dinámico (alta/baja en caliente).
3. Responde con citas documentales.
4. Clasifica criticidad (`verde` / `amarillo` / `rojo`) y escala cuando hay alarma o incertidumbre peligrosa.
5. Deja historial estructurado + métricas.

## 3. Modelo utilizado (declaración G3)

- **Modelo:** Google Gemini Flash (`GEMINI_MODEL`, default recomendado `gemini-2.0-flash-lite`)
- **Familia permitida:** Google Gemini, gama Flash
- **Por qué:** contexto amplio para guías, free tier, baja fricción de setup frente a modelos locales, alineado al artefacto oficial.

> Nota: IDs puntuales cambian. Si uno falla (404), usa `gemini-flash-latest` u otro Flash vigente; el agente intenta respaldos automáticamente.

## 4. Prompting (evidencia)

El system prompt (ver `backend/app/agent.py`) impone:

- Respuestas cortas hablables.
- Prohibición de inventar dosis/medicamentos.
- Obligación de declarar “no sé” sin evidencia RAG.
- Anti-inyección de prompt.
- Salida JSON estructurada (`reply`, `criticality`, `escalate`, `needs_more_info`).

El Decision Engine (`backend/app/decision.py`) actúa como harness de seguridad sobre la salida del LLM.

## 5. Configuración relevante

```env
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-flash-latest
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
TTS_VOICE=es-CO-GonzaloNeural
TTS_RATE=-6%
TTS_PITCH=-1Hz
RAG_TOP_K=5
```

## 6. Proceso de desarrollo

Etapas: scaffold → RAG vivo → agente/decisión → admin UI → voz → métricas → tests → docs.

Uso del material `ParticipantArtifacts-main/dataset`:

- PDF `textos/` indexados (semilla multi-escenario + consola G5).
- Excel de perfiles/trayectorias/diálogos cargados en runtime (`app/dataset.py`).
- En `/call` el procedimiento se elige desde los del dataset; el nombre es libre.
- Eval offline `scripts/eval_triage.py` contra `label_ground_truth` (prioridad: no perder rojos).

Pruebas automatizadas: unitarias de decisión, integración RAG, golden triage, carga del dataset xlsx, anti-repetición en fallback de caminar.

## 7. Capturas / evidencia para el video

Pegar aquí capturas de:

1. Consola admin con documento “Procesado y disponible”.
2. Llamada usando el documento.
3. Eliminación y falla controlada al reconsultar.
4. Escalamiento en caso rojo.
5. Panel de métricas `/historial`.

## 8. Limitaciones y trabajo futuro

- STT del navegador puede degradarse con ruido; Whisper (Groq) sería el siguiente paso.
- Un PDF escaneado sin texto requiere OCR (no incluido para mantener G2).
- Material de evaluación puede incluir docs no vistos: la consola G5 es la mitigación.

## 9. Cumplimiento

Datos sintéticos, PII enmascarada en logs, sin afirmaciones clínicas fuera del corpus, aviso de no-uso-clínico en UI.
