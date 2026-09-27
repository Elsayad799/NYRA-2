from pathlib import Path
from src.media.music import MusicEngine
from src.media.voice_chat import VoiceChatEngine


def test_music_queue_repeat_volume(tmp_path):
    m = MusicEngine(tmp_path)
    assert m.queue_add(10, {'title': 'A'}) == 1
    assert m.queue_add(10, {'title': 'B'}) == 2
    assert [x['title'] for x in m.queue_peek(10)] == ['A', 'B']
    assert m.queue_pop(10)['title'] == 'A'
    assert m.set_repeat(10, 'all') == 'all'
    assert m.set_volume(10, 999) == 200


def test_voice_chat_is_optional_without_credentials(monkeypatch):
    monkeypatch.delenv('NYRA_VOICE_CHAT', raising=False)
    v = VoiceChatEngine()
    assert not v.available
    assert v.status().startswith('OFF')
