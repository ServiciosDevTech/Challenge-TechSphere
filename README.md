# PostOp Care — Tech Sphere Challenge 2026

Agente de voz con IA para **seguimiento postoperatorio** en español colombiano.

El paciente habla desde el navegador. El agente consulta una base de conocimiento clínica (**RAG dinámico**), responde solo con evidencia documental, y decide si la evolución es esperada o si debe **escalar a un humano**.

> Datos sintéticos. No es un dispositivo médico ni un sistema de atención real.

## Compuertas que cubre esta entrega

| Compuerta | Cómo se cumple |
|---|---|
| G1 Entregables | Repo + `docs/` (arquitectura, informe, guion de video) |
| G2 ≤15 min | Scripts de arranque + README |
| G3 Modelo permitido | **Google Gemini Flash** (`GEMINI_MODEL`, free tier AI Studio) |
| G4 Voz en navegador | `/call` con micrófono (Web Speech API) + TTS `edge-tts` |
| G5 Conocimiento vivo | `/admin` subir/eliminar documentos; efecto inmediato en el agente |

## Arquitectura (resumen)

```text
Paciente (voz) → React /call → FastAPI → RAG Chroma + Gemini Flash → Decisión → Paciente / Escalamiento
                     ↑
              React /admin (alta/baja de PDFs en caliente)
```

Detalle: [`docs/arquitectura.md`](docs/arquitectura.md)

## Stack

| Pieza | Tecnología |
|---|---|
| LLM | Google Gemini Flash (familia permitida) |
| Backend | Python 3.11+ / FastAPI |
| Frontend | React + Vite + TypeScript |
| RAG | ChromaDB + `paraphrase-multilingual-MiniLM-L12-v2` |
| STT | Web Speech API (`es-CO`) |
| TTS | edge-tts (`es-CO-GonzaloNeural`) · agente **Beto** |

## Requisitos previos

- Python **3.11+** (probado con 3.13)
- Node.js **20+**
- Cuenta gratuita en [Google AI Studio](https://aistudio.google.com/apikey) → `GOOGLE_API_KEY`
- Micrófono y Chrome/Edge recomendados para voz
- Corpus clínico del reto en `data/textos` (ver [`data/README.md`](data/README.md))

## Arranque en ≤15 minutos

### 1. Clonar e instalar

```powershell
git clone https://github.com/ServiciosDevTech/Challenge-TechSphere.git
cd Challenge-TechSphere
copy .env.example .env
# Edita .env y pega GOOGLE_API_KEY=...

cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
cd ..\frontend
npm install
```

### 2. Datos clínicos

```powershell
# Si tienes ParticipantArtifacts-main junto a este repo:
cmd /c mklink /J data\textos "..\ParticipantArtifacts-main\dataset\textos"
```

O copia la carpeta `textos` del artefacto a `data/textos`.

### 3. (Opcional) Sembrar corpus

```powershell
cd backend
.\.venv\Scripts\python scripts\seed_corpus.py --limit 6
```

Esto indexa `data/samples/*.txt` y guías prioritarias de apendicectomía (plan de cuidado, instrucciones postoperatorias, etc.) si `data/textos` está disponible.

### 4. Levantar

Terminal A:

```powershell
.\scripts\start-backend.bat
```

Terminal B:

```powershell
.\scripts\start-frontend.bat
```

Abre:

- Llamada: http://127.0.0.1:5173/call
- Consola: http://127.0.0.1:5173/admin
- API docs: http://127.0.0.1:8000/docs

## Demo rápido de G5 (conocimiento vivo)

1. En `/admin`, sube un TXT/PDF de prueba con una frase inventada única (ej. “protocolo ZETA-42”).
2. En `/call`, pregunta por ese protocolo: el agente debe citarlo.
3. Elimina el documento en `/admin`.
4. Repite la pregunta: el agente debe declarar que no tiene esa información / no citar ZETA-42.

## Modelo declarado (G3)

- **Familia:** Google Gemini, gama Flash
- **Variable:** `GEMINI_MODEL` (default `gemini-flash-latest`)
- **Por qué:** familia permitida por el artefacto, ventana de contexto amplia para guías clínicas, free tier suficiente para demo, una sola API key.

Si el snapshot deja de existir, el agente prueba automáticamente otros Flash (`gemini-3.1-flash-lite-preview`, `gemini-2.0-flash-lite`, etc.). Guía: [`docs/setup-gemini.md`](docs/setup-gemini.md).

## Métricas (obligatorias en README)

Se exponen en `GET /api/metrics` y en `/historial`. Tras una sesión local de desarrollo:

| Métrica | Cómo se mide |
|---|---|
| Latencia P50 / P95 | Desde fin de turno de paciente hasta respuesta del agente (`total_ms` en logs) |
| Tokens in/out | `usage_metadata` de Gemini por turno |
| Invocaciones LLM / consultas RAG | Contadores por evento |
| Costo estimado / llamada | Extrapolación a precios orientativos de producción; en free tier el costo real es **US$0** |

> Ejecuta al menos una llamada real y consulta `/historial` o `GET /api/metrics` para pegar números verificables antes de la entrega. No reportes cifras que no estén en tus logs.

Ejemplo de formato (rellenar tras tu smoke test):

```text
Latencia respuesta (paciente deja de hablar → audio agente): P50 ≈ _ ms · P95 ≈ _ ms
Tokens promedio / turno: in _ · out _
Invocaciones LLM / turno: 1
Consultas RAG / llamada: ≈ N turnos
Costo estimado / llamada (extrapolado): US$ _
```

## Pruebas

```powershell
cd backend
.\.venv\Scripts\pytest -q
```

Incluye:

- Unitarias del motor de decisión y PII
- Integración RAG: alta → retrieval → baja → olvido
- Golden triage (verde / amarillo / rojo)

## Estructura

```text
Challenge-TechSphere/
  backend/          FastAPI + RAG + agente + TTS
  frontend/         React ( /call · /admin · /historial )
  data/             Corpus clínico (local)
  docs/             Arquitectura, informe, video
  scripts/          Arranque Windows/Linux
```

## Seguridad / compliance (síntesis)

- Sin login empresarial (fuera de alcance del reto)
- `.env` fuera de git; PII enmascarada en logs (`mask_pii`)
- El agente no inventa dosis/medicamentos; sin evidencia RAG → “no sé” / escalar
- Aviso visible de datos sintéticos en la UI

## Entregables adicionales

- Diagrama y decisiones: [`docs/arquitectura.md`](docs/arquitectura.md)
- Informe: [`docs/informe-final.md`](docs/informe-final.md)
- Guion de video: [`docs/guion-video.md`](docs/guion-video.md)

## Licencia

MIT — ver [`LICENSE`](LICENSE). Los PDF clínicos conservan derechos de sus autores y se usan solo como material del reto.
