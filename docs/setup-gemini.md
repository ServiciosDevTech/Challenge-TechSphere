# Etapa 2 — Activar Gemini Flash

El agente ya está cableado. Sin key corre en **modo plantilla** (fallback). Con key usa **Gemini Flash** (familia permitida G3).

## 1. Crear la API key

1. Entra a [Google AI Studio — API keys](https://aistudio.google.com/apikey)
2. Inicia sesión con tu cuenta Google
3. **Create API key**
4. Copia la key (no la subas a Git ni al chat si puedes evitarlo)

## 2. Configurar el proyecto

Edita el archivo `.env` en la raíz de `Challenge-TechSphere`:

```env
GOOGLE_API_KEY=pega_aqui_tu_key
GEMINI_MODEL=gemini-flash-latest
```

> Algunos IDs (`gemini-2.5-flash`, `gemini-1.5-flash`) pueden devolver 404 para cuentas nuevas. Usa `gemini-flash-latest` u otro Flash vigente en AI Studio. El agente además prueba automáticamente modelos Flash de respaldo si el configurado falla.

## 3. Reiniciar el backend

Detén `start-backend.bat` (Ctrl+C) y vuelve a lanzarlo:

```powershell
.\scripts\start-backend.bat
```

En `/call` deberías ver el modelo activo (sin el aviso amarillo de “Gemini aún no está configurado”).

## 4. Probar

1. Sube o confirma `data/samples/protocolo_zeta42.txt` en `/admin`
2. En `/call`, pregunta: “¿qué dice el protocolo ZETA-42?”
3. Luego di: “me está faltando el aire” → debe pasar a **ROJO** y escalar (no repetir ZETA-42)
4. Sin documentos: si ofrece escalar y respondes “sí, escálalo”, debe escalar de verdad

## 5. Commit sugerido (cuando pase tu prueba)

```text
feat: enable Gemini Flash clinical agent with live grounding
```
