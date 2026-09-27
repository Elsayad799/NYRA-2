from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone

class MediaMemory:
    """Stores metadata only. Telegram remains the media store."""
    def __init__(self, db): self.db = db
    def remember(self, *, chat_id, user_id, file_id, media_type, caption='', unique_id='', mime_type='', metadata=None):
        meta = metadata or {}
        self.db.execute("""INSERT INTO media_memories(chat_id,user_id,file_id,media_type,caption,unique_id,mime_type,metadata_json,created_at)
        VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET caption=excluded.caption,metadata_json=excluded.metadata_json""",
        (chat_id,user_id,file_id,media_type,caption or '',unique_id or '',mime_type or '',json.dumps(meta,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))
    def recent(self, chat_id, user_id=None, limit=8):
        if user_id is None:
            return self.db.query('SELECT * FROM media_memories WHERE chat_id=? ORDER BY id DESC LIMIT ?', (chat_id,limit))
        return self.db.query('SELECT * FROM media_memories WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT ?', (chat_id,user_id,limit))
    @staticmethod
    def stable_media_key(file_unique_id: str) -> str:
        return hashlib.sha256((file_unique_id or '').encode()).hexdigest()[:16]
