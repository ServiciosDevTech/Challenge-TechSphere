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

## Semilla rápida

```powershell
cd backend
.\.venv\Scripts\python scripts\seed_corpus.py --limit 5
```

La consola `/admin` también permite subir documentos uno a uno (requisito G5).
