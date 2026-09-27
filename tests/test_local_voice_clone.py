from pathlib import Path

from src.media.local_voice_clone import LocalReferenceVoice


def test_local_reference_voice_detects_reference(tmp_path):
    ref = tmp_path / 'nyra_voice.mp3'
    ref.write_bytes(b'reference')
    engine = LocalReferenceVoice(str(ref))
    assert engine.available()


def test_missing_reference_is_unavailable(tmp_path):
    engine = LocalReferenceVoice(str(tmp_path / 'missing.mp3'))
    assert not engine.available()
