from pathlib import Path


def test_bridge_is_additive_and_does_not_create_a_bot():
    p = Path('integrations/telegram_voice_transcription/bridge.py')
    text = p.read_text(encoding='utf-8')
    assert 'TelegramVoiceTranscriptionBridge' in text
    assert 'TeleBot' not in text
    assert 'polling' not in text


def test_adapter_routes_voice_through_bridge():
    text = Path('src/telegram/adapter.py').read_text(encoding='utf-8')
    assert 'TelegramVoiceTranscriptionBridge' in text
    assert 'self.voice_transcription=TelegramVoiceTranscriptionBridge(self.voice)' in text
    assert 'self.voice_transcription.transcribe(data' in text


def test_existing_voice_handler_still_processes_transcript():
    text = Path('src/telegram/adapter.py').read_text(encoding='utf-8')
    assert "content_types=['audio','voice','video','video_note','animation','sticker']" in text
    assert "self._process_event(m,e)" in text
