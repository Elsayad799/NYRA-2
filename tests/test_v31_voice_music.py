from pathlib import Path


def test_self_voice_request_is_detected():
    text=Path("src/telegram/adapter.py").read_text(encoding="utf-8")
    assert "سمعيني صوتك" in text
    assert "_looks_like_self_voice_request" in text


def test_music_tries_more_than_one_result():
    text=Path("src/telegram/adapter.py").read_text(encoding="utf-8")
    assert "results[:5]" in text
    assert "trying next result" in text
