from __future__ import annotations
import re
from datetime import datetime, timezone
from src.memory.store import MemoryStore

class LearningEngine:
    """Conservative learning: explicit statements, media metadata and observable outcomes."""
    def __init__(self, memory: MemoryStore): self.memory=memory
    def observe(self, user_id:int, chat_id:int, text:str):
        text=(text or '').strip()
        if not text: return
        patterns=[
            (r"(?:أنا|I)\s+(?:بحب|أحب|احب|like|love)\s+(.+)$", "preference", .85),
            (r"(?:أنا|I)\s+(?:مش بحب|لا أحب|don't like|dislike)\s+(.+)$", "preference", .9),
            (r"(?:اسمي|my name is)\s+(.+)$", "name", .95),
            (r"(?:افتكر|remember|تذكر)\s*[:：]?\s*(.+)$", "explicit_memory", .95),
            (r"(?:صحح|correction)\s*[:：]?\s*(.+)$", "correction", .95),
        ]
        for pat,kind,conf in patterns:
            m=re.search(pat,text,re.I)
            if m and m.group(1).strip():
                self.memory.upsert('user',user_id,kind,m.group(1).strip()[:700],.8,conf,'explicit_user_statement')
        if len(text)>20:
            self.memory.upsert('group',chat_id,'topic_observation',text[:300],.2,.35,'conversation_observation')
    def learn_claim(self, db, subject_id, chat_id, claim, kind='observation', confidence=.35, source_user_id=None, status='inferred'):
        claim=(claim or '').strip()[:700]
        if not claim:return
        ts=datetime.now(timezone.utc).isoformat()
        db.execute('''INSERT INTO learned_claims(subject_id,chat_id,claim,kind,confidence,source_user_id,status,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(subject_id,chat_id,claim) DO UPDATE SET confidence=MAX(confidence,excluded.confidence),updated_at=excluded.updated_at''',
        (subject_id,chat_id,claim,kind,confidence,source_user_id,status,ts,ts))
