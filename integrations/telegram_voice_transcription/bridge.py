from __future__ import annotations

from src.media.voice import VoiceEngine


class TelegramVoiceTranscriptionBridge:
    """Adapt Telegram voice bytes to NYRA's normal text/event pipeline.

    This is intentionally a bridge, not a second Telegram bot. It follows the
    useful transcription behavior of vgvr0/Telegram-Bot-Voice-Transcription
    (Telegram voice -> SpeechRecognition/Google text) while delegating decoding,
    fallback STT, and temporary-file cleanup to NYRA's existing VoiceEngine.
    """

    SOURCE = "telegram_voice_transcription"

    def __init__(self, voice_engine: VoiceEngine | None = None):
        self.voice_engine = voice_engine or VoiceEngine()

    def transcribe(self, telegram_voice_bytes: bytes, language: str | None = None) -> str:
        if not telegram_voice_bytes:
            raise ValueError("empty Telegram voice payload")
        return self.voice_engine.transcribe(
            telegram_voice_bytes,
            language=language or self.voice_engine.language,
        ).strip()
