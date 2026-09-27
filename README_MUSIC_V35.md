# NYRA v35 — Multi-Source Music + Temporary Media

This build keeps the existing NYRA agent and Telegram integration intact while improving the music delivery layer.

## Behavior

- Private chat: searches multiple supported sources, downloads temporarily, converts to MP3, sends it, then deletes the local temporary directory.
- Group Voice Chat: uses the optional Pyrogram/PyTgCalls bridge on supported desktop/Linux environments; the source file is retained only long enough for playback and is then deleted.
- YouTube failure does not terminate the request. NYRA can continue with SoundCloud results or a direct audio URL.
- Direct HTTP(S) audio URLs are accepted as a playable source.
- Startup cleanup removes only stale `nyra_audio_*` temporary directories left by interrupted runs.
- No cookie extraction, cookie harvesting, or anti-bot bypass is added.

## Android / Termux

Private MP3 delivery and music search can work. Group Voice Chat remains unavailable when the native PyTgCalls/tgcalls layer is unavailable.

## Linux / supported desktop

Install the optional voice-chat dependencies from `requirements-voice-chat.txt`, configure Telegram API credentials, enable `NYRA_VOICE_CHAT=1`, and start a group Voice Chat before asking NYRA to play music.
