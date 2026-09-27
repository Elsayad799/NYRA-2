# tg-music-bot integration for NYRA

This directory is an integration boundary around the feature set documented by
`mehrshadharry/tg-music-bot`. NYRA keeps one Telegram Bot API process and does
not start a second bot instance.

Preserved feature contract:
- `/play`, `/queue`, `/clear`, `/help`
- voice-chat controls: `/skip`, `/pause`, `/resume`, `/stop`, `/now`, `/volume`, `/repeat`, `/leave`
- queue/repeat/volume/admin concepts
- YouTube, SoundCloud and direct-link source model through yt-dlp
- Android/Termux limited mode and optional Linux voice-chat mode

The upstream project itself is a Pyrogram + PyTgCalls standalone application.
NYRA therefore uses this bridge rather than launching its `main.py` as a second
Telegram bot.


## NYRA Voice Clone v40

The primary NYRA reply voice can use an authorized reference voice through
`src/media/voice_clone.py`.

Configuration:
- `NYRA_VOICE_CLONE_ENABLED=1`
- `NYRA_VOICE_REFERENCE=assets/voice/nyra_voice.mp3`
- `NYRA_VOICE_SESSION_FILE=voice_clone_session.json` (or keep the original `sessions.json`; it is auto-detected)
- `NYRA_VOICE_CACHE_FILE=voice_clone_cache.json` (persistent cloned `voiceId`)
- or `NYRA_VOICE_COOKIE=...`

The visible AI response is preserved. Before synthesis, role-play/action annotations
such as `*أضحك بصوت عالي*`, `*أتنهد*`, and bracketed stage directions are removed
from the private speech text only.

If the authorized cloning session or reference file is unavailable, the existing
Edge-TTS/gTTS fallback remains active.
