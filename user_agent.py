"""Compatibility shim for the standalone NYRA voice-clone engine.

The supplied engine imports ``user_agent`` directly. Some Termux/Python
installations do not have that module even when ``user-agents`` is present.
Keep the original engine untouched and provide the single API it expects.
"""

_DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 10; K) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0.0.0 Mobile Safari/537.36"
)


def generate_user_agent(*args, **kwargs):
    return _DEFAULT_UA
