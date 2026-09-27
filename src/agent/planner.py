from __future__ import annotations
import json
import re
import time
from typing import Any

ALLOWED_ACTIONS = {"observe", "reflect", "send_message"}

class PlanStore:
    """Persistent plans and validated steps. Execution is limited to allowlisted actions."""
    def __init__(self, db):
        self.db = db
        self.db.execute("""CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL, chat_id INTEGER NOT NULL,
            title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
            created_at REAL NOT NULL, updated_at REAL NOT NULL,
            failure_count INTEGER NOT NULL DEFAULT 0
        )""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS plan_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL, step_no INTEGER NOT NULL,
            action_type TEXT NOT NULL, objective TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0, result TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL, updated_at REAL NOT NULL,
            UNIQUE(plan_id, step_no)
        )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_plans_goal ON plans(goal_id,status)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_plan_steps_plan ON plan_steps(plan_id,step_no)")

    def create(self, goal_id: int, chat_id: int, title: str, steps: list[dict[str, str]]):
        valid=[]
        for i, step in enumerate(steps, 1):
            action=str(step.get("action_type", "")).strip().lower()
            objective=str(step.get("objective", "")).strip()
            if action not in ALLOWED_ACTIONS or not objective or len(objective)>500:
                continue
            valid.append((i, action, objective))
        if not valid:
            return None
        now=time.time()
        cur=self.db.execute("INSERT INTO plans(goal_id,chat_id,title,created_at,updated_at) VALUES(?,?,?,?,?)",
                            (goal_id,chat_id,(title or "Goal plan")[:200],now,now))
        plan_id=cur.lastrowid
        for no,action,obj in valid:
            self.db.execute("INSERT INTO plan_steps(plan_id,step_no,action_type,objective,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                            (plan_id,no,action,obj,now,now))
        return self.get(plan_id)

    def get(self, plan_id):
        rows=self.db.query("SELECT * FROM plans WHERE id=?",(plan_id,))
        return dict(rows[0]) if rows else None

    def active_for_goal(self, goal_id):
        rows=self.db.query("SELECT * FROM plans WHERE goal_id=? AND status='active' ORDER BY id DESC LIMIT 1",(goal_id,))
        return dict(rows[0]) if rows else None

    def next_step(self, plan_id):
        rows=self.db.query("SELECT * FROM plan_steps WHERE plan_id=? AND status='pending' ORDER BY step_no LIMIT 1",(plan_id,))
        return dict(rows[0]) if rows else None

    def complete_step(self, step_id, result=""):
        rows=self.db.query("SELECT * FROM plan_steps WHERE id=?",(step_id,))
        if not rows:return None
        step=dict(rows[0]); now=time.time()
        self.db.execute("UPDATE plan_steps SET status='done',result=?,updated_at=? WHERE id=?",((result or '')[:1000],now,step_id))
        pending=self.db.query("SELECT id FROM plan_steps WHERE plan_id=? AND status='pending'",(step['plan_id'],))
        if not pending:
            self.db.execute("UPDATE plans SET status='done',updated_at=? WHERE id=?",(now,step['plan_id']))
        else:
            self.db.execute("UPDATE plans SET updated_at=? WHERE id=?",(now,step['plan_id']))
        return step

    def fail_step(self, step_id, error=""):
        rows=self.db.query("SELECT * FROM plan_steps WHERE id=?",(step_id,))
        if not rows:return None
        step=dict(rows[0]); attempts=int(step['attempts'])+1; now=time.time()
        if attempts >= 2:
            self.db.execute("UPDATE plan_steps SET status='failed',attempts=?,result=?,updated_at=? WHERE id=?",(attempts,(error or '')[:1000],now,step_id))
            self.db.execute("UPDATE plans SET failure_count=failure_count+1,updated_at=? WHERE id=?",(now,step['plan_id']))
        else:
            self.db.execute("UPDATE plan_steps SET attempts=?,result=?,updated_at=? WHERE id=?",(attempts,(error or '')[:1000],now,step_id))
        return dict(self.db.query("SELECT * FROM plan_steps WHERE id=?",(step_id,))[0])

    def list_for_chat(self, chat_id, limit=8):
        return self.db.query("SELECT * FROM plans WHERE chat_id=? ORDER BY updated_at DESC LIMIT ?",(chat_id,limit))

class PlanningEngine:
    """Uses the configured LLM to propose a small validated plan; never executes arbitrary code."""
    def __init__(self, db, provider, store=None):
        self.db=db; self.provider=provider; self.store=store or PlanStore(db)

    def ensure_plan(self, goal, chat_id, topic="", recent=""):
        goal_id=int(goal["id"])
        existing=self.store.active_for_goal(goal_id)
        if existing:return existing
        system=("Create a short execution plan for a Telegram AI agent. "
                "Return JSON only: {\"title\": string, \"steps\": [{\"action_type\": \"observe\"|\"reflect\"|\"send_message\", \"objective\": string}]}. "
                "Use 2-5 steps. No shell, Python, HTTP, file, admin, account, or arbitrary tool actions. "
                "The plan must be achievable from group conversation context. Do not invent facts.")
        prompt=(f"Goal: {goal['goal']}\nTopic: {topic or 'none'}\nRecent messages:\n{recent or 'none'}")
        try:
            result=self.provider.generate([{"role":"user","content":prompt}],system,max_tokens=500)
            raw=result.text.strip()
            raw=re.sub(r"^```(?:json)?|```$", "", raw, flags=re.I).strip()
            data=json.loads(raw)
            if not isinstance(data,dict):return None
            return self.store.create(goal_id,chat_id,str(data.get("title") or "Goal plan"),data.get("steps") or [])
        except Exception:
            return None

    def execution_context(self, plan, step, goal, topic="") -> str:
        return (f"Plan #{plan['id']} step {step['step_no']}: {step['objective']}\n"
                f"Goal: {goal['goal']}\nTopic: {topic or 'current conversation'}")
