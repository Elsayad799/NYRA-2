# NYRA Voice Integration

NYRA now has three voice output levels:

1. **Local reference voice (preferred)** — optional XTTS-v2 via `TTS`, using the fixed `assets/voice/nyra_voice.mp3` reference. No external account/session/cookie flow is required.
2. **Edge-TTS** — automatic fallback and the default lightweight path when the local model is not installed.
3. **Legacy VoicesLab** — retained only for compatibility and disabled by default. Enable with `NYRA_LEGACY_VOICESLAB=1` if an existing installation still needs it.

The old external activation flow must not block normal NYRA replies.

Reference file:
`assets/voice/nyra_voice.mp3`

Optional environment variables:
- `NYRA_VOICE_REFERENCE=/absolute/path/to/nyra_voice.mp3`
- `NYRA_LOCAL_VOICE_ENABLED=1`
- `NYRA_LOCAL_VOICE_MODEL=tts_models/multilingual/multi-dataset/xtts_v2`
- `NYRA_LOCAL_VOICE_GPU=0`
- `NYRA_LEGACY_VOICESLAB=0`
