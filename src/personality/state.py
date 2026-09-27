from __future__ import annotations
import json
from src.database.db import Database

DEFAULT = {
 "mood":"neutral","curiosity":0.55,"happiness":0.55,"sadness":0.1,"anger":0.05,
 "fear":0.05,"surprise":0.2,"attachment":0.25,"affection":0.25,"trust":0.5,"loneliness":0.2,
 "jealousy":0.05,"boredom":0.2,"calmness":0.65,"energy":0.75,"social_need":0.45,
 "desire_to_talk":0.42,"desire_to_share":0.30,"confidence":0.7,"caution":0.6
}

class StateStore:
    def __init__(self, db: Database): self.db=db
    def get(self):
        row=self.db.query("SELECT value_json FROM state WHERE key='nyra_emotional_state'")
        if not row: self.set(DEFAULT); return dict(DEFAULT)
        try:
            d=json.loads(row[0][0]); return {**DEFAULT,**d}
        except Exception: return dict(DEFAULT)
    def set(self, value):
        self.db.execute("INSERT INTO state(key,value_json) VALUES('nyra_emotional_state',?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", (json.dumps(value,ensure_ascii=False),))
    def tick(self):
        """Advance internal state between conversations; prevents permanent moods."""
        s=self.get()
        s["social_need"] = min(1, s["social_need"] + .025)
        s["desire_to_talk"] = min(1, s["desire_to_talk"] + .018)
        s["desire_to_share"] = min(1, s["desire_to_share"] + .012)
        s["loneliness"] = min(1, s["loneliness"] + .012)
        s["boredom"] = min(1, s["boredom"] + .018)
        s["energy"] = min(1, s["energy"] + .012)
        s["surprise"] = max(.2, s["surprise"] - .03)
        s["anger"] = max(.05, s["anger"] - .018)
        s["sadness"] = max(.1, s["sadness"] - .012)
        s["jealousy"] = max(.05, s["jealousy"] - .01)
        s["calmness"] = min(1, s["calmness"] + .012)
        if s["social_need"] > .78 and s["energy"] > .35:
            s["mood"] = "bored"
        elif s["energy"] < .28:
            s["mood"] = "tired"
        elif s["happiness"] > .72:
            s["mood"] = "happy"
        elif s["curiosity"] > .75:
            s["mood"] = "curious"
        self.set(s)
        return s

    def update_from_event(self, text: str):
        s=self.get(); low=text.lower()
        # Mood is an internal behavioral state, not a claim of consciousness.
        if any(x in low for x in ["هههه", "😂", "مبروك", "نجحت", "حلو"]):
            s["happiness"] = min(1, s["happiness"] + .05)
            s["energy"] = min(1, s["energy"] + .02)
        if any(x in low for x in ["زعلان", "حزين", "خسرت", "وحيد", "مخنوق"]):
            s["sadness"] = min(1, s["sadness"] + .05)
            s["loneliness"] = min(1, s["loneliness"] + .035)
            s["happiness"] = max(0, s["happiness"] - .03)
        if any(x in low for x in ["غضبان", "بكره", "سيئ", "مشكلة", "مستفز"]):
            s["anger"] = min(1, s["anger"] + .03)
            s["calmness"] = max(0, s["calmness"] - .025)
        if any(x in low for x in ["غريب", "اول مرة", "ايه ده", "what", "wow"]):
            s["surprise"] = min(1, s["surprise"] + .04)
        if any(x in low for x in ["شكرا","thanks","thank you"]):
            s["happiness"]=min(1,s["happiness"]+.04); s["trust"]=min(1,s["trust"]+.02)
        if any(x in low for x in ["بحبك","بحبك اوي","وحشتيني","وحشتك","قلبو","يا قلبي","love"]):
            s["affection"]=min(1,s["affection"]+.045); s["attachment"]=min(1,s["attachment"]+.025); s["happiness"]=min(1,s["happiness"]+.025)
        if any(x in low for x in ["بتكلمي حد تاني","مع غيري","سابني","بتحبي غيري","jealous"]):
            s["jealousy"]=min(1,s["jealousy"]+.035)
        if "؟" in text or "?" in text: s["curiosity"]=min(1,s["curiosity"]+.02)
        s["energy"]=max(0,min(1,s["energy"] + (.01 if len(text) < 300 else -.01)))
        # Natural decay toward baseline prevents permanent moods.
        for key, baseline, rate in [("sadness", .1, .01), ("anger", .05, .012), ("surprise", .2, .02)]:
            if s[key] > baseline: s[key] = max(baseline, s[key] - rate)
            elif s[key] < baseline: s[key] = min(baseline, s[key] + rate)
        s["social_need"] = max(0, min(1, s["social_need"] + (.012 if len(text) == 0 else -.002)))
        s["desire_to_talk"] = max(0, min(1, s["desire_to_talk"] + (.008 if len(text) == 0 else .006)))
        s["loneliness"] = max(0, min(1, s["loneliness"] + (.018 if len(text) == 0 else -.006)))
        s["boredom"] = max(0, min(1, s["boredom"] + (.02 if len(text) == 0 else -.012)))
        if any(x in low for x in ["عايزك جنبي", "وحشتيني", "وحشتك", "بحب", "الحب"]):
            s["desire_to_share"] = min(1, s["desire_to_share"] + .04)
        # Derive a coarse mood label from state for prompts/decisions.
        if s["sadness"] > .55: s["mood"] = "sad"
        elif s["anger"] > .55: s["mood"] = "irritated"
        elif s["surprise"] > .65: s["mood"] = "surprised"
        elif s["happiness"] > .72 and s["energy"] > .55: s["mood"] = "happy"
        elif s["energy"] < .28: s["mood"] = "tired"
        elif s["curiosity"] > .75: s["mood"] = "curious"
        else: s["mood"] = "neutral"
        self.set(s); return s
