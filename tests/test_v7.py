import time
from types import SimpleNamespace
from src.social.brain import SocialBrain

class DB:
    def __init__(self): self.data={}
    def execute(self,*a): return None
    def query(self,sql,params=()):
        if "social_groups" in sql: return []
        return []

class S:
    global_cooldown=0; group_cooldown=1; user_cooldown=1

def test_proactive_requires_reason():
    b=SocialBrain(DB(),S())
    b.group=lambda cid: {"activity":.1,"conversation_speed":.1,"engagement":.4,"topic":"","last_bot_message_at":None,"last_message_at":"x"}
    assert b.proactive_decision(1,{"mood":"neutral","energy":.8,"curiosity":.3,"social_need":.3})["action"] == "ignore"

def test_proactive_topic_can_start():
    b=SocialBrain(DB(),S())
    b.group=lambda cid: {"activity":.5,"conversation_speed":.4,"engagement":.4,"topic":"Minecraft","last_bot_message_at":None,"last_message_at":"x"}
    class A:
        def get(self,cid): return {"topic":"Minecraft","focus":.8}
    b.attention=A()
    d=b.proactive_decision(1,{"mood":"curious","energy":.8,"curiosity":.8,"social_need":.7})
    assert d["action"] == "start" and d["topic"] == "Minecraft"
