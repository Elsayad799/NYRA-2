from src.social.brain import SocialBrain
from src.agent.events import Event
from src.database.db import Database

class S:
    global_cooldown=0; group_cooldown=0; user_cooldown=0

def test_directed_group_reply(tmp_path):
    db=Database(str(tmp_path/'t.db')); brain=SocialBrain(db,S())
    e=Event(1,2,3,'supergroup','NYRA شايفة ايه؟',is_mention=True)
    r=brain.choose(e,{"familiarity":.2},{"mood":"neutral","energy":.8,"social_need":.5,"curiosity":.6,"happiness":.5,"sadness":.1,"anger":.05})
    assert r["action"] == "reply" and r["target"] == "user"

def test_short_group_message_is_ignored(tmp_path):
    db=Database(str(tmp_path/'t.db')); brain=SocialBrain(db,S())
    e=Event(1,2,4,'supergroup','ok')
    r=brain.choose(e,{}, {"mood":"neutral","energy":.8,"social_need":.5,"curiosity":.6,"happiness":.5,"sadness":.1,"anger":.05})
    assert r["action"] == "ignore"


def test_bored_state_increases_social_need(tmp_path):
    from src.personality.state import StateStore
    db=Database(str(tmp_path/'state.db')); state=StateStore(db)
    for _ in range(15): state.tick()
    assert state.get()["social_need"] > .45
    assert state.get()["mood"] in {"bored", "neutral", "curious", "happy"}
