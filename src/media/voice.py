from __future__ import annotations
import logging, os, subprocess, tempfile, shutil
from pathlib import Path

log = logging.getLogger('Voice')

class VoiceEngine:
    """NYRA speech I/O.

    TTS priority:
      1. Edge-TTS ar-EG-SalmaNeural (female Egyptian Arabic)
      2. gTTS fallback

    STT priority:
      1. faster-whisper when installed
      2. SpeechRecognition/Google Web Speech fallback

    The engine is deliberately optional: heavy local Whisper packages are not
    required just to start the Telegram bot on Android.
    """
    def __init__(self, language='ar-EG'):
        self.language = language or 'ar-EG'
        self.tts_gender = os.getenv('NYRA_TTS_GENDER', 'female').strip().lower()
        self.tts_voice = os.getenv('NYRA_TTS_VOICE', '').strip()
        self.whisper_model = os.getenv('NYRA_WHISPER_MODEL', 'small').strip()
        self.whisper_device = os.getenv('NYRA_WHISPER_DEVICE', 'auto').strip()
        self.whisper_compute = os.getenv('NYRA_WHISPER_COMPUTE', 'int8').strip()
        self._whisper = None
        self._voice_clone = None
        self._local_voice_clone = None
        # The old VoicesLab activation/account flow is opt-in only. This keeps
        # a broken external activation flow from blocking every NYRA reply.
        if os.getenv('NYRA_LEGACY_VOICESLAB', '0').strip().lower() in ('1','true','yes','on'):
            try:
                from .voice_clone import NyraVoiceClone
                self._voice_clone = NyraVoiceClone()
            except Exception as exc:
                log.warning('Legacy VoicesLab voice engine unavailable: %s', exc)
        if os.getenv('NYRA_LOCAL_VOICE_ENABLED', '1').strip().lower() not in ('0','false','no','off'):
            try:
                from .local_voice_clone import LocalReferenceVoice
                candidate = LocalReferenceVoice()
                if candidate.available():
                    self._local_voice_clone = candidate
            except Exception as exc:
                log.debug('Local reference-voice engine unavailable: %s', exc)

    @staticmethod
    def _ffmpeg():
        configured = os.getenv('FFMPEG_BIN', '').strip()
        if configured:
            return configured
        try:
            import imageio_ffmpeg
            path = imageio_ffmpeg.get_ffmpeg_exe()
            if path:
                return path
        except Exception:
            pass
        return shutil.which('ffmpeg') or 'ffmpeg'

    def _decode_to_wav(self, data: bytes) -> Path:
        if not data:
            raise ValueError('empty audio')
        td = Path(tempfile.mkdtemp(prefix='nyra_voice_'))
        src = td / 'input.ogg'
        wav = td / 'input.wav'
        src.write_bytes(data)
        cmd=[self._ffmpeg(), '-y', '-i', str(src), '-vn', '-ac', '1', '-ar', '16000', '-sample_fmt', 's16', str(wav)]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=90, text=True, errors='replace')
        except FileNotFoundError as exc:
            shutil.rmtree(td, ignore_errors=True)
            raise RuntimeError('ffmpeg is not available. Set FFMPEG_BIN or install ffmpeg.') from exc
        except subprocess.TimeoutExpired as exc:
            shutil.rmtree(td, ignore_errors=True)
            raise RuntimeError('ffmpeg timed out while decoding voice') from exc
        except subprocess.CalledProcessError as exc:
            detail=(exc.stderr or '').strip().splitlines()[-1:] or ['unknown ffmpeg error']
            shutil.rmtree(td, ignore_errors=True)
            raise RuntimeError(f'ffmpeg could not decode the voice: {detail[0][:300]}') from exc
        if not wav.exists() or wav.stat().st_size < 100:
            shutil.rmtree(td, ignore_errors=True)
            raise RuntimeError('decoded audio is empty')
        return wav

    def _load_whisper(self):
        if self._whisper is not None:
            return self._whisper
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return None
        device = self.whisper_device
        if device == 'auto':
            device = 'cpu'
        compute = self.whisper_compute
        try:
            self._whisper = WhisperModel(self.whisper_model, device=device, compute_type=compute)
        except Exception as exc:
            log.warning('faster-whisper unavailable (%s); using fallback STT', exc)
            self._whisper = None
        return self._whisper

    def _transcribe_whisper(self, wav: Path, language: str | None) -> str | None:
        model=self._load_whisper()
        if model is None:
            return None
        lang=(language or self.language or 'ar').split('-')[0]
        try:
            segments, info = model.transcribe(str(wav), language=lang, beam_size=5, vad_filter=True)
            text=' '.join((s.text or '').strip() for s in segments).strip()
            return text or None
        except Exception:
            log.exception('faster-whisper transcription failed')
            return None

    def _transcribe_google(self, wav: Path, language: str | None) -> str:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise RuntimeError('No speech recognizer installed. Install SpeechRecognition or faster-whisper.') from exc
        recognizer=sr.Recognizer()
        with sr.AudioFile(str(wav)) as source:
            audio=recognizer.record(source)
        primary=language or self.language
        try:
            return recognizer.recognize_google(audio, language=primary).strip()
        except sr.UnknownValueError:
            if primary.lower() not in ('ar','en'):
                try:
                    return recognizer.recognize_google(audio, language='ar').strip()
                except sr.UnknownValueError as exc:
                    raise RuntimeError('speech was not clear enough to transcribe') from exc
            raise RuntimeError('speech was not clear enough to transcribe')
        except sr.RequestError as exc:
            raise RuntimeError(f'speech recognition service unavailable: {exc}') from exc

    def transcribe(self, data: bytes, language: str | None = None) -> str:
        wav=self._decode_to_wav(data)
        td=wav.parent
        try:
            text=self._transcribe_whisper(wav, language)
            if text:
                return text
            text=self._transcribe_google(wav, language)
            if not text:
                raise RuntimeError('speech recognizer returned empty text')
            return text
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def _select_edge_voice(self, language: str | None = None, gender: str | None = None) -> str:
        """Select a stable Edge voice from NYRA's language/gender profile.

        The original Txt2SpeechBot exposes language choices rather than a fixed
        voice-gender registry. NYRA therefore keeps the same language-first idea
        while selecting an explicit female/male neural voice locally.
        """
        if self.tts_voice:
            return self.tts_voice
        lang=(language or self.language or 'ar-EG').lower().replace('_','-')
        gender=(gender or self.tts_gender or 'female').lower()
        profiles={
            'ar': {'female':'ar-EG-SalmaNeural','male':'ar-EG-HamedNeural'},
            'en': {'female':'en-US-JennyNeural','male':'en-US-GuyNeural'},
            'de': {'female':'de-DE-KatjaNeural','male':'de-DE-ConradNeural'},
            'es': {'female':'es-ES-ElviraNeural','male':'es-ES-AlvaroNeural'},
            'fr': {'female':'fr-FR-DeniseNeural','male':'fr-FR-HenriNeural'},
            'it': {'female':'it-IT-ElsaNeural','male':'it-IT-DiegoNeural'},
            'pt': {'female':'pt-BR-FranciscaNeural','male':'pt-BR-AntonioNeural'},
            'el': {'female':'el-GR-AthinaNeural','male':'el-GR-NestorasNeural'},
            'ru': {'female':'ru-RU-SvetlanaNeural','male':'ru-RU-DmitryNeural'},
            'tr': {'female':'tr-TR-EmelNeural','male':'tr-TR-AhmetNeural'},
            'zh': {'female':'zh-CN-XiaoxiaoNeural','male':'zh-CN-YunxiNeural'},
            'ja': {'female':'ja-JP-NanamiNeural','male':'ja-JP-KeitaNeural'},
        }
        base=lang.split('-')[0]
        selected=profiles.get(base, profiles['en']).get(gender) or profiles.get(base, profiles['en'])['female']
        return selected

    def set_tts_gender(self, gender: str) -> str:
        gender=(gender or '').strip().lower()
        aliases={'أنثى':'female','انثى':'female','بنت':'female','female':'female','f':'female',
                 'ذكر':'male','راجل':'male','male':'male','m':'male'}
        gender=aliases.get(gender, gender)
        if gender not in ('female','male'):
            raise ValueError('gender must be female or male')
        self.tts_gender=gender
        return self._select_edge_voice(self.language, gender)

    def _synthesize_edge(self, text: str, language: str | None = None) -> bytes:
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError('edge-tts is not installed') from exc
        with tempfile.TemporaryDirectory(prefix='nyra_tts_') as td:
            path=Path(td)/'nyra.mp3'
            voice=self._select_edge_voice(language, self.tts_gender)
            communicate=edge_tts.Communicate(text, voice, rate=os.getenv('NYRA_TTS_RATE','+0%'), pitch=os.getenv('NYRA_TTS_PITCH','+0Hz'), volume=os.getenv('NYRA_TTS_VOLUME','+0%'))
            # edge-tts has used both async save APIs across releases; support the current one.
            import asyncio
            asyncio.run(communicate.save(str(path)))
            if not path.exists() or path.stat().st_size < 100:
                raise RuntimeError('Edge-TTS returned an empty audio file')
            return path.read_bytes()

    def _synthesize_gtts(self, text: str, language: str) -> bytes:
        try:
            from gtts import gTTS
        except ImportError as exc:
            raise RuntimeError('gTTS is not installed') from exc
        with tempfile.NamedTemporaryFile(prefix='nyra_tts_', suffix='.mp3', delete=False) as f:
            path=Path(f.name)
        try:
            gTTS(text=text, lang=(language or 'ar').split('-')[0], slow=False).save(str(path))
            return path.read_bytes()
        finally:
            path.unlink(missing_ok=True)

    def synthesize(self, text: str, language: str = 'ar') -> bytes:
        text=(text or '').strip()
        if not text:
            raise ValueError('empty text')

        # Preferred path: local reference-voice synthesis, if its optional
        # engine is installed. It never creates external accounts or sessions.
        if self._local_voice_clone is not None:
            try:
                return self._local_voice_clone.synthesize(text, language=language)
            except Exception as exc:
                log.warning('NYRA local reference voice unavailable; using TTS fallback: %s', exc)

        # Compatibility path for users who explicitly enable the old engine.
        if self._voice_clone is not None and self._voice_clone.available():
            try:
                return self._voice_clone.synthesize(text)
            except Exception as exc:
                log.warning('Legacy NYRA voice clone failed; using TTS fallback: %s', exc)

        try:
            return self._synthesize_edge(text, language)
        except Exception as exc:
            log.warning('Edge-TTS failed; falling back to gTTS: %s', exc)
            return self._synthesize_gtts(text, language)
