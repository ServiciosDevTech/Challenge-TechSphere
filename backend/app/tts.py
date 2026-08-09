from __future__ import annotations

import io
import logging

import edge_tts

from app.config import get_settings

logger = logging.getLogger(__name__)

# Voces masculinas neurales (Colombia primero)
FALLBACK_VOICES = (
    "es-CO-GonzaloNeural",
    "es-MX-JorgeNeural",
    "es-US-AlonsoNeural",
    "es-PE-AlexNeural",
    "es-ES-AlvaroNeural",
)


async def synthesize_speech(text: str, voice: str | None = None) -> bytes:
    settings = get_settings()
    candidates: list[str] = []
    preferred = voice or settings.tts_voice
    candidates.append(preferred)
    for v in FALLBACK_VOICES:
        if v not in candidates:
            candidates.append(v)

    # Ritmo conversacional: un poco más lento, sin exceso de “robot”
    rate = settings.tts_rate or "-6%"
    pitch = settings.tts_pitch or "-1Hz"

    last_error: Exception | None = None
    for selected in candidates:
        try:
            communicate = edge_tts.Communicate(
                text,
                selected,
                rate=rate,
                pitch=pitch,
            )
            buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])
            audio = buffer.getvalue()
            if not audio:
                raise RuntimeError(f"TTS vacío con voz {selected}")
            logger.info("TTS ok voice=%s bytes=%s", selected, len(audio))
            return audio
        except Exception as exc:  # noqa: BLE001
            logger.warning("TTS falló con %s: %s", selected, exc)
            last_error = exc

    raise RuntimeError(f"No se pudo sintetizar audio: {last_error}")
