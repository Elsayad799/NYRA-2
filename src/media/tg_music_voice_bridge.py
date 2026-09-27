from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger("NYRA.TgMusicVoiceBridge")


class TgMusicVoiceBridge:
    """HTTP adapter for the supplied TgMusicBot/NTgCalls engine.

    This adapter is additive: the original Go project remains intact and is
    run as a local sidecar when the host provides Go + its native NTgCalls
    dependencies. NYRA falls back to its existing Python voice engine when the
    sidecar is unavailable.
    """

    def __init__(self):
        self.base_url = os.getenv("NYRA_TG_VOICE_BRIDGE_URL", "http://127.0.0.1:8765").rstrip("/")
        self.token = os.getenv("NYRA_TG_VOICE_BRIDGE_TOKEN", "").strip()
        self.timeout = float(os.getenv("NYRA_TG_VOICE_BRIDGE_TIMEOUT", "8"))

    @property
    def configured(self) -> bool:
        return os.getenv("NYRA_TG_VOICE_BRIDGE_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}

    def _request(self, endpoint: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}/{endpoint.lstrip('/')}", data=data, method="POST" if data else "GET")
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("X-NYRA-Bridge-Token", self.token)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
        if not body.get("ok"):
            raise RuntimeError(body.get("error") or "TgMusicBot bridge request failed")
        return body

    def available(self) -> bool:
        if not self.configured:
            return False
        try:
            self._request("health")
            return True
        except Exception:
            return False

    def play(self, chat_id: int, path: str | Path, video: bool = False) -> None:
        self._request("play", {"chat_id": int(chat_id), "path": str(path), "video": bool(video)})

    def pause(self, chat_id: int) -> None:
        self._request("pause", {"chat_id": int(chat_id)})

    def resume(self, chat_id: int) -> None:
        self._request("resume", {"chat_id": int(chat_id)})

    def stop(self, chat_id: int) -> None:
        self._request("stop", {"chat_id": int(chat_id)})

    def mute(self, chat_id: int) -> None:
        self._request("mute", {"chat_id": int(chat_id)})

    def unmute(self, chat_id: int) -> None:
        self._request("unmute", {"chat_id": int(chat_id)})
