from __future__ import annotations

"""Optional local reference-voice synthesis for NYRA.

This module is deliberately optional. It uses an installed local TTS engine
(when available) and a fixed, authorized NYRA reference recording. No external
account/session/cookie flow is used here.
"""

import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger("NYRA.LocalVoiceClone")


class LocalReferenceVoice:
    """XTTS-v2 adapter loaded only when the optional `TTS` package is installed."""

    def __init__(self, reference_audio: str | None = None):
        ref = reference_audio or os.getenv("NYRA_VOICE_REFERENCE", "assets/voice/nyra_voice.mp3")
        self.reference_audio = Path(ref)
        if not self.reference_audio.is_absolute():
            self.reference_audio = Path.cwd() / self.reference_audio
        self.model_name = os.getenv(
            "NYRA_LOCAL_VOICE_MODEL",
            "tts_models/multilingual/multi-dataset/xtts_v2",
        ).strip()
        self._tts = None
        self._load_error: Exception | None = None

    def available(self) -> bool:
        return self.reference_audio.is_file()

    def _load(self):
        if self._tts is not None:
            return self._tts
        if self._load_error is not None:
            raise self._load_error
        if not self.available():
            raise FileNotFoundError(f"NYRA reference voice not found: {self.reference_audio}")
        try:
            from TTS.api import TTS
        except Exception as exc:
            self._load_error = RuntimeError(
                "Optional local voice clone is not installed. Install the optional "
                "NYRA local-voice requirements to enable it."
            )
            raise self._load_error from exc
        try:
            gpu = os.getenv("NYRA_LOCAL_VOICE_GPU", "0").strip().lower() in ("1", "true", "yes", "on")
            self._tts = TTS(model_name=self.model_name, progress_bar=False, gpu=gpu)
            return self._tts
        except Exception as exc:
            self._load_error = exc
            raise

    def synthesize(self, text: str, language: str = "ar") -> bytes:
        text = str(text or "").strip()
        if not text:
            raise ValueError("empty text")
        tts = self._load()
        language = (language or "ar").split("-")[0]
        with tempfile.TemporaryDirectory(prefix="nyra_local_voice_") as td:
            output = Path(td) / "nyra.wav"
            kwargs = {
                "text": text,
                "speaker_wav": str(self.reference_audio),
                "language": language,
                "file_path": str(output),
            }
            tts.tts_to_file(**kwargs)
            if not output.is_file() or output.stat().st_size < 100:
                raise RuntimeError("local voice clone returned empty audio")
            return output.read_bytes()
