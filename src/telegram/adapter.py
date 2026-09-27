from __future__ import annotations
import logging, re, time, threading
import telebot
from telebot import types
from src.agent.events import Event
from src.media.voice import VoiceEngine
from integrations.telegram_voice_transcription import TelegramVoiceTranscriptionBridge
from src.media.youtube import YouTubeAudio
from src.media.music import MusicEngine
from integrations.tg_music_bot import TgMusicBridge
from src.media.vision import VisionEngine
from src.media.shazam import ShazamEngine
from src.media.voice_chat import VoiceChatEngine
from src.media.tg_music_voice_bridge import TgMusicVoiceBridge
import asyncio
log=logging.getLogger('Telegram')

class TelegramAdapter:
    def __init__(self,settings,agent,scheduler=None):
        self.settings,self.agent,self.scheduler=settings,agent,scheduler
        if self.scheduler: self.scheduler.callback=self._handle_autonomous_action
        self.bot=telebot.TeleBot(settings.telegram_token,parse_mode=None,threaded=True,num_threads=8)
        self.voice=VoiceEngine()
        self.voice_transcription=TelegramVoiceTranscriptionBridge(self.voice)
        self.youtube=YouTubeAudio()
        self.music=MusicEngine()
        # Voice Chat is optional (especially on Android/Termux). Initialize it
        # before the music bridge and always expose a safe object to the bridge.
        try:
            self.voice_chat=VoiceChatEngine()
        except Exception as exc:
            log.warning("Voice Chat initialization failed; continuing without it: %s", exc)
            self.voice_chat=None
        self.tg_music=TgMusicBridge(self.music, self.voice_chat)
        self.tg_voice_bridge=TgMusicVoiceBridge()
        self.vision=VisionEngine()
        self.shazam=ShazamEngine()
        # Short-lived conversational state for follow-up music requests.
        # This lets "عندك أغاني؟" -> "عمرو دياب" become a music action.
        self._pending_music={}
        try:self.bot_user=self.bot.get_me()
        except Exception:self.bot_user=None
        self._register()

    def _register(self):
        @self.bot.message_handler(commands=['start'])
        def start(m):
            self.bot.reply_to(m,'أهلاً بيك ✨ أنا نايرا. قولي اللي في بالك، وأنا معاكي في الكلام من غير تكلف. 💜')
        @self.bot.message_handler(commands=['voice', 'say', 'صوت'])
        def voice(m):
            parts=(m.text or '').split(maxsplit=2)
            if len(parts)==1:
                self.bot.reply_to(m,'اكتب: /voice النص اللي عايزني أقوله بصوت.\nوتقدر تختار: /voice female النص أو /voice male النص')
                return
            gender=None
            text=parts[1]
            if parts[1].lower() in ('female','f','male','m','أنثى','انثى','بنت','ذكر','راجل') and len(parts)>=3:
                gender=parts[1]
                text=parts[2]
            try:
                if gender:
                    self.voice.set_tts_gender(gender)
                payload=self.voice.synthesize(text, self.settings.tts_language)
                import io
                stream=io.BytesIO(payload); stream.name='nyra.mp3'
                self.bot.send_voice(m.chat.id,stream,caption='🔊 NYRA')
            except Exception:
                log.exception('manual TTS failed')
                self.bot.reply_to(m,'مش عارفة أطلع الصوت دلوقتي 😅 جرّب تاني بعد شوية.')
        @self.bot.message_handler(commands=['music', 'song', 'اغنية', 'أغنية'])
        def music(m):
            parts=(m.text or '').split(maxsplit=1)
            if len(parts)==1:
                self.bot.reply_to(m,'اكتب اسم الأغنية بعد الأمر، مثال: /music اسم الأغنية')
                return
            self._send_youtube_audio(m, parts[1].strip())
        @self.bot.message_handler(commands=['queue', 'قائمة'])
        def queue(m):
            rows=self.music.queue_peek(m.chat.id)
            current=self.music.current.get(m.chat.id)
            out=[]
            if current: out.append(f"▶️ الآن: {current.get('title','Unknown')}")
            if rows: out.append('\n'.join(f"{i+1}. {x.get('title','Unknown')}" for i,x in enumerate(rows[:20])))
            self.bot.reply_to(m, '\n'.join(out) if out else 'القائمة فاضية دلوقتي 😌')
        @self.bot.message_handler(commands=['clear'])
        def clear_queue(m):
            self.music.clear(m.chat.id); self.bot.reply_to(m,'تم مسح قائمة الأغاني 🗑️')
        @self.bot.message_handler(commands=['repeat'])
        def repeat(m):
            parts=(m.text or '').split(maxsplit=1); mode=parts[1].strip().lower() if len(parts)>1 else 'off'
            try:
                self.music.set_repeat(m.chat.id,mode); self.bot.reply_to(m,f'🔁 التكرار: {mode}')
            except ValueError:
                self.bot.reply_to(m,'استخدم: /repeat off | one | all')
        @self.bot.message_handler(commands=['volume'])
        def volume(m):
            parts=(m.text or '').split(maxsplit=1)
            if len(parts)==1:
                self.bot.reply_to(m,f"🔊 الصوت: {self.music.volume.get(m.chat.id,100)}"); return
            try:
                self.bot.reply_to(m,f"🔊 الصوت: {self.music.set_volume(m.chat.id,int(parts[1]))}")
            except Exception:
                self.bot.reply_to(m,'اكتب رقم من 0 إلى 200.')
        @self.bot.message_handler(commands=['vcstatus'])
        def vcstatus(m):
            self.bot.reply_to(m,f"🎙️ Voice Chat: {self.voice_chat.status()}")
        @self.bot.message_handler(commands=['vplay'])
        def vplay(m):
            parts=(m.text or '').split(maxsplit=1)
            if m.chat.type=='private':
                self.bot.reply_to(m,'الفيديو في Voice Chat لازم يكون داخل جروب؛ في الخاص هبعتلك الصوت كـMP3. 🎵'); return
            if len(parts)==1:
                self.bot.reply_to(m,'اكتب: /vplay اسم الفيديو أو الأغنية'); return
            self._play_voice_chat(m,parts[1].strip(),video=True)
        @self.bot.message_handler(commands=['vcplay'])
        def vcplay(m):
            parts=(m.text or '').split(maxsplit=1)
            if m.chat.type=='private':
                self.bot.reply_to(m,'مكالمة Voice Chat لازم تكون داخل جروب/قناة؛ في الخاص هبعتلك الصوت كملف عادي. 🎵'); return
            if len(parts)==1:
                self.bot.reply_to(m,'اكتب: /vcplay اسم الأغنية'); return
            self._play_voice_chat(m,parts[1].strip(),video=False)
        @self.bot.message_handler(commands=['vcstop'])
        def vcstop(m):
            try:
                self._run_async(self.voice_chat.stop_call(m.chat.id)); self.bot.reply_to(m,'⏹️ وقفت الـVoice Chat.')
            except Exception:
                self.bot.reply_to(m,'الـVoice Chat مش شغال حاليًا 😅')
        @self.bot.message_handler(commands=['shazam', 'شازام'])
        def shazam_command(m):
            if not m.reply_to_message or not (m.reply_to_message.voice or m.reply_to_message.audio or m.reply_to_message.video):
                self.bot.reply_to(m,'ردّي على مقطع صوتي أو فويس وقولي /shazam 🎵')
                return
            self._recognize_media(m, m.reply_to_message)
        @self.bot.message_handler(commands=['status'])
        def status(m):
            if m.from_user.id not in self.settings.admin_ids:return
            s=self.agent.state.get()
            self.bot.reply_to(m,f"NYRA online\nAI sources: {', '.join(p.name for p in self.agent.providers.providers)}\nState: {s}\nImage tool: {self.agent.image_generator.status}\nVision: {'READY' if self.vision.available else 'OCR/VLM not configured'}\nMusic cache: {len(self.music.cache)}\nVoice Chat: {self.voice_chat.status()}")
        @self.bot.message_handler(commands=['selfie'])
        def selfie(m): self._self_image(m)
        @self.bot.message_handler(commands=['photo','see'])
        def photo(m): self._self_image(m, request=(m.text or '').split(maxsplit=1)[1] if len((m.text or '').split(maxsplit=1))>1 else None)
        @self.bot.message_handler(commands=['presentation'])
        def presentation(m):
            if m.chat.type!='private':
                self.bot.reply_to(m,'في الجروب هويتي التقديمية ثابتة كبنت.')
                return
            parts=(m.text or '').split(maxsplit=1)
            if len(parts)==1:
                p=self.agent.presentations.get(m.from_user.id,m.chat.id,'private')
                self.bot.reply_to(m,f"presentation={p['presentation']}")
                return
            value=parts[1].strip().lower()
            aliases={'بنت':'female','ولد':'male','محايد':'neutral','adaptive':'adaptive','female':'female','male':'male','neutral':'neutral'}
            if value not in aliases:
                self.bot.reply_to(m,'استخدم: /presentation بنت | ولد | محايد | adaptive'); return
            self.agent.presentations.set_private(m.from_user.id,m.chat.id,aliases[value])
            self.bot.reply_to(m,'تمام، هخلي أسلوبي التقديمي في الشات ده متوافق مع الاختيار.')
        @self.bot.message_handler(commands=['goal'])
        def goal(m):
            if m.from_user.id not in self.settings.admin_ids:return
            parts=m.text.split(maxsplit=2)
            if len(parts)<3 or parts[1] not in ('group','user'):
                self.bot.reply_to(m,'الاستخدام: /goal group <الهدف>'); return
            owner_id=m.chat.id if parts[1]=='group' else m.from_user.id
            row=self.agent.goals.add(parts[1],owner_id,parts[2],.7)
            self.bot.reply_to(m,f'تمت إضافة الهدف #{row["id"]}: {row["goal"]}')
        @self.bot.message_handler(commands=['conflict'])
        def conflict(m):
            if m.from_user.id not in self.settings.admin_ids:return
            parts=m.text.split(maxsplit=1)
            if len(parts)<2 or not parts[1].lstrip('-').isdigit():
                self.bot.reply_to(m,'الاستخدام: /conflict <user_id>'); return
            user_id=int(parts[1]); s=self.agent.conflicts.get(user_id,m.chat.id)
            self.bot.reply_to(m,f"user={user_id}\nanger={s['anger']:.2f}\nfrustration={s['frustration']:.2f}\nannoyance={s['annoyance']:.2f}\ntrust={s['trust']:.2f}\nforgiveness={s['forgiveness']:.2f} ({s['forgiveness_status']})")
        @self.bot.message_handler(commands=['plans'])
        def plans(m):
            if m.from_user.id not in self.settings.admin_ids:return
            rows=self.agent.plans.list_for_chat(m.chat.id,8)
            if not rows:self.bot.reply_to(m,'لا توجد خطط لهذا الجروب.'); return
            out=[]
            for r in rows:
                step=self.agent.plans.next_step(r['id']); suffix=f" → {step['action_type']}: {step['objective']}" if step else ''
                out.append(f"#{r['id']} [{r['status']}] {r['title']}{suffix}")
            self.bot.reply_to(m,'\n'.join(out))
        @self.bot.message_handler(commands=['goals'])
        def goals(m):
            if m.from_user.id not in self.settings.admin_ids:return
            rows=self.agent.goals.open('group',m.chat.id,8)
            if not rows:self.bot.reply_to(m,'لا توجد أهداف مفتوحة لهذا الجروب.'); return
            self.bot.reply_to(m,'\n'.join(f"#{r['id']} [{float(r['progress']):.0%}] {r['goal']}" for r in rows))
        @self.bot.message_handler(commands=['memory'])
        def memory(m):
            if m.from_user.id not in self.settings.admin_ids:return
            rows=self.agent.memory.recall('user',m.from_user.id,'',8)
            self.bot.reply_to(m,'\n'.join(f"• {r['kind']}: {r['content']}" for r in rows) or 'No memories.')
        @self.bot.message_handler(commands=['forget_me'])
        def forget(m):
            self.agent.memory.forget_user(m.from_user.id); self.bot.reply_to(m,'تم مسح الذاكرة الشخصية والأحداث المرتبطة بهذا الحساب من قاعدة المشروع.')
        @self.bot.message_handler(content_types=['text'])
        def message(m): self._handle(m)
        @self.bot.message_handler(content_types=['photo'])
        def image(m): self._handle_media(m,'photo')
        @self.bot.message_handler(content_types=['document'])
        def document(m): self._handle_media(m,'document')
        @self.bot.message_handler(content_types=['audio','voice','video','video_note','animation','sticker'])
        def other_media(m): self._handle_media(m,m.content_type)

    def _event(self,m,text='',media_type=None,file_id=None,file_unique_id=None,mime_type=None,caption='',meta=None):
        chat_type='private' if m.chat.type=='private' else ('supergroup' if m.chat.type=='supergroup' else 'group' if m.chat.type=='group' else m.chat.type)
        bot_id=self.bot_user.id if self.bot_user else None
        low=(text or '').lower(); reply=bool(m.reply_to_message and m.reply_to_message.from_user and bot_id and m.reply_to_message.from_user.id==bot_id)
        mention=('@nyra' in low or 'nyra' in low or 'نايرا' in low)
        return Event(m.chat.id,m.from_user.id,m.message_id,chat_type,text or '',m.from_user.first_name or '',m.from_user.username or '',getattr(m.chat,'title','') or '',reply,mention,media_type,file_id,file_unique_id,mime_type,caption or '',meta or {})

    def _handle(self,m):
        if not m.text:return
        e=self._event(m,text=m.text)
        self._process_event(m,e)

    def _handle_media(self,m,media_type):
        caption=getattr(m,'caption','') or ''
        file_id=file_unique_id=mime=None; meta={}
        if media_type=='photo' and getattr(m,'photo',None):
            ph=m.photo[-1]; file_id=ph.file_id; file_unique_id=ph.file_unique_id; mime='image/jpeg'
            # Ephemeral in-memory inspection only; no project file is created.
            try:
                info=self.bot.get_file(file_id); data=self.bot.download_file(info.file_path)
                from src.media.understanding import MediaUnderstanding
                meta=MediaUnderstanding().inspect_image(data,caption)
                # Vision is ephemeral: only the compact result is attached to the event.
                try:
                    vision=self.vision.analyze(data, caption=caption, question=caption)
                    if vision.get('description'): meta['vision']=vision['description'][:5000]
                    if vision.get('ocr'): meta['ocr']=vision['ocr'][:5000]
                except Exception:
                    log.exception('vision analysis failed')
                del data
            except Exception: log.exception('photo inspection failed')
        elif media_type=='document' and getattr(m,'document',None):
            d=m.document; file_id=d.file_id; file_unique_id=d.file_unique_id; mime=d.mime_type or ''
            meta={'filename':d.file_name or '', 'size':d.file_size or 0}
        elif getattr(m,'audio',None):
            a=m.audio; file_id=a.file_id; file_unique_id=a.file_unique_id; mime=a.mime_type or 'audio'
            meta={'duration':a.duration,'title':a.title or '','performer':a.performer or ''}
        elif getattr(m,'voice',None):
            a=m.voice; file_id=a.file_id; file_unique_id=a.file_unique_id; mime='audio/ogg'; meta={'duration':a.duration}
            try:
                info=self.bot.get_file(file_id); data=self.bot.download_file(info.file_path)
                transcript=self.voice_transcription.transcribe(data, language=self.voice.language)
                meta['transcript']=transcript
            except Exception as exc:
                log.exception('voice transcription failed')
                meta['transcription_error']=str(exc)
                transcript=''
            e=self._event(m,text=transcript if transcript else caption,media_type=media_type,file_id=file_id,file_unique_id=file_unique_id,mime_type=mime,caption=caption,meta=meta)
            if not e.text:
                reason=meta.get('transcription_error','')
                if 'ffmpeg' in reason.lower():
                    msg='الفويس وصلني، بس عندي مشكلة في فك ملف الصوت على السيرفر 😅 تأكد إن ffmpeg متاح عندك.'
                elif 'speech recognition service unavailable' in reason.lower():
                    msg='الفويس وصلني، لكن خدمة تحويل الكلام لنص مش متاحة دلوقتي 😅 جرّبه تاني بعد شوية.'
                elif 'speech was not clear enough' in reason.lower():
                    msg='سمعت الفويس، بس الكلام مش واضح كفاية المرة دي 😅 ابعته تاني بصوت أوضح.'
                else:
                    msg='الفويس وصلني، بس مقدرتش أفك الكلام المرة دي 😅 ابعته تاني أو اكتبلي اللي اتقال.'
                self.bot.reply_to(m,msg)
                return
            self._process_event(m,e)
            return
        elif getattr(m,'video',None):
            a=m.video; file_id=a.file_id; file_unique_id=a.file_unique_id; mime=a.mime_type or 'video'; meta={'duration':a.duration,'width':a.width,'height':a.height}
        elif getattr(m,'video_note',None):
            a=m.video_note; file_id=a.file_id; file_unique_id=a.file_unique_id; mime='video'; meta={'duration':a.duration,'length':a.length}
        elif getattr(m,'animation',None):
            a=m.animation; file_id=a.file_id; file_unique_id=a.file_unique_id; mime=a.mime_type or 'animation'; meta={'duration':a.duration,'width':a.width,'height':a.height}
        elif getattr(m,'sticker',None):
            a=m.sticker; file_id=a.file_id; file_unique_id=a.file_unique_id; mime='sticker'; meta={'emoji':a.emoji or '','set_name':a.set_name or ''}
        e=self._event(m,text=caption,media_type=media_type,file_id=file_id,file_unique_id=file_unique_id,mime_type=mime,caption=caption,meta=meta)
        self._process_event(m,e)

    def _process_event(self,m,e):
        self.agent.observe(e)
        if e.text and re.match(r'^(?:شازام|/shazam)(?:\s*)$', e.text.strip(), re.I) and getattr(m, 'reply_to_message', None):
            self._recognize_media(m, m.reply_to_message)
            return
        # Explicit requests to hear NYRA herself should produce a voice reply,
        # rather than being treated as ordinary conversation.
        if self._looks_like_self_voice_request(e.text):
            self._send_tts(e.chat_id, 'حاضر 😌 اهو صوتي ليك. قولي بقى عايزني أقولك إيه.')
            return
        tts_text = self._extract_tts_request(e.text)
        if tts_text:
            self._send_tts(e.chat_id, tts_text)
            return
        # Music intent is handled before the social brain so a music follow-up
        # cannot be mistaken for ordinary conversation.
        yt_query=YouTubeAudio.extract_query(e.text) if e.text else None
        if yt_query:
            self._pending_music.pop(e.chat_id, None)
            self._send_youtube_audio(m, yt_query)
            return
        pending=self._pending_music.get(e.chat_id)
        if pending and time.time() < pending.get('expires',0):
            candidate=(e.text or '').strip()
            if candidate and len(candidate) >= 2 and not candidate.startswith(('/', '?', '؟')):
                self._pending_music.pop(e.chat_id,None)
                self._send_youtube_audio(m,candidate)
                return
        elif pending:
            self._pending_music.pop(e.chat_id,None)
        music_reply=self._music_followup(e.text, e.chat_id)
        if music_reply is not None:
            self.bot.reply_to(m, music_reply)
            return
        # Natural-language self-image requests bypass no AI reasoning: they simply
        # invoke the same persistent Visual DNA used by autonomous image actions.
        if e.chat_type == 'private' and self._looks_like_self_image_request(e.text):
            # Image requests are an auxiliary action. They must never replace or
            # corrupt the normal conversation pipeline. Send the portrait first,
            # then leave the agent/session fully usable for the next message.
            self._self_image(m, request=e.text)
            return
        rel=self.agent.db.query('SELECT * FROM relationships WHERE user_id=? AND chat_id=?',(e.user_id,e.chat_id)); rel=dict(rel[0]) if rel else None
        social=self.agent.social.choose(e,rel,self.agent.state.get())
        if social['action']!='reply': return
        try:
            self.bot.send_chat_action(e.chat_id,'typing')
            text=None
            last_exc=None
            # A transient AI-source failure should not turn the conversation into
            # repeated generic error messages. ProviderManager already has source
            # fallback; this second attempt handles short-lived network failures.
            for attempt in range(2):
                try:
                    text,_=self.agent.respond(e,social['reason'])
                    break
                except Exception as exc:
                    last_exc=exc
                    log.exception('AI response attempt %s failed', attempt + 1)
            if text is None:
                raise last_exc or RuntimeError('AI response returned no text')
            if not text:return
            # NYRA can autonomously request a fictional image through a strict directive.
            match=re.search(r'IMAGE_PROMPT\s*:\s*(.+)',text,re.I|re.S)
            if match and self.agent.image_generator.available:
                prompt=match.group(1).strip()[:1600]
                clean=re.sub(r'IMAGE_PROMPT\s*:\s*.+','',text,flags=re.I|re.S).strip()
                if clean:self.bot.reply_to(m,clean)
                self._send_generated_image(e.chat_id,prompt,caption='— NYRA')
            else:
                self.bot.reply_to(m,text)
                if self.settings.auto_tts or e.media_type == 'voice':
                    self._send_tts(e.chat_id, text)
        except Exception as exc:
            log.exception('message handling failed')
            # Keep the conversation alive without pretending the message was
            # processed. The technical exception stays in logs; the user gets a
            # natural transient-failure notice instead of a hard conversation stop.
            try:
                self.bot.reply_to(m,'استنى عليا ثانية 😅 حصل لخبطة صغيرة في الرد، ابعتلي تاني.')
            except Exception:
                log.exception('failed to send conversation error message')


    def _music_followup(self, text, chat_id):
        raw=(text or '').strip()
        now=time.time()
        pending=self._pending_music.get(chat_id)
        if pending and now < pending.get('expires',0):
            # A short natural answer after a music question is interpreted as
            # the requested artist/title, unless it is clearly another command.
            if raw and len(raw) >= 2 and not raw.startswith('/') and not self._extract_tts_request(raw):
                self._pending_music.pop(chat_id,None)
                # We cannot call the downloader here because this method needs
                # the Telegram message object. Returning a marker lets the event
                # path handle it safely.
                return None
        elif pending:
            self._pending_music.pop(chat_id,None)

        low=raw.lower()
        music_word=bool(re.search(r'(?:اغن(?:ي|ية|يه)|موسيقى|مزيكا|songs?|music)', low))
        request_word=bool(re.search(r'(?:عندك|فيه|هات|جيب|عايز|عاوز|شغل|شغلي|شغّل|شغليه|play|send)', low))
        if music_word and request_word:
            self._pending_music[chat_id]={'expires':now+120}
            return 'آه طبعًا 😌 قولي اسم المطرب أو الأغنية اللي نفسك فيها.'
        return None

    def _recognize_media(self, message, replied):
        try:
            file_id = None
            suffix = '.ogg'
            if replied.voice:
                file_id = replied.voice.file_id; suffix = '.ogg'
            elif replied.audio:
                file_id = replied.audio.file_id; suffix = '.mp3'
            elif replied.video:
                file_id = replied.video.file_id; suffix = '.mp4'
            if not file_id:
                self.bot.reply_to(message,'مش لاقية ملف الصوت 😅')
                return
            info = self.bot.get_file(file_id)
            payload = self.bot.download_file(info.file_path)
            result = self.shazam.recognize_bytes(payload, suffix=suffix)
            if not result:
                self.bot.reply_to(message,'مش قادرة أتعرف على الأغنية من المقطع ده 😅')
                return
            text=f"🎵 لقيتها!\n{result['title']} — {result['artist']}"
            if result.get('genre'): text += f"\nالنوع: {result['genre']}"
            self.bot.reply_to(message,text)
        except Exception:
            log.exception('Shazam recognition failed')
            self.bot.reply_to(message,'حصلت لخبطة وأنا بتعرف على الصوت 😅')

    @staticmethod
    def _looks_like_self_voice_request(text):
        raw=(text or '').strip().lower()
        patterns=(
            'سمعيني صوتك','سمعني صوتك','اسمعني صوتك','اسمعيني صوتك',
            'عايز اسمع صوتك','عاوز اسمع صوتك','نفسي اسمع صوتك',
            'ابعتلي صوتك','ابعتى صوتك','ابعتي صوتك','ابعت صوتك',
            'send me your voice','let me hear your voice','i want to hear your voice',
        )
        return any(p in raw for p in patterns)

    @staticmethod
    def _extract_tts_request(text):
        raw=(text or '').strip()
        patterns=(
            r'^(?:اقريلي|اقرأيلي|اقري لي|اقرأي لي|قوليه بصوت|قولي بصوت|ابعتلي صوت|ابعت صوت|ممكن بصوت)\s*[:：-]?\s*(.+)$',
            r'^(?:read this aloud|say this aloud|send voice)\s*[:：-]?\s*(.+)$',
        )
        for pattern in patterns:
            m=re.match(pattern,raw,flags=re.I|re.S)
            if m:
                value=m.group(1).strip()
                return value or None
        return None

    @staticmethod
    def _extract_voice_gender(text):
        raw=(text or '').strip().lower()
        if re.search(r'\b(?:male|ذكر|راجل)\b', raw):
            return 'male'
        if re.search(r'\b(?:female|أنثى|انثى|بنت)\b', raw):
            return 'female'
        return None

    def _send_tts(self, chat_id, text, gender=None):
        try:
            if gender:
                self.voice.set_tts_gender(gender)
            payload=self.voice.synthesize(text, self.settings.tts_language)
            import io
            stream=io.BytesIO(payload); stream.name='nyra.mp3'
            self.bot.send_voice(chat_id,stream,caption='🔊 NYRA')
            return True
        except Exception:
            log.exception('automatic TTS failed')
            return False

    @staticmethod
    def _run_async(coro):
        return asyncio.run(coro)

    def _play_voice_chat(self, message, query, video=False):
        # Prefer the supplied TgMusicBot/NTgCalls engine when its sidecar is running.
        # The Python VoiceChatEngine remains a safe fallback.
        sidecar_error = None
        if self.tg_voice_bridge.configured and self.tg_voice_bridge.available():
            sidecar_path = None
            try:
                self.bot.send_chat_action(message.chat.id,'upload_audio')
                original_rows=self._run_async(self.tg_music.original_search(query, 'en'))
                for row in original_rows[:3]:
                    try:
                        sidecar_path=self.tg_music.download_original_sync(row['url'])
                        if not sidecar_path:
                            continue
                        self.tg_voice_bridge.play(message.chat.id, sidecar_path, video=video)
                        self.music.current[message.chat.id]={'title':query,'url':row['url'],'source':'TgMusicBot/NTgCalls'}
                        self.bot.reply_to(message, ('📹' if video else '🎙️') + f' شغلت: {query}')
                        threading.Timer(max(30, 60), self._safe_unlink, args=(sidecar_path,), daemon=True).start()
                        sidecar_path=None
                        return
                    except Exception as exc:
                        sidecar_error=exc
                        if sidecar_path:
                            self._safe_unlink(sidecar_path); sidecar_path=None
                        log.warning('TgMusicBot sidecar result failed; trying next result: %s', exc)
            except Exception as exc:
                sidecar_error=exc
                log.warning('TgMusicBot sidecar unavailable during playback: %s', exc)
            finally:
                if sidecar_path:
                    self._safe_unlink(sidecar_path)

        if not self.voice_chat or not self.voice_chat.available:
            detail = '🎙️ الـVoice Chat مش مفعّل في البيئة دي.'
            if sidecar_error:
                detail += f'\nمحرك TgMusicBot رجّع: {sidecar_error}'
            detail += ' على Android/Termux هفضل أبعتلك الصوت كملف، ولو عايز مكالمات جماعية فعّل محرك Voice Chat على Linux.'
            self.bot.reply_to(message, detail)
            return
        path=None
        try:
            self.bot.send_chat_action(message.chat.id,'upload_audio')
            # First use the supplied youtube-music-download-bot exactly as its
            # downloader service. If it cannot fetch this track, retain NYRA's
            # existing multi-source resolver as a fallback.
            original_rows=self._run_async(self.tg_music.original_search(query, 'en'))
            for row in original_rows[:3]:
                try:
                    path=self.tg_music.download_original_sync(row['url'])
                    if not path:
                        continue
                    self._run_async(self.voice_chat.start())
                    self._run_async(self.voice_chat.play_file(message.chat.id,path))
                    self.music.current[message.chat.id]={'title':query,'url':row['url'],'source':'youtube-music-download-bot'}
                    self.bot.reply_to(message,f'🎙️ شغلت: {query}')
                    # Keep the exact temporary MP3 used by the original tool until
                    # playback has had enough time to consume it, then delete it.
                    duration=0
                    keep_for=max(30, int(duration or 0)+30)
                    threading.Timer(keep_for, self._safe_unlink, args=(path,), daemon=True).start()
                    path=None
                    return
                except Exception as exc:
                    if path: self._safe_unlink(path); path=None
                    log.warning('original music tool VC result failed; trying next result: %s', exc)

            results=self.music.search(query,limit=6)
            if not results:
                self.bot.reply_to(message,'مش لاقية نتيجة مناسبة 😅'); return
            last=None
            for chosen in results[:5]:
                try:
                    path,meta=self.music.download(chosen, output_mp3=False)
                    self._run_async(self.voice_chat.start())
                    self._run_async(self.voice_chat.play_file(message.chat.id,path))
                    self.music.current[message.chat.id]={'title':meta['title'],'url':meta['webpage_url'],'source':chosen.get('source','unknown')}
                    self.bot.reply_to(message,f"🎙️ شغلت: {meta['title']}")
                    keep_for=max(15, int(meta.get('duration') or 0) + 15)
                    threading.Timer(keep_for, self.music.cleanup, args=(path.parent,), daemon=True).start()
                    path=None
                    return
                except Exception as exc:
                    last=exc
                    if path:self.music.cleanup(path.parent); path=None
                    log.warning('voice chat fallback source failed: %s',exc)
            raise last or RuntimeError('no playable result')
        except Exception:
            log.exception('voice chat play failed')
            self.bot.reply_to(message,'مش قدرت أشغلها في الـVoice Chat دلوقتي 😅 تأكد إن المكالمة بدأت وإن NYRA عندها صلاحية إدارة المكالمة.')
        finally:
            if path:self._safe_unlink(path)

    @staticmethod
    def _safe_unlink(path):
        try:
            import shutil
            p=__import__('pathlib').Path(path)
            if p.is_dir(): shutil.rmtree(p, ignore_errors=True)
            elif p.exists(): p.unlink()
        except Exception:
            log.debug('temporary music cleanup failed', exc_info=True)

    def _send_youtube_audio(self, message, query):
        query=(query or '').strip()
        if not query:return
        # In groups, a music request means Voice Chat playback. In private chats,
        # keep the existing MP3 delivery behavior.
        if getattr(message.chat, 'type', '') in {'group', 'supergroup'}:
            self._play_voice_chat(message, query)
            return
        try:
            self.bot.send_chat_action(message.chat.id,'upload_audio')
            # Use the supplied youtube-music-download-bot unchanged as the first
            # downloader. NYRA's existing cache/fallback remains available if it fails.
            original_rows=self._run_async(self.tg_music.original_search(query, 'en'))
            for row in original_rows[:3]:
                path=None
                try:
                    path=self.tg_music.download_original_sync(row['url'])
                    if not path or not path.exists():
                        continue
                    with path.open('rb') as audio:
                        sent=self.bot.send_audio(message.chat.id,audio,title=query,caption=f'🎵 {query}\n🔗 {row["url"]}')
                    file_id=getattr(getattr(sent,'audio',None),'file_id',None)
                    if file_id:
                        self.music.remember(query,file_id,query,'',0,row['url'])
                    self._safe_unlink(path)
                    return
                except Exception as exc:
                    if path:self._safe_unlink(path)
                    log.warning('original music tool private result failed; trying next result: %s',exc)
            cached=self.music.cached(query)
            if cached and cached.get('file_id'):
                self.bot.send_audio(message.chat.id,cached['file_id'],title=cached.get('title') or None,duration=cached.get('duration') or None,performer=cached.get('performer') or None,caption=f"🎵 {cached.get('title') or query}\n⚡ من ذاكرة الموسيقى")
                return

            results=self.music.search(query,limit=6)
            if not results:
                self.bot.reply_to(message,'دورت على الأغنية ومطلعتليش نتيجة مناسبة 😅')
                return
            last_exc=None
            for idx,chosen in enumerate(results[:5]):
                try:
                    if idx==0:self.bot.reply_to(message,f"🎵 لقيت: {chosen['title']}\n⏳ جاري جلب الصوت...")
                    path,meta=self.music.download(chosen, output_mp3=True)
                    try:
                        with path.open('rb') as audio:
                            sent=self.bot.send_audio(message.chat.id,audio,title=meta['title'],duration=meta['duration'] or None,performer=meta['channel'] or None,caption=f"🎵 {meta['title']}\n🔗 {meta['webpage_url']}")
                        file_id=getattr(getattr(sent,'audio',None),'file_id',None)
                        if file_id:
                            self.music.remember(query,file_id,meta['title'],meta['channel'],meta['duration'] or 0,meta.get('webpage_url',''))
                    finally:
                        self.music.cleanup(path.parent)
                    return
                except Exception as exc:
                    last_exc=exc
                    log.warning('music source result failed; trying next result: %s',exc)
            if last_exc:raise last_exc
        except RuntimeError as exc:
            log.exception('music request failed')
            detail=str(exc)
            if 'yt-dlp غير مثبت' in detail:
                self.bot.reply_to(message,'أداة الموسيقى ناقصها yt-dlp 😅 شغّل: python -m pip install -U yt-dlp')
            else:
                self.bot.reply_to(message,'جلب الصوت من المصدر فشل دلوقتي 😅 لو الأغنية موجودة عندي في ذاكرة تيليجرام هبعتهالك مباشرة، غير كده جرّب مصدر/وقت تاني.')
        except Exception as exc:
            log.exception('music request failed')
            detail=str(exc).lower()
            if 'sign in to confirm you’re not a bot' in detail or 'sign in to confirm you are not a bot' in detail:
                self.bot.reply_to(message,'المصدر منع جلب الصوت دلوقتي 😅 مش هتجاوز الحماية. لو النسخة دي كانت اتبعت قبل كده هجيبها من ذاكرة تيليجرام مباشرة؛ غير كده جرّب نسخة/مصدر تاني.')
            else:
                self.bot.reply_to(message,'حصلت مشكلة وأنا بجيب الصوت 😅 جرّب تاني بعد شوية.')

    @staticmethod
    def _looks_like_self_image_request(text):
        low=(text or '').strip().lower()
        phrases=('وريني شكلك','ورييني شكلك','عايز اشوفك','عاوز اشوفك','عايز اشوف صورتك','عاوز اشوف صورتك','عايزك صورة','عاوزك صورة','عايز صورة ليكي','عاوز صورة ليكي','ابعتلي صورتك','ابعتلي صورة ليكي','ابعت صورتك','ابعت صورة ليكي','صورة ليكي','صوره ليكي','صورة منك','صوره منك','شكلك ايه','وريني صورتك','show me yourself','send me your picture','what do you look like')
        if any(p in low for p in phrases):
            return True
        # Common Egyptian-Arabic variants such as: عايزك تبعتيلي صورة / عايز اشوف صورة بتاعتك
        return bool(re.search(r'(عاي[زظ]|عاوز|محتاج).{0,24}(صو?ر[ةه]|شكلك)|صو?ر[ةه].{0,20}(ليكي|منك|بتاعتك)', low, re.I))

    def _self_image(self,m,request=None):
        if not self.agent.image_generator.available:
            self.bot.reply_to(m,'كنت هوريك صورتي، بس مولّد الصور مش متاح دلوقتي. جرّب تاني بعد شوية 🖤')
            return
        state=self.agent.state.get()
        prompt=self.agent.visual_identity.build_prompt(
            m.from_user.id,m.chat.id,state,request=request,
            scene='natural self-portrait for the current Telegram conversation'
        )
        self._send_generated_image(
            m.chat.id,prompt,caption='دي صورتي الحالية — NYRA',
            user_id=m.from_user.id,scene=request or 'self-portrait'
        )

    def _send_generated_image(self,chat_id,prompt,caption='',user_id=None,scene=None):
        try:
            import io
            import requests

            images=self.agent.image_generator.generate(prompt,'1:1',1)
            if not images:
                raise RuntimeError('image generator returned an empty result')

            sent_any=False
            for item in images:
                # Prefer downloading the generated URL ourselves. This avoids
                # Telegram rejecting a provider URL because of redirects,
                # headers, hotlink protection, or a non-standard content type.
                if isinstance(item, (bytes, bytearray)):
                    payload=bytes(item)
                    source_ref='generated-bytes'
                else:
                    source_ref=str(item)
                    response=requests.get(source_ref, timeout=90, allow_redirects=True)
                    response.raise_for_status()
                    payload=response.content
                    if not payload:
                        raise RuntimeError('image provider returned an empty HTTP body')

                stream=io.BytesIO(payload)
                stream.name='nyra.png'
                self.bot.send_photo(chat_id,stream,caption=caption)
                sent_any=True
                if user_id is not None:
                    self.agent.visual_identity.remember(
                        user_id,chat_id,prompt,scene,
                        self.agent.state.get().get('mood','neutral'),source_ref
                    )

            if not sent_any:
                raise RuntimeError('no image was sent to Telegram')
            return True
        except Exception as exc:
            log.exception('image generation/send failed')
            # Give the user a useful failure message while keeping technical
            # details in the log for the administrator.
            try:
                self.bot.send_message(chat_id, 'حاولت أعمل الصورة، بس مصدر الصور رجّع خطأ. جرّب تاني بعد شوية.')
            except Exception:
                log.exception('failed to send image error message')
            return False

    def _handle_autonomous_action(self,action):
        if not action:return
        chat_id=int(action.get('chat_id',0))
        if action.get('type')=='proactive_message':
            text=(action.get('text') or '').strip()
            if text:
                try:self.bot.send_message(chat_id,text)
                except Exception:log.exception('failed proactive message')
        elif action.get('type')=='proactive_image' and self.agent.image_generator.available:
            state=self.agent.state.get()
            prompt=self.agent.visual_identity.build_prompt(chat_id,chat_id,state,scene=action.get('prompt','NYRA spontaneous self-portrait'))
            self._send_generated_image(chat_id,prompt,'NYRA',user_id=chat_id,scene=action.get('prompt','autonomous self-portrait'))

    def run(self):
        if self.scheduler:self.scheduler.start()
        log.info('Telegram connected; NYRA AI online')
        try:self.bot.infinity_polling(skip_pending=True,timeout=30,long_polling_timeout=30)
        finally:
            if self.scheduler:self.scheduler.stop()
