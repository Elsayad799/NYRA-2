from __future__ import annotations
import logging
import os
import re
import tempfile
from pathlib import Path

log = logging.getLogger('YouTube')

class YouTubeAudio:
    """Search YouTube and download one requested audio track to a temp file.

    This is an on-demand downloader, not a separate Telegram bot. It does not
    persist downloaded media after the send operation completes.
    """
    MAX_DURATION = int(os.getenv('YOUTUBE_MAX_DURATION', '3600'))
    MAX_BYTES = int(os.getenv('YOUTUBE_MAX_BYTES', str(49 * 1024 * 1024)))

    @staticmethod
    def extract_query(text: str) -> str | None:
        raw = (text or '').strip()
        if not raw:
            return None
        patterns = [
            r'^(?:شغ+ل(?:ي|ى)?|شغل(?:ي|ى)?|شغّل(?:ي|ى)?|شغلي|شغّلي)\s+(?:اغنية|أغنية|اغنيه|أغنيه|موسيقى|صوت)?\s*(.+)$',
            r'^(?:هات(?:لي|لى)?|جيب(?:لي|لى)?|نزّل(?:لي|لى)?|نزل(?:لي|لى)?)\s+(?:اغنية|أغنية|اغنيه|أغنيه|موسيقى|صوت)\s+(.+)$',
            r'^(?:play|send|download)\s+(?:song|music|audio)?\s*(.+)$',
        ]
        for pattern in patterns:
            m = re.match(pattern, raw, flags=re.I)
            if m:
                q = m.group(1).strip(' "“”\'')
                return q or None
        return None

    @staticmethod
    def _require_yt_dlp():
        try:
            from yt_dlp import YoutubeDL
            return YoutubeDL
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                'yt-dlp غير مثبت. ثبّته بالأمر: python -m pip install yt-dlp'
            ) from exc

    @staticmethod
    def search(query: str, limit: int = 5) -> list[dict]:
        YoutubeDL = YouTubeAudio._require_yt_dlp()
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': True,
        }
        with YoutubeDL(opts) as ydl:
            data = ydl.extract_info(f'ytsearch{max(1, min(limit, 8))}:{query}', download=False)
        results = []
        for item in (data.get('entries') or []):
            if not item:
                continue
            item_id=item.get('id') or ''
            item_url=item.get('webpage_url') or item.get('url') or ''
            if item_url and not str(item_url).startswith(('http://','https://')) and item_id:
                item_url=f'https://www.youtube.com/watch?v={item_id}'
            results.append({
                'id': item_id,
                'title': item.get('title') or 'Unknown title',
                'url': item_url,
                'duration': item.get('duration'),
                'channel': item.get('channel') or item.get('uploader') or '',
            })
        return results

    def download(self, url: str, source: str = 'youtube', output_mp3: bool = False) -> tuple[Path, dict]:
        YoutubeDL = self._require_yt_dlp()
        td = Path(tempfile.mkdtemp(prefix='nyra_audio_'))
        template = str(td / '%(id)s.%(ext)s')
        opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'format': 'bestaudio/best',
            'outtmpl': template,
            'max_filesize': self.MAX_BYTES,
            'socket_timeout': 30,
            'retries': 2,
            'fragment_retries': 2,
        }
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                duration = int(info.get('duration') or 0)
                if duration > self.MAX_DURATION:
                    raise RuntimeError(f'الصوت أطول من الحد المسموح ({self.MAX_DURATION // 60} دقيقة).')
                path = Path(ydl.prepare_filename(info))
                if not path.exists():
                    candidates = [p for p in td.iterdir() if p.is_file()]
                    if not candidates:
                        raise RuntimeError('لم أجد ملف الصوت بعد التحميل')
                    path = candidates[0]
                if path.stat().st_size > self.MAX_BYTES:
                    raise RuntimeError('ملف الصوت أكبر من الحد المسموح للإرسال.')
                if output_mp3:
                    path = self._to_mp3(path, td)
                meta = {
                    'title': info.get('title') or f'{source.title()} audio',
                    'duration': duration,
                    'channel': info.get('channel') or info.get('uploader') or '',
                    'webpage_url': info.get('webpage_url') or url,
                    'source': source or 'unknown',
                }
                return path, meta
        except Exception:
            self.cleanup(td)
            raise


    @staticmethod
    def _to_mp3(path: Path, temp_dir: Path) -> Path:
        """Normalize a downloaded track to MP3 for private-chat delivery."""
        import subprocess
        try:
            from imageio_ffmpeg import get_ffmpeg_exe
            ffmpeg = get_ffmpeg_exe()
        except Exception:
            ffmpeg = os.getenv('FFMPEG_BIN') or 'ffmpeg'
        out = temp_dir / (path.stem + '.mp3')
        cmd = [ffmpeg, '-y', '-i', str(path), '-vn', '-codec:a', 'libmp3lame', '-q:a', '4', str(out)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=120)
        if not out.exists() or out.stat().st_size <= 0:
            raise RuntimeError('FFmpeg did not create the MP3 file')
        try:
            path.unlink()
        except Exception:
            pass
        return out

    @staticmethod
    def cleanup(path_or_dir):
        p = Path(path_or_dir)
        try:
            if p.is_dir():
                for child in p.iterdir():
                    try: child.unlink()
                    except Exception: pass
                p.rmdir()
            elif p.exists():
                p.unlink()
        except Exception:
            log.exception('YouTube temporary cleanup failed')
