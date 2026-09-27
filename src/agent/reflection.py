from __future__ import annotations
from src.memory.store import MemoryStore
from src.database.db import Database
from src.agent.goals import GoalStore

class ReflectionEngine:
    def __init__(self,db:Database,memory:MemoryStore):
        self.db,self.memory=db,memory; self.goals=GoalStore(db)
    def reflect(self, chat_id:int, summary:str, confidence=.55):
        summary=(summary or '').strip()
        if not summary: return
        self.memory.upsert('group',chat_id,'reflection',summary[:700],.45,confidence,'reflection_summary')
    def recent_unresolved(self, limit=5): return self.goals.open(limit=limit)
