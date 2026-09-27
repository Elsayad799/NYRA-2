from __future__ import annotations
import asyncio
import os
import tempfile
from pathlib import Path

class ShazamEngine:
    """Identify a short Telegram audio/voice clip using ShazamIO.

    The temporary media file is deleted after recognition. No Telegram bot or
    provider token is created here.
    """
    MAX_SECONDS = 300
    MAX_BYTES = 25 * 1024 * 1024

    def _recognize_async(self, path: str):
        from shazamio import Shazam
        async def run():
            return await Shazam().recognize_song(path)
        return asyncio.run(run())

    def recognize_file(self, source_path: str) -> dict | None:
        p = Path(source_path)
        if not p.exists() or p.stat().st_size > self.MAX_BYTES:
            return None
        try:
            out = self._recognize_async(str(p))
        except Exception:
            return None
        if not out or not out.get('matches') or not out.get('track'):
            return None
        track = out['track']
        return {
            'title': track.get('title') or '',
            'artist': track.get('subtitle') or '',
            'url': track.get('url') or '',
            'cover': (track.get('images') or {}).get('coverart') or (track.get('images') or {}).get('background') or '',
            'genre': track.get('genres', {}).get('primary') if isinstance(track.get('genres'), dict) else '',
        }

    def recognize_bytes(self, payload: bytes, suffix: str = '.ogg') -> dict | None:
        if not payload or len(payload) > self.MAX_BYTES:
            return None
        fd, name = tempfile.mkstemp(prefix='nyra_shazam_', suffix=suffix)
        os.close(fd)
        try:
            Path(name).write_bytes(payload)
            return self.recognize_file(name)
        finally:
            try: os.remove(name)
            except OSError: pass
