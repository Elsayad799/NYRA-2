from __future__ import annotations
import time

class OutcomeLearner:
    """Learns from observable conversation outcomes, not imagined feelings."""
    def __init__(self, db):
        self.db = db
        self.db.execute("""CREATE TABLE IF NOT EXISTS action_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
            action_type TEXT NOT NULL, reason TEXT, topic TEXT, target_user_id INTEGER,
            action_text TEXT, goal_id INTEGER, created_at REAL NOT NULL, outcome TEXT NOT NULL DEFAULT 'pending',
            reward REAL NOT NULL DEFAULT 0, evidence TEXT, resolved_at REAL
        )""")
        try: self.db.execute("ALTER TABLE action_outcomes ADD COLUMN goal_id INTEGER")
        except Exception: pass
        self.db.execute("""CREATE TABLE IF NOT EXISTS learned_policy (
            key TEXT PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 0,
            reward_sum REAL NOT NULL DEFAULT 0, confidence REAL NOT NULL DEFAULT 0.2,
            updated_at REAL NOT NULL
        )""")

    def record_action(self, chat_id, action_type, reason='', topic='', target_user_id=None, text='', goal_id=None):
        cur = self.db.execute("INSERT INTO action_outcomes(chat_id,action_type,reason,topic,target_user_id,action_text,goal_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (chat_id, action_type, reason, topic, target_user_id, text, goal_id, time.time()))
        return cur.lastrowid

    def observe_message(self, chat_id, user_id, text):
        """Resolve the newest pending autonomous action when a human responds."""
        rows = self.db.query("SELECT * FROM action_outcomes WHERE chat_id=? AND outcome='pending' ORDER BY id DESC LIMIT 1", (chat_id,))
        if not rows: return None
        row = dict(rows[0])
        age = time.time() - float(row['created_at'])
        if age > 900: return None
        reward = 0.75 if row.get('target_user_id') in (None, 0, user_id) else 0.55
        return self.resolve(row['id'], 'response', reward, 'A human message followed the action')

    def resolve_silence(self, max_age=900):
        cutoff=time.time()-max_age
        rows=self.db.query("SELECT * FROM action_outcomes WHERE outcome='pending' AND created_at<?", (cutoff,))
        for row in rows:
            self.resolve(row['id'], 'silence', -0.10, 'No observable response within the observation window')

    def resolve(self, action_id, outcome, reward, evidence):
        rows=self.db.query("SELECT * FROM action_outcomes WHERE id=?", (action_id,))
        if not rows:return None
        row=dict(rows[0])
        self.db.execute("UPDATE action_outcomes SET outcome=?,reward=?,evidence=?,resolved_at=? WHERE id=?", (outcome,reward,evidence,time.time(),action_id))
        key=f"{row['action_type']}:{row.get('reason') or 'unknown'}"
        old=self.db.query("SELECT * FROM learned_policy WHERE key=?",(key,))
        if old:
            o=dict(old[0]); attempts=o['attempts']+1; total=o['reward_sum']+reward
        else: attempts=1; total=reward
        confidence=min(1.0,0.2+0.08*attempts)
        self.db.execute("INSERT INTO learned_policy(key,attempts,reward_sum,confidence,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET attempts=excluded.attempts,reward_sum=excluded.reward_sum,confidence=excluded.confidence,updated_at=excluded.updated_at",(key,attempts,total,confidence,time.time()))
        goal_id=row.get('goal_id')
        if goal_id:
            try:
                from src.agent.goals import GoalStore
                GoalStore(self.db).progress(goal_id, 0.08 if reward > 0 else -0.03, evidence)
            except Exception:
                pass
        return {'action_id':action_id,'key':key,'reward':reward,'outcome':outcome,'confidence':confidence,'goal_id':goal_id}

    def bias(self, action_type, reason):
        key=f"{action_type}:{reason or 'unknown'}"
        rows=self.db.query("SELECT attempts,reward_sum,confidence FROM learned_policy WHERE key=?",(key,))
        if not rows:return 0.0
        r=dict(rows[0]); return max(-0.15,min(0.15,(r['reward_sum']/max(1,r['attempts']))*0.2*r['confidence']))
