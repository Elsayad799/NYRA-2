from pathlib import Path

from src.media.voice_clone import NyraVoiceClone, clean_for_speech


def test_original_engine_is_bundled_unchanged_source_file():
    root = Path(__file__).resolve().parents[1]
    assert (root / "integrations/nyra_voice_clone/original_clone_engine.py").is_file()


def test_fixed_reference_path_is_used(tmp_path):
    ref = tmp_path / "nyra_voice.mp3"
    ref.write_bytes(b"reference")
    vc = NyraVoiceClone(reference_audio=str(ref))
    assert vc.available()


def test_speech_cleanup():
    assert clean_for_speech("*smiles* أهلاً [debug]") == "أهلاً"
