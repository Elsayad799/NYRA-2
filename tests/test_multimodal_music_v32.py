from pathlib import Path


def test_edge_tts_voice_and_whisper_engine_present():
    text=Path('src/media/voice.py').read_text(encoding='utf-8')
    assert 'ar-EG-SalmaNeural' in text
    assert 'faster_whisper' in text
    assert 'gTTS' in text


def test_vision_engine_has_ocr_and_vlm_paths():
    text=Path('src/media/vision.py').read_text(encoding='utf-8')
    assert 'pytesseract' in text
    assert 'chat/completions' in text
    assert 'image_url' in text


def test_music_has_telegram_cache_and_soundcloud_fallback():
    text=Path('src/media/music.py').read_text(encoding='utf-8')
    assert 'music_cache.json' in text
    assert 'file_id' in text
    assert 'scsearch' in text


def test_adapter_routes_vision_and_music_cache():
    text=Path('src/telegram/adapter.py').read_text(encoding='utf-8')
    assert 'self.vision=VisionEngine()' in text
    assert 'self.music=MusicEngine()' in text
    assert "self.music.cached(query)" in text
