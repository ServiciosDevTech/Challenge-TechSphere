# PostOp Care — Tech Sphere Challenge 2026

Agente de voz con IA para **seguimiento postoperatorio** en español colombiano.

El paciente habla desde el navegador. **Beto** (PostOp Care) consulta una base de conocimiento clínica (**RAG dinámico**), responde con evidencia documental trazable, clasifica criticidad (`verde` / `amarillo` / `rojo`) y **escala a un humano** cuando hay alarma o incertidumbre peligrosa.

> Datos sintéticos. No es un dispositivo médico ni un sistema de atención real.

---

## Entregables (enlaces para el jurado)

| Entregable | Ubicación |
|---|---|
| **Video demo** | [Google Drive — `Reto TechSphere.mp4`](https://drive.google.com/drive/folders/1mVbegDRf-KAdfi5Z2rJQiof30KVWQOBl?usp=sharing) |
| **Informe final** | [`docs/informe-final.md`](docs/informe-final.md) (en este repositorio) |
| **Diagrama de arquitectura y decisión** | [`docs/arquitectura.md`](docs/arquitectura.md) (en este repositorio; diagramas Mermaid renderizados por GitHub) |

> El **informe** y el **diagrama** viven solo en GitHub para que el jurado los lea con formato y Mermaid. En Drive queda únicamente el **video**.

### LLM y herramientas de voz (declaración)

| Rol | Herramienta |
|---|---|
| **LLM** | Google Gemini Flash (`GEMINI_MODEL`, free tier [AI Studio](https://aistudio.google.com/apikey)) |
| **STT (voz → texto)** | Web Speech API del navegador |
| **TTS (texto → voz)** | edge-tts · voz `es-CO-GonzaloNeural` (agente Beto) |

---

## Compuertas que cubre esta entrega

| Compuerta | Cómo se cumple |
|---|---|
| G1 Entregables | Repo público + informe + diagrama + video (enlaces arriba) |
| G2 ≤15 min | Scripts de arranque + este README |
| G3 Modelo permitido | **Google Gemini Flash** (`GEMINI_MODEL`, free tier AI Studio) |
| G4 Voz en navegador | `/call` con micrófono (Web Speech API) + TTS `edge-tts` |
| G5 Conocimiento vivo | `/admin` subir/eliminar documentos; efecto inmediato en el agente |

---

## Funcionalidades

### Llamada (`/call`)
- Inicio con **nombre del paciente** + **procedimiento** (select alimentado desde el dataset del reto).
- Agente conversacional **Beto** con saludo hablado (TTS masculino colombiano).
- Entrada por **voz** (pulsar Hablar) o **texto**.
- Consulta **RAG** sobre el corpus indexado; respuestas con botón **Ver referencias** (documento, página, extracto).
- Clasificación por turno: ícono verde / amarillo / rojo + rationale.
- Memoria de la llamada (dolor, fiebre, etc.) para no contradecir el mensaje actual.
- Escalamiento explícito ante alarmas (fiebre alta, falta de aire, dolor ≥8, etc.).
- Finalizar llamada → resumen persistido.

### Consola de administración (`/admin`) — G5
- Subir PDF/TXT (opcionalmente con escenario).
- Estado **Procesado y disponible** cuando el índice está listo.
- Eliminar documento → el agente deja de usarlo (olvido en caliente).
- Listado de documentos indexados.

### Historial y métricas (`/historial`)
- Listado de llamadas (paciente, procedimiento, alerta, turnos, refs).
- Detalle en dos columnas: conversación compacta (agente izq. / paciente der.).
- Por cada respuesta del agente: clasificación + **Ver referencias** de ese turno.
- Métricas: latencia P50/P95, costo estimado / llamada, consultas RAG.

### Backend / agente
- FastAPI: llamadas, turnos, TTS, documentos, dataset, métricas.
- **Decision Engine** (heurísticas + LLM) prioriza no perder rojos.
- Fallback hablable si Gemini no responde (cuota/error).
- Cadena de modelos Flash de respaldo ante 404/429.
- Enmascarado de PII en logs; corpus y llamadas en disco local.

### Dataset del reto (offline / eval)
- Carga de Excel oficiales (perfiles, trayectorias, diálogos).
- Semilla multi-escenario del corpus PDF.
- Eval triage vs `label_ground_truth` (`scripts/eval_triage.py`).

---

## Arquitectura (resumen)

```text
Paciente (voz/texto)
    → React /call
        → FastAPI /api/calls/*
            → RAG (Chroma + embeddings multilingual)
            → Gemini Flash (JSON: reply + criticality)
            → Decision Engine (override de seguridad)
            → TTS edge-tts
    ← respuesta + citas + criticidad

React /admin → alta/baja PDF → Chroma (conocimiento vivo)
React /historial ← JSON de llamadas + metrics/events.json
```

Detalle: [`docs/arquitectura.md`](docs/arquitectura.md)

---

## Stack

| Pieza | Tecnología |
|---|---|
| LLM | Google Gemini Flash (familia permitida) |
| Backend | Python 3.11+ / FastAPI |
| Frontend | React + Vite + TypeScript |
| RAG | ChromaDB + `paraphrase-multilingual-MiniLM-L12-v2` |
| STT | Web Speech API (`es-ES` / `es-CO`) |
| TTS | edge-tts (`es-CO-GonzaloNeural`) · agente **Beto** |

---

## Requisitos previos

- Windows 10/11 (scripts `.bat`) o Linux/macOS (`.sh`)
- Python **3.11+** (probado con 3.13)
- Node.js **20+**
- Cuenta gratuita en [Google AI Studio](https://aistudio.google.com/apikey) → `GOOGLE_API_KEY`
- Micrófono + **Chrome o Edge** recomendados para voz (Opera suele fallar el STT)
- Corpus del reto **opcional**: puedes subir PDFs solo desde `/admin` (ver [`data/README.md`](data/README.md))

---

## Arranque paso a paso (≤15 minutos)

### 1. Clonar el repositorio

```powershell
git clone https://github.com/ServiciosDevTech/Challenge-TechSphere.git
cd Challenge-TechSphere
```

### 2. Configurar variables de entorno

```powershell
copy .env.example .env
```

Edita `.env` y define al menos:

```env
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.0-flash-lite
```

Asigna en `GOOGLE_API_KEY` la clave de [Google AI Studio](https://aistudio.google.com/apikey).

> **No** pongas una API key real en `.env.example` ni en el repositorio (queda público y se puede abusar de la cuota).  
> Crea tu propia clave gratis en [Google AI Studio](https://aistudio.google.com/apikey) (1–2 minutos) y pégala solo en tu `.env` local.
>
> Si el jurado necesita que le facilite una `GOOGLE_API_KEY` para la evaluación, puede contactarme por **WhatsApp** o **correo electrónico** usando los datos de contacto del formulario de inscripción / entrega. Respondo para generar o compartir una clave de evaluación sin publicar secretos en Git.

> Si un modelo se queda sin cuota (429), cambia `GEMINI_MODEL` a otro Flash vigente o espera el reset diario. El agente también prueba respaldos automáticamente.

### 3. Instalar backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
cd ..
```

### 4. Instalar frontend

```powershell
cd frontend
npm install
cd ..
```

### 5. Datos clínicos (opcional)

Sin corpus precargado también puedes usar solo `/admin` para subir documentos (G5).

Si tienes `ParticipantArtifacts-main` como carpeta hermana del repo:

```powershell
cmd /c mklink /J data\textos "..\ParticipantArtifacts-main\dataset\textos"
cmd /c mklink /J data\dataset "..\ParticipantArtifacts-main\dataset"
```

### 6. Sembrar corpus (opcional)

Solo si enlazaste `data/textos` o quieres las muestras locales:

```powershell
cd backend
.\.venv\Scripts\python scripts\seed_corpus.py
cd ..
```

También puedes saltarte este paso y subir PDFs después desde `/admin`.

### 7. Levantar servicios

**Terminal A — backend**

```powershell
.\scripts\start-backend.bat
```

**Terminal B — frontend**

```powershell
.\scripts\start-frontend.bat
```

### 8. Abrir la app

| Superficie | URL |
|---|---|
| Llamada | http://127.0.0.1:5173/call |
| Consola (G5) | http://127.0.0.1:5173/admin |
| Historial / métricas | http://127.0.0.1:5173/historial |
| API docs | http://127.0.0.1:8000/docs |
| Health | http://127.0.0.1:8000/api/health |

Comprueba que `GET /api/health` muestre `gemini_configured: true`.

---

## Demo rápido de G5 (conocimiento vivo)

1. En `/admin`, sube un TXT/PDF con una frase inventada única (ej. “protocolo ZETA-42”).
2. Espera **Procesado y disponible**.
3. En `/call`, inicia llamada y pregunta por ese protocolo → debe citarlo (Ver referencias).
4. Elimina el documento en `/admin`.
5. Repite la pregunta → no debe citar ZETA-42; declara límite / ofrece escalar.

---

## Flujo de demo clínica sugerido

1. Procedimiento: Apendicectomía · nombre libre.
2. Caso leve: dolor 2, caminando → verde/amarillo, cuidados + pregunta nueva.
3. Caso rojo: “tengo 39 grados de fiebre” → **rojo** + escalamiento.
4. Finalizar → `/historial` con conversación, alerta y referencias.

---

## Modelo declarado (G3)

- **Familia:** Google Gemini, gama Flash  
- **Variable:** `GEMINI_MODEL` (default recomendado: `gemini-2.0-flash-lite`)  
- **Por qué:** familia permitida por el artefacto, contexto amplio para guías, free tier, una sola API key, latencia razonable para demo de voz.

Si el ID falla (404) o hay cuota (429), el agente prueba otros Flash (`gemini-flash-lite-latest`, `gemini-2.0-flash`, etc.). Guía: [`docs/setup-gemini.md`](docs/setup-gemini.md).

---

## Dataset del reto (ParticipantArtifacts)

| Archivo | Uso en PostOp Care |
|---|---|
| `dataset/textos/` (PDFs) | Corpus RAG (seed + `/admin`) |
| `dataset_final.xlsx` | Casos/diálogos + `label_ground_truth` (eval offline) |
| `trayectorias_postop_silver.xlsx` | Contexto / eval — no se inyecta como verdad al LLM en la llamada |
| `perfiles_clinicos_*.xlsx` + `perfiles_pacientes_co.xlsx` | Procedimientos del select + perfiles para eval |

```powershell
cd backend
.\.venv\Scripts\python scripts\seed_corpus.py
.\.venv\Scripts\python scripts\eval_triage.py
```

Última corrida local de referencia (capa1_limpia): recall rojo ≈ **83% (10/12)**; los 2 fallos son relatos muy evasivos sin cifra de fiebre ni secreción explícita (en llamada el LLM debe indagar; el harness solo usa heurísticas).

API útiles: `GET /api/dataset/procedures`, `GET /api/dataset/stats`, `GET /api/dataset/patients`.

---

## Métricas (obligatorias en README)

Medidas vía `GET /api/metrics` (logs en `backend/data/metrics/events.json`):

```text
Latencia respuesta (turno → reply agente, sin TTS): P50 ≈ 1432 ms · P95 ≈ 3483 ms
Tokens promedio / turno: in ≈ 1292 · out ≈ 205
Invocaciones LLM / turno: 1 (con API key y cuota disponible)
Consultas RAG / evento: 1
Eventos registrados (muestra de entrega): 5 · llamadas: 2
Costo estimado / llamada (extrapolado $0.10/1M in + $0.40/1M out): ≈ US$ 0.0005
Costo real en free tier AI Studio: US$ 0
```

Fuente: `GET /api/metrics` / panel `/historial`. La latencia de voz extremo-a-extremo (fin de habla → inicio de audio) suma STT + LLM + TTS y suele ser mayor que el P50 del turno.

---

## Pruebas

```powershell
cd backend
.\.venv\Scripts\pytest -q
.\.venv\Scripts\python scripts\eval_triage.py
```

Incluye: decision engine, PII, RAG alta→retrieval→baja, escenarios clínicos, dataset xlsx, anti-repetición de preguntas en fallback.

---

## Estructura del repo

```text
Challenge-TechSphere/
  backend/          FastAPI + RAG + agente + TTS + dataset
  frontend/         React (/call · /admin · /historial)
  data/             Corpus / dataset (local o junction)
  docs/             Arquitectura + informe final
  scripts/          Arranque Windows/Linux
```

---

## Seguridad / compliance (síntesis)

- Sin login empresarial (fuera de alcance del reto)
- `.env` fuera de git; PII enmascarada en logs (`mask_pii`)
- El agente no inventa dosis/medicamentos; sin evidencia RAG → declara límite / escala
- Aviso visible de datos sintéticos en la UI

---

## Documentación en `docs/`

| Documento | Contenido |
|---|---|
| [`docs/arquitectura.md`](docs/arquitectura.md) | Diagrama y flujo de decisión (Mermaid) |
| [`docs/informe-final.md`](docs/informe-final.md) | Informe final + capturas |
| [`docs/capturas/`](docs/capturas/) | Evidencia visual del demo |
| [`docs/setup-gemini.md`](docs/setup-gemini.md) | Cómo obtener `GOOGLE_API_KEY` |
| Video | [Google Drive](https://drive.google.com/drive/folders/1mVbegDRf-KAdfi5Z2rJQiof30KVWQOBl?usp=sharing) |

---

## Licencia

MIT — ver [`LICENSE`](LICENSE). Los PDF clínicos conservan derechos de sus autores y se usan solo como material del reto.
