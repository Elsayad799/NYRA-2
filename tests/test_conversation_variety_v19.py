from src.social.conversation import SocialConversationEngine

def test_anti_repetition_shows_recent_replies_and_bans_stock_loop():
    e=SocialConversationEngine()
    f=e.anti_repetition_fragment(['فضفضي براحتك أنا سامعاكي', 'أنا هنا معاكي'])
    assert 'RECENT NYRA RESPONSES' in f
    assert 'فضفضي براحتك' in f
    assert 'أنا سامعاكي' in f
    assert 'محدش هيضغط عليكي' in f

def test_emotional_mode_does_not_force_helpdesk():
    e=SocialConversationEngine()
    f=e.prompt_fragment('EMOTIONAL')
    assert 'help-desk' in f
