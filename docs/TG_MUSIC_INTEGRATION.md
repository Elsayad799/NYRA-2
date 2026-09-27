# NYRA v34 — tg-music-bot integration

NYRA v34 is additive: the v33 NYRA agent, memory, social system, image, voice,
YouTube and provider layers remain in place.

The upstream `tg-music-bot` project is a standalone Pyrogram/PyTgCalls bot.
NYRA cannot safely launch its `main.py` as-is because that would create a
second Telegram client/bot lifecycle. The integration boundary in
`integrations/tg_music_bot/bridge.py` keeps the upstream command/feature contract
while using NYRA's existing Bot API process.

Voice chat remains optional and platform dependent. The upstream documentation
states that Android/Termux supports music search/download but not voice-chat
playback because of the native tgcalls dependency. Full voice chat requires the
corresponding Telegram API credentials and optional PyTgCalls stack.
