from __future__ import annotations
import math, re
from datetime import datetime, timezone


def _tokens(text: str):
    return set(re.findall(r"[\w\u0600-\u06ff]+", (text or "").lower()))


class ActiveRecall:
    """Finds older memories that are meaningfully related to the current event.

    It never creates a memory merely because a word matches. A recall is only
    returned when there is measurable lexical overlap or a stored topic match.
    """
    def __init__(self, db, memory):
        self.db = db
        self.memory = memory

    def find(self, chat_id, user_id, text, limit=4):
        q = _tokens(text)
        if not q:
            return []
        candidates = []
        for scope, owner in (("group", chat_id), ("user", user_id), ("episodic", chat_id)):
            for row in self.memory.recall(scope, owner, text, limit=20):
                content_tokens = _tokens(row["content"])
                overlap = len(q & content_tokens)
                if overlap == 0:
                    continue
                ratio = overlap / max(1, min(len(q), len(content_tokens)))
                age_days = 0.0
                try:
                    age_days = max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(row["created_at"])).total_seconds() / 86400)
                except Exception:
                    pass
                recency = math.exp(-age_days / 45.0)
                score = overlap * .55 + ratio * .9 + float(row["importance"]) * .35 + float(row["confidence"]) * .25 + recency * .15
                candidates.append((score, row))
        candidates.sort(key=lambda x: x[0], reverse=True)
        seen = set()
        out = []
        for score, row in candidates:
            key = (row["scope"], row["owner_id"], row["kind"], row["content"])
            if key in seen:
                continue
            seen.add(key)
            item = dict(row)
            item["recall_score"] = round(score, 3)
            out.append(item)
            if len(out) >= limit:
                break
        return out
