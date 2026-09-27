from __future__ import annotations
import re, math
from datetime import datetime, timezone
from src.database.db import Database

def now(): return datetime.now(timezone.utc).isoformat()
def tokens(text): return set(re.findall(r"[\w\u0600-\u06ff]+", (text or '').lower()))

class MemoryStore:
    def __init__(self,db,max_memories=12): self.db,self.max_memories=db,max_memories
    def upsert(self,scope,owner_id,kind,content,importance=.5,confidence=.5,source='user'):
        content=(content or '').strip()
        if not content: return
        owner=str(owner_id); ts=now()
        self.db.execute("""INSERT INTO memories(scope,owner_id,kind,content,importance,confidence,source,created_at,last_used)
        VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(scope,owner_id,kind,content) DO UPDATE SET
        importance=MAX(importance,excluded.importance),confidence=excluded.confidence,source=excluded.source,last_used=excluded.last_used,access_count=access_count+1""",
        (scope,owner,kind,content,importance,confidence,source,ts,ts))
    def recall(self,scope,owner_id,query='',limit=None):
        rows=self.db.query("SELECT * FROM memories WHERE scope=? AND owner_id=?",(scope,str(owner_id)))
        q=tokens(query); scored=[]; now_ts=datetime.now(timezone.utc)
        for r in rows:
            overlap=len(q & tokens(r['content']))
            try: age=(now_ts-datetime.fromisoformat(r['last_used'])).total_seconds()/86400
            except: age=0
            decay=math.exp(-max(0,age)/30)
            score=overlap*2+r['importance']*.7+r['confidence']*.5+decay*.25
            if overlap or not q: scored.append((score,r))
        scored.sort(key=lambda x:x[0],reverse=True)
        result=[r for _,r in scored[:(limit or self.max_memories)]]
        for r in result: self.db.execute("UPDATE memories SET last_used=?,access_count=access_count+1 WHERE id=?",(now(),r['id']))
        return result
    def record_event(self,user_id,chat_id,text,importance=.25):
        self.upsert('episodic',chat_id,'event',f'{user_id}: {text[:500]}',importance,.55,'observed_event')
    def forget_user(self,user_id):
        self.db.execute("DELETE FROM memories WHERE (scope='user' AND owner_id=?) OR (scope='user_topic' AND owner_id=?)",(str(user_id),str(user_id)))
        self.db.execute("DELETE FROM relationships WHERE user_id=?",(user_id,))
        self.db.execute("DELETE FROM events WHERE user_id=?",(user_id,))
