from __future__ import annotations

"""NYRA legacy VoiceLabs adapter.

Kept for compatibility with older NYRA installations. It is no longer the
default voice path because the external activation flow is unreliable.
"""

import importlib.util
import logging
import os
import threading
from pathlib import Path
from urllib.parse import urljoin

import requests

log = logging.getLogger("NYRA.VoiceClone")


def clean_for_speech(text: str) -> str:
    """Remove non-spoken role-play markup before synthesis."""
    text = str(text or "")
    import re
    text = re.sub(r"\*[^*\n]{1,240}\*", " ", text)
    text = re.sub(r"_[^_\n]{1,240}_", " ", text)
    text = re.sub(r"\[[^\]\n]{1,240}\]", " ", text)
    text = re.sub(r"\(([^\)\n]{1,240})\)", " ", text)
    text = re.sub(
        r"<(?:action|emotion|reaction|stage)[^>]*>.*?</(?:action|emotion|reaction|stage)>",
        " ", text, flags=re.I | re.S,
    )
    return re.sub(r"\s{2,}", " ", text).strip()


_ENGINE = None
_ENGINE_ERROR = None
_ENGINE_LOCK = threading.RLock()


def _load_engine():
    global _ENGINE, _ENGINE_ERROR
    with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE
        if _ENGINE_ERROR is not None:
            raise _ENGINE_ERROR

        engine_path = Path(__file__).resolve().parents[2] / "integrations" / "nyra_voice_clone" / "original_clone_engine.py"
        if not engine_path.exists():
            raise FileNotFoundError(f"Original NYRA voice engine not found: {engine_path}")

        try:
            spec = importlib.util.spec_from_file_location("nyra_original_clone_engine", engine_path)
            if spec is None or spec.loader is None:
                raise ImportError("Could not load original voice engine")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not callable(getattr(module, "synthesize_text_to_audio", None)):
                raise ImportError("Original voice engine does not expose synthesize_text_to_audio")
            _ENGINE = module
            return module
        except Exception as exc:
            _ENGINE_ERROR = exc
            raise


class NyraVoiceClone:
    """Thin NYRA-facing wrapper around the supplied standalone clone bot."""

    def __init__(self, reference_audio: str | None = None, session_file: str | None = None):
        self.reference_audio = Path(
            reference_audio
            or os.getenv("NYRA_VOICE_REFERENCE", "assets/voice/nyra_voice.mp3")
        )
        if not self.reference_audio.is_absolute():
            self.reference_audio = Path.cwd() / self.reference_audio
        self.session_file = session_file or os.getenv("NYRA_VOICE_SESSION_FILE", "sessions.json")
        self._lock = threading.RLock()

    def available(self) -> bool:
        return self.reference_audio.is_file()

    def synthesize(self, text: str) -> bytes:
        clean = clean_for_speech(text)
        if not clean:
            raise ValueError("No speakable text remains after removing actions")
        if not self.reference_audio.is_file():
            raise FileNotFoundError(
                f"NYRA voice reference not found: {self.reference_audio}. "
                "Put the authorized reference recording at this path."
            )

        with self._lock:
            engine = _load_engine()
            # The original standalone function is called unchanged.  NYRA only
            # supplies generated text + the fixed NYRA reference recording.
            result = engine.synthesize_text_to_audio(clean, str(self.reference_audio))
            if not result:
                raise RuntimeError("Original voice engine did not return an audio URL")

            base_url = str(getattr(engine, "base_url", "https://voiceslab.io")).rstrip("/")
            audio_url = urljoin(base_url + "/", str(result))
            response = requests.get(audio_url, timeout=120)
            response.raise_for_status()
            if not response.content:
                raise RuntimeError("Voice engine returned empty audio")
            return response.content
