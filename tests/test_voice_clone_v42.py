import json
from src.media.voice_clone import NyraVoiceClone, clean_for_speech


def test_actions_removed():
    s="*أضحك بصوت عالي* إيه يا عم الصياد؟ 🙈"
    assert clean_for_speech(s)=="إيه يا عم الصياد؟ 🙈"


def test_original_session_is_loaded(tmp_path, monkeypatch):
    session=tmp_path/"sessions.json"
    session.write_text(json.dumps({"cookies":{"__Secure-next-auth.session-token":"abc"}}), encoding="utf-8")
    ref=tmp_path/"nyra_voice.mp3"; ref.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    vc=NyraVoiceClone(reference_audio=str(ref), session_file=str(session))
    assert vc.available()


def test_fixed_reference_is_required(tmp_path):
    vc=NyraVoiceClone(reference_audio=str(tmp_path/"missing.mp3"))
    assert not vc.available()
