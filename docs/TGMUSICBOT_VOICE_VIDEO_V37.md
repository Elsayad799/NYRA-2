# NYRA v37 — TgMusicBot Voice/Video

NYRA v37 includes the user-supplied `TgMusicBot-master` project as an intact
subtree. The original 116 source files are preserved byte-for-byte. Two additive
bridge files are added for NYRA integration.

## Runtime behavior

- Private chat: existing NYRA MP3 flow remains unchanged.
- Group: NYRA's music intent can download with the supplied original downloader,
  then hand the local media path to the original TgMusicBot/NTgCalls engine.
- `/vplay <query>` asks the same engine for video playback.
- `/vcplay <query>` requests audio playback.
- If the Go sidecar is unavailable, NYRA falls back to its existing Python
  VoiceChatEngine rather than crashing.

## Required for the Go sidecar

The supplied TgMusicBot currently declares Go 1.26.4+ and FFmpeg as prerequisites
and requires its configured Telegram API ID/hash, bot token, assistant session,
MongoDB, and owner ID. See the original `sample.env` and README inside the
included project. The sidecar is an additive HTTP adapter; it does not replace
its original bot entrypoint.

The sidecar uses the original assistant-session/NTgCalls path for group calls.
A real user session is therefore required for the assistant account.
