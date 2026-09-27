# NYRA — Voiceslab voice clone integration

This integration keeps the supplied standalone clone bot flow for account/session
creation and voice cloning. NYRA does not ask the user to upload a reference voice
each time: it uses the fixed reference file `assets/voice/nyra_voice.mp3`.

## Original flow retained

1. Load `sessions.json` when a valid session exists.
2. If no valid session exists, create the temporary email account using the same
   temp-mail endpoint, request the Voiceslab email sign-in, poll for the callback,
   follow it, and save the resulting session to `sessions.json`.
3. Check clone credits with the same `get-user-info` call.
4. When the original quota condition is reached, remove `sessions.json` and let
   the same authentication flow establish the next session.
5. Upload the fixed NYRA reference with the same `create-voice` endpoint.
6. Send NYRA's generated text to the same `clone-voice` endpoint and retrieve
   the returned `audioUrl`.

## NYRA behavior

The written NYRA response is kept intact. Only the private speech copy removes
role-play markers such as `*actions*`, brackets, and stage directions before
cloning. The resulting audio is sent to Telegram automatically when `AUTO_TTS=true`.
Edge-TTS/gTTS remain fallback paths if clone generation is unavailable.

## Files

- `sessions.json` — runtime session; keep private.
- `uploaded_audios.json` — original clone cache format; keep private.
- `assets/voice/nyra_voice.mp3` — fixed NYRA reference recording; supply your
  authorized recording here.

Never commit session cookies, access tokens, or other secrets to GitHub.
