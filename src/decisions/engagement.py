from __future__ import annotations
import re,time

class EngagementDecision:
    def __init__(self,s):
        self.s=s; self.last_global=0.0; self.last_group={}; self.last_user={}; self.recent_bot={}
    def decide(self,event, relationship=None):
        if event.chat_type=="private": return True,"private_chat"
        text=event.text or ""; low=text.lower(); mentioned=any(x in low for x in ["nyra","نايرا","@nyra"])
        if mentioned or event.is_reply_to_bot: return self._cooldown_ok(event,"directed")
        if not text.strip() or text.startswith("/"): return False,"not_conversational"
        if len(text)<3: return False,"too_short"
        # Participation is conservative: questions/relevant ongoing conversation can trigger a reply.
        question=("?" in text or "؟" in text)
        relevant=any(k in low for k in ["ذكاء","ai","بوت","مشروع","لعبة","minecraft","ماينكرافت","برمجة","حل","حد يعرف"])
        social=float((relationship or {}).get("familiarity",0))
        probability=0.05 + (0.12 if question else 0) + (0.12 if relevant else 0) + min(.12,social*.1)
        # deterministic sampling based on event id avoids repeated random spam while remaining non-fixed.
        import hashlib
        n=int(hashlib.sha256(f"{event.chat_id}:{event.message_id}".encode()).hexdigest()[:8],16)/0xffffffff
        if n>probability: return False,"low_engagement_score"
        return self._cooldown_ok(event,"opportunistic")
    def _cooldown_ok(self,e,reason):
        now=time.monotonic()
        if now-self.last_global<self.s.global_cooldown: return False,"global_cooldown"
        if now-self.last_group.get(e.chat_id,0)<self.s.group_cooldown: return False,"group_cooldown"
        if now-self.last_user.get(e.user_id,0)<self.s.user_cooldown: return False,"user_cooldown"
        self.last_global=now; self.last_group[e.chat_id]=now; self.last_user[e.user_id]=now
        return True,reason
