from __future__ import annotations
class ContextBuilder:
    def __init__(self,db,memory,settings,state=None,goals=None,active_recall=None,presentations=None,media_memory=None):
        self.db,self.memory,self.s,self.state,self.goals=db,memory,settings,state,goals
        self.active_recall=active_recall; self.presentations=presentations; self.media_memory=media_memory
    def build(self,e):
        hist=self.db.query("SELECT event_type,user_id,text,created_at FROM events WHERE chat_id=? ORDER BY id DESC LIMIT ?",(e.chat_id,self.s.max_history))[::-1]
        rel=self.db.query("SELECT * FROM relationships WHERE user_id=? AND chat_id=?",(e.user_id,e.chat_id))
        rel=dict(rel[0]) if rel else {"trust":.2,"familiarity":0,"interaction_count":0,"style":None}
        usermem=self.memory.recall('user',e.user_id,e.text,self.s.max_memories)
        groupmem=self.memory.recall('group',e.chat_id,e.text,max(5,self.s.max_memories//2))
        lines=[f"Chat type: {e.chat_type}",f"User: {e.user_name} (Telegram ID {e.user_id})",f"Group: {e.chat_title or e.chat_id}",f"Relationship: trust={rel['trust']:.2f}, familiarity={rel['familiarity']:.2f}","Recent conversation:"]
        if self.presentations: lines.append(self.presentations.prompt_fragment(e.user_id,e.chat_id,e.chat_type))
        if e.media_type:
            lines.append(f"Current media: {e.media_type}; metadata={e.media_meta}; caption={e.caption}")
            if isinstance(e.media_meta,dict):
                if e.media_meta.get('vision'):
                    lines.append('Visual understanding (observed, not guaranteed):\n'+str(e.media_meta['vision'])[:5000])
                if e.media_meta.get('ocr'):
                    lines.append('OCR text from image:\n'+str(e.media_meta['ocr'])[:5000])
        for r in hist: lines.append(f"{r['user_id']}: {r['text'] or ''}")
        if self.state: lines.append(f"Internal state: {self.state.get()}")
        if self.goals:
            goals=self.goals.open('group',e.chat_id,3)+self.goals.open('user',e.user_id,3)
            if goals: lines.append('Open goals:\n'+'\n'.join(f"- {g['goal']}" for g in goals))
        if usermem: lines.append('Relevant user memories:\n'+'\n'.join(f"- {r['content']} [{r['confidence']:.2f}]" for r in usermem))
        if groupmem: lines.append('Relevant group memories:\n'+'\n'.join(f"- {r['content']} [{r['confidence']:.2f}]" for r in groupmem))
        claims=self.db.query('SELECT claim,kind,confidence,status FROM learned_claims WHERE subject_id=? AND chat_id=? ORDER BY confidence DESC LIMIT 5',(e.user_id,e.chat_id))
        if claims: lines.append('Learned claims about this user (treat as evidence, not certainty):\n'+'\n'.join(f"- {r['claim']} [{r['status']}; {r['confidence']:.2f}]" for r in claims))
        if self.media_memory:
            medias=self.media_memory.recent(e.chat_id,e.user_id,4)
            if medias: lines.append('Recent media metadata:\n'+'\n'.join(f"- {r['media_type']}: {r['caption'] or r['metadata_json'][:220]}" for r in medias))
        if self.active_recall:
            recalls=self.active_recall.find(e.chat_id,e.user_id,e.text,4)
            if recalls:
                lines.append('Active recalled memories (use only if genuinely relevant):\n'+'\n'.join(f"- {r['content']} [score={r['recall_score']:.2f}, confidence={r['confidence']:.2f}]" for r in recalls))
        return '\n'.join(lines),hist,rel
