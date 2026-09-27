from src.personality.identity import IDENTITY

def test_identity_is_ai(): assert 'AI' in IDENTITY and 'human' in IDENTITY.lower()
