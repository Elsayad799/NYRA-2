from src.media.voice import VoiceEngine


def test_nyra_defaults_to_female_egyptian_voice():
    v=VoiceEngine('ar-EG')
    assert v._select_edge_voice() == 'ar-EG-SalmaNeural'


def test_voice_gender_switch_changes_voice():
    v=VoiceEngine('ar-EG')
    assert v.set_tts_gender('male') == 'ar-EG-HamedNeural'
    assert v.set_tts_gender('female') == 'ar-EG-SalmaNeural'


def test_supported_language_profiles():
    v=VoiceEngine('en-US')
    assert v._select_edge_voice('en-US','female') == 'en-US-JennyNeural'
    assert v._select_edge_voice('ja-JP','male') == 'ja-JP-KeitaNeural'
