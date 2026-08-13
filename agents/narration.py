"""Spoken verdict narration via the Gemini Live API (native audio, GA on Vertex AI in
us-central1). Live API is normally a duplex mic-in/speaker-out session; used here in a
much narrower text-in/audio-out shape — no microphone, no back-and-forth — because the
verdict text is already decided by the crew pipeline (agents/supervisor/orchestrate.py)
and this module's only job is to have the Supervisor's call spoken aloud the way a real
First AD would call it on set. Best-effort: narration failing must never break a take.
"""
from __future__ import annotations

import io
import logging
import wave

from google import genai
from google.genai import types

from agents.config import config

_log = logging.getLogger(__name__)

_SAMPLE_RATE_HZ = 24000
_SAMPLE_WIDTH_BYTES = 2  # 16-bit PCM, per the Live API's fixed output format
_CHANNELS = 1

_SYSTEM_INSTRUCTION = """\
You are the on-set Supervisor on an LED-volume virtual-production stage, calling a
take the moment its verdict lands. Speak the given verdict aloud exactly like a real
film-set call: brief, direct, no filler, the way a supervisor actually talks over a
radio — not a narrator reading a report. State the call, then the one-line reason.
Do not add anything not present in the given text.
"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=config.google_cloud_project,
            location=config.google_cloud_location,
        )
    return _client


def _pcm_to_wav(pcm_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(_CHANNELS)
        wav_file.setsampwidth(_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(_SAMPLE_RATE_HZ)
        wav_file.writeframes(pcm_bytes)
    return buf.getvalue()


async def synthesize_verdict_audio(line_to_speak: str) -> bytes | None:
    """Returns a WAV file (browser-playable) of the verdict spoken aloud, or None if
    the Live API call fails for any reason — narration is a demo enhancement, not a
    dependency the take pipeline should ever fail on."""
    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(parts=[types.Part(text=_SYSTEM_INSTRUCTION)]),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.narrator_voice)
            )
        ),
    )

    try:
        pcm_chunks: list[bytes] = []
        client = _get_client()
        async with client.aio.live.connect(model=config.gemini_live_model, config=live_config) as session:
            await session.send_client_content(
                turns=types.Content(role="user", parts=[types.Part(text=line_to_speak)]),
                turn_complete=True,
            )
            async for message in session.receive():
                content = message.server_content
                if content and content.model_turn:
                    for part in content.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            pcm_chunks.append(part.inline_data.data)
                if content and content.turn_complete:
                    break

        if not pcm_chunks:
            _log.warning("Live API narration returned no audio for: %r", line_to_speak[:80])
            return None
        return _pcm_to_wav(b"".join(pcm_chunks))
    except Exception:
        _log.exception("Live API narration failed for: %r", line_to_speak[:80])
        return None
