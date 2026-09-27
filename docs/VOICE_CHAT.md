# NYRA Voice Chat

NYRA now has two music delivery paths:

1. **Audio message** — the normal Bot API path and the recommended Android/Termux path.
2. **Group Voice Chat** — optional Pyrogram + PyTgCalls bridge, inspired by `tg-music-bot`.

The upstream `tg-music-bot` documents search/download on Termux and Voice Chat on Linux; its architecture also separates queue, player and handlers. NYRA keeps those ideas but does not start a second Telegram bot.

## Android / Termux

Use `/music NAME` or natural language such as `شغلي أغنية ...`. NYRA searches supported sources, tries multiple results, sends the audio through the existing bot and caches the resulting Telegram `file_id` for reuse.

Voice Chat is intentionally disabled on Android because the native `tgcalls` layer is not available there in the upstream project.

## Linux Voice Chat

Install:

```bash
pip install -r requirements-voice-chat.txt
```

Configure the optional variables:

```text
NYRA_VOICE_CHAT=1
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_VC_SESSION=nyra_voice_chat
```

Then start a Voice Chat in the group and use:

```text
/vcstatus
/vcplay اسم الأغنية
/vcstop
```

A normal private chat cannot host a Telegram group Voice Chat, so NYRA sends an audio message there instead. PyTgCalls requires an MTProto client and Telegram API credentials.

## Source protection

The music layer does not implement cookie extraction, anti-bot bypasses, or other mechanisms whose purpose is to defeat a source's access controls. If a source rejects a request, NYRA reports the failure and can try another supported result/source.
