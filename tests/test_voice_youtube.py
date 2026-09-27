from pathlib import Path
from src.media.youtube import YouTubeAudio


def test_youtube_query_parser_arabic():
    assert YouTubeAudio.extract_query('شغلي أغنية عمرو دياب') == 'عمرو دياب'
    assert YouTubeAudio.extract_query('هاتلي اغنية تملي معاك') == 'تملي معاك'
    assert YouTubeAudio.extract_query('شغل موسيقى هادية') == 'هادية'


def test_youtube_query_parser_english():
    assert YouTubeAudio.extract_query('play song Believer Imagine Dragons') == 'Believer Imagine Dragons'
    assert YouTubeAudio.extract_query('hello nyra') is None


def test_youtube_cleanup(tmp_path):
    d=tmp_path/'nyra_yt'; d.mkdir(); f=d/'a.m4a'; f.write_bytes(b'x')
    YouTubeAudio.cleanup(d)
    assert not d.exists()


def test_youtube_requires_yt_dlp_with_clear_error(monkeypatch):
    import builtins
    original = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == 'yt_dlp':
            raise ModuleNotFoundError("No module named 'yt_dlp'")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', fake_import)
    try:
        YouTubeAudio.search('عمرو دياب')
    except RuntimeError as exc:
        assert 'yt-dlp غير مثبت' in str(exc)
    else:
        raise AssertionError('expected clear yt-dlp dependency error')


def test_voice_engine_prefers_configured_ffmpeg(monkeypatch):
    from src.media.voice import VoiceEngine
    monkeypatch.setenv('FFMPEG_BIN', '/custom/ffmpeg')
    assert VoiceEngine._ffmpeg() == '/custom/ffmpeg'
