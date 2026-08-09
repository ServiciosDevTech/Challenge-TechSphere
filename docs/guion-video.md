# Guion de video — PostOp Care

Duración sugerida: 5–8 minutos. Pantalla + cara para las dos preguntas de cierre.

## Parte A — Demo funcional (pantalla)

1. **Arranque (30 s):** mostrar README y levantar backend/frontend (o app ya corriendo).
2. **Admin G5 (90 s):**
   - Subir documento de prueba con frase única.
   - Mostrar badge “Procesado y disponible”.
3. **Llamada de voz (120 s):**
   - Iniciar llamada en `/call`.
   - Saludo hablado.
   - Preguntar algo cubierto por el documento → respuesta + fuente visible.
4. **Olvido en caliente (60 s):**
   - Eliminar el documento.
   - Repetir la pregunta → el agente ya no lo usa.
5. **Escalamiento (45 s):**
   - Relatar síntoma de alarma (dificultad respiratoria / sangrado).
   - Mostrar decisión `rojo` y mensaje de escalamiento.
6. **Historial (30 s):** abrir `/historial` y un JSON de llamada.

## Parte B — Preguntas de cierre (cámara)

### Pregunta 1 — Valor para un cliente

Enmarcar:

- Problema: seguimiento postoperatorio costoso, no escalable, riesgo de falsos negativos.
- Solución: voz + RAG vivo + decisión explícita de escalar.
- Diferencial: conocimiento actualizable en caliente con citas; honestidad cuando no sabe; orientado a español colombiano.

### Pregunta 2 — Decisión técnica más relevante

Sugerencia: **Gemini Flash + Decision Engine + RAG borrable por `document_id`**.

Cubrir:

- Alternativas (Groq Llama, Ollama, BGE-M3, LangChain).
- Por qué se descartaron (setup 15 min, familia permitida, control de citas).
- Riesgos (rate limits, STT del navegador, PDF sin texto).
- Con dos semanas más: Whisper, OCR, evaluación golden ampliada sobre el Excel completo.
