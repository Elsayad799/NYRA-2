from src.social.conversation import SocialConversationEngine

def test_robotic_tone_feedback_enters_immersion_mode():
    e = SocialConversationEngine()
    assert e.classify('خخخ مش المفروض اني احس انك بني ادمه', {}, {}) == 'IMMERSION_FEEDBACK'

def test_immersion_feedback_rejects_helpdesk_tone():
    e = SocialConversationEngine()
    f = e.prompt_fragment('IMMERSION_FEEDBACK')
    assert 'drop formal/technical language' in f
    assert 'Do not explain that you are an AI' in f
