# NYRA AI — Voice + YouTube integration

## Voice input
Telegram `voice` messages are downloaded temporarily, converted to WAV with the ffmpeg binary exposed by `imageio-ffmpeg`, transcribed with SpeechRecognition/Google Web Speech, then passed into the normal NYRA Core as text. The original recording is not persisted by NYRA.

## Voice output
The supplied gTTS approach is integrated as `src/media/voice.py`.

- `/voice <text>`
- `/say <text>`
- `/صوت <text>`
- Natural requests beginning with phrases such as `اقريلي` or `قولي بصوت`
- `AUTO_TTS=true` enables a voice copy after normal text replies.
- A user who sends a Telegram voice message also receives a voice copy of NYRA's reply.

## YouTube audio
`src/media/youtube.py` searches with yt-dlp and downloads the best available audio track into a temporary directory. After Telegram sends the audio, the temporary file/directory is deleted.

Supported examples:

- `شغلي أغنية تملي معاك`
- `شغل موسيقى ...`
- `/music ...`
- `/song ...`

Limits are controlled by `YOUTUBE_MAX_DURATION` and `YOUTUBE_MAX_BYTES`; defaults are one hour and 49 MiB.

The YouTube feature is integrated into the existing Telegram bot and does not create another Telegram client/bot or require another bot token.
