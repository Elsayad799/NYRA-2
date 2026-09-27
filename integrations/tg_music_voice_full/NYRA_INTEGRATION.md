# NYRA + TgMusicBot integration

The directory `TgMusicBot-master/` is the supplied upstream project copied intact.
NYRA does not remove or rewrite its source files, including its cookie support,
NTgCalls implementation, assistant sessions, queue/player code, or configuration.

The only additions inside that directory are:

- `cmd/nyra_voice_bridge/main.go` — localhost HTTP adapter around the original
  `internal/calls` engine. It does not replace the original bot entrypoint.

NYRA uses the bridge only for group Voice/Video Chat playback. Private chats keep
using the original NYRA MP3 delivery path.

## Environment

For the sidecar:

- `API_ID`, `API_HASH`, `TOKEN`, `STRING1`... — the original TgMusicBot settings.
- `MONGO_URI` and `OWNER_ID` — required by the original project.
- `NYRA_TG_VOICE_BRIDGE_ADDR=127.0.0.1:8765`
- `NYRA_TG_VOICE_BRIDGE_TOKEN=<optional local shared secret>`

For NYRA:

- `NYRA_TG_VOICE_BRIDGE_ENABLED=1`
- `NYRA_TG_VOICE_BRIDGE_URL=http://127.0.0.1:8765`
- same `NYRA_TG_VOICE_BRIDGE_TOKEN` value if configured.

Build from the `TgMusicBot-master` directory with the toolchain required by the
supplied project. The bridge uses the original NTgCalls assistant sessions, so a
real Telegram user session (`STRING1`) is required for group-call playback.

If the sidecar is unavailable, NYRA falls back to its existing Python VoiceChat
engine instead of crashing.
