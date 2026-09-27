from __future__ import annotations
import json
import logging
import re
import time
from pathlib import Path

log=logging.getLogger('VisualIdentity')

DEFAULT_VISUAL_DNA = (
    "NYRA is a fictional recurring young-adult woman with a distinctive, consistent face: "
    "soft oval face, expressive almond-shaped dark eyes, naturally arched brows, small straight nose, "
    "defined lips, long dark slightly wavy hair, warm olive-neutral skin, subtle natural makeup, "
    "a calm intelligent gaze with a playful edge. Her appearance is elegant, modern and cinematic, "
    "photorealistic real-life human photography with natural skin pores and texture, fine facial detail, "
    "realistic individual hair strands, natural eyes, realistic hands and anatomy, physically accurate lighting, "
    "authentic professional camera optics and natural depth of field. She is a fictional character, "
    "not based on a real person or celebrity. Keep her facial identity stable across generations. "
    "Never depict NYRA as anime, cartoon, illustration, painting, 3D render, CGI, doll-like, plastic, "
    "game character, or stylized artwork."
)

class VisualIdentityStore:
    """One shared NYRA visual identity plus per-user image history."""
    def __init__(self, db, providers=None):
        self.db=db; self.providers=providers
        self.data_dir = Path(getattr(db, 'path', '.')).parent / 'nyra_visual'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure()

    def _ensure(self):
        self.db.execute("""CREATE TABLE IF NOT EXISTS nyra_visual_identity (
            id INTEGER PRIMARY KEY CHECK(id=1), base_prompt TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS nyra_image_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL, prompt TEXT NOT NULL, scene TEXT,
            mood TEXT, image_url TEXT, created_at TEXT NOT NULL
        )""")

    def get(self):
        rows=self.db.query('SELECT * FROM nyra_visual_identity WHERE id=1')
        return dict(rows[0]) if rows else None

    def ensure(self):
        row=self.get()
        if row and row.get('base_prompt'):
            self._write_shared_file(row['base_prompt'], row.get('updated_at') or time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime()))
            return row['base_prompt']
        prompt=DEFAULT_VISUAL_DNA
        if self.providers:
            try:
                result=self.providers.generate(
                    [{"role":"user","content":"Create NYRA's permanent visual DNA prompt. Return only one detailed English image prompt. Preserve a fictional recurring character, stable face/hair/skin/features, and explicitly avoid real-person or celebrity likeness."}],
                    "You define a fictional character's visual identity. Do not use a real person's likeness. Output only the reusable base visual description.",
                    max_tokens=500,
                )
                candidate=re.sub(r'\s+',' ',result.text).strip()
                if len(candidate)>=180:
                    prompt=candidate[:5000]
            except Exception:
                log.exception('could not generate visual DNA; using deterministic default')
        now=time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime())
        self.db.execute("INSERT OR REPLACE INTO nyra_visual_identity(id,base_prompt,version,created_at,updated_at) VALUES(1,?,?,COALESCE((SELECT created_at FROM nyra_visual_identity WHERE id=1),?),?)",(prompt,1,now,now))
        self._write_shared_file(prompt, now)
        return prompt

    def _write_shared_file(self, prompt, updated_at):
        try:
            (self.data_dir / 'nyra_visual_dna.json').write_text(
                json.dumps({'character':'NYRA','base_prompt':prompt,'updated_at':updated_at},
                           ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            log.exception('failed to persist visual DNA file')

    def _write_user_file(self, user_id, prompt, scene, mood, image_url=None):
        try:
            path=self.data_dir / f'user_{int(user_id)}.json'
            current={}
            if path.exists():
                current=json.loads(path.read_text(encoding='utf-8'))
            current.update({'user_id':int(user_id),'base_prompt':self.ensure(),'last_scene':scene,
                             'last_mood':mood,'last_image_url':image_url,'updated_at':time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime())})
            path.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        except Exception:
            log.exception('failed to persist per-user visual file')

    def build_prompt(self,user_id,chat_id,state,request=None,scene=None):
        base=self.ensure()
        mood=state.get('mood','neutral') if isinstance(state,dict) else 'neutral'
        additions=[]
        if scene: additions.append(str(scene))
        if request: additions.append(str(request))
        additions.append(f"current emotional presentation: {mood}")
        additions.append("Photorealistic real-life human photography is mandatory: natural skin pores and texture, realistic individual hair strands, natural eyes, realistic hands and anatomy, physically accurate lighting, authentic camera optics and depth of field. No anime, cartoon, illustration, painting, 3D render, CGI, doll-like or plastic appearance. Keep the same face, hair, skin tone, facial proportions and identity as the permanent NYRA visual DNA. Change only scene, clothing, pose, expression, lighting and camera direction as requested.")
        # Keep the same shared DNA in a per-user file so continuity can be inspected/recovered.
        self._write_user_file(user_id, base, scene or request or 'self-portrait', mood)
        return base + "\nDynamic scene: " + ", ".join(additions)

    def remember(self,user_id,chat_id,prompt,scene,mood,image_url):
        self.db.execute("INSERT INTO nyra_image_history(user_id,chat_id,prompt,scene,mood,image_url,created_at) VALUES(?,?,?,?,?,?,datetime('now'))",(user_id,chat_id,prompt,scene,mood,image_url))
        self._write_user_file(user_id, prompt, scene, mood, image_url)

    def recent(self,user_id,limit=5):
        return [dict(r) for r in self.db.query('SELECT * FROM nyra_image_history WHERE user_id=? ORDER BY id DESC LIMIT ?', (user_id,int(limit)))]
