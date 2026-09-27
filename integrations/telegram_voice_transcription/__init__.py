"""Additive bridge for Telegram voice transcription.

The upstream project is a standalone TeleBot example. NYRA reuses its
SpeechRecognition approach without creating a second bot, token, or polling
loop. Telegram download/decode and NYRA's existing STT fallbacks remain in
VoiceEngine.
"""
from .bridge import TelegramVoiceTranscriptionBridge

__all__ = ["TelegramVoiceTranscriptionBridge"]
