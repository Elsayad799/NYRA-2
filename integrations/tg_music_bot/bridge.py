from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("NYRA.TgMusicBridge")


@dataclass
class MusicRequest:
    chat_id: int
    user_id: int
    query: str


class TgMusicBridge:
    """Connect NYRA to the supplied youtube-music-download-bot.

    The supplied project is copied intact under integrations/youtube_music_download_bot.
    Nothing inside that project is edited by this bridge and it is never started as a
    second Telegram bot. NYRA keeps its single Bot API instance and calls the original
    downloader service directly.
    """

    COMMANDS = ("play", "queue", "clear", "skip", "pause", "resume", "stop",
                "now", "volume", "repeat", "leave", "help")

    def __init__(self, music, voice_chat=None):
        self.music = music
        self.voice_chat = voice_chat
        self._original_youtube = None
        self._original_load_error: Exception | None = None
        self._load_original_tool()

    def _load_original_tool(self) -> None:
        """Load the original downloader package without starting its bot."""
        root = Path(__file__).resolve().parent.parent / "youtube_music_download_bot"
        src = root / "src"
        if not src.exists():
            self._original_load_error = FileNotFoundError(f"missing supplied music tool: {src}")
            return
        src_s = str(src)
        if src_s not in sys.path:
            sys.path.insert(0, src_s)
        try:
            from tgbot.services.youtube import youtube as original_youtube
            self._original_youtube = original_youtube
            log.info("Original youtube-music-download-bot downloader loaded")
        except BaseException as exc:
            # The original project exits during construction if ffmpeg is unavailable.
            # Do not let that take down NYRA; the existing NYRA music fallback remains.
            self._original_load_error = exc if isinstance(exc, Exception) else RuntimeError(str(exc))
            log.warning("Original music downloader unavailable; NYRA fallback remains active: %s", exc)

    def original_available(self) -> bool:
        return self._original_youtube is not None

    async def original_search(self, query: str, lang_code: str = "en") -> list[dict[str, Any]]:
        """Search using the supplied tool's original YouTube service."""
        if not self._original_youtube:
            return []
        rows = await self._original_youtube.search_videos(query, lang_code)
        out: list[dict[str, Any]] = []
        for row in rows or []:
            out.append({
                "title": getattr(row, "description", "Unknown title"),
                "url": getattr(row, "url", ""),
                "source": "youtube-music-download-bot",
            })
        return out

    async def original_download(self, url: str) -> Path | None:
        """Download using the supplied tool's original YouTube implementation."""
        if not self._original_youtube:
            return None
        path = await self._original_youtube.download_audio(url)
        return Path(path) if path else None

    def download_original_sync(self, url: str) -> Path | None:
        """Synchronous wrapper for NYRA's existing worker/thread model."""
        try:
            return asyncio.run(self.original_download(url))
        except RuntimeError as exc:
            # If called from an already-running event loop, execute in a helper thread.
            if "cannot be called from a running event loop" not in str(exc).lower():
                raise
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(self.original_download(url))).result()

    def is_admin(self, user_id: int, admin_ids) -> bool:
        ids = set(int(x) for x in (admin_ids or []) if str(x).lstrip("-").isdigit())
        return not ids or int(user_id) in ids

    def help_text(self) -> str:
        return (
            "🎵 **موزيك NYRA**\n\n"
            "/play <اسم أو رابط> — تشغيل/إرسال الأغنية\n"
            "/queue — عرض القائمة\n"
            "/clear — مسح القائمة (أدمن)\n"
            "/skip — تخطي الحالي\n"
            "/pause — إيقاف مؤقت\n"
            "/resume — استكمال\n"
            "/stop — إيقاف\n"
            "/now — الحالي\n"
            "/volume <0-200> — مستوى الصوت\n"
            "/repeat <off|one|all> — التكرار\n"
            "/leave — الخروج من المكالمة (أدمن)"
        )

    def queue_text(self, chat_id: int) -> str:
        current = self.music.current.get(int(chat_id))
        rows = self.music.queue_peek(int(chat_id))
        out = []
        if current:
            out.append(f"▶️ الآن: **{current.get('title','Unknown')}**")
        if rows:
            out.append("\n📋 **القائمة:**")
            for i, item in enumerate(rows[:20], 1):
                out.append(f"{i}. {item.get('title','Unknown')}")
            if len(rows) > 20:
                out.append(f"… و{len(rows)-20} كمان")
        return "\n".join(out) if out else "📭 القائمة فاضية."

    def set_repeat(self, chat_id: int, mode: str):
        return self.music.set_repeat(chat_id, mode)

    def set_volume(self, chat_id: int, value: int):
        return self.music.set_volume(chat_id, value)

    def clear(self, chat_id: int):
        self.music.clear(chat_id)

    def status(self, chat_id: int) -> dict:
        current = self.music.current.get(int(chat_id))
        return {
            "current": current,
            "queue": self.music.queue_peek(int(chat_id)),
            "repeat": self.music.repeat.get(int(chat_id), "off"),
            "volume": self.music.volume.get(int(chat_id), 100),
            "voice_chat": self.voice_chat.status() if self.voice_chat else "OFF",
            "original_downloader": "READY" if self.original_available() else "OFF",
        }
