from __future__ import annotations
import json
import requests

class TelegramPublicInfo:
    """Fetch a limited, non-sensitive public profile summary by username.

    This deliberately omits phone numbers, access hashes, flags and other
    internal identifiers exposed by some third-party lookup APIs.
    """
    URL = 'https://www.telegram-finder.io/api/telegram/username/check'

    @classmethod
    def lookup(cls, username: str) -> dict:
        u = (username or '').strip().lstrip('@')
        if not u or len(u) > 64:
            raise ValueError('invalid username')
        r = requests.post(cls.URL, json={'username': u}, timeout=20)
        r.raise_for_status()
        data = r.json()
        user = data.get('user') or {}
        if not user:
            return {'found': False, 'username': u}
        return {
            'found': True,
            'username': user.get('username') or u,
            'first_name': user.get('firstName') or '',
            'last_name': user.get('lastName') or '',
            'bio': user.get('bio') or '',
            'verified': bool(user.get('verified')),
            'premium': bool(user.get('premium')),
            'bot': bool(user.get('bot')),
            'deleted': bool(user.get('deleted')),
            'restricted': bool(user.get('restricted')),
            'scam': bool(user.get('scam')),
            'fake': bool(user.get('fake')),
        }
