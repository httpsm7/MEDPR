"""
integrations/elevenlabs.py
───────────────────────────
Text-to-Speech via ElevenLabs.
Fallback: pyttsx3 (offline, no API key needed).
"""

import requests
from pathlib import Path
from core.config import ELEVENLABS_KEY, VOICES_DIR, log

# Voice presets
VOICES = {
    "professional":   "AZnzlk1XvdvUeBnXmlld",   # Domi
    "authoritative":  "21m00Tcm4TlvDq8ikWAM",   # Rachel
    "energetic":      "ErXwobaYiN019PkySvjV",    # Antoni
    "conversational": "MF3mGyEYCl7XYWbV9V6O",   # Elli
}


def _offline_tts(text: str, dest: Path) -> str:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, str(dest))
        engine.runAndWait()
        log(f"[TTS] Offline pyttsx3 → {dest.name}")
        return str(dest)
    except Exception as e:
        log(f"[TTS] pyttsx3 fallback failed: {e}")
        return ""


def generate(text: str, style: str = "professional", filename: str = "voice") -> str:
    """
    Generate MP3 voiceover. Returns local file path or empty string.
    """
    key      = ELEVENLABS_KEY()
    voice_id = VOICES.get(style, VOICES["professional"])
    dest     = VOICES_DIR / f"{filename}.mp3"

    if not key:
        log("[TTS] No ElevenLabs key — using offline TTS.")
        return _offline_tts(text, dest.with_suffix(".wav"))

    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key":   key,
                "Content-Type": "application/json",
            },
            json={
                "text":             text,
                "model_id":         "eleven_monolingual_v1",
                "voice_settings":   {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=60,
        )
        if r.ok:
            dest.write_bytes(r.content)
            log(f"[TTS] ElevenLabs generated → {dest.name}")
            return str(dest)
        else:
            log(f"[TTS] ElevenLabs error {r.status_code} — trying offline.")
            return _offline_tts(text, dest.with_suffix(".wav"))
    except Exception as e:
        log(f"[TTS] Exception: {e} — trying offline.")
        return _offline_tts(text, dest.with_suffix(".wav"))
