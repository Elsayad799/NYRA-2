from __future__ import annotations

class RelationshipEngine:
    def __init__(self, db):
        self.db = db

    def get(self, user_id, chat_id):
        rows = self.db.query('SELECT * FROM relationships WHERE user_id=? AND chat_id=?', (user_id, chat_id))
        return dict(rows[0]) if rows else {'user_id':user_id,'chat_id':chat_id,'trust':.2,'familiarity':0.0,'interaction_count':0,'style':None}

    def observe(self, event):
        if event.user_id is None:
            return
        # Familiarity grows with interaction; trust changes only on simple observable signals.
        low = (event.text or '').lower()
        delta_trust = .008 if any(x in low for x in ('شكرا','thanks','thank you')) else 0.0
        delta_trust -= .004 if any(x in low for x in ('كذب','غبي','اكره','بكره')) else 0.0
        self.db.execute("""INSERT INTO relationships(user_id,chat_id,interaction_count,familiarity,trust)
            VALUES(?,?,1,.015,MAX(.2,MIN(1,.2+?)))
            ON CONFLICT(user_id,chat_id) DO UPDATE SET interaction_count=interaction_count+1,
            familiarity=MIN(1,familiarity+.012),trust=MAX(0,MIN(1,trust+?))""",
            (event.user_id,event.chat_id,delta_trust,delta_trust))
