# NYRA Voice Bridge

Additive bridge only. The upstream TgMusicBot files are not replaced.

Run from the `TgMusicBot-master` directory after configuring the same environment
variables required by the upstream project:

```bash
go run ./cmd/nyra_voice_bridge
```

The bridge listens on `127.0.0.1:8765` by default and exposes local `/play`,
`/pause`, `/resume`, `/stop`, `/mute`, `/unmute`, and `/health` endpoints for NYRA.
