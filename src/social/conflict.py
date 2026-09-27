from __future__ import annotations
import json
from datetime import datetime, timezone

class ConflictEngine:
    """Persistent, per-user conflict/frustration/forgiveness state.

    This is behavioral state for the agent. It does not infer sensitive traits.
    """
    def __init__(self, db):
        self.db = db
        self.db.execute("""CREATE TABLE IF NOT EXISTS conflicts (
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            annoyance REAL NOT NULL DEFAULT 0.0,
            frustration REAL NOT NULL DEFAULT 0.0,
            anger REAL NOT NULL DEFAULT 0.0,
            trust REAL NOT NULL DEFAULT 0.2,
            forgiveness REAL NOT NULL DEFAULT 0.5,
            forgiveness_status TEXT NOT NULL DEFAULT 'none',
            last_reason TEXT,
            incident_count INTEGER NOT NULL DEFAULT 0,
            positive_streak INTEGER NOT NULL DEFAULT 0,
            last_event_at TEXT,
            PRIMARY KEY(user_id, chat_id)
        )""")

    def get(self, user_id: int, chat_id: int) -> dict:
        rows = self.db.query("SELECT * FROM conflicts WHERE user_id=? AND chat_id=?", (user_id, chat_id))
        if rows:
            return dict(rows[0])
        return {
            'user_id': user_id, 'chat_id': chat_id, 'annoyance': 0.0,
            'frustration': 0.0, 'anger': 0.0, 'trust': 0.2,
            'forgiveness': 0.5, 'forgiveness_status': 'none',
            'last_reason': None, 'incident_count': 0, 'positive_streak': 0,
            'last_event_at': None,
        }

    def _upsert(self, s: dict):
        self.db.execute("""INSERT INTO conflicts
            (user_id,chat_id,annoyance,frustration,anger,trust,forgiveness,
             forgiveness_status,last_reason,incident_count,positive_streak,last_event_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id,chat_id) DO UPDATE SET
             annoyance=excluded.annoyance, frustration=excluded.frustration,
             anger=excluded.anger, trust=excluded.trust, forgiveness=excluded.forgiveness,
             forgiveness_status=excluded.forgiveness_status, last_reason=excluded.last_reason,
             incident_count=excluded.incident_count, positive_streak=excluded.positive_streak,
             last_event_at=excluded.last_event_at""",
            (s['user_id'],s['chat_id'],s['annoyance'],s['frustration'],s['anger'],s['trust'],
             s['forgiveness'],s['forgiveness_status'],s['last_reason'],s['incident_count'],
             s['positive_streak'],s['last_event_at']))

    @staticmethod
    def _clamp(v): return max(0.0, min(1.0, float(v)))

    def observe(self, user_id: int, chat_id: int, text: str) -> dict:
        s = self.get(user_id, chat_id)
        low = (text or '').lower()
        explicit_apology = any(x in low for x in ('اسف','آسف','سامحني','حقك عليا','حقك عليّ','sorry','my bad','forgive me'))
        hostile = any(x in low for x in ('اخرس','اسكت','غبي','تافه','بكرهك','اكرهك','hate you','shut up'))
        repeated_annoyance = any(x in low for x in ('كل شوية','تاني','مرة تانية','again','stop','بس بقى','بطل'))
        positive = any(x in low for x in ('شكرا','شكراً','معلش','تمام','حاضر','thanks','thank you','you are right'))

        if explicit_apology:
            s['forgiveness'] = self._clamp(s['forgiveness'] + 0.20)
            s['anger'] = self._clamp(s['anger'] - 0.18)
            s['frustration'] = self._clamp(s['frustration'] - 0.12)
            s['positive_streak'] += 1
            s['last_reason'] = 'apology'
        elif hostile:
            s['annoyance'] = self._clamp(s['annoyance'] + 0.10)
            s['frustration'] = self._clamp(s['frustration'] + 0.09)
            s['anger'] = self._clamp(s['anger'] + 0.16)
            s['trust'] = self._clamp(s['trust'] - 0.06)
            s['forgiveness'] = self._clamp(s['forgiveness'] - 0.08)
            s['positive_streak'] = 0
            s['incident_count'] += 1
            s['last_reason'] = 'hostile_language'
        elif repeated_annoyance:
            s['annoyance'] = self._clamp(s['annoyance'] + 0.07)
            s['frustration'] = self._clamp(s['frustration'] + 0.10)
            s['anger'] = self._clamp(s['anger'] + 0.03)
            s['positive_streak'] = 0
            s['incident_count'] += 1
            s['last_reason'] = 'repeated_annoyance'
        elif positive:
            s['annoyance'] = self._clamp(s['annoyance'] - 0.05)
            s['frustration'] = self._clamp(s['frustration'] - 0.06)
            s['anger'] = self._clamp(s['anger'] - 0.04)
            s['trust'] = self._clamp(s['trust'] + 0.03)
            s['forgiveness'] = self._clamp(s['forgiveness'] + 0.04)
            s['positive_streak'] += 1
            s['last_reason'] = 'positive_interaction'
        else:
            # Ordinary interaction cools conflict slowly but does not erase history.
            s['annoyance'] = self._clamp(s['annoyance'] - 0.012)
            s['frustration'] = self._clamp(s['frustration'] - 0.010)
            s['anger'] = self._clamp(s['anger'] - 0.008)

        if s['anger'] >= 0.65:
            s['forgiveness_status'] = 'not_ready'
        elif s['forgiveness'] >= 0.68 and s['positive_streak'] >= 2:
            s['forgiveness_status'] = 'forgiven'
        elif s['forgiveness'] >= 0.55 and s['positive_streak'] >= 1:
            s['forgiveness_status'] = 'partial'
        elif s['incident_count']:
            s['forgiveness_status'] = 'pending'
        else:
            s['forgiveness_status'] = 'none'
        s['last_event_at'] = datetime.now(timezone.utc).isoformat()
        self._upsert(s)
        return s

    def behavior_guidance(self, user_id: int, chat_id: int) -> str:
        s = self.get(user_id, chat_id)
        if s['anger'] >= .65:
            return 'high_anger: be firm and concise; set boundaries; do not insult or threaten.'
        if s['frustration'] >= .65:
            return 'high_frustration: keep replies shorter, reduce engagement, and avoid escalating.'
        if s['annoyance'] >= .55:
            return 'annoyed: prefer concise replies and optional distance from the interaction.'
        if s['forgiveness_status'] == 'partial':
            return 'partial_forgiveness: normal conversation is possible, but trust should recover gradually.'
        if s['forgiveness_status'] == 'forgiven':
            return 'forgiven: return toward normal interaction; do not erase historical facts.'
        return 'normal_conflict_state'
