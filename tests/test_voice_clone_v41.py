import json
from src.media.voice_clone import NyraVoiceClone, clean_for_speech


def test_actions_and_parentheticals_removed():
    assert clean_for_speech("*أضحك* أهلاً (بضحك) يا صاحبي") == "أهلاً يا صاحبي"


def test_original_session_cookie_is_read(tmp_path, monkeypatch):
    session=tmp_path/"sessions.json"
    session.write_text(json.dumps({"cookies":{"__Secure-next-auth.session-token":"abc","sid":"x"}}), encoding="utf-8")
    ref=tmp_path/"nyra_voice.mp3"; ref.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    vc=NyraVoiceClone(reference_audio=str(ref), session_file=str(session))
    assert vc.available()
