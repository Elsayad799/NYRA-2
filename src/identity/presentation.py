from __future__ import annotations
import json

class PresentationEngine:
    """Contextual fictional presentation. One NYRA core, different presentation per context."""
    def __init__(self, db): self.db=db
    def get(self, user_id, chat_id, chat_type):
        rows=self.db.query('SELECT * FROM presentations WHERE user_id=? AND chat_id=?',(user_id,chat_id))
        if rows: return dict(rows[0])
        # Groups are consistently feminine by design; private chats may adapt after interaction.
        presentation='female' if chat_type!='private' else 'adaptive'
        self.db.execute('INSERT OR IGNORE INTO presentations(user_id,chat_id,presentation,style,confidence) VALUES(?,?,?,?,?)',(user_id,chat_id,presentation,'natural',.8))
        return {'user_id':user_id,'chat_id':chat_id,'presentation':presentation,'style':'natural','confidence':.8}
    def set_private(self,user_id,chat_id,presentation):
        if presentation not in ('female','male','neutral','adaptive'): raise ValueError('invalid presentation')
        self.db.execute('INSERT INTO presentations(user_id,chat_id,presentation,style,confidence) VALUES(?,?,?,?,?) ON CONFLICT(user_id,chat_id) DO UPDATE SET presentation=excluded.presentation,confidence=excluded.confidence',(user_id,chat_id,presentation,'natural',.85))
    def prompt_fragment(self,user_id,chat_id,chat_type):
        p=self.get(user_id,chat_id,chat_type)
        if chat_type!='private':
            return 'Presentation in this group: feminine fictional persona. Keep NYRA identity consistent in this group.'
        return f"Private presentation context: {p['presentation']}. This is a fictional persona presentation, not a claim of human identity."
