# Datos del reto

> **Importante:** el corpus PDF/Excel **no se versiona en Git** (nombres demasiado largos en Windows y peso excesivo). Solo se sube `data/samples/` y este README.

## ¿Es obligatorio precargar PDFs?

**No.** El proyecto arranca sin `data/textos/`. Puedes subir documentos uno a uno desde **`/admin`** (eso cubre la compuerta G5).

Tener el corpus del artefacto es **opcional pero recomendado** si quieres:

- sembrar varias guías de golpe (`scripts/seed_corpus.py`),
- demos clínicas más ricas sin subir archivo por archivo,
- evaluación offline (`scripts/eval_triage.py`).

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

## Opción C — solo consola admin

1. Levanta backend y frontend (ver README raíz).
2. En http://127.0.0.1:5173/admin sube PDF/TXT.
3. En `/call` pregunta sobre ese contenido; elimínalo y verifica que el agente ya no lo use.

## Semilla de corpus (opcional)

```powershell
cd backend
.\.venv\Scripts\python scripts\seed_corpus.py
# Más rápido (solo apendicectomía):
.\.venv\Scripts\python scripts\seed_corpus.py --appendicitis-only
```

## Excel → evaluación (opcional)

Con `data/dataset/` enlazado:

- `GET /api/dataset/procedures` — procedimientos del select en `/call`
- `GET /api/dataset/stats` — conteos del bundle
- `scripts/eval_triage.py` — Decision Engine vs `label_ground_truth`
