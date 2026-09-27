from __future__ import annotations
import math, time

class AttentionManager:
    """Persistent social attention: what NYRA is currently following and why."""
    def __init__(self, db):
        self.db = db
        self._ensure()

    def _ensure(self):
        self.db.execute("""CREATE TABLE IF NOT EXISTS attention_state (
            chat_id INTEGER PRIMARY KEY, target_user_id INTEGER, topic TEXT NOT NULL DEFAULT '',
            focus REAL NOT NULL DEFAULT 0.0, last_event_at TEXT, last_attention_at TEXT,
            turns_since_reply INTEGER NOT NULL DEFAULT 0, updated_at TEXT
        )""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS conversation_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
            topic TEXT NOT NULL, started_at TEXT NOT NULL, last_event_at TEXT NOT NULL,
            last_user_id INTEGER, turns INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active', UNIQUE(chat_id, topic)
        )""")

    def _tokens(self, text):
        import re
        return set(re.findall(r"[\w\u0600-\u06ff]+", (text or '').lower()))

    def _topic(self, text):
        stop = {'انا','انت','هو','هي','ده','دي','في','من','على','عن','يا','the','and','is','to','a','of','فيه','ايه','هل'}
        words = [w for w in self._tokens(text) if w not in stop and len(w) > 2]
        return ' '.join(sorted(words)[:6])

    def observe(self, event):
        if event.chat_type == 'private':
            return
        topic = self._topic(event.text)
        now = "datetime('now')"
        state = self.get(event.chat_id)
        if topic:
            self.db.execute("""INSERT INTO conversation_threads(chat_id,topic,started_at,last_event_at,last_user_id,turns,status)
                VALUES(?,?,datetime('now'),datetime('now'),?,1,'active')
                ON CONFLICT(chat_id,topic) DO UPDATE SET last_event_at=datetime('now'),last_user_id=excluded.last_user_id,turns=turns+1,status='active'""",
                (event.chat_id, topic, event.user_id))
        if state['topic'] and topic:
            overlap = len(self._tokens(state['topic']) & self._tokens(topic))
        else:
            overlap = 0
        focus = min(1.0, state['focus'] * 0.88 + (0.20 if overlap else 0.08))
        self.db.execute("""INSERT INTO attention_state(chat_id,target_user_id,topic,focus,last_event_at,last_attention_at,turns_since_reply,updated_at)
            VALUES(?,?,?,?,datetime('now'),NULL,1,datetime('now'))
            ON CONFLICT(chat_id) DO UPDATE SET target_user_id=excluded.target_user_id,topic=excluded.topic,
            focus=excluded.focus,last_event_at=datetime('now'),turns_since_reply=attention_state.turns_since_reply+1,updated_at=datetime('now')""",
            (event.chat_id, event.user_id, topic, focus))

    def get(self, chat_id):
        rows = self.db.query('SELECT * FROM attention_state WHERE chat_id=?', (chat_id,))
        if rows:
            return dict(rows[0])
        return {'chat_id': chat_id, 'target_user_id': None, 'topic': '', 'focus': 0.0,
                'last_event_at': None, 'last_attention_at': None, 'turns_since_reply': 0}

    def score(self, event, relationship, state):
        a = self.get(event.chat_id)
        score = 0.0
        text = event.text or ''
        low = text.lower()
        if event.is_mention or event.is_reply_to_bot or 'nyra' in low or 'نايرا' in low:
            score += .65
        if a.get('target_user_id') == event.user_id:
            score += .18
        score += min(.18, float(a.get('focus', 0)) * .18)
        score += min(.12, float(a.get('turns_since_reply', 0)) * .015)
        score += min(.12, float((relationship or {}).get('familiarity', 0)) * .12)
        score += .08 * float(state.get('curiosity', .5))
        return min(1.0, score)

    def mark_attention(self, chat_id, user_id, reason='reply'):
        self.db.execute("UPDATE attention_state SET target_user_id=?,last_attention_at=datetime('now'),turns_since_reply=0,updated_at=datetime('now') WHERE chat_id=?", (user_id, chat_id))

    def decay(self):
        self.db.execute("UPDATE attention_state SET focus=MAX(0,focus*.94),updated_at=datetime('now')")
        self.db.execute("UPDATE social_groups SET activity=MAX(.05,activity*.985),conversation_speed=MAX(.05,conversation_speed*.98)")
