from pathlib import Path

from src.media.music import MusicEngine

def test_music_direct_url_is_source_tagged(tmp_path):
    m=MusicEngine(tmp_path)
    rows=m.search("https://example.com/audio.mp3")
    assert rows and rows[0]["source"] == "direct"
    assert rows[0]["url"] == "https://example.com/audio.mp3"

def test_music_search_keeps_soundcloud_when_youtube_fails(tmp_path, monkeypatch):
    m=MusicEngine(tmp_path)
    def bad(*args, **kwargs):
        raise RuntimeError("youtube blocked")
    monkeypatch.setattr(m.youtube, "search", bad)
    class FakeYDL:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def extract_info(self, query, download=False):
            assert query.startswith("scsearch")
            return {"entries":[{"id":"abc","title":"Track","webpage_url":"https://soundcloud.com/x/track","duration":123,"uploader":"x"}]}
    import sys, types
    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=lambda opts: FakeYDL()))
    rows=m.search("Track", limit=3)
    assert rows and rows[0]["source"] == "soundcloud"

def test_adapter_uses_mp3_for_private_audio():
    text=Path("src/telegram/adapter.py").read_text(encoding="utf-8")
    assert "output_mp3=True" in text
    assert "self.music.download(chosen, output_mp3=False)" in text

def test_stale_cleanup_targets_only_nyra_dirs(tmp_path, monkeypatch):
    # Structural regression: the cleanup routine must use the NYRA prefix.
    text=Path("src/media/music.py").read_text(encoding="utf-8")
    assert "nyra_audio_*" in text
    assert "cleanup_stale_temp" in text
