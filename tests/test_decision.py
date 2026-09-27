from src.decisions.engagement import EngagementDecision
from src.agent.events import Event
class S:
    global_cooldown=0; group_cooldown=0; user_cooldown=0

def test_private_always_engages():
    d=EngagementDecision(S()); ok,reason=d.decide(Event(1,2,3,'private','hello')); assert ok and reason=='private_chat'
