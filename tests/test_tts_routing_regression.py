from pathlib import Path


def _adapter_source():
    return Path('src/telegram/adapter.py').read_text(encoding='utf-8')


def test_tts_text_is_defined_before_routing_check():
    source = _adapter_source()
    assignment = source.index('tts_text = self._extract_tts_request(e.text)')
    check = source.index('if tts_text:')
    assert assignment < check


def test_normal_chat_does_not_match_tts_routing_pattern():
    source = _adapter_source()
    assert "if tts_text:" in source
    assert "def _extract_tts_request(text):" in source
    # Ordinary conversational text must reach the normal agent path; it is not
    # one of the explicit voice-request prefixes.
    assert 'اقريلي' in source and 'قولي بصوت' in source
