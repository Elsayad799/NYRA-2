from __future__ import annotations
from datetime import datetime, timezone
from src.database.db import Database

def now(): return datetime.now(timezone.utc).isoformat()

class GoalStore:
    """Persistent goals. Goals guide behavior; they never override social safety/cooldowns."""
    def __init__(self, db: Database):
        self.db=db
        # v9 migration: progress is kept separately so old DBs remain usable.
        self.db.execute("""CREATE TABLE IF NOT EXISTS goal_progress (
            goal_id INTEGER PRIMARY KEY, progress REAL NOT NULL DEFAULT 0,
            evidence TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL
        )""")

    def add(self, scope, owner_id, goal, priority=.5):
        goal=(goal or '').strip()
        if not goal: return None
        self.db.execute("INSERT INTO goals(scope,owner_id,goal,status,priority,created_at,updated_at) VALUES(?,?,?,'open',?,?,?)",
                        (scope,str(owner_id),goal,float(max(0,min(1,priority))),now(),now()))
        row=self.db.query("SELECT * FROM goals ORDER BY id DESC LIMIT 1")[0]
        self.db.execute("INSERT OR IGNORE INTO goal_progress(goal_id,progress,evidence,updated_at) VALUES(?,?,?,?)",
                        (row['id'],0.0,'',now()))
        return row

    def open(self, scope=None, owner_id=None, limit=10):
        sql="SELECT g.*,COALESCE(p.progress,0) progress FROM goals g LEFT JOIN goal_progress p ON p.goal_id=g.id WHERE g.status='open'"; params=[]
        if scope is not None: sql += " AND g.scope=?"; params.append(scope)
        if owner_id is not None: sql += " AND g.owner_id=?"; params.append(str(owner_id))
        sql += " ORDER BY g.priority DESC, g.updated_at DESC LIMIT ?"; params.append(limit)
        return self.db.query(sql,tuple(params))

    def best_for_group(self, chat_id):
        rows=self.open('group',chat_id,5)
        return dict(rows[0]) if rows else None

    def best_for_user(self, user_id):
        rows=self.open('user',user_id,5)
        return dict(rows[0]) if rows else None

    def progress(self, goal_id, delta, evidence=''):
        rows=self.db.query("SELECT progress FROM goal_progress WHERE goal_id=?",(goal_id,))
        current=float(rows[0]['progress']) if rows else 0.0
        value=max(0.0,min(1.0,current+float(delta)))
        self.db.execute("INSERT INTO goal_progress(goal_id,progress,evidence,updated_at) VALUES(?,?,?,?) ON CONFLICT(goal_id) DO UPDATE SET progress=excluded.progress,evidence=excluded.evidence,updated_at=excluded.updated_at",
                        (goal_id,value,(evidence or '')[:500],now()))
        if value>=1.0:
            self.db.execute("UPDATE goals SET status='done',updated_at=? WHERE id=?",(now(),goal_id))
        else:
            self.db.execute("UPDATE goals SET updated_at=? WHERE id=?",(now(),goal_id))
        return value

    def close(self, goal_id):
        self.db.execute("UPDATE goals SET status='done',updated_at=? WHERE id=?",(now(),goal_id))
