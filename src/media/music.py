from __future__ import annotations
import json, logging, re, time, tempfile
from pathlib import Path
from collections import deque
from .youtube import YouTubeAudio

log = logging.getLogger("Music")

class MusicEngine:
    """NYRA music layer inspired by tg-music-bot, without creating a second bot.

    Keeps NYRA's Bot API + file_id cache, while adding per-chat queues, repeat
    state, source metadata and a clean boundary for an optional voice-chat layer.
    Downloads remain temporary and are removed after sending/streaming.
    """
    def __init__(self, base_dir: Path | None = None):
        self.youtube = YouTubeAudio()
        root = base_dir or Path(__file__).resolve().parents[2]
        self.path = root / "data" / "music_cache.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load()
        self.queues: dict[int, deque] = {}
        self.current: dict[int, dict | None] = {}
        self.repeat: dict[int, str] = {}
        self.volume: dict[int, int] = {}
        self.cleanup_stale_temp()

    @staticmethod
    def key(query: str) -> str:
        return re.sub(r"\s+", " ", (query or "").strip().casefold())

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def cached(self, query):
        return self.cache.get(self.key(query))

    def remember(self, query, file_id, title="", performer="", duration=0, source="telegram_cache"):
        if not file_id:
            return
        self.cache[self.key(query)] = {
            "file_id": file_id, "title": title, "performer": performer,
            "duration": duration, "source": source, "updated_at": time.time(),
        }
        self._save()

    def queue_add(self, chat_id: int, track: dict):
        q = self.queues.setdefault(int(chat_id), deque())
        q.append(dict(track))
        return len(q)

    def queue_pop(self, chat_id: int):
        q = self.queues.get(int(chat_id))
        if not q:
            return None
        item = q.popleft()
        if not q:
            self.queues.pop(int(chat_id), None)
        return item

    def queue_peek(self, chat_id: int):
        q = self.queues.get(int(chat_id), deque())
        return list(q)

    def clear(self, chat_id: int):
        self.queues.pop(int(chat_id), None)

    def set_repeat(self, chat_id: int, mode: str):
        mode = mode.lower().strip()
        if mode not in {"off", "one", "all"}:
            raise ValueError("repeat must be off, one or all")
        self.repeat[int(chat_id)] = mode
        return mode

    def set_volume(self, chat_id: int, volume: int):
        volume = max(0, min(200, int(volume)))
        self.volume[int(chat_id)] = volume
        return volume

    @staticmethod
    def _is_url(value: str) -> bool:
        return bool(re.match(r'^https?://\S+$', (value or '').strip(), re.I))

    def search(self, query, limit=8):
        """Search multiple playable sources and return source-tagged tracks.

        YouTube is only one source. If its extractor/search is unavailable,
        SoundCloud is still attempted. Direct URLs are accepted without search.
        """
        query=(query or '').strip()
        if not query:
            return []
        if self._is_url(query):
            return [{'id':'direct', 'title':query.rsplit('/',1)[-1] or 'Audio',
                     'url':query, 'duration':None, 'channel':'', 'source':'direct'}]

        results=[]
        seen=set()
        try:
            for r in self.youtube.search(query, limit=max(1, min(limit, 8))):
                r=dict(r); r['source']='youtube'
                key=r.get('url') or r.get('id') or r.get('title')
                if key and key not in seen:
                    seen.add(key); results.append(r)
        except Exception as exc:
            log.warning('YouTube search failed; continuing with other sources: %s', exc)

        try:
            from yt_dlp import YoutubeDL
            opts={'quiet':True,'no_warnings':True,'skip_download':True,'extract_flat':True}
            with YoutubeDL(opts) as ydl:
                data=ydl.extract_info(f'scsearch{max(1,min(limit,8))}:{query}', download=False)
            for item in data.get('entries') or []:
                if not item:
                    continue
                url=item.get('webpage_url') or item.get('url') or ''
                if url and not str(url).startswith(('http://','https://')):
                    sid=item.get('id') or ''
                    if sid: url=f'https://soundcloud.com/{sid}'
                if not url: continue
                r={'id':item.get('id') or '', 'title':item.get('title') or 'Unknown title',
                   'url':url, 'duration':item.get('duration'),
                   'channel':item.get('uploader') or item.get('channel') or '',
                   'source':'soundcloud'}
                key=r['url']
                if key not in seen:
                    seen.add(key); results.append(r)
        except Exception as exc:
            log.warning('SoundCloud search failed: %s', exc)

        return results

    def download(self, track_or_url, output_mp3=False):
        """Download a track using its tagged source, or a raw URL.

        No cookies, account scraping, or anti-bot bypass is performed. A failed
        source can therefore safely fall through to the next source.
        """
        if isinstance(track_or_url, dict):
            url=track_or_url.get('url') or ''
            source=track_or_url.get('source') or 'unknown'
        else:
            url=str(track_or_url or '')
            source='direct'
        if not url:
            raise RuntimeError('empty audio source URL')
        return self.youtube.download(url, source=source, output_mp3=output_mp3)

    @staticmethod
    def cleanup_stale_temp(max_age_seconds: int = 6 * 3600):
        """Remove only NYRA-created temporary music directories left by crashes."""
        root=Path(tempfile.gettempdir())
        now=time.time()
        for p in root.glob('nyra_audio_*'):
            try:
                if p.is_dir() and now - p.stat().st_mtime > max_age_seconds:
                    YouTubeAudio.cleanup(p)
            except Exception:
                log.warning('stale music cleanup failed for %s', p, exc_info=True)

    def cleanup(self, path):
        self.youtube.cleanup(path)
