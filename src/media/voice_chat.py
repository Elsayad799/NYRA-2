from __future__ import annotations
import asyncio, logging, os
from pathlib import Path

log = logging.getLogger("VoiceChat")

class VoiceChatEngine:
    """Optional Linux Voice Chat bridge based on Pyrogram + PyTgCalls.

    NYRA's normal Telegram Bot API path stays independent. This bridge is only
    activated when API_ID/API_HASH are supplied and the optional dependencies
    are installed. It never tries to bypass Telegram/YouTube protections.
    """
    def __init__(self):
        self.enabled = os.getenv("NYRA_VOICE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.api_id = os.getenv("TELEGRAM_API_ID", "").strip()
        self.api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
        self.session = os.getenv("TELEGRAM_VC_SESSION", "nyra_voice_chat").strip()
        self._app = None
        self._calls = None
        self.available = False
        self._started = False
        self.reason = "disabled"
        if self.enabled:
            self._load()

    def _load(self):
        if not (self.api_id and self.api_hash):
            self.reason = "TELEGRAM_API_ID and TELEGRAM_API_HASH are required"
            return
        try:
            from pyrogram import Client
            from pytgcalls import PyTgCalls
        except Exception as exc:
            self.reason = f"optional voice-chat dependencies unavailable: {exc}"
            return
        try:
            # Bot token may be used when Telegram accepts the bot for the target
            # call; otherwise a normal MTProto user session can be configured.
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
            kwargs = {"name": self.session, "api_id": int(self.api_id), "api_hash": self.api_hash}
            if bot_token:
                kwargs["bot_token"] = bot_token
            self._app = Client(**kwargs)
            self._calls = PyTgCalls(self._app)
            self.available = True
            self.reason = "ready"
        except Exception as exc:
            self.reason = str(exc)
            log.exception("voice chat initialization failed")

    def status(self) -> str:
        return "READY" if self.available else f"OFF ({self.reason})"

    async def start(self):
        if not self.available:
            raise RuntimeError(self.reason)
        if self._started:
            return
        await self._app.start()
        self._calls.start()
        self._started = True

    async def stop(self):
        if self._calls:
            try:
                self._calls.stop()
            except Exception:
                pass
        if self._app:
            try:
                await self._app.stop()
            except Exception:
                pass
        self._started = False

    async def play_file(self, chat_id: int, path: str | Path):
        if not self.available:
            raise RuntimeError(self.reason)
        from pytgcalls.types import MediaStream
        # The exact PyTgCalls media API is kept isolated here so Android/normal
        # Bot API operation never imports or depends on native tgcalls.
        await self._calls.play(int(chat_id), MediaStream(str(path)))

    async def stop_call(self, chat_id: int):
        if self.available:
            self._calls.leave_call(int(chat_id))
