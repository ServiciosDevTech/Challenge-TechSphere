# Configurar Gemini Flash (G3)

El agente ya está cableado. Sin `GOOGLE_API_KEY` corre en **modo plantilla** (fallback hablable). Con key usa **Gemini Flash** (familia permitida).

## 1. Crear la API key

1. Entra a [Google AI Studio — API keys](https://aistudio.google.com/apikey).
2. Inicia sesión con tu cuenta Google.
3. Crea una API key y cópiala.
4. **No** la subas a Git ni la dejes en `.env.example`.

## 2. Configurar el proyecto

En la raíz del repo:

```powershell
copy .env.example .env
```

Edita `.env`:

```env
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite-preview
```

Asigna tu clave en `GOOGLE_API_KEY`. Usa un Flash **lite** vigente para menor latencia. Si el ID falla (404) o hay cuota (429), el agente prueba otros Flash automáticamente.

Si el jurado necesita una clave de evaluación, puede contactar al autor por WhatsApp o correo (datos del formulario de inscripción), como indica el README.

## 3. Reiniciar el backend

```powershell
.\scripts\start-backend.bat
```

Comprueba `GET http://127.0.0.1:8000/api/health` → `gemini_configured: true`.

## 4. Probar

1. Sube `data/samples/protocolo_zeta42.txt` (o cualquier TXT) en `/admin`.
2. En `/call`, pregunta por ese contenido → debe citarlo.
3. Relata una alarma (“me está faltando el aire” o “tengo 39 grados”) → **rojo** y escalamiento.
4. Sin evidencia en el corpus: el agente declara el límite u ofrece escalar; si aceptas, escala.
