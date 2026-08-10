# Datos del reto

> **Importante:** el corpus PDF/Excel **no se versiona en Git** (nombres demasiado largos en Windows y peso excesivo). Solo se sube `data/samples/` y este README.

Para reproducibilidad (compuerta G2), este proyecto espera el corpus clínico en:

- `data/textos/` — PDFs por escenario
- `data/dataset/` — Excel del reto (opcional para demos/evaluación)

## Opción A — junction/symlink (desarrollo local)

Si tienes `ParticipantArtifacts-main` al lado de este repo:

```powershell
# Windows
cmd /c mklink /J data\textos "..\ParticipantArtifacts-main\dataset\textos"
cmd /c mklink /J data\dataset "..\ParticipantArtifacts-main\dataset"
```

```bash
# macOS / Linux
mkdir -p data
ln -s ../ParticipantArtifacts-main/dataset/textos data/textos
ln -s ../ParticipantArtifacts-main/dataset data/dataset
```

## Opción B — copiar

Copia `ParticipantArtifacts-main/dataset/textos` a `data/textos`.

## Semilla de corpus (RAG)

```powershell
cd backend
# Prioritarios de los 5 escenarios (recomendado)
.\.venv\Scripts\python scripts\seed_corpus.py
# Solo apendicectomía (más rápido)
.\.venv\Scripts\python scripts\seed_corpus.py --appendicitis-only
```

## Excel → llamada y evaluación

- `GET /api/dataset/patients` — 40 pacientes + casos 1/3/7/14
- `/call` — selector de paciente/caso; el agente recibe nombre/procedimiento/día (sin spoilear síntomas)
- `scripts/eval_triage.py` — Decision Engine vs `label_ground_truth`

La consola `/admin` también permite subir documentos uno a uno (requisito G5).
