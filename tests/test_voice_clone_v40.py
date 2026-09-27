from src.media.voice_clone import clean_for_speech

def test_removes_star_actions():
    text="*أضحك بصوت عالي* إيه يا عم الصياد، دخلت في الصعب؟ 🙈"
    assert clean_for_speech(text) == "إيه يا عم الصياد، دخلت في الصعب؟ 🙈"

def test_keeps_normal_parentheses():
    # Parenthetical stage directions are intentionally stripped for speech.
    assert clean_for_speech("أهلاً (بضحك) يا صاحبي") == "أهلاً يا صاحبي"

def test_no_speakable_text_after_action():
    assert clean_for_speech("*أضحك* *أتنهد*") == ""
